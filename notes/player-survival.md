# Player survival systems (scripts)

Part of the DayZ static analysis notes (see `README.md` in this folder for the map). The player survival model: stats, modifiers, environment, injuries, items' temperature, contamination, cooking and soft skills. Sections 6 and 6.1 to 6.15, 6.18 to 6.21. Section numbers are the original ones, so cross-references such as "see 6.10" still resolve.

## 6. Player survival systems (from the scripts) [obs unless noted]

Source: `4_World\Entities\ManBase\PlayerBase.c` (10,144 lines, the largest script file) and `4_World\Classes\{PlayerStats, PlayerModifiers, PlayerNotifiers, PlayerSymptoms, VirtualHud}`, `TransferValues.c`, `PlayerStomach.c`. Numbers below are the shipped defaults in the scripts; servers can override some through the gameplay config (stamina max is read from `CfgGameplayHandler`).

### 6.1 Big picture

The server owns the simulation. A player object is built differently on each side:

| Part | Server | Client |
|---|---|---|
| `PlayerStats` (stat values) | yes | yes |
| `SymptomManager` | yes | yes |
| `VirtualHud` (created on first use) | yes | yes |
| `PlayerStomach`, `NotifiersManager`, `ModifiersManager`, `BleedingSourcesManagerServer`, `Environment`, agent pool, sound manager | **yes** | no |

These objects are created inside an `if (g_Game.IsServer())` block in the `PlayerBase` constructor. The client never runs modifiers, notifiers, the stomach or bleeding, so it cannot compute its own hunger, health regeneration or disease state. It only receives results.

Data flow per player:
`engine damage zones (Health, Blood, Shock)` and `PlayerStats` are written by **modifiers**; **notifiers** read them and compute HUD indicators; **symptoms** play animations and effects. Everything the owning client needs is pushed by RPC; what other players see goes through net-synced variables.

### 6.2 Tick model

- `MissionServer.OnUpdate` calls `TickScheduler`, which ticks **5 players per call** (`SCHEDULER_PLAYERS_PER_TICK`), cycling round-robin through the player list. With many players, each one is ticked less often.
- `PlayerBase.OnTick` computes elapsed time from the game clock (first tick uses 0) and calls `OnScheduledTick(delta)`. That, in order: ticks all modifiers, ticks notifiers, ticks `TransferValues`, ticks the virtual HUD, ticks bleeding, updates the environment, and ticks the thermal-bias handler. It skips everything for dead or not-yet-selected players. It also unplugs a held electric device if the player moves too far from its power source.
- `MissionGameplay.TickScheduler` calls `OnScheduledTick` on the local player too, but the managers above do not exist there, so on the client this is mostly a no-op [inf].
- Symptoms are ticked from `OnCommandHandlerTick` instead (per animation frame), because they play animations.

### 6.3 Stats (`PlayerStats`)

- `PlayerStat<T>` holds min, max, value and label, clamped on every `Set`. A `PCOHandlerStats` keeps versioned layouts for save compatibility. Layouts v100 and v101 plus `current` are registered, and `current` extends v130. Loading an older save falls back to the closest lower registered version.
- Current stats (v130), in order, with range and default:

| Stat | Range | Default |
|---|---|---|
| HeatComfort | -1 to 1 | 0 |
| Tremor | 0 to 1 | 0 |
| Wet (int) | 0 to 1 | 0 |
| Energy | 0 to 5000 | 600 |
| Water | 0 to 5000 | 600 |
| Diet | 0 to 5000 | 2500 |
| Stamina | 0 to configured max | 100 |
| Specialty | -1 to 1 | 0 |
| BloodType (int) | 0 to 128 | randomly generated |
| Toxicity | 0 to 100 | 0 |
| HeatBuffer | -30 to 30 | 0 (**the only SYNCED stat**) |
| ThermalBias | -1 to 1 | 0 |

- Older layouts also had stomach solid/energy/water stats. They were removed in later versions in favour of the separate `PlayerStomach` class.
- **Health, Blood and Shock are not `PlayerStats`.** They are engine damage-zone values read with `GetHealth("GlobalHealth", "Health" | "Blood" | "Shock")`.
- Level bands (`EStatLevels`: GREAT, HIGH, MEDIUM, LOW, CRITICAL):

| Value | Critical | Low | Normal | High |
|---|---|---|---|---|
| Health | 15 | 30 | 50 | 80 |
| Blood | 3000 | 3500 | 4000 | 4500 |
| Energy | 0 | 300 | 800 | 3500 |
| Water | 0 | 300 | 1000 | 3500 |

  Energy and water max is 5000. Fatal blood level is 2500. The unconscious threshold constant is 25.

### 6.4 Modifiers (`ModifiersManager`, `ModifierBase`)

- **What they are:** one class per physiological rule or condition. 59 are registered in every build plus one extra (`TestDiseaseMdfr`) only in `DEVELOPER` builds. The `eModifiers` enum has 67 IDs, a few of them legacy or unused.
- **Lifecycle:** each modifier has an activate condition, a deactivate condition and an `OnTick`. Inactive modifiers re-check their activation every few seconds (default 3 to 5 s); active ones tick every 1 to 3 s. Many "always on" modifiers (hunger, thirst, health, health regen) simply return true from the activation check and disable the deactivation check. Activation can also be requested by code (for example when a pill is taken). `OnActivate` runs on a fresh trigger, and `OnReconnect` runs when the modifier is restored from a save.
- **Persistence:** active modifiers flagged persistent are saved by ID (plus accumulated time where tracked) in storage version 121.
- **Groups (from the shipped class names):** nutrition (Hunger, Thirst, Stomach, StuffedStomach, VomitStuffed), recovery (HealthRegen, BloodRegen, BoneRegen, Saline, Immunity boost), injury and shock (Bleeding check, Shock, ShockDamage, Unconsciousness, BrokenLegs, BrokenArms), medication (Morphine, PainKillers, Epinephrine, Antibiotics, Charcoal, Chelation, Disinfect), environment (HeatComfort, HeatBuffer, Wet, Burning, Drowning, Fatigue, breath vapour, sandstorm exposure, heat stroke phases 1 to 4, contamination stages 1 to 3, area exposure, mask, flies) and diseases (Cholera, CommonCold, Influenza, Pneumonia, Salmonella, BrainDisease, Poisoning, HeavyMetal phases, Silicosis, WoundInfection stages, HemolyticReaction, HeartAttack, Fever).

**Worked examples:**
- **Hunger and Thirst** (tick every 1 s):
  - Energy (or water) drops by `metabolic_speed x (stat / 5000 + 1) x dt`.
  - Metabolic speed is a basal 0.01 per second, plus 0.1 when walking, 0.3 jogging or 0.6 sprinting. Water uses the same numbers. The stat factor makes a full stat burn up to twice as fast as an empty one.
  - At 300 or below, the "hungry" or "thirsty" sound state is set. If the stomach is not currently digesting that nutrient, the player also loses 0.05 health per second.
- **Health regen** (tick every 3 s):
  - Rate per second is interpolated from 0.005 (blood at the fatal 2500) to 0.03 (full blood).
  - It is added to global health, arms and hands, torso (x0.7 each) and head (x1.4, a deliberate boost).
  - Legs regain a fixed 1 per tick, or 0.18 per tick while broken or splinted.
- **Blood regen:** 0.3 per second, multiplied by a water factor and an energy factor (HIGH or better 1.0, MEDIUM 0.65, LOW or CRITICAL 0). It is doubled while unconscious at critical blood.
- **Bleeding:** each bleeding source drains 20 blood per second, scaled by flow level (0.1, 0.6 or 1.0).
- **Shock:** refills at 5 per second while conscious, or at 1 per second while unconscious. Shock damage over time starts at 3000 blood and grows toward 2500.

### 6.5 Stomach

`PlayerStomach` (storage version 106) holds `StomachItem` entries (amount, food stage, agents, temperature). Each tick digests at 1.7 "digestion points": energy transfers at 3 kcal per second, water at 6 ml per second, solids empty at 7 g or ml per second. It also passes disease agents to the player (with random jitter of plus or minus 50 percent) and feeds toxicity. `DIGESTING_ENERGY` and `DIGESTING_WATER` flags are what the hunger and thirst modifiers check before applying starvation damage.

### 6.6 Notifiers (`NotifiersManager`, `NotifierBase`)

- **Role:** they translate stats into HUD indicators.
- **Set:** 12 are registered (Health, Hunger, Thirst, Stuffed, Sick, Wetness, Warmth, Fever, Blood, Pills, FracturedLeg, InjuredLeg). They run on the server only.
- **Scheduling:** the manager ticks **one notifier per call**, round-robin, each with its own interval (default 1 s). There is also a queue for "immediate" refreshes, processed before the round-robin and still one per call.
- **Tendency:** each notifier keeps a short buffer of its observed value and derives a moving-average delta. That delta maps to a tendency (stable, or increasing/decreasing by low, medium, high) with per-notifier thresholds. Thirst, for example, reads the water stat and applies thresholds of 0.2 and 0.85.
- **Display:** the result is written into `VirtualHud` display elements together with a seriousness level from `EStatLevels`.

### 6.7 Symptoms (`SymptomManager` in `StateManager.c`)

- 22 symptom IDs (19 registered): cough, vomit, blindness, bullet hit, bleeding source, blood loss, sneeze, fever blur, laughter, unconscious, freeze (and rattle), hot, pain (light, heavy), hand shivers, complete deafness, severe HMP, gasp, squint, irritated eyes and faint.
- **Two kinds.** Primary symptoms are animation-driven and queued (maximum 5). A new one can interrupt a queued one if it has higher priority and the current one allows interruption. Only one primary runs at a time. Secondary symptoms (for example the standing blood-loss effect) are not queued by priority.
- **Rules.** Each symptom has a maximum count, can be blocked while the player is unconscious, and may be persistent (saved in storage version 121).
- **Sync.** The server tells the owning client with `RPC_PLAYER_SYMPTOM_ON` / `_OFF` (symptom ID plus a random UID) and `RPC_SYMPTOM_PARAM_SYNC`. The client then spawns the same symptom locally to play the animation and effects. Other players learn only the active primary symptom's ID, through a net-synced variable, and only for symptoms flagged to sync to remotes.

### 6.8 How state reaches clients

| Channel | What | Direction |
|---|---|---|
| Net-synced variables on `PlayerBase` | 32 values registered: persistent flags, lifespan state, blood type visibility, simplified shock, bleeding bits, shakes, breath vapour, **health level** (a coarse pristine-to-ruined band), mixed sound states (hungry, thirsty and similar), corpse state, broken-leg state, **synced modifiers bitmask**, stamina state, active primary symptom, heat-buffer stage, plus unconscious, restrained, in-water and effect-area flags and the current shock value | server to **all** relevant clients |
| `m_SyncedModifiers` | one bit per synced modifier; 9 are defined (wound infection 1 and 2, contamination, contamination 2/3, zone exposure, drowning, fever, eye particles, heat stroke); a comment limits the scheme to 32 | server to all relevant clients |
| `RPC_PLAYER_STAT` | a stat's ID and value, only for SYNCED stats (currently HeatBuffer); float stats skip changes under 0.05 | server to owner |
| `RPC_SYNC_DISPLAY_STATUS` | bit-packed HUD element values; sent only when the packed array changes | server to owner |
| `RPC_DAMAGE_VALUE_SYNC` (`TransferValues`) | normalized **Health** and **Blood** for the owner's UI; checked every 5 s; sent when the change exceeds 1 percent, plus once at start. Blood is normalized between 3000 and max | server to owner |
| `RPC_PLAYER_SYMPTOM_ON/OFF`, `RPC_SYMPTOM_PARAM_SYNC` | symptom start, stop and parameters | server to owner |

- Client handling: `PlayerBase.OnRPC` receives these only in non-server builds. `OnVariablesSynchronized` diffs the modifier bitmask against its previous value (XOR) and fires effects such as drowning when a bit flips, and handles bleeding, corpse state and lifespan visuals.
- Consequences [inf]:
  - Other players never see your exact hunger, energy, water or health numbers. They get coarse bands and flags.
  - The owner's client doesn't hold authoritative values for most stats. The HUD is driven by server-pushed display bits and the health/blood values above.
  - Authoritative state therefore stays on the server.

### 6.9 Transmission agents and the immune system [obs unless noted]

Source: `4_World\Classes\TransmissionAgents\` (11 agent classes, `PlayerAgentPool`), `Plugins\PluginBase\PluginTransmissionAgents.c`, and the modifiers in `PlayerModifiers\Modifiers\{diseases, conditions}`.

**Model.** An *agent* is a pathogen or toxin with its own growth rules. Players, items and stomach contents each carry a bitmask of agents. IDs are single bits (a comment caps the system at 32 and says they must match the config side): CHOLERA 1, INFLUENZA 2, SALMONELLA 4, BRAIN 8, FOOD_POISON 16, CHEMICAL_POISON 32, WOUND_AGENT 64, NERVE_AGENT 128, HEAVYMETAL 256, SILICOSIS 512, EYES_IRRITATION 1024. Only the player's `PlayerAgentPool` (server, saved at storage version 137) keeps a **count per agent**. Each count is capped by that agent's maximum.

**Agent attributes (`AgentBase`).** Invasibility (growth per second), transferability in / out / airborne-out, digestibility (default 0.1, the share of an eaten item's agents that reach the player), maximum count, auto-infection count and probability, potency, die-off speed per second, and a resistance per drug type (antibiotics, chelation).

| Agent | Max | Growth/s | Potency | Die-off/s | Notes from the code |
|---|---|---|---|---|---|
| Cholera | 1000 | 0.15 | HIGH | 0.45 | antibiotics work fully |
| Influenza | 1200 | 0.33 base, but see below | MEDIUM | 0.30 | transferability 1 in / out / air; antibiotics work fully |
| Salmonella | 300 | 0.75 | HIGH | 1.0 | no antibiotic effect |
| Brain (kuru) | 5000 | 1.0 | GREAT | 1.0 | no antibiotic effect |
| Food poison | 800 | share of stomach holding it | GREAT (LOW if none in stomach) | 0, or 0.3 under the threshold, 0.5 with charcoal | digestibility 0.5 |
| Wound | 500 | 0.208 (comment: reaches 250 in 20 min) | GREAT | 1.0 | antibiotics at half strength |
| Chemical | 500 | 0 | CRITICAL | 0.1 (0 in contamination stages 2 and 3) | out 1, air-out 1 |
| Nerve | 500 | 0 | CRITICAL | 0.1 | antibiotics at half strength |
| Heavy metal | 600 | share of stomach holding it (0 in phase 3) | MEDIUM (LOW under chelation, GREAT in phase 3) | 1.0 (x0.3 under chelation, as coded) | chelation fully effective |
| Silicosis | 1000 | 0 | LOW | 0.9 (0 if unconscious) | transferability in 3.5 |
| Eyes irritation | 100 | 0 | LOW | 0.3 (0 if unconscious) | |

**Immunity.** `GetImmunity()` is the plain average of four normalized values: energy / 5000, water / 5000, health / max, blood / max, clamped to 0..1. It maps to a level with `GetStatLevel` using 0.15 / 0.35 / 0.72 / 0.95 (critical / low / normal / high). An active *immunity boost* (vitamins, 300 s) forces the level to GREAT.

**Pool simulation** (`ImmuneSystemMdfr`, always on, every 3 s): processes temporary resistances, tries auto-infection, then grows or shrinks each agent:
- An agent **grows** when `potency <= immunity level`, comparing enum order (GREAT=0 ... CRITICAL=4). So a GREAT-potency agent always grows; a CRITICAL one grows only when immunity is itself critical.
- Growth is skipped while the agent has temporary resistance, or while a drug that stops it is active.
- Otherwise the agent **dies off** by its die-off speed. Counts are clamped to 0..max. Adding agents is ignored during temporary resistance.
- The same modifier toggles the *Sick* notifier while any disease is counted and the *Pills* notifier while any healing is active.

**Drugs and treatment** (all persistent, each counts as a "healing"):
- Antibiotics (300 s) and chelation (300 s) subtract `strength x (1 - agent resistance)` per second from every agent.
- Charcoal removes salmonella and speeds food-poison die-off.
- Disinfection (100 s) removes wound agent over time and, when it expires during wound stage 1, clears it with a large subtraction (10,000).
- After each disease ends, the player gets a temporary resistance to the influenza agent: 900 s after the cold, 300 s after influenza, 600 s after pneumonia.

**How agents get in** (`PluginTransmissionAgents.TransmitAgentsEx`, server). The dose is `(1 - protection) x transferability x dose size`, where protection comes from worn mask, eyewear or headgear.

| Pathway | Effect |
|---|---|
| Eating or drinking | item agents enter the stomach and reach the pool on digestion; the player's agents can also pass to the item |
| Open pond water | adds cholera, plus heavy metal where polluted |
| Snow | heavy metal where polluted |
| Hot spring | food poison and heavy metal |
| Bandages, sewing | the item's agents go "item to flesh" |
| Blood transfusion | agents travel with the blood (and chemical agent can be removed) |
| Coughing, sneezing, laughing | each event has a 25 percent chance to spread the player's agents to players within 3 m; protection of both sides combines as `1 - (1 - t)(1 - s)` |
| Contaminated zones | chemical agent through `AreaExposure`; mask protection applies |
| Sandstorms | silicosis and eye irritation; mask, eyewear and NVG protection applies |

Other injection points: closing a bleeding source rolls to add wound agent (item's infection chance or a default constant); a rotting food item adds food poison when its decay timer ends (bloody hands raise the dose); skinning animals puts salmonella on the organs; skinning human bodies puts the brain agent on lard and guts; and liquid transfers copy agents.

**Auto-infection (influenza).** Only when there is no temporary resistance and heat comfort is below -0.15 (cold). A hidden timer counts toward 8,650 s, and each pool tick shortens the target by a random 10 to 200 s, scaled by 0.25 (cold), 0.6 (very cold) or 1.0 (freezing). When it triggers, the player gets 110 influenza agents. When warm, the timer drains back. [inf, my arithmetic assuming 3 s ticks: roughly 15 minutes of mild cold, or about 4 minutes of freezing, to trigger.] While cold the influenza agent's growth is 0.40, 0.60 or 0.70 per second by severity; when warm it falls at -0.3 per second (0 while pneumonia is active). Antibiotics triple its die-off; the immunity boost doubles it.

**Diseases** (modifiers; thresholds are agent counts for on / off):

| Disease | Agent | On / off | Effects |
|---|---|---|---|
| Common cold | influenza | 100 / 0 | sneezing (chance 0.4 to 0.75 divided by a random 15 to 20 per tick; halved by painkillers or morphine); spreads airborne |
| Influenza | influenza | 600 / 400 | coughing (up to 0.85 chance per tick, divider 5 to 20) and airborne spread; also drives fever |
| Pneumonia | influenza | 1150 / 1100 | 0.1 health loss per second; stamina depletion x1.3, recovery x0.5; gasping |
| Cholera | cholera | 250 / 50 | water loss 0.5/s scaled by count; when stomach holds 200 or more, vomit chance 10 percent plus up to 30 percent each tick; each vomit costs 450 water and 310 energy plus 30 s of stamina exhaustion; fever |
| Salmonella | salmonella | 60 / 20 | vomit chance 10 percent plus up to 20 percent per tick (each vomit removes 30 percent of the agent, same costs); light pain every 12 to 18 s |
| Food poisoning | food poison | 1 / 40 | vomiting 2 to 5 times per 300 s scaled by count; each vomit removes 60 agents and costs 70 water and 55 energy |
| Wound infection 1 | wound | 1 up to 250 | light pain every 18 to 26 s; synced to other clients |
| Wound infection 2 | wound | 250 / 0 | hand shivers; pain every 6 to 12 s; without antibiotics, heavy pain plus health damage of `elapsed x (0.04 + health regen speed)`; synced to other clients |
| Kuru (brain disease) | brain | 2000 / 0 | laughter (chance count/8 per tick, spreads airborne) and shaking via a sync event |
| Contamination 1 / 2 / 3 | chemical | 1 to 100, 100 to 400, 400 and up | escalating chemical poisoning; die-off stops at stages 2 and 3 |
| Heavy metal 1 / 2 / 3 | heavy metal | 1 / 200 for phase 1 | phases escalate; chelation needed to reduce |
| Silicosis, eye irritation | silicosis, eye irritation | not tabulated | from sandstorm exposure |

- **Fever** is a condition modifier that is active while cholera, influenza or wound stage 2 is. It drains water, plays a "hot" animation every 12 to 18 s, applies a fever-blur effect, lights the *Feverish* notifier, and is visible to other players through the synced-modifier bitmask.
- Wound agent and antibiotics: once stage 1 is no longer active, the wound agent stops growing while antibiotics are in use; during stage 1 it keeps growing.
- **Sync:** the pool writes the active-agent mask into `PlayerBase.m_Agents` and marks the player dirty, but `m_Agents` is not registered for network sync anywhere in the scripts (I searched all of them for the registration call). A synced variable needs that call, so the mask stays on the server [obs: no registration; inf: therefore not replicated]. What other players see is the disease effect (cough, sneeze, fever, wound-infection flags), not the agent counts.

### 6.10 Environment, heat comfort, wetness, heat buffer, thermal bias and heat stroke [obs unless noted]

Source: `4_World\Classes\Environment\Environment.c` (2,380 lines, server only), `3_Game\WorldData.c` and the per-map classes in `4_World\Classes\Worlds\`, `PlayerModifiers` (`HeatComfortMdfr`, `HeatBuffer`, `Wet`, `diseases\HeatStroke`), `ThermalBiasHandler.c`, and the `ENVIRO_*` constants in `3_Game\constants.c`.

**Cadence.** Each server-side player has one `Environment`, updated from `PlayerBase.OnScheduledTick`. Its own timers: a full environment tick every **3 s**; wetness/dryness every second tick (**6 s**); a roof raycast (straight up 25 m) every **10 s**, skipped when inside a building (which counts as roofed); a shadow raycast toward the sun or moon every **30 s** (inside a building always counts as shadow). Each tick: cache the items on the player; check water contact and depth; read speed (player heat = speed x 2.5); read weather (rain, snowfall, fog, cloud cover, wind, time of day); compute ambient temperature; gather heat sources; update item temperatures; compute heat comfort (or set it directly in some vehicles); then wet or dry items.

**World temperature (`WorldData`).**
- Base: each map has two 12-value arrays (monthly minimum and maximum, interpolated across the month). The daily curve rises from the minimum at sunrise to the maximum at 75 percent of daylight, falls to a mid "evening minimum" at sunset, and drifts back to the minimum through the night. Sunrise and sunset times vary through the year.
- Adjustments: altitude lowers it, cloud cover and fog change it (fog -2 degrees at full), and wind chill applies. The wind formula is `-(T - 30) / (-35 - 30) x wind x map wind coefficient`: wind cools you below 30 degrees and warms you above it.
- **Map tables confirm what the extra folders are:** the scripts define world-data classes for ChernarusPlus, Enoch (the game's internal name for Livonia), Nasdara and Sakhal. Monthly maxima run from about 3 to 26 on Chernarus, about -2 to 25 on Enoch (reduced for altitude), 17 to 38 on Nasdara (the hot map; sun adds up to +8 at noon), and -5 to 17 on Sakhal (the cold map). Liquid temperatures by type: fresh and river water 15, clean water 10, salt water 23, snow -5.
- **Altitude reduction (resolved).** `GetBaseEnvTemperatureAtPosition` subtracts `max(0, height x modifier)` from the base temperature, where height is the object's world Y (metres above the water level) and the modifier is set per map: **0.012 for Chernarus, 0.01 for Enoch, 0.005 for Nasdara**, and the class default of **0.02** for Sakhal (no override found). The unit is therefore degrees C per metre, which is about 1.2 degrees per 100 m on Chernarus. The constant `ENVIRO_TEMPERATURE_HEIGHT_REDUCTION` (0.02) and its comment "per 100 meters" are stale: nothing uses that constant. The player's own height gets the same formula (`Environment.GetTemperatureHeightCorrection`). [obs formula and values; inf that the Y unit is metres]

**Player ambient temperature (`GetEnvironmentTemperature`).**
- In water: the water temperature minus 20.
- Inside a building: base plus the building modifier (default +1).
- In a car: base plus `|T| x 0.051`.
- Under a roof: includes fog, with wind scaled by 0.75.
- Outdoors: base plus fog, wind (scaled by surface type) and, in daylight and outside shadow, a sun bonus scaled by overcast and headgear.
- Nearby heat sources can replace the value. With `T` the computed ambient temperature and `U` the averaged source temperature, the code tests `(T - U) x ((T - U) - T) > 0`, which simplifies to `U x (U - T) > 0`. So `T` is replaced by `U` when the sources are **warmer than the air and positive** (`U > 0` and `U > T`) or **colder than the air and negative** (`U < 0` and `U < T`). A source that is weaker than the ambient air on its own side (for example a +10 fire in 20 degree air, or a -2 cold source in -5 degree air) changes nothing, and with no sources (`U = 0`) the test is false. [obs, resolved algebraically]

**Heat comfort (HC), range -1 to 1, stored in the `HeatComfort` stat.** The target is the sum of:
- clothing isolation per slot times a slot weight: body 0.12, legs 0.12, feet 0.06, headgear 0.05, mask 0.05, vest 0.04, gloves 0.04, back 0.03, hips 0 (weights sum to 0.51). [obs: each item's isolation is first multiplied by a health factor and a wetness factor (dry 1.0, damp 0.9, wet 0.5, soaked 0.1, drenched -0.15; pristine 1.0, worn 0.9, damaged 0.8, badly damaged 0.5, ruined 0); the function is `GetCurrentItemHeatIsolation`, documented in 6.14.]
- heat from hot or cold items in attachments and cargo;
- a penalty for each uncovered slot outdoors in heavy rain (above 0.2) or snow (above 0.4);
- stomach content temperature (weight 0.2);
- the player's own heat (`speed x 2.5 / 100`); and
- `(ambient - 24) / 40`.

It is clamped to -1..1 (or 0..1 while the heat buffer is active) and rounded to 0.01. The stat then follows the target through a **20-sample moving average**; if the gap exceeds 0.25 the target is pulled in by 0.25 first. So the stat reacts over about a minute.

Vehicles override this (server decides):
- a **car with the engine on** forces HC target to 0;
- a **motorbike above 20 or boat above 15** lowers the target by an ease-in-cubic of speed, up to 0.8. The boat code uses the motorbike's constant.

Levels used by the HUD and influenza: plus 0.15 / 0.45 / 0.75, minus 0.15 / 0.45 / 0.75.

**What HC does** (`HeatComfortMdfr`, always on, 3 s):
- **Hot** (above +0.15): water loss. The code uses `Lerp` here where the cold branch uses `InverseLerp`, so by my arithmetic loss is only about **0.08 to 0.18 per second** rather than the 0 to 0.4 the constants suggest.
- **Cold** (below -0.15): energy loss rising from 0.2 to 0.45 per second as HC falls to -0.45. Below -0.45 it also deals **health damage** rising from 0.035 to 0.30 per second (ease-in-quad toward -1).
- It also feeds the thermal bias below.

**Wetness.**
- Each carried item has a wetness 0..1: damp 0.05, wet 0.25, soaking 0.5, drenched 0.8.
- The player `Wet` stat is binary. It becomes 1 when the wettest item on the player reaches 0.25 and returns to 0 when it falls below. `WetMdfr` then lights the wetness notifier.
- **Wetting:**
  - Outdoors, in rain: `0.01 x 2 x rain x (1 + 0.25 x wind)` per step. Snow wets only when the combined snowfall and wind value exceeds 1.3.
  - Not applied indoors, under a roof or in a car.
  - In water by depth: at 1.5 m and above all slots; 1.2 to 1.5 upper body; 0.5 to 1.2 hips, legs, feet and hands; 0.15 to 0.5 feet only.
  - An item inside a wet or liquid-filled container also gets wet.
- **Drying:** only when not being wetted. Items dry at their own drying rate times a temperature factor `clamp(((T + 20) / 90)^2 x 10.5, 0.1, 4)`. That works out to roughly 0.5 at 0 degrees and 2.5 at 24. A nearby heat source divides the rate by the distance to it, so closer is faster. Items only dry while wetness is at least damp. (`GetWetDelta` also has fog, cloud and wind terms, but item drying as coded uses only the item's rate, the temperature factor and the heat-source distance.)

**Heat sources** (`UniversalTemperatureSource`). Each has a temperature cap, a full range and a max range. Entities within 20 m, plus a held item, count. The temperature at the player equals the cap inside full range and falls linearly to 0 at max range. Values go into a 10-sample average (hot and cold sources average max and min). The result drives the heat buffer, item heating, and drying.

**Heat buffer** (stat -30..30, the one **synced** stat; a stage and a capacity are also net-synced):
- Capacity runs from 0.35 for a naked character to 1.0 with full warm clothing (clothing HC divided by the 0.51 weight sum).
- **Fills** only near a heat source with HC above -0.15 and a positive average source temperature: `0.18 / (capacity x (1 - 0.4 x HC target))` per tick up to the capacity.
- **Drains** otherwise: `0.01 / (capacity x (1 + 0.4 x HC target))` per tick, multiplied by a per-stage rate limit (stage 1: 1.82 to 4.0, stage 2: 0.8 to 1.6, scaled by capacity). In water it drains 20 x depth faster. Removing clothing shrinks capacity and cuts the buffer.
- While `HeatBufferMdfr` is active (buffer above zero), target HC is held at 0 or above, so you cannot feel cold. Stages: 1 below 0.6, 2 from 0.6, 3 from 0.85 of capacity.
- When it empties the player gets at least **300 s of influenza resistance**.

**Thermal bias** (stat -1..1, `ThermalBiasHandler`, server only, saved with the player). It integrates overheating, and accumulates in `HeatComfortMdfr`:

| Condition | Change per second |
|---|---|
| HC above 0.75 | +0.0005 (extra) |
| HC above 0.45 | +0.00032 (extra) |
| HC above 0.15 and water under 1000 (conscious) | +0.00022, or +0.00032 from bias 0.6, or +0.0005 above 0.85 |
| HC above 0.15 and water 1000 to 3500 | +0.00022 while bias is under 0.4, otherwise -0.0001 |
| HC above 0.15 and water 3500 or more | nothing from this block (the two extra rows above still apply) |
| HC at 0.15 or below | -0.0001, snapped to 0 at or below zero |

A head wash is defined as subtracting 0.175 and blocking further `Add` calls for 30 s (the constants exist; I did not trace the action that uses them). [inf, my arithmetic from these rates: with water under 1000, bias reaches 0.6 (phase 3) after roughly 45 minutes of mild overheating (HC 0.15 to 0.45), about 18 minutes with HC above 0.45, and about 14 minutes above 0.75. Reaching 0.85 (phase 4) takes about 58, 25 and 19 minutes. Recovering from 0.85 by cooling alone takes about 2.4 hours.]

**Heat stroke** (four modifiers keyed to thermal bias; one synced bit shows it to other clients):

| Phase | Bias | Effects |
|---|---|---|
| 1 | above 0 | water drain |
| 2 | above 0.4 | fever blur effect; stamina depletion and recovery penalties (the pneumonia multipliers); random "hot" animation (chance `lerp(2, 10, bias) / 500` per second); water drain; counts as a disease |
| 3 | from 0.6 | water drain 0.75/s; vomiting (chance `lerp(1, 2, remapped bias) / 900` per second), each vomit costing 70 water and 55 energy plus exhaustion for up to 30 s |
| 4 | above 0.85 | health damage rising from 0.01 to 0.35 per second while conscious; a screen-fading "faint" effect with shortening cycles; and, once bias exceeds 0.75 with shock above 90, the player blacks out every 60 to 120 s for 5 to 10 s (shock is set to 25) |

- Phases 1 and 2 deactivate at or below their threshold, phases 3 and 4 below it.
- The phase water-drain constants (0.35, 0.5, 0.75) are declared as `int`. If Enforce truncates a float assigned to an int they would be 0 and phases 1 to 3 would drain nothing. The engine's value converter does truncate float to int (`CVTTSS2SI`, see the int-constant section in `open-questions.md`), so this is the likely behaviour; a server test would confirm it.

### 6.11 Stamina, shock and unconsciousness [obs unless noted]

Source: `4_World\Classes\StaminaHandler.c` (1,284 lines), `ShockHandler.c`, `ShockHitReaction`, and the `Shock`, `ShockDamage` and `Unconsciousness` modifiers. Constants are in `3_Game\constants.c` (`GameConstants.STAMINA_*`) and `PlayerConstants.c`; several can be overridden by the server's gameplay config (`cfggameplay.json`).

**Stamina model.** The meter runs 0 to `STAMINA_MAX` (100 by default, configurable), and the `Stamina` stat mirrors it on the server.
- **Load cap:** once carried weight reaches 6,000 g, the usable maximum drops by 1.75 per extra kilogram, with a floor of 5. The cap is recomputed when the load changes by more than 1 g; if the cap shrinks, current stamina is clamped to it.
- **Per-frame update:** `Update` is driven from the command-handler tick. It works out a stamina delta from the movement state, applies the active multipliers, subtracts any one-off cost, clamps to 0..cap, and updates exhaustion and the depleted flag.
- **Drain per second:**
  - sprint standing 4, crouched 1, fast swimming 5, fast ladder climb 8 (all scaled by `sprint*StaminaModifier` config values, default 1);
  - sprinting prone falls through to the jog recovery value instead (the prone drain constant of 3 is unused as coded).
- **Recovery per second:** idle 5, walk 4, jog 2, slow swim 1, slow ladder 1, rolling 0. A "gain bonus" adds up to 3 more when not depleting: `min(stamina / 10, 3)`, and the full 3 when stamina is 25 or below.
- **Cooldown:** every drain re-arms a 0.45 s pause before regeneration resumes. Hitting zero sets the depleted flag and a 0.5 s exhaustion cooldown.
- **One-off costs:** jump 25, vault 20, climb 42, light melee 5, heavy melee 25, evade random 3 to 8, roll 5, drowning 10, push car and hold breath exponential (hold breath ramps from 0.2 to 1.0 over 5 s with exponent 3). An "overall drain" entry removes the whole bar. Melee, obstacle and hold-breath costs are scaled by gameplay-config modifiers (default 1).
- **Minimum stamina to act** (the `StaminaConsumers` table): hold breath 10 (keeps draining down to 0), sprint `min cap + 15` (20 by default), jump 25, vault 20, climb 42, heavy melee 25, evade 8, roll 5, drowning and pushing 0. Sprint has hysteresis: after depletion it stays blocked until stamina climbs back above its threshold, or reaches the cap.
- **Multipliers** (active ones multiply together; registered in `Init`):

| Source | Depletion | Recovery |
|---|---|---|
| Mask | x1.25 | x0.5 |
| Fatigue | x1.33 | x0.33 |
| Epinephrine | x0 (no drain) | none |
| Vomit exhaustion | x1.3 | x0.5 |
| Pneumonia (also used by heat stroke 2 and 3) | x1.3 | x0.5 |
| Drowning | none | x0 |

- **Sync:** the server sends stamina, cap and the cooldown flag to the owning client every 0.5 s and when the cap changes, using a sync juncture (`SJ_STAMINA`; a second one carries the multipliers). The client's movement prediction stores the stamina value and capacity in the move data, so movement code on both sides agrees. Other players see only a coarse net-synced stamina state, plus the player's exhaustion animation, set from `1 - stamina / cap` (switched off on the local player while aiming through optics or iron sights). Low stamina also adds turning inertia while sprinting.

**Shock.** "Shock" is an engine health value (maximum 100, a health-like meter that falls when hit), not a `PlayerStat`.
- **Intake:** hits add to `ShockHandler`'s accumulator. Once the accumulated amount reaches 3 (or a forced check), it is multiplied by a multiplier, dealt as shock damage, and the new value is sent to the client by a sync juncture. A periodic check also runs every 0.95 s.
- **Regeneration** (`ShockMdfr`, ticks every 0.35 s): only when at least 1 s has passed since the last hit and the pulse is regular.
  - Conscious: 5 per second. Unconscious: 1 per second (both from gameplay config); x0.8 more if blood is at or below 3,000.
  - Stopped while drowning; blocked while standing with broken legs (prone, swimming and ladders are exceptions).
  - An unconsciousness refill modifier can slow regeneration after projectile knock-outs, if the config allows it.
- **Shock damage over time** (`ShockDamageMdfr`, ticks every 0.5 s): when conscious with blood at or below 3,000 and a cooldown since the last blackout has passed (90 to 150 s, longer when energy and water are low), shock drains at 5.5 per second rising to 6.25 as blood falls to 2,500.
- **Unconsciousness** (`UnconsciousnessMdfr`, 0.5 s): turns on when shock falls to **25** or below and informs the client; turns off when shock reaches **50** and the pulse is regular, recording the end time. Other code can force it (heat stroke phase 4 sets shock to 25). A constant gives an unconscious player in water 20 s before death.
- **Screen effects (client):** a tunnel-vision vignette follows `1 - easeInQuart(shock / max)` with smoothing (rises at most 0.05 and falls at most 0.01 per update), plus a 0.5 s pulse, and `ShockDealtEffect` adds a 0.6 to 1.0 s blur, colour and vignette flash per hit scaled by intensity. The pulse is added when shock is above 80 percent of its maximum, which looks backwards compared to the vignette; I did not check it in play.

### 6.12 Bleeding, hits, broken legs and injury state [obs unless noted]

Source: `4_World\Classes\BleedingSources\*`, `BleedChanceData.c`, `InjuryHandler.c`, the `Bleeding`, `BrokenLegs` and `BrokenArms` modifiers, `PlayerBase.EEHitBy` and the broken-leg functions, the bandage and splint actions, and the hit-feedback classes.

**What happens when a player is hit** (`PlayerBase.EEHitBy`, server):
1. Admin-log the hit; if the hit dealt shock damage, remember the time (this pauses shock regeneration) and set the knock-out refill modifier from the ammo's config.
2. A flashbang empties stamina.
3. **Bleeding check** (below).
4. Interrupt any action in progress.
5. For "non-lethal" ammo (a config flag that moves shock into health), convert shock damage into health damage on the whole body and on the hit zone (not the head).
6. **Leg check:** if any of the four leg or foot zones is at health 1 or less, (re)start the broken-legs modifier.
7. A special ammo type (`Bullet_CupidsBolt`) instead resets the whole player: damage zones, modifiers, bleeding, most stats, agents and stamina.
8. Force an immediate shock-handler check.

**Bleeding sources.**
- **Zones:** 29 named body zones, each one bit of an integer. Flow multipliers: **1.0** for head, neck, pelvis and the four spine zones (7); **0.6** for shoulders, arms, forearms and legs (16); **0.1** for hands and feet (6). Each zone is tied to the clothing slot that covers it (mask, headgear, body, gloves, legs, feet).
- **Which bits are set** is a net-synced integer on the player, so every client sees every player's wounds.
- **Creation** (`ProcessHit`): uses the Blood damage dealt and two values from the ammo config, `bleedThreshold` (0 to 1) and damage `type`.
  - For `Melee` and `Infected` types a chance table applies: chance = table value at the lower of (blood damage, threshold), scaled by the higher one. Melee: 5 percent at 10, 15 at 20, 23.4 at 30, then +7.8 per 10 up to 70.2 at 90, and 100 at 100. Infected is higher mid-range (27.5 at 30, 40 at 40, 55 at 50, 70 at 70).
  - Hits from infected with other damage types: chance equals the damage in percent.
  - Anything else (bullets and so on): a source is created if blood damage exceeds `zone maximum x (1 - threshold)`.
  - A zone that already bleeds cannot get a second source.
- **Other causes:** sliding down a ladder without gloves (30 percent per second, gloves take 3 damage a second), constructing by hand (50 percent once, gloves take 10), and burns in contaminated areas (a "contaminated" source type at x0.65 flow).
- **Blood loss:** every 3 s each source subtracts `20 x flow x pressure scale x elapsed` blood. The pressure scale is `InverseLerp(2500, 4000, blood)` clamped to 0.3 to 1, so bleeding slows as blood falls (to 30 percent at worst). Full-pressure rates: 20 per second for torso and head, 12 for limbs, 2 for hands and feet.
- **Duration:** 300 s, then the wound closes itself. A self-closing wound has a **40 percent** chance to add wound agent; a wound closed with a bandage uses the bandage's infection chance (a clean bandage dressing 0, dirty 5 percent).
- **Death:** `BleedingCheckMdfr` sets health to -1000 as soon as blood is under 2,500 and logs "bleeding out".
- **Treatment:** `ActionBandageBase.ApplyBandage` removes the **highest-flow** source, uses up one bandage, and transmits the item's agents to the player. Time spent is the base time divided by the item's effectiveness (bandage dressing: 2.0). The bandage action only appears while the player is bleeding.
- **Client:** every client keeps a `BleedingSourcesManagerRemote` for every player. When the synced bits change it starts or ends the bleeding state, spawns blood particles on the right bones, and for the local player shows the screen bleeding drops, the bleeding badge with a source count and a bleeding sound. Removing a source also drops arrows stuck in the player (one if still bleeding, all if not).

**Broken legs** (three states: none, broken, splinted):
- **Trigger:** leg or foot zone health of 1 or less after a hit. Script `OnLand` adds no fall logic [inf: fall damage comes from the engine and reaches the leg zones through the same check].
- **On break:** all four leg zones are set to 0 health, the player is forced prone if possible, 20 shock is dealt, and a break sound plays. The state is net-synced and sent to the owner.
- **While broken** (modifier ticks every 0.5 s; persistent across logout): moving costs shock. Erect: only jogging or faster, 4 / 6 / 8 shock per check depending on average leg health (about 75 or more, in between, 25 or less). Crouched: any movement at half that. Swimming: 2. Ladders: as erect. Standing still: 0. Light and heavy melee swings cost 10 and 25, and rolling 10. Shock regeneration is also blocked while standing (see 6.11). With shock at or below 25 you black out, so sprinting on a broken leg ends in unconsciousness.
- **Recovery:** legs regenerate at 0.18 per tick instead of 1. The modifier ends when both legs reach 100 health, which also removes a worn splint.
- **Splint:** the action converts a splint into an applied splint on the `Splint_Right` slot and sets the splinted state. Splinted movement does not apply the walking shock, so the player can walk. The injury animation is held at "damaged" instead of "ruined". Healing still needs time.
- **Broken arms:** the modifier turns on when either arm reaches 0 health and off when both are at 80 or more. The effect calls are commented out in the scripts, so any effect is on the engine side [inf].

**Injury animation level** (`InjuryAnimationHandler`, server, every 5 s): overall health fraction maps to five levels: pristine at 0.5 or more, worn below 0.5, damaged below 0.3, badly damaged below 0.2, ruined below 0.1, with animation strengths 0, 0.3, 0.6, 0.8 and 1. Overrides can cap the shown level: morphine to pristine, painkillers to worn or damaged, being prone to pristine, and broken legs set it from average leg health. The level is net-synced so other players see the limp.

**Client feedback on being hit:** a camera shake scaled by impact speed (0 to 500), a short screen flash (0.1 s), a radial pain blur (0.6 s), the shock vignette flash from 6.11, directional hit indicators (arrow, spike or splash variants, randomly scattered), the map closes, and a blocked melee hit just plays a block sound. Notifiers exist for bleeding, a fractured leg and an injured leg.

### 6.13 Not covered yet

Ragdoll handling, sewing wounds, and the exact `StatLevel` formulas for stamina. (Item temperature and clothing isolation are in 6.14; heavy metal, contamination, silicosis and sandstorms are in 6.15.)

### 6.14 Item temperature and clothing isolation [obs unless noted]

Sources: `3_Game\Entities\EntityAI.c` (temperature core), `3_Game\Systems\TemperatureAccess\*`, `4_World\Entities\ItemBase.c`, `4_World\Classes\Environment\Environment.c` (`ProcessItemsTemperature` and helpers), `4_World\Static\MiscGameplayFunctions.c` (`GetCurrentItemHeatIsolation`) and the constants in `3_Game\constants.c`. This is the item side of 6.10: the player's heat comfort uses the isolation function below, and the same environment tick also moves the temperature of everything the player carries.

**Two different quantities.** An item has a *temperature* (`m_VarTemperature`, network-synced between a configured min and max) and a *heat isolation* (a 0 to 1 config number, `m_HeatIsolation`). Temperature governs freezing, thawing, overheating and cooking. Isolation only matters for clothing worn by a player.

**Isolation function** (`GetCurrentItemHeatIsolation`). The result is the config isolation times a health factor times a wetness factor:
- *Wetness factor* by item wetness: dry (below 0.05) 1.0; damp (0.05 to 0.25) 0.9; wet (0.25 to 0.5) 0.5; soaked (0.5 to 0.8) 0.1; **drenched (0.8 or more) returns -0.15 outright**, a drenched item makes the wearer colder than nothing at all.
- *Health factor* by damage level: pristine 1.0, worn 0.9, damaged 0.8, badly damaged 0.5, ruined 0.0.
- Example: a clothing piece with isolation 0.8 that is worn and wet gives 0.8 x 0.9 x 0.5 = 0.36.
- A naked slot is penalised only in the rain or snow: if it is outdoors (not inside, under a roof, in a car or in water) and rain exceeds 0.2 or snowfall 0.4, an empty slot costs the drenched value (-0.15) times the slot's coefficient.

**Config isolation values** (`data\clothing.csv`, column `heat`, 899 pieces; 819 have a non-zero value). It is a coarse scale: 0.1 (115 pieces), 0.2 (83), 0.3 (95), 0.4 (77), 0.5 (76), 0.6 (37), 0.7 (46), 0.8 (84), 0.9 (55) and **1.0 (98)**, plus 80 pieces at 0. The maximum is 1.0 in every main clothing slot (witch hood, military winter coat, ushanka and others). Per slot, the mean is highest for gloves (0.68), masks (0.62) and backpacks (0.59), then feet (0.53), body (0.52), vests (0.51), headgear (0.47) and legs (0.41). Hips and eyewear are at most 0.1, and armbands, holsters and belts have none.

**Which slots count** (Environment tick lists): head = headgear and mask; body = gloves, hips, body, back, vest, melee and shoulder; feet = legs and feet. Eyewear is in none of them.

**Item temperature core** (`SetTemperatureEx`, server only):
1. *Source arbitration* (`TemperatureAccessComponent`): each change request names a source type. Priorities: world 0, universal temperature source 1, and inventory, fireplace and cooking 2. A request is accepted if its priority is at least that of the last accepted source, or if more time than the request's own update interval has passed since that source last wrote. So while a fire or a carrying player keeps writing, the world's pull toward ambient temperature is rejected.
2. *Interpolation* (`TemperatureDataInterpolated`): the step per second is `Lerp(0.17, 1.02, fraction)` degrees C, where the fraction is how far the current-to-target difference is between 1 and 300 degrees (`TEMPERATURE_RATE_AVERAGE_ABS` 0.17, max 6 times that). The step is multiplied by the elapsed time, a source coefficient and the *heat permeability* of the item and every parent in its hierarchy (container chains multiply). The result never overshoots the target. Example: a 20-degree gap moves about 0.67 degrees per 3 s tick at coefficient 1.
3. *Freezing and thawing:* only items whose freeze threshold is inside their temperature range can freeze. A crossing clamps the temperature at the threshold while a *progress* value (0 to 1) fills over the item's freeze or thaw time (at least 120 s each, scaled by the item's quantity for stacks and liquids, divided by the source coefficient). Progress that reverses (an item that was cooling toward frozen but now warms, or the opposite) moves back 20 times faster. When a freeze or thaw completes, the leftover progress converts back into temperature; leftovers under 0.1 degrees are discarded. Liquid containers take their thresholds from the liquid (`Liquid.GetFreezeThreshold`, `GetThawThreshold`, `GetBoilThreshold`).
4. *Overheating* applies to items with a configured overheat time (at least 180 s); the overheat threshold defaults to the maximum temperature.

**Where items get their target temperature:**
- *Items on the ground, in containers or vehicles* (`ProcessVariables`): target is the base environment temperature at the object (`ACCESS_WORLD`, coefficient 1), with heat permeability multiplied up the parent chain. This runs only when world wet/temperature updates are enabled in the server settings.
- *Items carried by a player* (`Environment.ProcessItemsTemperature`, every environment tick, `ENVIRO_TICK_RATE` 3 s): head, body and feet slots plus the hands, recursing through every attachment and cargo item. **The target is the middle of the neutral zone, 25 degrees C (zone 15 to 35)**, not the weather. Body heat keeps carried items near 25 whatever the air temperature. Coefficient is 1 normally, the average of nearby heat sources' own coefficients near a fire or stove (a universal temperature source has 6, a fireplace 2, a gas stove 1), and **5 while swimming**, when the target becomes the water temperature and global cooling is switched off.
- *Cooling coefficient* is always 1 (`TEMP_COEF_COOLING_GLOBAL`), so items cool at a base rate and warm up to six times faster beside a heat source.
- *Self-adjusting* entities (their own simulation) are skipped.

**Item temperature levels** (display and gameplay thresholds, degrees C): hot level 1 at 35, level 2 at 70, level 3 at 250, level 4 at 600; neutral 15; cold level 1 at 3, level 2 at -10, level 3 at -50, level 4 at -100. An item explodes from heat at 100 or more (`ITEM_TEMPERATURE_TO_EXPLODE_MIN`) [inf: used for sealed items such as cans]. In heat comfort, each carried item adds a value based on its temperature and `GetTemperaturePerQuantityWeight`, scaled by 0.04 per unit of the item's config weight (`ITEM_TEMPERATURE_QUANTITY_WEIGHT_MULTIPLIER`) [inf from the constant name; the use is in 6.10].

**Wetness of non-worn items** (`ProcessItemWetness`, for the same tick family). Items not on a player: if the parent item is soaked or wetter they gain 0.002 per second; if the parent holds liquid they gain 0.015 per second; otherwise they dry by the ground rate (twice that when inside a parent). Constants: wetting inside 0.002, wetting from liquid 0.015, drying inside -0.0016, drying on the ground -0.0008 per second.

**Not covered:** the cooking temperature path (`ACCESS_COOKING`), how fireplaces push item temperatures (5.7 covers the fire itself), and the clothing wetness gain/loss on the player, which is in the environment tick of 6.10.

### 6.15 Heavy metal, contamination, silicosis and sandstorms [obs unless noted]

Sources: `4_World\Classes\PlayerModifiers\Modifiers\diseases\{HeavyMetal, Silicosis, Contamination, Contamination2, Contamination3, IrritatedEyes}.c`, `conditions\{AreaExposure, SandstormExposure}.c`, `4_World\Classes\ContaminatedArea\*`, `4_World\Entities\ScriptedEntities\Triggers\ContaminatedTrigger.c`, `3_Game\Sandstorm.c`, `4_World\Systems\Sandstorm\ScriptedSandstormController.c`. The agent counts and thresholds below are the units from 6.9 (agent maximums: chemical 500, heavy metal 600, silicosis 1,000). Each phase is a separate modifier that activates and deactivates on the agent count.

**Heavy metal** (agent 256; comes from polluted water, snow and hot springs, see the source table in 6.9). Chelation is the cure.

| Phase | Agent count | Effects (per modifier tick unless stated) |
|---|---|---|
| 1 | 1 to 200 | water loss `deltaT x 0.8 x max(0.3, count/600)` on every tick; the agent decays by 0.5 per tick up to 300; hand shiver every 20 to 40 s |
| 2 | 200 to 400 | light pain every 20 to 40 s; a per-tick chance of complete deafness of `(count/600) / rand(5 to 10)`, lasting `3 + 0.6 x (count/600)` seconds; the same water loss; the agent decays 0.5 per tick up to 400 |
| 3 | 400 to 600 | **health loss** `deltaT x 0.05 x max(0.03, count/600)` per second (about 0.03 per second at 400, 0.05 at 600); vomit (30% of stomach) every 180 to 360 s; complete deafness and the severe HMP symptom for as long as the phase is active; **no decay and no water loss in this phase's own code** |

The heavy-metal modifiers tick every 3 s (`DEFAULT_TICK_TIME_ACTIVE`), so the 0.5 decay is about 0.17 agents per second in phases 1 and 2. Phase 3 has no decay of its own (the agent's own die-off rules in 6.9 are separate), so it leaves only when chelation or another removal drops the count under 400.

**Chemical contamination** (agent 32, count 0 to 500; stages are modifiers):
- *Stage 1* (1 to 100): one cough when it starts.
- *Stage 2* (100 to 400): counts as a disease; a cough every 20 to 40 s and a vomit every 200 to 400 s.
- *Stage 3* (400 and up): vomits on entry; after 4 s active, whenever the player is not currently vomiting, **100 shock is removed** (this knocks the player out, see 6.11); while unconscious, health drops **3 per second**. So stage 3 is effectively lethal unless the agent count is brought down.

**Contaminated zones** (`AreaExposure`, activated on first entry to any contaminated area, deactivated on leaving the last; areas are counted per player):
- *On activation:* a teleport check against the safe positions in the area file runs and the "area presence" persistent flag is cleared [inf: this moves a player who logged back in inside an area]; one agent dose is applied, with an immediate cough if any was transmitted.
- *Each tick:* airborne chemical agent at **5 per second** (subject to mask and clothing protection from 6.9); a cough every 3 to 5 s while any is transmitted (25% of the time the next gap doubles).
- *Every 13 to 18 s:* a **bleeding-source check**. For each free bleeding location, a chemical-protection roll is made (clothing at that body part); a failed roll makes it eligible, and one eligible location gets a new bleeding source of type "contaminated" (see 6.12).
- *Bleeding sources inject agent:* each open bleeding source adds **0.33 agents per second**, whatever the protection.
- *Creatures:* animals and infected in an area lose `3 x accumulated time / overlapping triggers` health every 10 s (`AI_CONTAMINATION_DMG_PER_SEC` 3).

**Area types.** *Static* areas are loaded from a JSON file at server start (the 9 Chernarus zones in 5.6): position, radius, height range above and below, particle rings and a trigger class. *Dynamic* areas (artillery gas): after a 20 s airborne-explosion delay and a 10 s setup, 2 to 5 `Grenade_ChemGas` items are scattered 5 to 15 m from the centre, and the area has decay stages (start of decay, finish of decay) that change particle density on clients. *Local* gas (from a grenade) is a 10 m radius, plus or minus 3 m high zone that lives 360 s with its decay stages in the last 20 s and 10 s. Entering any of them goes through the same player counter and modifier.

**Silicosis** (agent 512, count 0 to 1,000; one modifier ticking every 5 s while the count is above 0):

| Count | Effect |
|---|---|
| 200 and up | heavy breathing sound with intensity 0.1 to 1.0 (over 200 to 1,000); interval from 25 s down to 3 s |
| 600 and up | stamina recovery and depletion penalties (the pneumonia stamina modifiers from 6.11) |
| above 700 and rising | per tick health loss `2.0 x Remap(700 to 800 -> 0 to 1)` |
| above 800 | fainting vignette (strength up to 2, fade up to 5 s, repeating more often as the count climbs) and **forced unconsciousness**: an episode every 60 to 120 s lasting 5 to 10 s, each time setting shock to 25 |

**Eye irritation** (agent 1,024): active while the count is above 0, ticking every 5 s. From 15 agents it drives the irritated-eyes symptom, remapped from 15 to the agent maximum, and it is cleared below 15. It is fed only by sandstorms in the scripts.

**Sandstorms.**
- *Engine side:* `SandstormController` is native and server-driven (start with a fade-in time, stop with a fade-out time, position, direction, speed, intensity at any world position, magnitude). The rate is the server setting `sandstormFrequency` in `cfggameplay.json` (0 = never, 1 = normal, 2 = twice as often); the weather system can start storms itself.
- *Scripted per-player intensity* (`ScriptedSandstormController.GetIntensityForPlayer`): the world intensity at the head position, reduced in sequence by shelter. **Underground** fades to zero over 1.5 s and below the surface by depth (full fade over 2 m). **A building** (roof overhead and inside the building sound zone) fades it to zero over 1.5 s; crash sites and plants do not count as shelter. **A car** fades it to zero over 1.5 s (only cars, not boats or other transports).
- *Exposure* (`SandstormExposureDynamic`): active while a storm is on and the local intensity is above 0. Each tick it adds **silicosis and eye-irritation agents at `intensity x 1.0` per second** through the airborne-solid route (so mask and goggles protection from 6.9 applies); nothing is added while unconscious. A static variant (for test zones) adds a flat 1 per second.
- *Cough:* a mask or eyewear item with dust protection reduces it: cough intensity is `clamp(intensity - protection)`; the gap between possible coughs runs from 25 s down to 3 s as that rises, and each possible cough passes a roll against the intensity.
- *Squint:* a client-side screen effect with strength `clamp(intensity - eye protection)`.
- *Other effects found elsewhere:* AI hearing is reduced by `intensity x 0.5` (now native, the script version is obsolete), infected cower (5.4), base-building decay speeds up 1.5x (5.7).

**Protection items** have a per-agent-route protection level in config (`DEF_DUST_PARTICLE_BREATH`, `DEF_DUST_PARTICLE_EYES`, chemical and biological; see the 85 items in 5.1).

**Tick lengths:** heavy metal 3 s, contamination stages 1 and 2 are 3 s and stage 3 is 1 s, zone exposure and sandstorm exposure 1 s, silicosis and eye irritation 5 s. A per-tick number above is per that interval.

**Not covered:** the engine-side storm shape, travel and magnitude curve (native), and the particle and post-process effects.

### 6.18 Sewing wounds and ragdoll (task S3) [obs unless noted]

**Sewing wounds** (`ActionSewSelf`, `ActionSewTarget`; items `SewingKit` and `LeatherSewingKit`).
- *Who and when:* a player sews their own wounds (the action has no target) or another player's, within the default interaction distance, standing or crouched, using a non-ruined kit, and only while the target `IsBleeding()`. A target in a vehicle is allowed.
- *Time:* the action repeats for **8 seconds** (`UATimeSpent.SEW_CUTS`).
- *Effect on finish (server):* the **most significant bleeding source is closed**, meaning the open source with the highest flow modifier (6.12), not a random one; the kit's agents are transmitted to the patient (item to flesh route, 6.9); and the kit loses **20 quantity** (kits start with 100, so five sewings), or is deleted if it has no quantity. One action closes one source.
- *Infection:* when a source is closed by an item, the chance of adding the wound agent is the item's own `GetInfectionChance`: **0 for a clean kit and 0.30 for a dirty one** (sewing kit). With no item (a wound that closes by itself) the chance is **0.40** (`BLEEDING_SOURCE_CLOSE_INFECTION_CHANCE`). For comparison, a bandage dressing is 0 clean and 0.05 dirty; a rag is 0 clean and 0.15 dirty; the other consumable bandage-type items are 0 and 0.15. Cleanliness is a flag on the item; disinfecting it makes it clean.
- *Kit config:* both kits hold 100 units; the sewing kit weighs 210 g and the leather kit 1,200 g. The sewing kit also repairs tents and shelters and is the second ingredient of several crafting recipes (armband, leather items).

**Ragdoll.** The scripts hold almost no ragdoll logic: ragdoll physics are engine-side. The script surface is `IsRagdoll()` and `PhysicsSetRagdoll`/`PhysicsIsRagdoll` on the human (the old death-state hook), a ragdoll collision layer, and four uses: the third-person camera follows a ragdoll (`DayZPlayerImplement` ~2882), the player input handler skips normal handling while the human controller reports ragdoll (`PlayerBase` ~3346), the unconscious logic checks ragdoll before restoring the vehicle command (~3769), and the player is re-possessed after a possible ragdoll (~4586). There is a note in `DayZPlayerImplement` (~2454) that a dedicated ragdoll command is still to come. When the player is knocked out, the animation and physics are engine-driven. [obs for the script surface; the physics are not analysed]

### 6.19 The soft-skills system (task S4) [obs unless noted]

Sources: `4_World\Classes\SoftSkillsManager.c` (636 lines), `UASoftSkillsWeight` in `ActionConstants.c`, `ActionBase.GetSpecialtyWeight`, and every use of `GetSoftSkillsManager` and `m_Specialty`.

**The model.** Each player has one number, the **specialty level**, from -1 (fully "precise") to +1 (fully "rough"), kept in the `Specialty` player stat (saved and synced to the owning client by RPC). Actions that declare a weight push it: rough actions add a positive weight, precise ones a negative weight.

| Constant | Value |
|---|---|
| `ROUGH_LOW` / `MEDIUM` / `HIGH` | +0.01 / +0.02 / +0.03 |
| `PRECISE_LOW` / `MEDIUM` / `HIGH` | -0.01 / -0.02 / -0.03 |

**Update rule** (`AddSpecialty`, server):
- Ignored when the system is switched off (it is on by default) or during a **cooldown**. After each accepted action the cooldown is `|weight x 100| x 5` seconds (5, 10 or 15 s).
- *Linear mode* (off by default): level += weight, clamped to [-1, 1].
- *Exponential mode* (the default): a counter tracks consecutive actions of the same direction (positive for rough, negative for precise); an opposite action resets the level to 0 and restarts the counter at 1; the applied weight is `weight / sqrt(|counter|)`, so repeating the same kind of action has diminishing returns. The result is clamped to [-1, 1].

**How the level would be used.** Helper functions turn the level into bonuses: `AddSpecialtyBonus` and `SubtractSpecialtyBonus` scale a value by `1 +/- level / limit` (limit 2 by default, so at most +/-50%; limit 0 means no halving), and `AdjustCraftingTime` shortens a crafting time by `level / 2` of itself. The precise side of the level only helps precise actions (negative weight) and the rough side only rough ones.

**Is it live in retail? Barely.** In the scripts I read, 146 action and recipe files set a `m_SpecialtyWeight`, but:
- `GetSpecialtyWeight()` has **no caller** besides its definition;
- `AddSpecialty` is called from exactly one place, **`ActionFishing`**;
- `AddSpecialtyBonus`, `SubtractSpecialtyBonus` and `AdjustCraftingTime` are called only in commented-out code (`ActionBreakLongWoodenStick`, `ActionBurnSewSelf`);
- recipes carry a `m_Specialty` value (-0.02 to 0.03, see 5.8) and pass it to their `Do`, but the base `ApplySoftSkillsSpecialty` is empty.
So the specialty level changes only through fishing, and nothing found reads it to alter a gameplay value. The framework, the stat and a Diag debug window exist; the effects look unfinished or removed. [obs for the call graph in the scripts; engine code could still use the stat, which was not checked]

### 6.20 Cooking, food stages and rotting (task S5) [obs unless noted]
Sources: `Cooking.c`, `FoodStage.c`, `Edible_Base.c` (`ProcessDecay`), `FireplaceBase.c`, `PortableGasStove.c`, `constants.c`, and the merged `Food >> FoodStages / FoodStageTransitions` config bodies. Table: `data/food_stages.csv` (65 food items, 317 stage rows, one per item and stage, with transitions). It needed the config merge tool to resolve nested classes whose parent is a root-level class (`FoodStageTransitions: FruitStageTransitions` and similar); `cfgmodel.py` now does that, and a regression run against the previous version lost and changed nothing (26,124 keys gained).

**Stages and methods.** Stage ids: 1 Raw, 2 Baked, 3 Boiled, 4 Dried, 5 Burned, 6 Rotten. Cooking methods: 1 baking, 2 boiling, 3 drying, 4 time. Each item has a `FoodStages` body (per stage: `visual_properties` [selection, texture, material], `nutrition_properties`, `cooking_properties`) and a `FoodStageTransitions` body (per current stage, named transitions `ToBaked`, `ToBoiled`, `ToDried`, `ToBurned`, `ToRotten`, each with `transition_to` and `cooking_method`).
- `cooking_properties` = [minimum item temperature, seconds of cooking to complete, maximum temperature (drying only)]. They belong to the *target* stage: the cook time and minimum temperature of the stage you would move into. Typical values: Baked 70 °C for 35 s (45 s on 26 items), Boiled 105 °C for 45 s (55 s), Dried 70 °C for 30 s (45 or 120 s on a few), with a 80 °C maximum, Burned 100 °C for 20 s (30 s; one item 150 s).
- `nutrition_properties` index order (from the getters): 0 fullness index, 1 energy, 2 water, 3 nutritional index, 4 toxicity, 5 agents bitmask, 6 digestibility, 7 agents per digest. Rotten and Burned rows add the agent fields (for example Apple Rotten `... 16 | 1 | 9`: agent 16, digestibility 1, 9 agents per digest; agent bit 16 is FOOD_POISON in `EAgents.c`).
- A food with an empty `nutrition_properties` array falls back to a base stage plus `NutritionModifiers` classes (code path present, not used by the 65 items here).
- Shapes: 46 items have all six stages, 17 have only Raw and Rotten, one has all six in a different order and one has Raw only.

**Next stage choice** (`GetNextFoodStageType(method)`): look up the current stage's transitions and return the `transition_to` of the first one whose `cooking_method` equals the method in use; if none matches the answer is **Burned** (so any unlisted method burns the food). Example, Apple: Raw → ToBaked(baking→Baked), ToBoiled(boiling→Boiled), ToDried(drying→Dried), ToBurned(drying→Burned), ToRotten(time→Rotten). The Dried and Burned entries share method 3, and the transition keys are scanned in a fixed global order, so drying a raw item reaches Dried first. Every cooked stage (Baked, Boiled, Dried) maps all of baking, boiling and drying to Burned. Rotten food only has `ToBurned` (baking). Burned has no transitions.

**Method selection** (`GetCookingMethodWithTimeOverride`, cookware = pot, frying pan, cauldron): cookware with quantity (liquid) → boiling, time coefficient 1; liquid is gasoline → drying with coefficient 2 (this is how fuel in a pot burns the food); no liquid and Lard in the cargo → baking, coefficient 1; no liquid, no lard, cargo not empty → baking, coefficient 2 (half speed); empty → none. A non-cookware liquid container with liquid fakes boiling for effects. Anything else defaults to baking at coefficient 2.

**Per tick** (`UpdateCookingState`, server, once per fireplace cooking update): the item is heated toward the cooking target temperature (see below); if the item is overheated its quantity drops by 25. If the next stage exists and `item temperature >= min temp` and min temp > 0, cooking time grows by `2 x coefficient` (the "cooking time increase" constant is 2); when it reaches the stage's cook time the stage changes and the timer resets. A stage change in cookware while baking uses up 25 units of Lard if present, otherwise removes 25 units of the food's quantity; changes outside baking in cookware do not charge anything (as read), and direct cooking removes 25 quantity at every stage change. Items that cannot be cooked but sit in the fire are heated, lose quantity if they overheat (2 per tick for solids, 2 for boiling liquids) or take 5 % of their health per tick if they cannot overheat; boiling liquids lose all agents except heavy metal.

**Heating path.** `AddTemperatureToItem` sets `TemperatureDataInterpolated(target, ACCESS_COOKING, update interval, coefficient 2.0, heat-permeability)` where the permeability is the product of the cookware's and the item's. Target temperature: the hierarchy root's `GetCookingTargetTemperature` (a fireplace returns its own current temperature; a gas stove returns 400 °C), else the cookware's temperature, else 150 °C (the default, also used for food on a stick). A gas stove advances cooking time at half rate (`0.5 x time factor`). Max food temperature constant 150. Food on a stick uses `CookOnStick` (always the baking stage chain, heating only when the food is an attachment). Smoking (`SmokeItem`): once the item is at the Dried minimum temperature, Raw becomes Dried after the Dried cook time; any other stage becomes Burned after that time.

**Rotting** (`Edible_Base.ProcessDecay`, only when not frozen and not already Rotten; skipped by the server-wide `FoodDecay` global when it is 0). The timer per stage, in seconds, plus up to 25 % random extra, runs down at `delta x FoodDecay x (1 + (1 - health01))`, plus 2.5 when the item is in a player's hierarchy (`DECAY_RATE_ON_PLAYER`):

| Kind | Raw | Boiled | Baked | Dried |
|---|---|---|---|---|
| Fruit, vegetable, mushroom | 43,200 | 172,800 | 259,200 | never |
| Meat | 21,600 | 259,200 | 345,600 | 691,200 |
| Corpse (animal) | 32,400 | none | none | none |
| Opened can | 172,800 to food poison | | | |

Burned and Rotten never decay further. When a raw fruit or vegetable timer ends, 43 % of the time it becomes Dried (if the item has a Dried stage), otherwise Rotten; every other expiry becomes Rotten. An opened can does not rot: its timer expiry inserts the FOOD_POISON agent. `FoodDecay` is a Central Economy global (name read from `GetCEGlobalFloat("FoodDecay")`); the stock `globals.xml` of the server missions sets it to 1 (full speed).

**Open:** which classes derive `IsFruit`/`IsMeat` was not enumerated; the engine side that applies `ACCESS_COOKING` temperature changes was not looked at. Backlog items 3 (cooking path) and 11 (food stages) are closed by this section.

### 6.21 Stat levels: health, blood, energy, water, immunity (task S6, addendum to 6.11) [obs]
There is no stamina "level" mapping; the `GetStatLevel*` family in `PlayerBase.c` (about line 5455 to 5580) turns the main stats into a five-step `EStatLevels` enum (0 GREAT, 1 HIGH, 2 MEDIUM, 3 LOW, 4 CRITICAL) using thresholds in `PlayerConstants.c`. The rule is the same for all of them: `value <= critical` gives CRITICAL, `<= low` LOW, `<= normal` MEDIUM, `<= high` HIGH, anything above GREAT.

| Stat | critical | low | normal | high | max (for borders) |
|---|---|---|---|---|---|
| Health | 15 | 30 | 50 | 80 | stat max |
| Toxicity (uses the health thresholds, not the toxicity ones) | 15 | 30 | 50 | 80 | stat max |
| Blood | 3000 | 3500 | 4000 | 4500 | stat max |
| Energy | 0 | 300 | 800 | 3500 | 5000 |
| Water | 0 | 300 | 1000 | 3500 | 5000 |
| Immunity (fraction) | 0.15 | 0.35 | 0.72 | 0.95 | 1 |

- `GetStatLevelToxicity` calls `GetStatLevel` with the **health** thresholds; `SL_TOXICITY_*` (20 / 40 / 60 / 80) are defined in `PlayerConstants.c` but have no use in this function [obs; whether they are used elsewhere was not searched, so treat as unused only for this path].
- Immunity returns GREAT whenever the player is immunity-boosted (`m_ImmunityBoosted`), regardless of the value.
- `GetStatLevelBorders*` returns a continuous 0 to 1 position inside the current band: `InverseLerp(0, critical, v)` below critical, then `InverseLerp(critical, low, v)`, and so on, with the last band running from `high` to the stat's maximum. It is used for gauge-style displays; each band therefore fills 0 to 1 separately.
- Where the levels are read: the hunger, thirst, health and blood notifiers (arrow icons), `BloodRegen` (below), `PlayerAgentPool` (immunity level scales infection), the pulse-check actions (report the target's blood level) and a developer sync window.
- `BloodRegen`: water level MEDIUM or energy level MEDIUM multiplies blood regeneration by 0.65, LOW or CRITICAL by 0 (the test is `>= LOW` because the enum counts upward toward CRITICAL), and GREAT and HIGH by 1.
- Dehydration and starvation damage start at `LOW_WATER_THRESHOLD`/`LOW_ENERGY_THRESHOLD`, which are set equal to the 300 low thresholds above.
