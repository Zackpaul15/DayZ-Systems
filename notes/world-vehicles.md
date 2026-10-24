# World, server economy, vehicles and base building

Part of the DayZ static analysis notes (see `README.md` in this folder for the map). Section numbers are the original ones, so cross-references such as "see 6.10" still resolve.

### 5.6 Server mission data: gameplay config and the Central Economy [obs unless noted]

Source: the four `worlds_*_ce.pbo` archives. Each holds the **server mission template** for one map: 42 to 43 plain-text files plus a large binary. I read the Chernarus one (`DZ\worlds\chernarusplus\ce`) in full; Enoch's has the same layout. The files are uncompressed XML and JSON. Selected numbers are in `data\loot_types_chernarus.csv`.

| File | Purpose |
|---|---|
| `cfggameplay.json` | Server-tunable gameplay values (version 123) |
| `db\globals.xml`, `db\economy.xml` | Economy-wide variables and which object groups persist |
| `db\types.xml` | One row per spawnable item type: how many, how long, where |
| `db\events.xml` | Dynamic events: animals, infected groups, vehicles, crashes, convoys |
| `cfgeconomycore.xml`, `cfglimitsdefinition*.xml`, `cfgignorelist.xml` | Root classes, allowed category / usage / tier tags, items ignored by the economy |
| `cfgspawnabletypes.xml`, `cfgrandompresets.xml` | What an item or container spawns holding (attachments, cargo) |
| `cfgeventgroups.xml`, `cfgeventspawns.xml` | Group layouts and spawn positions for events |
| `cfgplayerspawnpoints.xml` | Where new players appear |
| `cfgweather.xml`, `cfgenvironment.xml`, `env\*_territories.xml` | Weather limits; animal and infected territories |
| `cfgeffectarea.json`, `cfgundergroundtriggers.json` | Contaminated areas; underground zones |
| `mapgroup*.xml`, `areaflags.map` | Building loot positions (4.6 to 4.7 MB each) and an 84 MB area-flag grid |

**`cfggameplay.json`** (defaults as shipped). Every key maps onto the script-side `CfgGameplayHandler` data classes read in 6.11 and 5.1, which confirms those scripts are driven by this file.
- *General:* base and container damage on, respawn dialog on.
- *Stamina:* sprint modifiers 1.0 (standing, crouched, swimming, ladder), max 100, weight threshold 6,000 g, 1.75 per kg penalty, minimum 5, melee, obstacle and hold-breath modifiers 1.0.
- *Shock:* refill 5 (conscious) and 1 (unconscious) per second, refill modifier on.
- *Movement:* time to sprint 0.45 s, time to strafe sprint 0.3 s, time to strafe jog 0.1 s, rotation speeds 0.15, "stamina affects inertia" on.
- *Drowning:* stamina, health and shock deplete at 10 per second.
- *World:* `environmentMinTemps` and `environmentMaxTemps` are the Chernarus tables from 6.10 (`-3, -2, 0, 4, 9, 14, 18, 17, 13, 11, 9, 0` and `3, 5, 7, 14, 19, 24, 26, 25, 18, 14, 10, 5`), so a server can override the map's climate. `wetnessWeightModifiers` = `1.0, 1.0, 1.33, 1.66, 2.0`: an item's weight multiplier at dry, damp, wet, soaked and drenched.
- *Base building:* a long list of placement checks, each switchable (all on except the cold-area check); no fences, territory flags or watchtowers underground.
- *UI and map:* hit-direction indicator style, colour `0xffbb0a1e`, 2 s, scatter 10; 2D map; player position hidden; navigation info shown.
- *Vehicles:* boat decay multiplier 1; wheels can be detached and damaged on cars and bikes.

**`db\globals.xml`** (29 variables). Highlights: up to 200 animals and **1,000 infected**; cleanup lifetimes in seconds (dead player 3,600, dead animal 1,200, dead infected 330, ruined item 330, default 45); flag refresh every 432,000 s (5 days) for up to 3,456,000 s (40 days); loot damage between 0.0 and 0.82; food decay on; initial spawn 100 and spawn-initial 1,200; zone spawn distance 300 m; player timing for logout, login and hopping 15 / 15 / 60 s with a 20 s penalty.
**`db\economy.xml`:** eight groups flagged for init, load, respawn and save: dynamic objects, vehicles, buildings and players are saved; animals, infected and randoms are not (animals and infected are created at start and respawn).

**Loot table (`types.xml`)**: **2,382 item types**.
- *Targets:* a "nominal" (how many should exist on the map) and a "min" (restock trigger). The nominals sum to **21,090**; **1,267 types have nominal 0** (not placed by the economy, only craftable or found otherwise). The highest nominal is 120 (hatchet, headtorches); 100 for common ammo, batteries, rope and sacks.
- *Timing:* the usual `lifetime` is 14,400 s (4 h) for 1,293 types, then 28,800 s (441 types) and 1,800 s (383). Car tents live 3,888,000 s (45 days) with a 43,200 s restock. 22 types have the 45-day lifetime.
- *Categories (types / nominal sum):* clothes 811 / 7,954, tools 280 / 6,482, weapons 302 / 3,677, loot-dispatch 196 / 1,045, food 111 / 831, containers 112 / 767, explosives 15 / 129, no category 555 / 205.
- *Where it spawns:* each type has `usage` tags (Town 469, Village 446, Military 384, Industrial 300, Farm 152, Hunting 116, School 71, Police 62, Medic 56, Coast 45, Office 43, seasonal event 41, Firefighter 21, Lunapark 21, ContaminatedArea 19, Historical 13, Prison 8) and `value` tags for four tiers (Tier1 205 items, Tier2 337, Tier3 312, Tier4 213, plus 8 unique).
- *Examples (nominal / min):* M4A1 1 / 1 (contaminated areas only), AKM 3 / 2 (military, tier 4), SVD 4 / 2, Mosin 45 / 35 (town and village, tiers 2 to 4), FNX45 14 / 12, plate carrier 2 / 1, Mich helmet 4 / 2, gas mask 10 / 8, bandage 40 / 30, cola 20 / 16, mountain backpack 10 / 7, blue jeans 35 / 25, STANAG magazine 5 / 2, 5.56 ammo 50 / 30, car tent 8 / 4.
- *Quantity:* each type has a `quantmin` / `quantmax` range, a percentage of capacity (weapons 30 to 80, STANAG magazine 5 to 50, 5.56 ammo 10 to 40); -1 means not applicable.
- `cfgignorelist.xml` lists 24 types that the economy ignores (for example a bandage, bandana masks, a cattle prod, the transit bus, flare gun and flares).

**Dynamic events (`events.xml`, 61 events).**
- *Infected:* 19 groups (`InfectedCity` with 43 child layouts, Village 24, Industrial 26, Solitude 19, Medic 13, Army, Police, Firefighter, NBC, Prisoner, Religious and the seasonal Santa and Spooky ones). Typical settings: nominal 50, min 25, max 100 or 250, lifetime 3 s.
- *Animals:* cow 7, deer 9, roe deer 10, goat 8, sheep 5, pig 6, wild boar 7, wolf 8 (min 4, max 6), bear (min 2, max 2), plus ambient fox, hare and hen; lifetime 180 s.
- *Vehicles:* sedan, hatchback, offroad and truck 8 each (3 for the offroad 02), motorbike 25, boats 17; lifetime 300 to 600 s.
- *Static events:* helicopter crash 3 (lifetime 2,100 s), military convoy 6, police situation 5, train 3, contaminated area (2 to 4), airplane crate 9. Inactive in this file: the police car, bonfire, Christmas tree, Santa crash and a test fridge.
- *Plants/loose loot:* fruit trajectories (apple, pear, plum, and others, nominal 140) and stones (100).
- 61 events in total, **10 of them inactive** (the NBC yellow, Santa and spooky infected, the police car, bonfire, Christmas tree, Santa crash, the test fridge, and two plant trajectories).

**Other files.**
- `cfgweather.xml` ships disabled (`enable="0"`). It sets overcast, fog, rain, wind (0 to 20 m/s), and storm limits: the fog stays between 0.02 and 0.08, rain only occurs when overcast is above 0.6, lightning needs overcast 0.9 and fires every 45 s, snowfall is 0 for this map.
- `cfgenvironment.xml` lists herd territories (deer, cattle, sheep and goat, roe deer, wolf, wild boar, pig, bear and others) with the group behaviour class for each.
- `cfgeffectarea.json`: **9 contaminated areas** in Chernarus (four ship sections and five Pavlovo areas), each with position, radius and gas-cloud particle settings.
- `cfgspawnabletypes.xml`: 721 type entries (342 with attachment lists, 534 with cargo); `cfgrandompresets.xml`: 78 random presets (for example "foodHermit", "foodVillage", "foodCity", "foodArmy", "toolsHermit"); `cfgeventgroups.xml`: 83 groups with 874 members; `cfgeventspawns.xml`: 35 spawn lists with 1,532 positions.
- `cfgplayerspawnpoints.xml`: three sets, **fresh** (11 groups, 49 positions), **hop** (10, 50) and **travel** (10, 50).
- `cfgeconomycore.xml` declares the root classes the economy tracks: weapons, magazines, inventory items, houses, survivors and infected/animals (as characters), cars, boats and motorbikes (as vehicles). It turns every economy log option off.

**How this ties to the rest.** The loot tags (usage, tier, category) are the economy's version of the class families in 5.1; the infected and animal events feed the creature classes in 5.4; and the gameplay config overrides the defaults the survival scripts in section 6 use.

### 5.7 Vehicles, base building and fireplaces [obs unless noted]

Sources: `4_World\Entities\Vehicles\{CarScript, MotorbikeScript, BoatScript}.c` plus the vehicle components, the engine-facing `3_Game\Vehicles\Car.c`, `4_World\Classes\ConstructionBase.c`, `ConstructionPart.c`, `BaseBuildingBase.c`, `Hologram.c`, and `FireplaceBase.c`, with per-vehicle and per-kit numbers from the merged configs.

**Vehicle scripts.**
- `Car.c` is the engine boundary: `proto native` calls for throttle, brake, clutch, gear, RPM, fluid fractions (`GetFluidFraction`), `Leak`, `Fill` and wheel queries. Four fluids: fuel, coolant, oil, brake. Gearboxes are manual or automatic, with gears up to eleventh.
- `CarScript` (2,981 lines) holds the gameplay rules; `MotorbikeScript` and `BoatScript` are separate classes. Lights, horn and VFX are components.

**Engine start** (`CheckOperationalRequirements`). It fails when any of these holds: the vehicle or its engine is ruined; the fuel fraction is 0 or less; the battery is missing, ruined, or holds less energy than the ignition costs; the spark plug or glow plug is missing or ruined. Starting spends battery energy. While the engine runs the alternator recharges (script constant 0.15); with the engine off, lights drain it (0.25). Script default ignition cost is 15; the sedan config overrides it (`electricConsumptionIgnition` 3001).

**Fluid leaks** (`LeakFluid`, per tick). Coolant loss is `(1 - radiator health) * rand(0.02, 0.05)`, oil is `(1 - engine health) * rand(0.02, 1.0)`, fuel is `(1 - fuel tank health) * rand(0.02, 0.05)`. Constants: tick range 0.02 to 0.05, leak threshold 0.5.

**Crash damage to occupants** (`DamageCrew`, from the contact impulse). Below 750 nothing; 150 is the minimum counted; at 1,200 or more the crew die. In between, shock = Lerp(50, 150) and health damage = Lerp(2, 100) of `InverseLerp(750, 1200, impulse)`. Drowning the engine: threshold 0.5 water depth, 350 damage.

**Per-car numbers** (17 spawnable `CarScript` classes; the main ones):

| Vehicle (class) | Fuel (L) | Drive | Peak torque | Redline | Gears | Notes |
|---|---|---|---|---|---|---|
| Ada 4x4 (OffroadHatchback) | 42 | AWD | 114 | 6,000 | 4 | |
| Olga 24 (CivilianSedan) | 55 | RWD | 187 | 4,700 | 4 | 4 seats |
| Gunter 2 (Hatchback_02) | 55 | FWD | 186 | 6,250 | 5 | |
| Sarka 120 (Sedan_02) | 38 | RWD | 82 | 5,750 | | |
| M1025 (Offroad_02) | 115 | AWD | 384 | 3,700 | | |
| M3S (Truck_01, covered and cargo) | 120 | 6x4 / 6x2 | 340 | 2,400 | | 2 seats |
| Jana (motorbike) | 3.5 | | | | | |
| Rubber boat | 25 | | | | | |

Oil capacity is 4 and coolant 6 on the cars. The sedan's damage zones are chassis, front, back, roof, four fenders, front and rear windows, two reflectors, engine and fuel tank. Its simulation: steering up to 35 degrees, torque curve (rpm:Nm) 400:0, 1000:157, 1700:183, 2500:187, 4500:147, 6000:0, idle 900, gear ratios 3.5 / 2.26 / 1.45 / 1.0, reverse 3.51. Central Economy spawns: sedan, hatchback, offroad and truck 8 each, motorbike 25, boats 17 (see 5.6).

**Base building: the construction model.** Everything buildable is described by a `Construction` tree in config, run by `ConstructionBase`. A kit has *groups*; each group has *parts* with an id, `required_parts`, `conflicted_parts`, collision data, build and dismantle action types and a material list (`type`, `slot_name`, `quantity`). Runtime: `BuildPartServer`, `DismantlePartServer`, `DestroyPartServer`, support checks, an item-fall pass that re-throws items that lose their support, and part state sent as bit masks.

Fence "wall" group (11 parts; mats are materials and counts):

| Part (id) | Needs | Materials |
|---|---|---|
| base (1) | none | 2 wooden logs |
| wall_base_down (6), wall_base_up (9) | base | 4 planks, 8 nails |
| wall_wood_down (7), wall_wood_up (10) | matching base | 5 planks, 10 nails |
| wall_metal_down (8), wall_metal_up (11) | matching base | 3 metal plates, 12 nails (excludes the wood version) |
| wall_platform (2) | base | 5 planks, 15 nails |
| platform stairs left and right (3, 4) | platform | 4 planks, 8 nails each |
| wall_gate (5) | base plus both wall bases | metal wire, quantity -1 (a special case) |

Watchtower: 12 groups, three levels of (level group plus three wall groups); level 1 holds base, stairs and roof. Territory flag totem: base (1 log), support (32 stones and 6 logs), pole (3 logs, 60 nails; wire and rope listed with quantity 0).

**Decay and repair** (`ProcessConstructionDecay`). Built parts that allow decay lose health at `-1 HP/s` by default times a coefficient (1.0, or 1.5 during a sandstorm) until health falls to 30% of its maximum, then stop. Repair uses 15% of the material cost; dismantling loses 20% of the materials. At most 64 material piles spawn on a collapse. Parts reaching ruined state are removed from the construction.

**Fireplaces** (`FireplaceBase`, constants from the script).
- *Temperature:* small fire up to 150 C, normal 1,000 C, outdoor 500 C; below 30 C the fire is inactive. Heating +10 C per second, cooling -3 C per second, updated every 3 s.
- *Ignition limits:* wetness at most 0.2 to ignite, 0.4 to keep burning; rain at most 0.1 to ignite, rain above 0.4 soaks the fire (snowfall 1.5); wind above 0.8 of the maximum blocks ignition; needs 5 m of clear height; not in water.
- *Fuel:* base consumption 0.5 per update, scaled by 1.0 (default), 0.92 (stone circle) or 0.85 (oven).
- *Heat reach:* full heat within 2 m, partial to 4 m; at most 20 degrees is passed to a player's environment (the feed into 6.10). Cooking starts at 100 C; 3 direct cooking slots and 4 smoking slots.
- *Stones:* a circle needs 8, an oven 16; an oven cannot be dismantled above 40 C. Lifetimes: circle 172,800 s (2 days), oven 604,800 s (7 days).
- *Fire damage:* items left in the fireplace cargo take burn damage with a coefficient of 5.

Not covered: the `Hologram` placement checks, tents and gardening, vehicle wheel and door state machines, and boat physics.

### 5.9 Placement hologram, tents and gardening [obs unless noted]

Follow-up to 5.7. Sources: `4_World\Classes\Hologram.c` (placement preview), `4_World\Entities\ItemBase\TentBase.c`, `4_World\Entities\GardenBase.c`, `GardenBase\{Slot, PlantBase}.c`, `Gear\Cultivation\cultivation.c`, the gardening actions, and the matching config values.

**The placement hologram.** When a player deploys an item (a kit, tent, fireplace, trap, garden plot and so on) a `Hologram` spawns a local, non-colliding copy of the item's `projectionTypename` class (or the item itself) and moves it with the camera. Every update `EvaluateCollision` decides whether the preview is red.
- *Where it floats:* a ray from the camera; the preview is kept between a minimum and maximum distance from the player. For objects with a radius under 1 m the range is 1 to 2 m; larger ones use their radius to twice their radius, capped at 6 m. At either limit the preview counts as *floating* and is refused. A watchtower's trigger-box components are corrected so the preview does not hover.
- *Per-item config:* `slopeTolerance` (max height difference of the four base corners to the preview position; garden plot 0.3), `alignHologramToTerain`, and `yawPitchRollLimit` (maximum tilt).
- *The checks, in order* (the item is "colliding" if the first one that applies fails): the player can place it at all; not floating or hidden; no overlap with other geometry, tested twice (an oriented box lifted 5 cm, and the model's geometry proxies); not overlapping a player; not clipping a roof (the preview is not above the camera and has no roof overhead); the base is viable (see below); not overlapping a garden plot (`IsCollidingGPlot`); not at the world origin; tilt within the limit; the item's own `CanBePlaced`; height within 1.5 m of the player's feet (`DEFAULT_MAX_PLACEMENT_HEIGHT_DIFF`); not under water (surface liquid, or any corner under sea level plus 3 cm, or with water depth); not poking into terrain (rays from 0.3 to 1.3 m above each corner). Traps add their own `IsPlaceableAtPosition` check at the end.
- *Base viable:* four rays at the corners (from 1 m above to 2 m below) must all hit the same object or all hit nothing, that object must be static (a building, a plain object, or a base-building part when the item being placed is not a kit), and each corner must be within the slope tolerance.
- *Server vs client:* in multiplayer the roof and base-viable checks run on the client only; the server skips them and relies on the action's own conditions.
- *Switches:* `cfggameplay.json` can disable 14 of these checks (bounding box, player, roof clipping, base viability, terrain, underwater, height, "placement permitted", angle, garden plot, generic collision, roof check, distance, cold area), which is the "placement checks, each switchable" list in 5.6.

**Tents** (`TentBase`). A tent is a two-state item, **packed** (0) or **pitched** (1).
- Only a packed tent can be taken, put in hands or in cargo. A pitched one can be packed only when its cargo and attachments are empty.
- Pitching needs the same height rule as other deployables (within 1.5 m of the player's height) and passes through the hologram above. A pitched tent is a house-like object: proxy physics, a clutter cutter, a navmesh update, and entrance and window toggles.
- Openings are a 16-bit mask (`OPENING_0` to `OPENING_15`), net-synced. Damage zones that reach the ruined level remove the matching proxy collision and open that part.
- A pitched tent that becomes ruined drops everything inside its bounds; a ruined tent cannot receive cargo or attachments. A camouflage net can be attached only while pitched. Container damage is disabled by the gameplay switch ("disableContainerDamage" invulnerability type).
- *Config:* large tent 2,000 health and 90 kg, medium 600 and 3 kg, car tent 1,700 and 60 kg, party tent 1,400 and 30 kg. These are the "tent" rows behind the 45-day lifetime of car tents in 5.6.

**Gardening.** A **garden plot** (weight 100 kg item, slope tolerance 0.3) has **9 slots** (`SeedBase_1` to `9`).
- *Workflow:* place a plot, get a slot into the `DIGGED` state (a digging action; I did not read it), plant a seed (only into a digged slot), water it, optionally fertilize, harvest. Seed packs hold 10 seeds.
- *Water:* a slot needs at least **190 ml** (`m_WaterNeeded`) to count as watered and holds up to **200 ml**. Without enough water a plant is `PAUSED`. Rain waters all slots every 15 s when rain is above 0.05: each slot gains `rain x 20 x 15 x random(0 to 1)` ml, up to the cap.
- *Fertilizer:* each slot accepts one fertilizer type. Garden lime adds fertility 1.0 for 250 g consumed; plant material (compost) adds 0.5 for 100. Fertility starts at the plot's base value (1) and **multiplies the crop count**: crops = `ceil(base crops x fertility x harvesting efficiency)` [inf: efficiency is 1.0 in the code I read, so a fully fertilized slot can roughly double the harvest].
- *Growth:* `PAUSED -> GROWING -> MATURE -> SPOILED`, with `DRY` as the failure state. The growth stage count (6 or 7) and crop count come from config; the time to full maturity is set in script (plus a random -60 to +180 s per plant):

| Plant | Stages | Crops | Full maturity |
|---|---|---|---|
| Tomato | 6 | 7 | 1,650 s (27.5 min) |
| Zucchini | 7 | 2 | 1,350 s (22.5 min) |
| Pepper | 6 | 3 | 2,250 s (37.5 min) |
| Potato | 6 | 3 | 2,850 s (47.5 min) |
| Pumpkin | 7 | 2 | 2,850 s (47.5 min) |
| Cannabis | 6 | 7 | not set in script |

- Each growth step takes full maturity divided by (stages - 2). At every step there is a **0.2 / stages** chance of infestation (about a 20% total over a plant's life); an infested plant that reaches the last stage turns `DRY` and dies instead of ripening. Sprayable: the spray usage is 5 units.
- A mature plant spoils after **4 hours** (14,400 s); a spoiled plant disappears 20 to 25 min later and a dry plant 10 to 12 min later, freeing the slot. Harvesting spawns the crops at the player's feet at full quantity and marks the plant as having no crops.
- Slots keep water, fertility, fertilizer type and harvesting efficiency in the save file; watered and fertilized flags are net-synced as three integer bitmaps each (slots 1 to 4, 5 to 8, and 9).

**Not covered:** the gardening and tent action classes in detail, tent navmesh handling, sound, and the animals' interaction with traps.

### 5.10 Restricted areas and the bunker broadcast (task W4) [obs unless noted]

Sources: `3_Game\CfgPlayerRestrictedArea{Handler,JsonData}.c`, `3_Game\CfgBunkerBroadcast{Handler,JsonData}.c`, `3_Game\MorseCodeConverter.c`, `4_World\Classes\BunkerBroadcast{Handler,Scheduler,Component,Proxy}.c`, the `PlayerBase` and `missionServer` call sites, and the shipped mission files (`pra\warheadstorage.json`, `cfgbunkerbroadcast.json`, `cfggameplay.json`).

#### Player restricted areas

**What they are.** Zones where a player may not be when they load in. They are not a live barrier: the only enforcement found is in `PlayerBase.AfterStoreLoad`. When a stored player is restored, the position is tested against every area; if it is inside one, the player is teleported to one of that area's **safe positions** and an admin-log line "Spawning in Player Restricted Area: <name>" is written. [obs; no other caller exists besides the Diag menu's "PRA - detect" and "Show PRA" options]

**Where the list comes from.** `CfgPlayerRestrictedAreaHandler.LoadData()` runs in the server mission start (`missionServer.c:90`). With the server setting `enableCfgGameplayFile` on, it reads the `playerRestrictedAreaFiles` array from `cfggameplay.json` (`WorldsData` block); otherwise it uses the map's defaults. Each file is tried first as `$mission:<file>`, then as `dz/worlds/<map>/ce/<file>`. The server sends the loaded areas to each connecting client by RPC (`RPC_PLAYERRESTRICTEDAREAS_SYNC`). Only **Sakhal** ships a default (`pra/warheadstorage.json`, also listed in its `cfggameplay.json`); Chernarus, Livonia and Nasdara have none.

**File format** (one area per file; `PlayerRestrictedAreaInstance`):

| Field | Type | Meaning |
|---|---|---|
| `areaName` | string (optional) | name used in logs |
| `PRABoxes` | list of boxes | each box is three vectors: sizes `[x,y,z]`, rotation `[yaw,pitch,roll]`, position `[x,y,z]`; the box is centred on the position |
| `PRAPolygons` | list of polygons | each polygon is at least three `[x,z]` points (2-D, any height) |
| `safePositions2D` | list of `[x,z]` | height is taken from the terrain at that point |
| `safePositions3D` | list of `[x,y,z]` | used as given |

An area is valid only if it has at least one box or polygon, every box has all three vectors in XYZ form, every polygon has 3 or more points of 2 numbers, and there is at least one safe position. Invalid areas are logged and dropped. **Test:** a player is inside if a vertical cylinder of radius 0.25 m and height 1 m intersects any box (oriented-box test), or the player's X and Z lie inside any polygon. Safe positions are handed out in shuffled round-robin order (never the same one twice in a row until the list is used up). [obs]

**The shipped example** (`warheadstorage.json`, Sakhal): area "RestrictedAreaWarheadStorage", one box of 27 x 5.2 x 11 m rotated 108 degrees at (2570, 15.22, 5963.8), and 6 safe positions near (2575, 15.25, 5954). [obs]

#### The bunker broadcast

**What it does.** A server-side event in which several map bunkers become "active", each with a random lock code, and the server **broadcasts the bunkers' map grid positions and lock codes to all players as Morse code** over the radio-like broadcast (the client messages `BunkerCode*` of 4.1 and the `BunkerBroadcastManager` natives). It is **off by default**: `cfggameplay.json` must set `bunkerBroadcastEnabled` to true, and only **Nasdara** does (the only map with a `cfgbunkerbroadcast.json`, with 23 bunker proxies). [obs]

**Configuration** (`cfgbunkerbroadcast.json`; all values are range-checked and the file is rejected if any is out of range):

| Block | Field | Default, range | Nasdara |
|---|---|---|---|
| `bunkerSettings` | `numberOfActive` | 2, 1 to 30 | 3 |
| | `lockCodeLength` | 4, 3 to 6 | 4 |
| | `lockCodeMode` | 0 (digits), 1 (digits and lowercase letters) | 0 |
| `schedulerSettings` | `batchLifetimeLength` (minutes) | 1, 1 to 1000 | 720 |
| | `reportInterval` (minutes) | 1, 1 to 120 | 10 |
| | `periods` (list of `startTime`, `endTime` as "HHMM") | 0000 to 2359 | one period, 17:45 to 06:00 |
| `playbackSettings` | `dotDuration` | 0.3 s, 0.1 to 5 | 0.5 |
| | `dashDuration` | 0.4 s, 0.1 to 5 | 1.5 |
| | `symbolGapDuration` | 0.1 s, 0.1 to 5 | 0.4 |
| | `wordGapDuration` | 0.3 s, 0.1 to 5 | 2.2 |
| | `pauseBetweenBunkers` | 2 s, 0.5 to 10 | 6 |
| | `bunkerRepetitions` | 0, 0 to 3 | 0 |
| | `messageRepetitions` | 0, 0 to 5 | 1 |
| `proxies` | list of `position [x,y,z]` | | 23 |

**How it runs.**
- At start the server spawns a `BunkerBroadcastProxy` at every listed position (an invisible helper bound to the `Bunker` object within 1 m); each proxy has a component holding its lock code and active flag.
- **Scheduling** (`BunkerBroadcastScheduler`, using world time): a period is active when the in-game time is inside any `periods` entry (a period whose start is later than its end wraps midnight; equal start and end means always). While active, a *batch* of bunkers lives for `batchLifetimeLength` in-game minutes, then a new batch is selected (a retry every 5 minutes if none was chosen). A report is sent every `reportInterval` minutes, and also forced at server start if more than 10 minutes passed since the last one (the last report time is stored in persistence).
- **Selection** (`BunkerBroadcastHandler`): bunkers are shuffled and the ones used recently (a history of about half the registered bunkers, at least the active count) are skipped; `numberOfActive` are picked at random. Each gets a freshly generated lock code (digits, or digits and lowercase letters in mode 1; regenerated if it repeats a recent code). Outside an active period the active bunkers are deactivated and their code is set to "-".
- **The report** is, for each active bunker, its map grid coordinates (the six grid digits from the navigation helper, X part then Y part) followed by its lock code, sent as Morse through `BroadcastTextAsMorse` with the playback timings above.
- **Persistence:** the active set and the last report time survive a restart (`BunkerBroadcastPersistenceStorage`).
- The bunker door has a code-lock attachment point (`att_codelock`); entering the broadcast code is how a player gets in. [inf from the attachment name and the code flow; the door interaction code was not read]
- **Diag only:** a fixed lock code `1234` exists under the `BUNKER_BROADCAST_CHEAT_CODE` define, and the Diag menu lists the bunkers; neither is in retail.

**Related message IDs** (4.2): 13 `BunkerCodeStart`, 14 `BunkerCode`, 15 `BunkerCodeEnd` and the setters 16 to 19 for the playback settings.

### 5.11 The Central Economy on all four maps (task W5) [obs unless noted]

5.6 covered Chernarus. The same server-mission templates exist for Livonia (`enoch`), Nasdara and Sakhal. They were extracted with `scripts\bootstrap.py` and tabulated with the new `scripts\ce_types.py`, which reproduces the existing Chernarus table exactly (2,382 rows, identical) before being used on the others. Files: `data\loot_types_enoch.csv`, `loot_types_nasdara.csv`, `loot_types_sakhal.csv` (same columns as the Chernarus one) and `data\maps_compare.csv` (one row per map).

| | Chernarus | Livonia | Nasdara | Sakhal |
|---|---|---|---|---|
| Loot types | 2,382 | 2,391 | 2,411 | 2,404 |
| Sum of nominals (items the economy aims to keep on the map) | **21,090** | 13,800 | **25,080** | 11,662 |
| Types with nominal 0 | 1,267 | 1,352 | 1,308 | 1,363 |
| Types uncategorised | 555 | 573 | 594 | 862 |
| Tier tags (types per tier) | T1 205, T2 337, T3 312, T4 213, Unique 8 | T1 136, T2 229, T3 180, Unique 8 (no Tier 4) | T1 225, T2 378, T3 293, Unique 38 | T1 356, T2 532, T3 353, T4 65, Unique 9 |
| Usual lifetime | 14,400 s for 1,293 types, then 28,800 s and 1,800 s | same ranking | same ranking | same ranking |
| Events (inactive) | 61 (10) | 54 (8) | 62 (23) | 63 (20) |
| Contaminated areas | 9 | 8 | 21 | 50 |
| Fresh-spawn groups / positions | 11 / 49 | 12 / 63 | 1 / 20 | 1 / 39 |
| Hop and travel groups / positions | 10 / 50 each | 6 / 44 each | 1 / 20 each | 1 / 39 each |
| `cfggameplay.json` version | 123 | 123 | **130** | 123 |
| Special settings | none | none | `bunkerBroadcastEnabled` true | player restricted area `pra/warheadstorage.json` |

**Shared and map-specific content.**
- The four maps share **2,357 of 2,460** distinct type names. Chernarus has none of its own; Livonia adds 3 (fox pelt, shrimp and a misspelled winter military coat, `WinterMilitaryCoat_Greay`); Nasdara adds 43 (mostly `Land_House_*` building entries); Sakhal adds 21 (locked containers in four colours, `Land_WarheadStorage_Room*` and similar).
- Of **82 distinct events**, 48 exist on all four maps. Chernarus alone has the desert army infected group and five fruit trajectories (apple, canina, pear, plum, sambucus). Nasdara alone has an ambient lizard, dog and mouflon animals, ION army infected, bricks, a big helicopter crash and a water truck. Sakhal alone has reindeer, heavy-army infected, bonfire infected, scientist infected and static scientist, an ambulance, fishing and military boat statics, a craterellus trajectory and a military boat vehicle event. Livonia has none of its own.
- **Global caps are identical on all four maps:** up to 200 animals, 1,000 infected, dead-player cleanup 3,600 s, loot damage up to 0.82, initial spawn 100.

**Item scarcity differs by map** (nominal counts in Chernarus / Livonia / Nasdara / Sakhal): AKM 3 / 2 / 4 / 2, M4A1 1 / 1 / 1 / 2, Mosin 45 / 16 / 24 / 10, bandage 40 / 15 / 55 / 9, canteen 20 / 20 / 55 / 13, hunting knife 60 / 25 / 25 / 10, hatchet 120 / 85 / 80 / 60. Measured by the sum of nominals against Chernarus, Livonia is at 65%, Sakhal at 55% and Nasdara at 119%, so Sakhal and Livonia are the scarce maps and Nasdara the most generous.

**Notes.** Nasdara's player spawn lists are tiny (one group of 20 positions for fresh, hop and travel alike) next to Chernarus's 11 groups. Sakhal has the most contaminated areas by far (50, against 8 to 21 elsewhere); see 6.15 for what an area does. The big binary area-flag file and the building loot position files were not decoded for any map.

### 5.14 The Central Economy inside the engine (task E1) [obs unless noted]
Static reading of `DayZ_x64.exe` (Ghidra, persistent project). Addresses are image-relative VAs; names are mine. Everything below is decompiled control flow and log strings; none of it was run. 5.6 and 5.11 cover the data; this covers how the engine consumes it.

**1. Loading (the "offlineDB" loader).**
- `FUN_1409aafe0` reads the types file (error "Wrong xml format of types file"); `FUN_1409aab20` handles one `<type>`. The name is hashed (multiplier 37, upper case folded to lower) and looked up in the registered item classes. A miss logs "Type '%s' will be ignored" with one of two reasons: "Type does not exist. (Typo?)" or "Not spawnable. (Scope is not public?)" [obs]. So an item needs config `scope=2` to be usable by types.xml.
- Per-type fields written into the item descriptor (offsets are in the descriptor): `nominal` +0x54 (clamped at 0 or more), `min` +0x58 (clamped to at most nominal), `lifetime` +0x18 and `restock` +0x1c (stored as floats, seconds), `quantmin` +0x60 and `quantmax` +0x64 (percent 0 to 100, stored as fractions; if only quantmin is given the max is taken from the current value), `cost` +0x5c (the unnamed fifth number, matches script `GetCost`) [inf for the name], category id +0x78, then three bit-mask lists `tag` +0x7c, `usage` +0x80 and `value` +0x84. An absent field leaves the previous value, which is how a later file can override an earlier one [obs].
- `flags` attributes become one mask at +0x74: count_in_map 1, count_in_cargo 2, count_in_player 4, count_in_hoarder 8, deloot 0x40, crafted 0x80, always OR 0x100. A second word at +0x88 gets bit 0x01 cleared when `crafted` is set, and bit 0x80 set from `deloot` [obs]. The counting flags decide which of the counters (+0x2c, +0x30) feed the shortfall `nominal - counted` used by the respawner [inf from `FUN_14078fb20`].
- `FUN_1409aa040` reads events ("Loaded %d dynamic events %d total types"); `FUN_1409a9940` handles one `<event>`: `active` 0 sends it to a removal call, `nominal` +0x14, `min` +0x18 (clamped to nominal unless limit is custom), `max` +0x1c, `lifetime` +0x20, `restock` +0x24 (floats), `saferadius` +0x2c and also +0x38, `distanceradius` +0x30, `cleanupradius` +0x34. Flags: init_random 1, deletable 2, remove_damaged 4. `position` word: fixed 0x100, player 0x200, uniform 0x400. `limit` word: parent 0x10000, child 0x20000, mixed 0x40000, custom 0x80000. An unknown position or limit value logs "Unknown value of ... element when parsing event". `secondary` is a name string at +0xb8 and each `<child>` goes to `FUN_1409a9e70` [obs].
- `FUN_1409aa6a0` loads every globals file in the mission folder (error "Failed to read globals file" or "Wrong xml format of globals file"). The root must be `variables`. `FUN_1409aa420` reads each `<var name value type>`: name up to 31 characters, type 0 integer (`strtol`), 1 float (`strtod`), 2 string; any other type is skipped silently. Then the consumers read their keys: `FUN_14078c610` (Cleanup*), `FUN_14078fa10` (loot respawner), `FUN_14078d6c0` (infected), `FUN_1407591b0` (`ZombieMaxCount` into +0xf8 and `AnimalMaxCount` into +0xfc of the manager), `FUN_140777b30` (`LootDamageMin` default 0 and `LootDamageMax`; the max is raised to the min if lower, and nothing is stored unless a max is given) [obs].

| Consumer | Keys read (all default to "unset" so the compiled value stays) |
|---|---|
| Cleanup (`FUN_14078c610`) | CleanupAvoidance, CleanupLifetimeLimit, CleanupLifetimeDefault, CleanupLifetimeRuined, CleanupLifetimeDeadPlayer, CleanupLifetimeDeadInfected, CleanupLifetimeDeadAnimal |
| Loot respawner (`FUN_14078fa10`) | RespawnTypes, RespawnAttempt, SpawnInitial, RestartSpawn, InitialSpawn, LootProxyPlacement, LootSpawnAvoidance |
| Infected (`FUN_14078d6c0`) | RespawnLimit, ZoneSpawnDist |
| Manager | ZombieMaxCount, AnimalMaxCount, LootDamageMin, LootDamageMax |

**2. The CE loop.** `FUN_140765c10` builds a table of named stages, each a 0x50-byte record (kind, order, name, flag bits, period fields, callback). Names, in registration order: `iterate`, `estimate`, `cleanup`, `save_start`, `save_world`, `save_animal`, `save_vehicle`, `save_infected`, `save_building`, `save_de`, `save_type`, `save_players`, `save_doors`, `save_end`, two stages whose names sit in unlabelled strings, `infected`, one more unlabelled, and the loop stage `FUN_140763740`. The save stages carry bit masks (world 0x20, animal 0x80, vehicle 0x200, infected 0x100, building 0x4000, de 0x10, type 4, players 0x8000, doors 0x10000) that select which persistence file each writes [obs]. A stage with a period of two or more is run on a counter that wraps; `FUN_140757810` stores `period - 1` as its trigger value [inf].
- `cleanup` (`FUN_1407634a0`): if a configuration flag at +0x13a is set it queues a reason-2 job and then calls the pop routine `FUN_14078b320` until the queue is empty; in any case it drains the queue [obs].
- `estimate` (`FUN_140763530`) calls `FUN_140763b90` and, if that returns true, sets a flag on the stage record [obs]; its meaning is [?].
- Loop stage (`FUN_140763740`): advances the stage counters, asks the player-count routine, and handles idle mode. With zero players it loads a countdown from a 16-bit configuration value (+0x136); when a player appears and the countdown is below zero it logs "[IdleMode] Leaving OUT". The debug flag at +0x104 prints "CE Loop took %0.1f (sec)", the player, loot, infected and animal counts, and either "Idle Mode Counting in %0.0f (sec)" or "Idle Mode Active!" [obs]. What idle mode skips is [?].

**3. Cleanup reason codes** (`FUN_14078b3e0`, log only): 1 "Depleted", 2 "Remove", 3 "Default Lifetime", 4 "Ruined Lifetime", 5 "Outside world". These map onto the Cleanup* globals [inf]; the loop that reads the lifetime counters is not yet traced [?].

**4. Loot spawning.**
- Per-type step (`FUN_14078fb20`): runs only when a mask bit (0x10 in the manager word) is set. It takes the next type from the candidate list, computes the shortfall as `nominal - (counter_a + counter_b)` when the count flag (+0x88 bit 5) is set and zero otherwise, caps it by a per-pass limit, and forces it to 1 when `restock` is above 0 [inf]. It calls the spawn routine; on success it counts a pass, and if `restock` is above zero and the count is still under nominal it copies the restock into the timer at +0x20 and sets a flag at +0x69. With logging on it prints "[RESPAWN CANDIDATE] ... missing:%d [cnt, nom, min]" [obs].
- Spawn routine (`FUN_14078f3a0`): first tries a placement through the proxy and cluster tables keyed by the item's category id; then two candidate lists with a random start and random direction. The random generator is the Microsoft linear congruential one (multiplier 0x343fd, increment 0x269ec3), shared with other engine code [obs]. A per-call test budget (`DAT_14123dadc`) limits attempts. Log lines: "Item exceeded max tests", "Item [%d] is hard to place, performance drops" and "Item [%d] causing search overtime" [obs]. The first list is tried with a "count limit" on; the second without.
- Candidate test (`FUN_140790480`): the container must have a parent ("Container missing parent"). The item's `value` mask (+0x84) must intersect the container's mask at +0x58 and its `usage` mask (+0x80) the one at +0x54, a zero on either side meaning "any"; the item's tag masks (+0x78, +0x7c) are checked the same way against two masks on the container's owner; a per-container count cap (+0x4c below +0x50) applies on the first pass; a pair of item floats must not exceed the container's pair at +8/+0xc; and when the loot-avoidance value is above zero a player-proximity test (`FUN_14077c520`, radius = avoidance + container radius) rejects the spot [obs for the gate structure, inf for the names of the masks].
- Placement (`FUN_14078fdb0`, `FUN_140790060`): create the entity (`FUN_1407679c0` with flag 0x6072), check it lies inside the zone's horizontal radius and height band, otherwise mark it dirty with 0x200 and re-register; then give the item its lifetime with a random jitter of the form `lifetime * (1 + rand * k)` [inf] [obs for the call, inf for the meaning].

**5. Script natives.** `FUN_140787e10` registers `CEApi` (about 70 methods) and `FUN_140757ab0` the class `CEItemProfile`:
- Item profile reads: GetNominal, GetMin, GetQuantity, GetQuantityMin, GetQuantityMax, GetLifetime, GetRestock, GetCost, GetUsageFlags, GetValueFlags.
- Spawning: SpawnLoot, SpawnGroup, SpawnDE, SpawnDEEx, SpawnDynamic, SpawnVehicles, SpawnBuilding, SpawnRotation, SpawnEntity, SpawnSingleEntity, SpawnAnalyze, SpawnPerfTest, InfectedSpawn, AnimalSpawn, AnimalAmbientSpawn, DynamicEventSpawn.
- Lifetime and damage: OverrideLifeTime (sets one value into two sub-objects, +0xe8 of the second manager and +0xd4 of the first), RadiusLifetimeIncrease, RadiusLifetimeDecrease, RadiusLifetimeReset, LootDepleteLifetime, LootSetDamageToOne, LootDepleteAndDamage, TimeShift, CleanMap, InfectedResetCleanup.
- Queries: GetCEGlobalInt, GetCEGlobalFloat, GetCEGlobalString (read the globals variables above), AvoidPlayer, AvoidVehicle, CountPlayersWithinRange.
- Tooling and diagnostics (names only): ExportSpawnData, ExportProxyData, ExportClusterData, ExportProxyProto, Mark/Remove/ListCloseProxy, EconomyLog, EconomyMap, EconomyOutput, DynamicEventExport, ToggleOverallStats, the visualisation toggles, Loot* group export and editing helpers. These look like editor and diagnostic aids [inf].
- Only `OverrideLifeTime`, `RadiusLifetimeIncrease` (forwards radius and two numbers to `FUN_14078c3d0`) were opened. The other bodies are labels not yet read [?].

**The sweeper's two passes (E1 follow-up) [obs structure, inf meaning].** The sweeper object (`DAT_141832b80`) keeps one list of all tracked objects plus 24 slice lists (24 entries of 16 bytes starting at +0x2218, 0x180 bytes in all). Both workers take a slice number: zero or less means the full list, a negative number means every slice in turn, a positive one means that slice only. [obs]
- **Cleanup pass** (`FUN_1405ad1c0`): for each object it calls a virtual method (vtable slot 0x30) on the object's CE sub-record at +0xA8. If that returns null, or a second check (`FUN_14094c060` on `FUN_14094b410`) is true, the object is handed to the cleanup queue (`FUN_14078b9e0` on the CE service's field +0x38), which is the enqueue path described above. So the pass itself holds no countdown; the expiry decision sits behind the virtual call. [obs structure, inf: slot 0x30 is the "is it still alive" test]
- **Estimate pass** (`FUN_1405ad3b0`): for each object it calls vtable slot 0xA0 on the same sub-record with a fixed argument (`DAT_141744d38`); when that returns true the object is passed to the counting routine `FUN_140757eb0` on the CE service's field +0x20 with the value 1. [obs] This is the per-slice item count that the nominal/min comparison uses. [inf]
- **Job builders**: `FUN_14078c450` appends one 0x38-byte job record (type, a 3-int payload, two parameters, a -1 default) and sets a field from the queue when the type is 2. The two RadiusLifetime wrappers call it with job types 0x200 (`FUN_14078c390`) and 0x400 (`FUN_14078c410`) and then run the queue pop `FUN_14078b320`. [obs]
- **Area flags**: the loader `FUN_140770df0` reads four ints and builds two grids (`FUN_14078c710`, filled by `FUN_14078c7f0`). [obs] I did not find the placement test that reads them, so their role in placement stays [?].
- **LootDepleteLifetime / LootDepleteAndDamage / LootSetDamageToOne**: the registered labels (`0x140787c50`, `0x140787c70`, `0x140787d30`) are 19-byte thunks, each loading two data addresses and jumping to the same shared routine at `0x1402cdaf0`; their only caller is the registration function `FUN_140787e10`. So the script natives share one forwarder and the per-name behaviour lives in the data the thunk passes, which I did not follow. [obs thunk, ?] meaning.

**Still not traced [?].** What the virtual slots 0x30 and 0xA0 do for each object kind (the actual lifetime countdown and what refreshes it, such as player proximity or FlagRefresh); the callback at `0x140763730` (a bare label, no function); the two unnamed stages; the shared forwarder at `0x1402cdaf0`; infected zone spawning (`FUN_14078ce20`), the vehicle respawner (`FUN_14078dce0`) and dynamic-event loot (`FUN_140783070`) beyond their entry points.
### 5.9a Gardening and tent actions (task W3, addendum to 5.9) [obs]
Sources: `ActionDigGardenPlot`, `ActionPlantSeed`, `ActionFertilizeSlot`, `ActionWaterPlant`, `ActionHarvestCrops`, `ActionPackTent`, `CAContinuousFertilizeGardenSlot`, `CAContinuousWaterPlant`, `TentBase`, `ActionConstants.c`; all rows are in `data/actions.csv`.
- **Dig a garden plot** (`ActionDigGardenPlot`): works from the placement hologram of the garden plot item (the held tool was not checked) and needs the hologram not to be colliding; the client refuses it with **broken legs** or, unless the server turns that check off (`DisableColdAreaPlacementCheck` in `cfggameplay.json`), when standing in a cold area. Standing only; duration `UATimeSpent.DIG_GARDEN` = 4 s; the surface under the plot is checked (`CheckSurfaceBelowGardenPlot`: the plot must be placeable at the adjusted position). The server side accepts without further checks.
- **Plant seed** (`ActionPlantSeed`): single use, target is a garden slot found from the selection name under the cursor; allowed when the seed stack has quantity and `GardenBase.CanPlantSeed(selection)` is true. Executes by moving the seed into the slot: a stack larger than 1 is split so only one stack unit goes in (`SplitIntoStackMax`), otherwise the item itself is attached.
- **Fertilize** (`ActionFertilizeSlot`): crouch, full body; allowed only when the slot has **no plant** and its fertility state is `NONE`. Rate base is 150 quantity per second, but the item's config sets the real pace: `Horticulture >> ConsumedQuantity` (what one slot needs) and `Horticulture >> FertilizeLength` (seconds; 1 if absent), and the component scales the rate by `(ConsumedQuantity / 150) / FertilizeLength`. The slot's fertilizer capacity is set to `ConsumedQuantity`, and the item is deleted when it reaches its minimum quantity.
- **Water a plant** (`ActionWaterPlant`): the container must have quantity, not be frozen and not be ruined; the plant must report `NeedsWater()`. Water moves at 150 per second until the plant's `GetWaterMax() - GetWater()` or the container is exhausted; the duration is `min(thirst, quantity) / 150`. Soft skills do not affect the rate (the code comment says they were removed).
- **Harvest** (`ActionHarvestCrops`): bare hands, standing or crouched, `UATimeSpent.DEFAULT_HARVEST` = 5 s, only on a plant that `IsHarvestable()`; the prompt text appends the crop's display name. The server calls `Plant.Harvest(player)`.
- **Pack a tent** (`ActionPackTent`): duration is the deploy time `DEFAULT_DEPLOY` = 5 s; hands must be empty (`CCINone`), the target must be the tent's "pack" selection, and `TentBase.CanBePacked()` must be true, which needs the tent to be **pitched** with **no cargo and no attachments**. A tent that is in someone's inventory cannot be packed. The check is repeated every tick (`ActionConditionContinue`), so adding cargo cancels the pack.
- **Open item:** the tent navmesh interaction and the digging of stashes (`ActionDigInStash`, `DIG_STASH` = 10 s) were not read in detail.

### 5.7a Vehicle table from the configs (task D2, addendum to 5.7) [obs]
`data/vehicles.csv` (built by `scripts/vehicles.py` from the merged configs) has one row per spawnable car, motorbike and boat class: **28 classes** (17 cars, 7 motorbikes, 4 boats), which collapse to 9 distinct models once colour variants are merged. Columns: fuel capacity and consumption, seats and crew slots, doors, drive type, gearbox type and gear count, reverse ratio, torque peak (Nm and rpm), idle and redline rpm, maximum steering angle, drag coefficient, frontal area, wheel count, damage zone count and global hit points. Units are the config's own (torque in Nm; fuel in litres; the consumption value is a per-engine-load rate whose unit I did not check [?]).

| Model | Type | Fuel l | Seats | Drive / gearbox | Torque peak | Idle / redline rpm | Wheels | Damage zones |
|---|---|---|---|---|---|---|---|---|
| Olga 24 (CivilianSedan) | car | 55 | 4 | RWD, manual 4 | 187 at 2,500 | 900 / 4,700 | 4 | 15 |
| Gunter 2 (Hatchback_02) | car | 55 | 4 | FWD, manual 5 | 186 at 4,400 | 1,250 / 6,250 | 4 | 14 |
| Ada 4x4 (OffroadHatchback) | car | 42 | 4 | AWD, manual 4 | 114 at 3,400 | 800 / 6,000 | 4 | 16 |
| Sarka 120 (Sedan_02) | car | 38 | 4 | RWD, manual 4 | 82 at 3,000 | 900 / 5,750 | 4 | 15 |
| M1025 (Offroad_02) | car | 115 | 4 | AWD, automatic 4 | 384 at 2,500 | 625 / 3,700 | 4 | 15 |
| M3S Covered (Truck_01_Covered) | truck | 120 | 2 | 6x4 ("DRIVE_642"), manual 4 | 340 at 1,400 | 650 / 2,400 | 6 | 15 |
| Jana 50 (Motorbike_01) | motorbike | 3.5 | 2 | manual 3 | 8 at 4,500 | 1,200 / 6,000 | 2 | 8 |
| Bitrak 682 (Motorbike_02) | motorbike | 13.5 | 2 | manual 4 | 36 at 5,142 | 1,300 / 6,000 | 2 | 9 |
| Rubber Boat (Boat_01) | boat | 25 | 4 | manual 1 (propeller) | 310 at 3,500 | 700 / 6,500 | none | 6 |

Fuel consumption values: Olga 13, Gunter 6.5, Ada 11, Sarka 7, M1025 30, M3S 30, Jana 1.8, Bitrak 3.5, boat 5.5. Global hit points are 1,000 for every car and motorbike, 1,500 for the truck and 600 for the boat; steering angles are 30 to 35 degrees for cars and the truck, 21 for the boat. The Ada's doors are driver, co-driver, hood and trunk; the Olga, Gunter, M1025 and Sarka also have two rear cargo doors. The torque curve is stored as rpm/torque pairs (the Ada: 650/0, 750/40, 1,400/80, 3,400/114, 5,400/95, 8,000/0).

**Not done for D2:** the building classes (233 `house` simulation classes), sound sections, and the per-wheel and per-door state machines (task W1) were not tabulated.

### 5.7b Vehicle scripts: engine start, battery, crashes, doors, boats and motorbikes (tasks W1, W2) [obs]
Sources: `CarScript.c` (2,981 lines), `BoatScript.c` (908), `MotorbikeScript.c` (1,780), `HelicopterScript.c`, `InheritedCars\*`, `InheritedBoats\Boat_01.c`, `InheritedMotorbikes\*`, constants in `constants.c` and `ActionGetOutTransport.c`. Most behaviour (the drive simulation itself: engine, clutch, gearbox, suspension) is native; the scripts decide start conditions, damage, fluids, lights and crew effects.

**Starting a car** (`CheckOperationalRequirements`, returned as flags): `RUINED` when the vehicle is destroyed or the Engine zone is ruined; `NO_FUEL` when the fuel fraction is 0 or less; `NO_BATTERY` when the model needs a battery (`NeedElectricitySourceDevice`, true for every car) and the battery is missing, ruined or holds less energy than the start cost; `NO_IGNITER` when a vital spark plug or glow plug is missing or ruined. Anything other than OK blocks the start, and the sound says which one failed (no battery, no spark plug, no fuel). Which parts are vital differs per model:

| Model class | Spark plug vital | Glow plug vital | Belt vital | Radiator vital | Battery vital |
|---|---|---|---|---|---|
| Civilian sedan, Hatchback_02, Offroad hatchback, Sedan_02, Van_01 | yes | no | yes | yes | yes |
| Offroad_02 (M1025) | no | yes | yes | no | yes |
| Truck_01 (all variants, derived from the base) | no | no | no | no | yes (the cargo variant also overrides the battery to no) |
| Truck_02 | no | no | no | no | yes |
The base class (`Transport`) makes the spark plug and glow plug vital by default, and the car class makes the belt, radiator and battery vital by default, so a model that overrides one to false drops that requirement. Both motorbikes need **no battery** and drop the glow plug (the spark plug stays vital), like the boat. Van_01 and Truck_02 exist as script classes but not as spawnable configs in `data/vehicles.csv` [inf from the missing rows].

**Battery.** A car start costs 15 energy (`m_BatteryConsume`). While the engine runs the alternator adds 0.15 per second of battery time; with the engine off and lights on the drain is 0.25 per second. These are applied in batches: the server accumulates time and calls `UpdateBattery` every 100 seconds, and also at engine start and stop. If the battery reaches 0 with the lights on and the engine off, the lights switch off. [The recharge is applied as `-(recharge) x elapsed`, a negative consumption.]

**Fluids.** Fluids tick every second (`VEHICLE_FLUIDS_TICK`). A leak takes `(1 - part health) x random` of the fluid per tick, where part health is a fraction taken from the part's health level: radiator for coolant (random 0.02 to 0.05), engine for oil (0.02 to 1.0) and fuel tank for fuel (0.02 to 0.05). Leaks run each tick while: coolant, the radiator is vital, coolant is left and radiator health is under 0.5; fuel, the tank health is below the damaged value; brake fluid and oil, engine health is below the damaged value; oil also leaks whenever engine health is under 0.25. Engine damage from running: at or above the redline rpm the engine takes `rpm x 0.001 x random(0.02 to 1)` per tick, and above the maximum rpm an extra 5 % of its maximum health; with a vital radiator and coolant under half, it takes `(1 - coolant) x random(0.02 to 10)` per tick. The engine also stops by itself when the vehicle is destroyed, fuel runs out, engine health reaches 0, or a vital spark or glow plug is missing. A car engine in water deeper than 0 for more than 0.5 s loses **350 engine health per second** (motorbike 150), and the engine stops when it is no longer operational.

**Crash damage** (`CheckContactCache`, server): each contact accumulates an impulse per zone. Damage to the zone = `|impulse| x m_dmgContactCoef`, where the coefficient is **0.058** by default and **0.079** on the Sarka (Sedan_02); the other models' overrides are commented out in the scripts, so the default applies [obs; the commented numbers were 0.065 Olga, 0.070 Gunter, 0.075 Ada, 0.0365 M1025, 0.018 trucks]. Thresholds: below **150** nothing happens; 150 to 750 is a light impact (sound, damage without transfer to neighbouring zones); **750 and above** is heavy (sound, full damage with transfer, and crew damage). Crew damage is computed as if the vehicle weighed 1000 kg: `base = |impulse / mass x 1000 x coef|`. Above **1,200** every occupant is killed outright (health set to 0). Between 750 and 1,200 each occupant takes shock `lerp(50, 150, t)` and health `lerp(2, 100, t)` with `t = (base - 750) / (1200 - 750)`. Motorbikes use their own thresholds: minimum 10, small 25, medium 40, kill crew 80 (rider damage by the same formula).

**Jumping out** (`OnVehicleJumpOutServer`, car): shock from `speed^2 / 60` (halved with a helmet) and a bleeding wound by speed class: below 20 an arm/leg-type low source with a 20 % chance of shock, 20 to 30 an upper-body source with 50 %, 30 and above bleeding at the head unless wearing headgear with 75 % shock; every equipped clothing slot (legs, back, vest, headgear, mask, body, feet, gloves) loses `speed^2 / 15` health, the legs take extra damage, and `FallDamageHealth` is applied scaled from speed 30 to 70. The boat does only the fall-damage part, at half strength.

**Doors and flip.** Door state is read from the animation phase: above 0.5 is open, otherwise closed, and a missing door part is `DOORS_MISSING`. Seats are tied to door selections and door inventory slots by per-model overrides (`GetDoorSelectionNameFromSeatPos`). A car counts as flipped when it fails the wheels test and its up vector is more than 45 degrees off the surface normal. The Ada has four doors (driver, co-driver, hood, trunk); the other cars, except the trucks, add two cargo doors (see `data/vehicles.csv`).

**Boats** (`BoatScript`, one model: Boat_01 in four colours): start needs the engine not ruined (hull and Engine zones), fuel above 0, and the spark plug if vital; there is no battery check. Contact damage does not damage the boat; it only picks a light or heavy impact sound (same 150 and 750 limits) and stops the engine if the boat is no longer operational. **Decay:** every 10 seconds the boat loses 0.017 Engine health times the server's `boatDecayMultiplier` (4 times that while flipped, 0.3 times within 100 m of a territory flag), and only when **no player is within 300 m** (the central economy's "avoid player" test); a multiplier of 0 disables it. Leaving the driver seat with a gear engaged stops the engine. `HelicopterScript` is still a stub (empty simulation callbacks).

**Motorbikes:** the rider is ejected (`CrewShouldEject`) when the bike has fallen, and a fallen bike cannot be entered; leaving the driver seat in gear stops the engine, and `CheckOperationalRequirements` is the same as for boats (engine, fuel, spark plug) with a drowning rate of 150 per second.

### 5.13 Fishing and trapping: the animal catching system (tasks S9 and W6 part) [obs]
Sources: `3_Game\Systems\AnimalCatching\*` (constants, yield bank, catch contexts, result), `4_World\Systems\AnimalCatchingSystem\*` (rod and trap contexts, fish, junk and land-animal yield items), `ActionConstants.c` (`UAFishingConstants`), `TrapSpawnBase.c`, the per-map world classes (`Enoch.c`, `Nasdara.c`, `Sakhal.c`, `missionBase.c`) and the `Fishing` and `Trapping` config bodies (`data/catching_items.csv`, 53 items, built by `scripts/catching.py`).

**Structure.** A *yield bank* holds the catchable things for the map. Each *yield item* has a type name, a **base weight**, an environment mask (pond, sea, forest, field) and a method mask (rod, large fish trap, small fish trap, snare). A *catching context* is built for one rod or one trap: it reads the `Fishing` / `Trapping` config bodies of the item and of everything attached to it (hook, bait), filters the bank by environment and method, and builds a pick list in which each type appears as many times as its weight, so the weights are the odds of what bites. A *result* then rolls a catch chance and a quality, and the winner is spawned.

**Yield banks per map** (base weights; the default in `missionBase.c` is the same as Livonia):
- Default and Livonia: Carp 42, Mackerel 42, Sardines 15, Bitterlings 15; junk (four pairs of wellies and an empty pot) 1 each; land: hare 4, rooster 1, three hens 1 each, fox 2.
- Nasdara: Carp 42, Catfish 42, Round goby 15; junk is four sandals and a pot at 1 each; land: hare 2, rooster 1, three hens 1 each, fox 2, lizard 4.
- Sakhal: Walleye pollock 61, Steelhead trout 36, Shrimp 1; junk is wellies and a pot at 1; land: hare 1, fox 1 (a bear entry is commented out).
Pond and sea masks split the water species (carp in ponds, mackerel in the sea, for example).

**Rod fishing** (`CatchingContextFishingRodAction`, `UAFishingConstants`): the line is checked in cycles of 5.5 to 6.5 seconds; the length depends on the hour for each fish, through a 24-value table (coefficient 1 at night and midday, 0 around 06:00 to 08:00 and 19:00 to 21:00), and the cycle is shortest where the coefficient is 0 [inf from the interpolation `lerp(min, max, coef)`, which gives 5.5 s at 0 and 6.5 s at 1]. Inside a cycle a "signal" (a bite) appears 0.5 to 2.5 s after the start and lasts 0.8 to 1.0 s. The chance per cycle rises with the number of cycles already done without a catch: an exponential ease-in from 0 to **0.5 at 20 cycles**, then from 0.5 to **0.9 at 30 cycles**. Equipment shifts both cycle targets by `signalCycleTargetAdjustment` (a bigger negative number means a bite sooner): rod -3, hook -2, bone hook -1, jig -11 (end target -17), earthworm bait -12 (end -20). Jig and earthworm also lengthen the signal window (jig 1.1 to 1.4 s, worm 1.2 to 1.6 s). The catch quality starts at 0.35 for fish and adds each item's `resultQuantityDispersionMin/Max` as a random range (rod 0.25 to 0.35, hook 0.15 to 0.30, bone hook 0.05 to 0.20, jig 0.20 to 0.30). Hooks can be lost: `hookLossChanceMod` is 0.5 % for the bone hook and 1 % for the wooden hook and the improvised rod; bait loss is configurable but 0 for every item in this build. Junk is always a flat 20 % per roll regardless of gear, spawns badly damaged, and the empty pot has quality 0. The fishing action is the only place the soft-skill specialty changes (6.19).

**Traps** (`CatchingContextTrapsBase`, `TrapSpawnBase`): the fish net, small fish trap and rabbit snare check every **30 s** (the base class is 60 s) for at most **1,200 s** (20 minutes, so up to 40 attempts), with a spawn delay of 30 s before the catch appears. The per-attempt chance is chosen so that the cumulative chance over all attempts equals the best bait match: `p = 1 - (1 - target)^(1 / attempts)`, where `target` is the maximum over the baits present of the bait's config chance times the prey's sensitivity to that bait type. Bait types: 0 empty, 1 small meat, 2 large meat, 3 plant, 4 seed, 5 mushroom. The traps themselves provide the "empty" bait with chance **0.15** (and `resultQuantityBaseMod` 0.5, dispersion 0 to 0.5). Item bait chances from config: steaks and fillets are type 2 at 0.75 (bear and dog 0.25, fox 0.10, chicken and lizard 0.70), fruit and peppers type 3 at 0.70, mushrooms type 5 at 0.60, seeds type 4 at 0.65 (plus plant 0.05), earthworms types 1 and 2 at 0.75 and 0.05. Each prey scales a bait by its sensitivity: hares take empty or plant bait only, foxes take empty, mushroom and both meat types, fish take empty or small meat. A failed attempt with bait uses up 20 % of the bait's quantity. Fish traps need water (sea or fresh) and the snare needs land; the environment is read when the trap starts. A caught animal plays a death sound at the trap and makes a noise for the infected AI (hare, rooster, hens and fox use the wolf-roar noise at strength 1).
