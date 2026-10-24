# Survival, combat, items and actions (scripts)

Part of the DayZ static analysis notes (see `README.md` in this folder for the map). Section numbers are the original ones, so cross-references such as "see 6.10" still resolve.

### 5.2 Inventory, items and actions [obs unless noted]

Source: `3_Game\Systems\Inventory\*` (hands and inventory commands), `3_Game\Entities\EntityAI.c`, `4_World\Entities\ItemBase.c`, `4_World\Classes\UserActionsComponent\*` (460-odd action classes), and the slot, size and cargo values from the config tables in 5.1.

**Slots and cargo.**
- `GameInventory` is the script face of an engine inventory, with about 190 methods covering cargo grids, attachment slots, reservations, locks, placement and checks. Every entity can have one.
- Slots come from `CfgSlots` (470 entries). The engine pre-populates the first 32 as `InventorySlots` constants. The first ones in config order are Head, Shoulder, Melee, Bow, Headgear, Mask, Eyewear, Hands, LeftHand, Gloves, Armband, Vest, Body, Back, Hips, Legs, Feet, Pistol, Knife, three magazine slots, Driver, Cargo and muzzle slots. The rest are mostly attachment slots: about 36 weapon parts, 55 base-building materials, 28 truck parts, seeds and more.
- The player's own attachment slots are 17: Head, Shoulder, Melee, Headgear, Mask, Eyewear, Hands, LeftHand, Gloves, Armband, Vest, Body, Back, Hips, Legs, Feet and Splint_Right.
- Slots can limit stacks (`stackMax`): firewood and rags 6, stones 16, sticks 10, bark 8, nails 99, planks 20 or 100, logs 4 or 50.
- **Items are grid tiles.** `itemSize` is width by height. The most common sizes are 2x2 (345 items), 3x2 (263), 4x3 (187), 10x10 (185, mostly large deployables) and 1x1 (154).
- 467 items have their own cargo grid. Examples: mountain backpack 7x8, Coyote 8x7, assault pack 6x6, Taloon 6x5, Gorka jacket 6x4, hoodie 5x3, cargo pants 5x4, jeans 4x3; tents 10x15 (party), 10x20 (medium), 10x40 (large) and **10x50 for the car tent** (500 cells); shelters 10x10.

**Inventory operations.**
- Commands: move, synchronous move, hand event, swap, force-swap, destroy, replace, cancel reservation.
- Four execution modes decide where an operation runs: *predictive* (same code on client and server, not used in multiplayer), *local*, *juncture* and *server*. A **juncture** is used wherever two players could race, such as picking the same item off the ground: the client asks, the server decides and answers. Results are failed, juncture or success.
- **Reservations:** while an operation is in flight, the client reserves the destination slot or cargo space. Reservation lookups have four modes (legacy, by item, by destination, exact match).
- Server-side checks include distance to the manipulated objects, take and drop requests, swap legality, locks and keys. Client requests travel as input user data messages.

**Hands.** The hands are a small state machine (`HumanInventoryWithFSM`) with two stable states, *Empty* and *Equipped*, and animated transitional states between them.
- Events: take, move-to, drop, throw, swap, force-swap, destroy, destroyed, created, three "destroy and replace with new" variants, replaced, and "human command action finished" or "aborted".
- Each transition has guards, built from small checks such as has-item-in-event, can-move, can-swap, has-room-for-item and not-surrendered, combined with and, or and not.
- Animated versions exist for taking from or moving to an attachment, swapping, and force-swapping.
- Hand events may only be processed inside the player's command-handler tick.

**Item state** (`ItemBase`, 143 KB). Besides the engine-side values, scripts track about 43 scalar members: quantity, wetness, cleanness (clean or dirty), liquid type, heat isolation, color, the attached-agents mask (contaminated, poisoned and dirty masks over the agent bits in 6.9), overheating shots, split and place flags, and several legacy sound fields. Items also carry temperature and, for food, food stage.

**Actions: how they exist.**
- There are **461 action classes**, of which **343 are explicitly registered** in `ActionConstructor.RegisterActions`. The list is sorted by type name and each action receives its **index as its numeric ID**, so client and server agree on IDs by building the same array. By folder: continuous 232 files, single-use 110, interact 74, weapon 7, instant 4.
- **Items declare their actions** in `SetActions()` with `AddAction(ActionX)`. Every item gets take, take-to-hands, world-craft, drop and attach-with-switch; subclasses add more (a bandage adds bandage-self and bandage-target, create-indoor-fireplace and so on). The per-type action map is cached by item type.
- An action is assembled from parts:
  - an **item condition** (none, non-ruined, not empty, present, not present, non-ruined and dry, non-ruined and empty);
  - a **target condition** (cursor variants, liquid, man, none, non-ruined, object, self, surface, tree, water surface);
  - an **action component** (about 40, for example continuous time, continuous quantity, repeat, single use, interact, and special ones for crafting, fishing, mining rock or wood, loading magazines, filling fuel, oil or coolant, and watering plants).
- Each action also sets a stance mask, full-body or additive animation, a condition mask (usable in a vehicle, on a ladder, swimming, restrained, raised, on the back, throwing, leaning, with broken legs, in free look), text, sound, a skill weight and whether the target is locked while in use.
- Typical durations (`UATimeSpent`, seconds): bandage 4, splint 10, sew wounds 2 or cuts 8, inject 3, measure temperature 12, restrain 10 and unrestrain 20, skin 10, shave 12.75, craft 6, dig a stash 10, bury a body 12, push a car 10, disarm a mine 15, base-building construct 5 to 10.
- **Inputs:** 21 input kinds (default, continuous default, interact, continuous interact, drop, vehicle horn short and long, toggle lights, toggle night vision, weapon manipulation, inventory-only, quickbar, externally controlled). An action declares its input kind and the item's action map is keyed by it. Weapon manipulation uses fixed IDs 1501 to 1509 (attach, swap and detach magazine, load bullet, unjam, eject, multi-bullet load start and end, next muzzle mode).

**Actions: how one runs** (multiplayer).
1. **Choose.** `ActionManagerClient` finds the target under the cursor (vicinity objects grouped by object) and the item in hands, collects the possible actions by category (single-use, continuous, interact), and lets the player cycle through a selectable list.
2. **Gate.** `ActionPossibilityCheck` blocks starting while sprinting, unconscious, already in an action or emote, with the weapon manager or throwing running, during inventory processing or while rolling, and requires an action, move, swim, ladder or vehicle command.
3. **Send.** `ActionStart` builds the action data and sends a "standard action start" user data message: the action ID, action-specific data and optionally an acknowledgment ID.
4. **Validate.** On the server, `OnInputUserDataProcess` reads it and `StartDeliveredAction` re-checks `Can(player, target, item)` and takes an action juncture. The server answers with an accept or reject sync juncture, which sets the client's pending state.
5. **Run.** The action's start, update and end hooks run on both sides; progress comes from the action component. The client can send an end request or input-end message, and either side can interrupt through a sync juncture (jumping also ends or interrupts it).
6. **Clean up.** Reservations and locks are released, and look and aim limits are restored (some full-body actions lock the camera).
- The server is authoritative: the client only predicts the presentation, and a rejected or timed-out action simply stops.

### 5.3 Firearms and recoil [obs unless noted]

Source: `4_World\Entities\Firearms\*` (`Weapon_Base.c` 69 KB, the weapon state machine in `FSM\`, one file per mechanism), `4_World\Classes\RecoilBase\*` (55 recoil profiles), `PropertyModifiers.c`, `Classes\Weapons\WeaponManager.c`, and the weapon, ammo and attachment numbers from the config tables in 5.1.

**What scripts do and don't do.** The scripts handle the weapon's *mechanism* (chambering, magazines, jams, fire modes), recoil and attachments. I found **no bullet-flight, penetration or damage code in the scripts**: names such as `airFriction`, `typicalSpeed`, `caliber`, `deflecting` and `initSpeedMultiplier`, and the `NoiseShoot` block, appear nowhere in them. Those values are read by the engine from config (see the ammo table in 5.1). The one `initSpeed` hit in scripts is unrelated.

**Class layout.** `Weapon_Base` is the shared base. One subclass per mechanism holds the logic and the state machine: bolt-action with external or inner magazine, free-bolt and locked-bolt rifles, open-bolt guns, chamber-first inner-magazine semi-autos, single-shot and manual single-shot rifles, double-barrel shotguns, pistols (plus alternate and single-shot pistols), a repeater, pump shotguns and a crossbow. Per-model classes sit under `AutomaticRifle`, `Pistol`, `Rifle`, `Shotgun`, `SMG`, `Machinegun`, `Launcher` and `Archery`.

**Each weapon is a state machine** (`WeaponFSM`) with **82 named stable states** plus transitional "action" states. Stable state names pack the mechanism: bolt open or closed, bullet in chamber (`BU0` or `BU1`), magazine attached (`MA0` or `MA1`), and jammed. For example `RBF_CLO_BU1_MA1` is a free-bolt rifle, closed, bullet chambered, magazine in. Families: `BAREM` / `BARIM` (bolt-action external and inner magazine), `CFIMSA` (chamber-first inner-magazine semi-auto), `SKS_…` (its own states), `DoubleBarrel…` (loaded, empty or fired-out per barrel), `OB` (open bolt), `Pistol_…`, `RBF` / `RBL` (free and locked bolt), `RSS` (single shot), `SSP`, `XB` (crossbow), `FLARE`, `RPT` (repeater) and pump shotguns.
- **Events:** 43 event classes: trigger, mechanism, trigger-to-jam, auto-fire start and end, load one bullet, continuous load start and end, unjam (with timeouts), attach, detach and swap magazine, reload and dry-fire timeouts, next muzzle mode, "human command action finished or aborted", and a long list of **animation events** that drive state (bullet show or hide, bullet in chamber or magazine, magazine attached, detached, shown or hidden, slider open, hammer cocked or uncocked, cylinder rotate, unjammed).
- **Guards:** 34 guard classes decide whether a transition is allowed. The FSM state is saved and restored with the weapon (so chamber and magazine state survive a restart), then validated and repaired after load.
- `WeaponManager` (34 KB) turns player commands into these events (attach, swap and detach magazine, load bullet, unjam, eject, next muzzle mode, using the fixed action IDs 1501 to 1509 from 5.2) and puts a juncture on the attached magazine during swaps.

**Firing and jams.**
- `CanFire` needs a loaded, non-fired-out chamber, no jam, no weapon-lift obstruction and an undamaged weapon.
- On the client, firing plays muzzle-flash and overheating effects from config, and handles a suppressor.
- **Jamming:** the jam check draws from a synchronized random generator and compares it with a chance taken from the weapon's **health level** through `Reliability.ChanceToJam`, an array indexed pristine, worn, damaged, badly damaged, ruined. 130 weapons define it. Typical value: **[0, 0.001, 0.01, 0.1, 1]**, so 0, 0.1 percent, 1 percent, 10 percent and certain at ruined. Pistols use 0.05 at badly damaged. Mosin, CZ527 and Winchester 70 use **[0, 0, 0, 0, 1]**: they never jam until ruined.
- **Barrel wear** is engine-side: each ammo type has `damageBarrel` (5.56 250, .308 and 7.62x54R 500, 9x19 about 167, .22 about 115, .45 ACP 187.5, 12 gauge slug 600) set against the weapon's `barrelArmor` (see the table in 5.1) [inf: how the two combine is in C++].
- **Weapon lift:** the script raycasts to lift the weapon when it would clip into a wall, using `WeaponLength` from config (M4A1 0.78 m, AKM 0.90, SVD 1.15, Mosin 1.235; pistols 0.21 to 0.28).
- **Noise:** each weapon has `NoiseShoot.strength` in config, from 2 to 100 (average 80). M4A1, AKM and AK74 are 80, SVD, Mosin, SKS and SCAR-H 100, MP5K 60, pistols 40 (Deagle 80), Ruger .22 20 and VSS 5. Suppressors carry a noise multiplier: -0.93 for the M4, AK and pistol suppressors, -0.90 for some barrels and -0.85 for the improvised one [inf: used by the engine for AI hearing; nothing in scripts reads it].

**Recoil.** Every shot spawns a `RecoilBase` object (`SpawnRecoilObject`) that lives for one reload interval and feeds the aiming model each frame.
- **Three outputs:** a *hands* offset taken from a 4-point Catmull-Rom curve, a *mouse* offset that nudges the aim along a random direction, and a small camera push forward.
- **Randomness is synchronized** between client and server (the curve points and the direction angle come from a shared generator), so both sides compute the same recoil.
- **Parameters** (`Init` of each profile): mouse kick distance and its direction range in degrees; mouse and hands timing as fractions of the weapon's reload time; the curve's peak; the camera push distance. The result is multiplied by the weapon's recoil vector.
- Selected profiles:

| Profile | Mouse kick | Mouse time | Hands time | Direction (deg) | Camera push | Curve peak |
|---|---|---|---|---|---|---|
| M4A1 | 1.5 | 0.5 | 0.5 | 50 to 120 | 0.01 | 1.5 |
| AK74 | 1.6 | 0.5 | 0.5 | 45 to 110 | 0.0125 | 1.75 |
| AKM | 1.8 | 0.5 | 0.5 | 45 to 110 | 0.0125 | 1.75 |
| SCAR-H | 1.5 | 0.5 | 0.5 | 90 to 120 | 0.01 | 1.6 |
| SVD | 1.8 | 0.5 | 1.0 | 45 to 110 | 0.015 | 0.75 |
| MP5K | 1.0 | 0.4 | 0.5 | 60 to 145 | 0.0075 | 1.5 |
| UMP45 | 0.8 | 0.3 | 0.3 | 55 to 120 | 0.005 | 0.95 |
| VSS | 0.7 | 0.25 | 0.25 | 65 to 105 | 0.0075 | 1.0 |
| Ruger 10/22 | 0.2 | 0.5 | 1.0 | 45 to 80 | 0.02 | 1.5 |
| Mosin | 1.8 | 0.0625 | 0.125 | 80 to 100 | 0.02 | 2.75 |
| CZ527 | 1.1 | 0.0625 | 0.125 | 80 to 100 | 0.02 | 2.0 |
| Winchester 70 | 1.25 | 0.0625 | 0.125 | 80 to 100 | 0.02 | 2.5 |
| MP-133 shotgun | 3.0 | 0.0625 | 0.125 | 70 to 110 | 0.05 | 6.0 |
| Izh-18 shotgun | 3.5 | 0.0625 | 0.125 | 70 to 110 | 0.05 | 6.0 |
| Glock | 1.0 | 0.5 | 1.0 | 40 to 90 | 0.04 | 3.0 |
| FNX45 | 1.2 | 0.5 | 1.0 | 45 to 105 | 0.04 | 5.0 |
| Deagle | 2.5 | 0.0625 | 0.125 | 70 to 110 | 0.05 | 5.5 |
| Crossbow | 0.6 | 0.0625 | 0.05 | 85 to 95 | 0 | 3.0 |

The biggest mouse kicks are the Siaga (4.5), Long Horn (4.0), Izh-18 and Izh-43 shotguns (3.5) and the sawn-off Izh-18 (3.0); the smallest are the Ruger .22 (0.2), the crossbow (0.6), the Mk II (0.65), the Skorpion (0.7) and the VSS (0.7). A bolt-action's very short timings (a sixteenth of the cycle) make it a sharp snap rather than a climb.

**Attachments change recoil by multiplication.** `PropertyModifiers` multiplies the weapon's own `recoilModifier` by those of every attachment, as three numbers. 66 attachments have a non-default value, and every one lowers recoil equally on all axes:

| Multiplier | Count | Examples |
|---|---|---|
| 0.6 | 2 | Mosin compensator, MP5 compensator |
| 0.7 | 15 | M4 CQB stock, AK wood stock, M4 and AK wood handguards |
| 0.75 | 9 | AK74 wood stock, FAL and SCAR stocks |
| 0.8 | 19 | M4 OE stock, AK plastic stock |
| 0.85 | 6 | AKS74U stock, FAL folding stock, SCAR precision stock |
| 0.9 | 15 | suppressors and some M4 stocks |

Two weapons raise it themselves: the sawn-off Mosin multiplies recoil by 2 and the sawn-off magnum by 1.5. 110 attachments also define a sway modifier, mostly 1. Suppressors additionally reduce dispersion slightly.

**Not covered:** the per-mechanism state transition tables in detail, the weapon manager's inventory juncture handling, melee fighting (`DayZPlayerImplementMeleeCombat`), grenade and flare simulation, and the engine-side ballistics, which need the exe.

### 5.4 Infected and animals [obs unless noted]

Source: `4_World\Entities\Creatures\{Infected, Animals}` (`ZombieBase.c` 1,207 lines, `AnimalBase.c` 649), `3_Game\Entities\{DayZInfected, DayZInfectedType, DayZAnimal}.c`, and the creature, behaviour and ammo values from the config tables in 5.1.

**What scripts do and don't do.** Infected and animals are *engine* AI agents (`DayZCreatureAI`). The engine's AI decides where to go, what to chase and when to attack. Scripts supply the *body*: animation commands, which attack to play, how to react to hits, death and crawl animations, vaulting, sound and arrows. The engine-facing animation commands for infected are move, vault, death, hit, attack, crawl and script; for animals they are move, jump, death, hit, attack and script. Perception (sight and hearing) is **configuration**, not script.

**Infected mind states** (set by the AI, read by script): calm, disturbed, alerted, chase, fight and a sandstorm *cower* state. A change of state resets the attack cooldown and selects the idle pose. Orientation and the mind state are net-synced so remote clients animate correctly.

**How an infected attacks** (`FightLogic`):
- Attacks only happen in the *chase* and *fight* states, and never against a player who is in a vehicle (a hotfix noted in the code).
- `ChaseAttackLogic`: while chasing it picks from two center attacks, light left and right at **2.4 m**, with cooldowns of 0.3 s and 0.4 s. The target must be inside a **20 degree** cone.
- `FightAttackLogic`: in a fight it picks from **ten attacks** across up, center and down pitch, light and "heavy" variants, at 1.4 to 1.7 m with probabilities 0.4 to 0.9 and cooldowns 0.1 to 0.6 s. The target cone is **30 degrees**. `ChooseAttack` scores each with a random roll, distance and pitch and takes the highest.
- The "heavy" flag is set to 0 on every registered attack in this build (the code shows `0/*1*/`).
- **Blocking:** if the player is blocking in melee and facing the infected within the blockable angle, a *heavy* attack would be reduced to the weaker `MeleeZombie` damage and a *light* attack is replaced by a dummy damage type that deals nothing. Because every attack here is flagged light, a successful block always negates the hit [inf from the code and flags].
- **Where it hits** is a weighted pick: head 2, torso 65, and 50 each for left and right arms and legs. That works out to about **24 percent torso, 19 percent per limb, 0.75 percent head** [my arithmetic].
- Config attack actions per infected: a long swing (damage type `MeleeInfectedLong`, reach 1.75 m, cooldown 2.75 s) and short, run and low attacks (`MeleeInfected`, reach 1.3 to 2 m, cooldown 1.25 s), plus crawl attacks at 2 m.
- Damage from `CfgAmmo`: `MeleeInfected` health 6.5 / blood 100 / shock 12, with a bleed threshold of 0.16; the long swing 8.5 / 100 / 12; the weaker `MeleeZombie` used when a block downgrades a heavy hit is 5 / 5 / 10. Those are the numbers fed to the player hit and bleeding logic in 6.12.

**Taking hits** (`EEHitBy`):
- *Crawl:* if a hit takes a leg zone to exactly 0 health, the infected goes down into a crawl, with the animation chosen by left or right leg and whether the hit came from the front.
- *Stagger:* a hit starts a hit animation (rate-limited to once per 0.3 s) if the ammo's `hitAnimation` flag marks it heavy, or the infected is calm or disturbed, or a random roll of 0 to 100 is below `2.82 x shock damage`. So the stagger chance in percent is 2.82 times the shock damage dealt.
- *Death:* the death animation depends on the ammo's `doPhxImpulse` flag (a physics impulse), a vehicle hit, or a backstab or neck-stab finisher. Infected always `CanBeBackstabbed`; suitable finisher zones are head, neck and torso.
- Infected can vault obstacles by height class, can be hit by vehicles (a server-side transport hit registers on contact), and carry arrows (`ArrowManager`).

**Health and variants (config).** 275 spawnable infected variants. Global health **100**, head **30**, torso, legs and feet 100, and no armor. All resolve to the `civilian` loot category in my merged config, so loot differences between types must come from elsewhere [inf]. Animals (spawnable variants 42; global health): red deer 400, cow 500, boar 350, wolf 200, brown bear 800 (with a shock pool of 5,000), chicken 15.

**Perception and hearing (config, `CfgAIBehaviours`, 36 behaviours).** Vision is a set of ranges and multipliers; hearing is a set of ranges and radii.

| Behaviour | Vision range (min / max m) | Field of view | Close range | Noise range | Shot noise range |
|---|---|---|---|---|---|
| Infected (standard) | 20 / 40 | 1.0 | 10 m (x1.5 strength) | 35 m | 25 to 110 m |
| Infected "mummy" | 30 / 60 | 1.0 | 20 m | 35 m | 110 m |
| Wolf | 100 / 200 | 1.8 | | 100 m | 50 m |
| Dobermann | 100 / 170 | 1.8 | | 80 m | 45 m |
| Bear | 20 / 60 | 2.0 | | 110 m | 300 m |
| Red deer | 5 / 80 | 2.0 | | 80 m | 300 m |
| Cow | 8 / 20 | 1.6 | | 30 m | 300 m |
| Boar | 5 / 60 | 1.2 | | 30 m | 300 m |
| Fox | | | | 15 m | 300 m |

- Standard infected also have a 2.5 m "proximity" vision band (strength x2), a peripheral band from 2.5 to 20 m, and weather multipliers: night vision falls to 0.3, rain to 0.6 and fog to 0.5 of normal. Noise radius runs 10 to 25 m, and 35 to 70 m for gunshots. Soldier and heavy infected showed only a smaller noise radius (20 m) in my tool; the rest is inherited and my merge did not resolve it.
- [inf] Weapon `NoiseShoot.strength` (5.3) and suppressor multipliers feed these ranges; no script reads either side.

**Animals.**
- **Script side** (`AnimalBase`): death and replacement (`ReplaceOnDeath`, `GetDeadItemName`: the live animal is replaced by a carcass item, keeping its health), skinning permission, arrows, ceiling-dust step effects, a "natural instincts" achievement hook, and contaminated-area resistance. Behaviour (herd, flee, hunt) is entirely engine and config.
- **Melee** (config): wolf 20 / 100 / 12 with bleed threshold 1.0; bear 25 / 100 / 35; the bear "shock" attack 25 / 100 / 110 (threshold 0.85), which can knock a player out.
- **Skinning yields** (config `Skinning`, scaled by a per-item quantity range):

| Animal | Steaks | Pelt | Guts | Lard | Bones |
|---|---|---|---|---|---|
| Red deer | 17 (7 chest, 5 belly, 6 pelvis) | 1 | 3 | 3 | 3 |
| Cow | 20 (6, 6, 6) | 1 | 5 | 3 | 4 |
| Boar | 13 (5, 3, 5) | 1 | 2 | 1 | 2 |
| Wolf | 10 (3, 3, 3) | 1 | 2 | 1 | 1 |
| Brown bear | 20 (8 belly, 8 pelvis) | 2 | 4 | 2 | 5 |
| Chicken | 2 breast | feathers | small guts | | 1 |

- Skinning attaches agents to the products: salmonella on animal organs and the brain agent on human fat and guts (see 6.9).

**Not covered:** the AI group and world helpers in `3_Game\AI` (small), how the engine uses these numbers to choose targets, ambient animal behaviour, infected sounds, and the player-bot debug framework in `4_World\Systems\Bot` (a state machine for test bots, not a creature AI).

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

### 6.16 Melee combat (task S1) [obs unless noted]

Sources: `4_World\Entities\DayZPlayerImplementMeleeCombat.c` (891 lines, the client-side targeting object), the `MeleeModes` config blocks, and the `Melee*` ammo classes. Table: `data\melee.csv` (178 items whose melee modes differ from the default fist). Bleed and shock reactions on the receiving side are in 6.12.

**Hit types** (`EMeleeHitType`): light, heavy, sprint, kick, three finishers (liver stab, neck stab, generic), and four weapon-mounted types (`WPN_HIT`, `WPN_HIT_BUTTSTOCK`, `WPN_STAB`, `WPN_STAB_FINISHER`). A hit selects a **weapon mode index** from the item: for a firearm, hit 0, butt-stock 1, stab 2; for other items the item's own light, heavy or sprint mode; bare hands use 0 (light), 1 (heavy) and 2 (sprint).

**Targeting (client, per swing).**
- Range is the mode's `range` from config plus **0.65 m** (`RANGE_EXTENDER_NORMAL`). The sprint constant `RANGE_EXTENDER_SPRINT` is 1.35 m but the script's `GetRange()` adds only the normal extender. [obs]
- First a ray from the head along the look direction: the target is accepted if it can be targeted and the hit point is within range squared.
- If that fails, a cone search runs from the player: range x 0.75, half-angle **30 degrees** (**15** for a sprint attack), from 2 m below to 2 m above, and a maximum distance of 0.5 m from the look ray.
- If a "hit" animation event already carries a target and no finisher is pending, that target is re-used if it is still in range.
- The chosen object, hit position, damage-zone index and finisher type are sent to the server in an input packet (`INPUT_UDT_MELEE_TARGET`); the server does not re-run the targeting.
- Items take wear: after the swing, `ProcessMeleeItemDamage` is called for the weapon and flagged on the player for a check.

**Finishers (backstabs).** Allowed only when it is not a follow-up hit, the target `CanBeBackstabbed`, the weapon is a finisher-capable melee item (or a stab with a firearm) and is not ruined, and there is a clear path to the target. For an infected the player must be within **60 degrees behind** it and the infected must be calm (mind state below disturbed). A crawling infected or prone player gets the generic finisher; a firearm stab uses `WPN_STAB_FINISHER`; otherwise the finisher is picked at random (synced random number) from the weapon's valid finishers (liver stab or neck stab), falling back to the liver stab. [obs]

**Damage numbers.** Each mode names a `CfgAmmo` class; its `DamageApplied` health, blood and shock values and bleed threshold are what the receiver gets. Bare hands (`MeleeFist`): range 1.2 m, light 10 health / 100 blood / 12 shock, heavy 15 / 100 / 17, sprint range 2.3 m. The ammo classes come in graded families:

| Family | Light (health / shock / bleed threshold) | Heavy |
|---|---|---|
| `MeleeBluntLight_1` to `_5` | 12 / 15 / 0, 13 / 18 / 0.05, 15 / 21 / 0.10, 17 / 28 / 0.15, 18 / 35 / 0.20 | `MeleeBluntHeavy_1` to `_5`: health 18, 22, 27, 30, 35; shock 24, 30, 45, 65, 80 |
| `MeleeSharpLight_1` to `_5` | 18 / 5 / 0.5, 18 / 8 / 0.6, 20 / 10 / 0.7, 22 / 12 / 0.8, 22 / 14 / 1.0 | `MeleeSharpHeavy_1` to `_5`: health 25, 28, 32, 38, 45; shock 12 to 20; threshold 0.5 to 1.0 |
| `MeleeCraftedLight_1` to `_5` (improvised) | 10 / 10 / 0.35, 10 / 10 / 0.45, 15 / 21 / 0.55, 17 / 28 / 0.65 | `MeleeCraftedHeavy_*`: health 15 to 30 |
| Single-purpose ammo | axe 15 / 25 and heavy 40 / 40; sword 35 / 25 and heavy 50 / 35; mace 25 / 40 and heavy 45 / 50; pickaxe 20 / 30 and heavy 40 / 40; sledgehammer 25 / 40 and heavy 50 / 50; fire axe 20 / 30 and heavy 50 / 40 | |

Blood is 100 for sharp and most bladed ammo and 0 for blunt (a blunt hit does not open a wound by itself); `MeleeFist` is 100 with a low threshold (0.10). Infected and animal ammo (`MeleeInfected` 6.5 health, soldier 8.5, mummy 10, zombie 5 to 7.5, bear 25 with a 110-shock variant, wolf 20) uses the same fields. The bleed threshold is the roll value below which the hit can cause a bleeding source (see 6.12). [obs for the values; the exact use of the threshold is in 6.12]

**Typical items** (light / heavy health, shock; range): hatchet 18 / 28 and 8 / 14, 1.4 m; kitchen knife 18 / 28 and 8 / 14, 1.2 m; hunting knife 22 / 38 and 12 / 18, 1.2 m; baseball bat 15 / 27 and 21 / 45, 1.8 m; crowbar 13 / 22 and 18 / 30, 1.8 m; shovel 15 / 27 and 21 / 45, 1.8 m. The sprint attack reaches 3.3 m with blades and 3.7 to 4.1 m with long blunt weapons.

**Counts.** About 1,800 spawnable items keep the default fist modes from the base item class (so almost any item can be swung); 178 have their own non-default modes, with 83 using the generic light-blunt ammo, 16 soft, 12 light fist and the rest the graded sharp, blunt and crafted families. The player has fist, fist-heavy and fist-sprint modes of range 1.2, 1.2 and 2.3 m.

### 6.17 Grenades and other explosives (task S2) [obs unless noted]

Sources: `4_World\Entities\ItemBase\Grenade_Base.c`, `Grenade_Base\{M67Grenade, RGD5Grenade, FlashGrenade, Grenade_ChemGas}.c`, and the explosive `CfgAmmo` classes. Table: `data\explosives.csv` (25 ammo classes with an indirect-hit or explosive flag). The smoke grenade classes were not read.

**Grenade behaviour (`Grenade_Base`).**
- *Types* (`EGrenadeType`): fragmentation, chemical, illuminating, non-lethal. For fragmentation and illuminating, the explosion runs `Explode(DamageType.EXPLOSION, ammo)` once per ammo type in the grenade's list; chemical and non-lethal skip it.
- *Pin:* a pinnable grenade can be pinned and unpinned; pinning stops the fuse timer and saves its remaining time, unpinning starts it (and turns on the "far bubble" so the grenade stays visible at distance). The pin state is saved with the item (save version 107 and later).
- *Fuse:* the default is 10 s; `M67Grenade` and `RGD5Grenade` use **4 s**, `FlashGrenade` **2 s**. When the fuse ends the server sets the grenade's health to 0 and makes it untakeable; the explosion is triggered by that destruction. A random-time activation (1 to 20 s) exists for use by other systems.
- *Activation by another item:* a grenade activated by an item other than itself is unpinned; activated by itself, it finishes at once.

**Ammo numbers** (config; `indirectHit` is the explosion's damage field, `indirectHitRange` the full-damage radius in metres, `indirectHitRangeMultiplier` the factor to the maximum range, default 4):

| Ammo | Range (m) | Max range multiplier | Direct health | Notes |
|---|---|---|---|---|
| `M67Grenade_Ammo` | 5 | 4 | 50 | fragmentation, radial |
| `RGD5Grenade_Ammo` | 3 | 4 | 50 | fragmentation, radial |
| `FlashGrenade_Ammo` | 5 | 4 | 5 | non-lethal effect, see below |
| `LandMineExplosion_Ammo` and `_CarWheel` | 2 | 4 | | `indirectHit` 0.5 |
| `ClaymoreMine_Ammo` | 10 | 3 | | **directional**; a secondary radial ammo adds range 1 |
| `Plastic_Explosive_Ammo` | 1 | 20 | | |
| `GasCanister_Ammo` | 1 | 2 | | |
| `LandFuelFeed_Ammo`, `Explosion_40mm_Ammo` | 5 | 4 | | |
| `GrenadeM4` (underbarrel launcher) | 7 | 4 | 99, blood 100, bleed threshold 0.75, unconscious 6 | `indirectHit` 28, `hit` 60 |
| `Bullet_40mm_Explosive` | 10 | 1 | 110, shock 110 | |
| `Rocket_RPG7_Base` / `_HE` / `_AP` | 2 / 2 / 30 | 4 | | `indirectHit` 150 / 20 / 80, `hit` 500 / 208 / 128 |
| `Rocket_LAW_Base` / `_HE` | 2 | 4 | | `indirectHit` 150 / 20, `hit` 500 / 208 |
| `Bullet_Flare` (and Red, Green, Blue) | 0.2 | 4 | 30 flare impact, blood 100, shock 10, unconscious 6 | `shotIlluminating` simulation, `indirectHit` 2 |

The grenade items weigh 400 g (M67), 350 g (RGD-5), 300 g (flash) and 500 g (chemical gas). The falloff of damage between the full-damage radius and the maximum range is applied by the engine (explosions are queued per frame by `ExplosionDamage`, 4.6), not by these scripts. [obs for the script path; ? for the falloff curve]

**Flash grenade effect** (client script, `FlashGrenade.OnExplosionEffects`). For the local player only: the range is `indirectHitRange x multiplier` = 5 x 4 = **20 m**. Inside it, a ray from the explosion to the player's head must hit a player first (items are ignored; if the grenade sat in a fireplace, that fireplace is ignored too). The effect strength is `1 - (distance - 5) / (20 - 5)`, clamped to at least 0.1, applied to all three flashbang values, and the player is told whether they were facing the blast (within **60 degrees**), which makes the effect stronger. Light: brightness 50, radius 20, lasting 0.35 s, visible in daylight.

**Chemical grenade** (`Grenade_ChemGas`): chemical type, cannot be pinned, armed from creation, and **explodes on any contact on the server** (no fuse). The explosion spawns a `ContaminatedArea_Local` (a 10 m radius zone that lives 360 s, see 6.15) at its position and deletes the grenade a second later; the client shows a particle burst and a sound.

**Not covered:** smoke grenade scripts (`SmokeGrenadeBase`, `M18SmokeGrenade`, `RDG2SmokeGrenade`), mine and trap triggering, and the engine's damage falloff.

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

### 6.22 What recipe `Do` methods change (task S10, addendum to 5.8) [obs for the listed calls, inf for the grouping]
`data/recipes.csv` now has `custom_do` (the recipe has a `Do` of its own or inherits one from a parent recipe class; `do_declared_in` names the declaring classes), `can_declared_in` and `do_effects` (tags derived from the calls in that method body by `scripts/recipes.py`; the grouping is my reading of the call names, so it is [inf] while each listed call is [obs]). 142 of the 234 recipe classes have an effective `Do` (68 of the 143 registered ones); the effective method is the nearest declaration up the parent chain, combined with the parent's when the child calls `super.Do` (this corrects a first version that only looked at each class's own body and missed the seed-cutting and animal and fish preparing families, CODEX.md CXR-003). Tag counts among the registered recipes: quantity changes 25, property copy to the result 20, plugin-based repair 10, random outcome 10, hand bloodying 10, repairs 9, item conversion 7 (the sawn-off weapons), extra spawns 6, placement 5, open or close 4, cleanness 4, agents 3, config reads 3, health 3, energy manager 3, blood type reveal 2, standing up 2, deleting an item 2, torch upgrades 2, and one each for liquid moves, a bleeding wound on the player, cargo drop, the wire material and opening a can (the paint recipes are not registered, so they are not counted).

The 32 registered recipes that create no item (the "no results" recipes in 5.8) are all effects on an ingredient:
- **Open and close:** `OpenCan` (swaps to the opened type), `OpenGunCase`, `CloseGunCase`, `OpenScientificBriefcase`, `CloseScientificBriefcase`.
- **Repair family:** `RepairWithSewingKit`, `RepairWithLeatherSewingKit`, `RepairWithTape`, `RepairEpoxy`, `RepairPlanks`, `RepairElectric`, `RepairWithTireKit`, `CleanWeapon`, `SharpenMelee` all call the repair plugin with the tool as the kit (heal amount comes from the kit / item config, see the repair kit data, not from the recipe); `RepairWithPliers` is different: it **costs 20 % of the first item's maximum health and gives 20 % of the second's** (two items trade health). `RepairWithRags` (not registered) adds 20 % of the item's max health.
- **Sawing off:** `SawOffIzh18`, `SawOffIzh18Shotgun`, `SawOFFB95`, `SawoffFAMAS`, `SawoffMagnum`, `SawoffMosin`, `SawoffShotgunIzh43` turn the weapon into its sawn-off type in place (`TurnItemIntoItem`); `SawOffMagnum` also deletes an item.
- **Liquids:** `ChelateWater` and `PurifyWater` remove agents from the container; `DisinfectItem` removes agents, sets cleanness and uses up disinfectant quantity; `BloodTest` reads the liquid type and reveals the blood type; `FuelChainsaw` and `ExtinguishTorch` work through the item's energy manager; `FillGasMask_Filter` converts charcoal tablets into filter charge (1 tablet = 10 units, any excess stays in the stack); `CraftTannedLeather` sets quantity from item config.
- **Torch upgrades:** `UpgradeTorchWithLard` and `UpgradeTorchWithLiquidFuel` call `Torch.Upgrade` with the lard or fuel vessel.

Recipes that create items and also have a body that changes the result:
- **Health of results:** `CraftMetalWire` sets the wire's health to 85 % of the barbed wire used (pliers damage); `RepairEyePatch` copies the rag's health onto the eye patch; `CraftBloodBagIV` and `CraftSalineBagIV` copy properties (including blood type visibility); `CleanRags` (commented out of the registration list, so not available in the stock game) would wash rags: needs `(100 - rag health) x quantity x 2` units of liquid, heals the rags up to a ceiling of 70 health, scaled down in proportion when the container runs dry.
- **Random yields:** `DeCraftWoodenCrate` scales planks and nails by the crate's damage state (pristine 6 to 8 planks and 12 to 16 nails at 60 to 80 % health, worn 5 to 7 and 9 to 13, damaged 4 to 6 and 6 to 10, badly damaged 3 to 5 and 3 to 7, ruined 1 to 2 and 1 to 4; result health ranges fall with the damage state to 5 to 20 %); `CutOutSeeds` and `CutOutPumpkinSeeds` give seeds in proportion to the fruit's remaining quantity (none below 30 %), halved for Dried or Rotten, zero for Baked, Boiled or Burned, times a random 0.5 to 1; other recipes use `RandomIntInclusive`/`RandomFloat` for similar spreads (`CraftBaseBallBatBarbed`, `DeCraftDetonator`).
- **Side effects on the player:** `CraftBaseBallBatBarbed` can open a bleeding wound on the player (through `AttemptAddBleedingSource`); `CraftGutsRope` and the animal-preparing recipes (`PrepareAnimal` base plus `PrepareChicken`, `PrepareFox`, `PrepareLizard`, `PrepareRabbit`) set the "bloody hands" flag; `CraftLongTorch` stands the player up.
- **Placement:** `CraftFireplace`, `CraftLongTorch` (also sets cleanness) and `CraftTruck01DoubleWheel` position or attach the result (for the wheel, at the ground ingredient's position when the other is in the player's hands); `CraftRag` drops overflow items on the ground around the player.
- **Consumed liquid:** `CraftMortarMix` removes exactly 1,000 units (1 L) of liquid from the container. `CraftTripWire` records the wire material on the trap for later decrafting.
- **Paint recipes (40 classes, none registered):** every `Paint*` class is commented out of the registration list or unregistered, so the stock game does not offer them. Each calls `PaintItem.Paint(ingredient, paint, "<target type>", player, specialty_weight)`, which swaps the item for its painted type and uses up part of the spray can.

Not read: the bodies of `PaintItem.Paint`, `OpenItem.OpenAndSwitch`, and the repair plugin's heal amounts; they determine how much paint or kit quantity is used [?].

### 6.23 The action catalog (task S8, addendum to 5.2) [obs]
`data/actions.csv` (built by `scripts/actions.py`) lists all **342 actions registered** in `ActionConstructor.RegisterActions`, in registration order, with the group from the section comments in that function: continuous use 177, single use 64, interact 62, weapon 27, vehicle 7, instant (debug) 4, motorbike 1. Registration sorts the list and gives each action a numeric ID equal to its position in the sorted list, so action IDs depend on the exact set of action classes (a mod that adds one shifts every later ID) [inf from the constructor: it sorts, then numbers in order].

Columns: parent chain, source file, `#` text key and English text (267 of 270 keys resolved), the callback class and the action component created by it (for example `CAContinuousTime(UATimeSpent.DIG_GARDEN)`), full-body flag, stance mask, animation command, soft-skill weight, the item and target condition components (`CCI...` for the held item, `CCT...` for the target), and whether the class overrides `ActionCondition` or the start and execute hooks. Values set at runtime (for example `SetupAnimation`) are not visible to the extractor, and 82 actions show empty condition fields because they inherit them from a parent.

What the table shows:
- **Components:** 192 actions use a callback component. `CAContinuousTime` 95 (one fixed duration from `UATimeSpent`), `CAContinuousRepeat` 50 (repeats a short step until stopped, for example bandaging or pumping), `CAContinuousQuantityEdible` 11 (eating and drinking), `CAContinuousMineWood`/`MineRock` 3 and 2, blood transfer 2, `CAContinuousFill` 2, and plugged turn-on 4.
- **Item conditions:** 164 use `CCINonRuined` (the tool must not be ruined), 78 `CCINone`, 9 `CCINotPresent` (nothing in hands), 8 `CCINotRuinedAndEmpty`.
- **Target conditions:** `CCTNone` 59, `CCTCursor` 57 (the object under the cursor, within range), `CCTNonRuined` 44, `CCTSelf` 34, `CCTMan` 25 (another player), `CCTObject` 11, `CCTLiquid` 11.
- **Base classes:** 135 derive from `ActionContinuousBase`, 40 from `ActionInteractBase`, 38 from `ActionSingleUseBase`, 9 from `FirearmActionBase`.
Use the CSV to find an action by its text, by which tool it needs, or by how long it takes (the `UATimeSpent` constants are in `3_Game/constants.c`).

### 6.24 Weapon state machine tables (task S7, addendum to 5.3) [obs]
`scripts/weapon_states.py` reads every firearm mechanism's `InitStateMachine()` and writes `data/weapon_states.csv` (the **82 stable states** with their flags: bullet in chamber, magazine attached, jammed, bolt open, and the muzzle state `E` empty / `L` loaded / `F` fired-out) and `data/weapon_transitions.csv` (**1,410 transitions** in 18 mechanism classes: from-state, event, to-state, guard). All from and to states resolved to a class; for transitions that combine guards (`GuardAnd`, `GuardNot`) only the outermost guard class is recorded.

Transitions per mechanism (stable states declared in that class in brackets): `Pistol_Base` 239 (10), `RifleBoltLock_Base` 182 (8), `BoltActionRifle_ExternalMagazine_Base` 177 (8), `RifleBoltFree_Base` 125 (6), `OpenBolt_Base` 122 (7), `DoubleBarrel_Base` 88 (8), `SKS_Base` 61 (4), `ChamberFirst_InnerMagazine_SemiAutomatic_Base` 59 (4), `Repeater_Base` 57 (5), `Mp133Shotgun_Base` 53 (4), `BoltActionRifle_InnerMagazine_Base` 51 (4), `RifleSingleShotManual_Base` 42, `RifleSingleShot_Base` 40 (4), `Crossbow_Base` 38 (3), `SingleShotPistol_Base` 30 (3), `Flaregun` 26 (3), `Magnum_Base` 17 (1), `Rifle_Base` 3. Mechanisms with no stable states of their own reuse a parent's.

The pattern is the same everywhere. A stable state is entered by the **end** of an action: "human command action finished" (490 transitions) or "aborted" (512) take an action state (charging, chambering, reloading, firing, unjamming) back to a stable one, and the guards pick which one from the real contents of the weapon. Other events start actions: trigger 91, mechanism (charge) 72, dry-fire timeout 59, load one bullet 51, reload timeout 43, swap, detach and attach magazine 20, 20 and 19, unjam 17, trigger-to-jam 16. Most common guards: current chamber empty 138, has magazine 94, weapon open 40, chamber fired-out 36, jammed 32.

Action states used as targets, by count: dry fire 60, charging 43, chambering 26, unjamming 17, attach magazine 16, replace magazine and chamber next 16, detach magazine 16, charge inner magazine 16, fire-to-jam 13, fire 12, fire last 10, eject bullet 5, multi-muzzle fire 4, fire and chamber next 4. State IDs follow the pattern in 5.3 (`BAREM_CLO_BU1_MA1` = bolt-action rifle with external magazine: closed, bullet, magazine). Use the CSVs to answer "what can happen to a loaded Mosin with a jammed round" by filtering on `from_class`.

### 6.25 Animals and AI helper classes (task S9, addendum to 5.4) [obs]
**Script AI helpers (`3_Game\AI`)** are thin native wrappers. `AIWorld` offers `CreateGroup(template)`, `CreateDefaultGroup`, `DeleteGroup` and navmesh queries (`FindPath`, `RaycastNavMesh`, `SampleNavmeshPosition`) that take a `PGFilter` (include, exclude and exclusive polygon flags, and a cost per area type). `AIGroup` has `AddAgent`, `RemoveAgent` and `GetBehaviour`; `AIAgent` has `SetKeepInIdle` and `GetGroup`; `AIGroupBehaviour` has one concrete behaviour, **`BehaviourGroupInfectedPack`**, which patrols a list of waypoints (a centre and radius each) from a start index, in a chosen direction, looping or not. Navmesh polygon flags: walk, disabled, door, inside, swim, sea swim, ladder, jump-over, jump-down, climb, crawl, crouch. Area types include terrain, water (shallow, deep, sea, deep sea), objects, building, roadway, tree, doors (open and closed), ladder, crawl, crouch, fence-wall and jump. No script calls `CreateGroup`, so pack behaviour is created by native code and the Central Economy event spawner, not by script [obs for the missing script callers].

**Animals (`AnimalBase.c`, 41 classes).** `AnimalBase` extends the native `DayZAnimal`. It carries an arrow manager (arrows stay in the carcass), caches a salmonella chance for skinning, and on death **replaces itself with a dead item** at the same position and orientation (`DeathUpdate`: create the dead class, transfer the item properties, delete the live animal). Each species defines `RegisterHitComponentsForAI`, a table of zone names and weights the engine uses to choose where a hit lands (the wolf, for example: head 2, neck 65, chest 50, back legs 75, front legs 70, default zone chest), plus a capture and a release sound used when the animal is trapped. Species: cow, wolf, goat (and a Halloween "spooky" goat with an eye light that resists contaminated-zone effects), roe deer, red deer, reindeer (and a Christmas variant), chickens (a rooster and three hens, replaced on death by a dead-item class and not skinnable), sheep, mouflon, domestic pig, wild boar, bear, hare, desert monitor lizard, fox, and Dobermann and German shepherd dogs in several skins. Only the **wolf, the bear and the two dog families** return `IsDanger()` true. `TrackNaturalInstinctsAchievement` is true for roe deer, red deer and reindeer. Ambient animals are spawned by the Central Economy (`AnimalMaxCount` in `globals.xml` and the event table, see 5.6 and 5.11), not by script.

### 6.26 AI perception: noise, vision and alert (engine slice, addendum to 5.4) [obs for the config and the hearing formula, inf for vision and alert details]
Tables: `data/ai_perception.csv` (the vision, noise and alert settings of all 36 `CfgAIBehaviours` classes, rebuilt with the fixed inheritance, so soldier and heavy infected now resolve) and `data/noise_sources.csv` (851 noise definitions on items, weapons and ammo), built by `scripts/ai_perception.py` and `scripts/noise_sources.py`. Engine classes: `enf::AITargetSystem` (each agent's knowledge of targets: vision, noise, damage), `enf::AINoiseSystem`, an alert system and `AIBehaviourHL`.

**What makes noise (script call sites).** The player adds noise through `AddNoise` with a `NoiseParams` template loaded from config: footsteps by stance, landing, voice, door and fence actions. Items add timed noise at a position (`AddNoiseTarget`). A config noise template has a `strength` and a `type` (`sound` or `shot`). Default player values (`SurvivorBase`): step standing 16, crouching 6, prone 5; light landing 8, heavy landing 16; whisper 5, talk 25, shout 40; door, fence and other actions 10. Others: campfire 30 (special fireplaces 15), road flare 30 (shot type), alarm clocks and the kitchen timer, car horns (41 vehicles), boat engines, smoke grenades, the flare gun flare 30, explosions and ammo hits (`cfgAmmo >> NoiseHit`: 221 ammo classes, for example 5.56 is 10), and each weapon's `NoiseShoot` (204 weapons, type `shot`: M4A1 80, Mosin 100, flare gun 40). Weather can lower noise strength: `GetEnvironmentNoiseReduction(pos)` applies the rain, snowfall, fog, wind, sandstorm and sea multipliers of the noise template (`maxNoiseRange` and the dampening multipliers are loaded from the same body, `FUN_140552590`).

**How an agent hears a noise** (`FUN_14054ec90`, [obs]):
1. The noise strength is first reduced by obstruction: the largest occlusion value on the way, times the agent's `noiseDampeningMultiplier`, never below 0. The collision multipliers (`noiseCollisionDampeningMultiplier`, and `noiseShotCollisionDampeningMultiplier` for shots, plus a raycast length) feed that occlusion.
2. Then the distance `d` from the source is tested against the agent's `NoiseSystemParams` window `[rangeMin, rangeMax]` for ordinary sounds, or `[rangeShotMin, rangeShotMax]` with `shotVolExponent` for shot-type noise. Beyond the maximum the noise is **not heard**. Inside the minimum it keeps its full strength. Between them the strength is multiplied by `(1 - (d - min) / (max - min)) ^ exponent` (exponent 1, so linear, for ordinary sounds).
3. If the window is degenerate (maximum not above minimum) the maximum is taken as the minimum plus 1.
So a noise's `strength` is its loudness at the source, and the listener's window decides how far it carries. The per-team `NoiseStrengthTeamMultipliers` (player, zombies, big game) scale the noise by who made it. Noises an agent remembers are kept in a short list; the weakest is dropped when the list is full (`FUN_14054e470`, with a randomised decay).

**Alert** (the alert system and its levels; [obs] for the fields, [inf] for the rate): each agent has an alert value that rises with what it perceives and falls over time. The rise per second is the vision contribution times `visionToAlertMultiplier` plus the noise contribution times `noiseToAlertMultiplier` (shot-type noise uses `noiseShotToAlertMultiplier`); `continuousNoiseToAlertMultiplier` and `damageToAlertMultiplier` also exist, and a damage multiplier of 10,000 (infected) pushes the alert to its maximum at once. The value falls by `dropSpeed` per second of the current level after `dropDelay` seconds. The levels are **Calm, NonSpecificThreat, SpecificThreat, Alerted**; each has a `maxAlertValue`, and the level is chosen from the alert value, so crossing a level's value moves the agent up. This is what drives the script-visible behaviour states (calm, disturbed, attracted, chase).

**Standard infected** (class `Infected`): vision to alert x20, noise x1.0, shot noise x1.7, damage x10,000; Calm drops 1 per second with no delay and a maximum of 20; Alerted drops 2.5 per second after 1 second, maximum 100. Hearing: ordinary sounds from 0 to 35 m (linear fall-off), shots from 25 to 110 m. Variants: the runner has noise x1.5, shot x2.0 and vision x25; the heavy soldier has vision x25, shot x2, a drop speed of 1, a **10 m minimum hearing range** and shots from 50 m, with smaller noise radii (5 to 20 m ordinary, 25 to 40 m shots); the mummy equals the male. `NoiseSystemParams` also holds `radiusMin/Max` and `radiusShotMin/Max` (10 to 25 and 35 to 70 for infected), whose use I did not decode [?].

**Animals.** Wolf: vision x20, noise x1.5, damage x200, calm maximum 30, alerted maximum 100 dropping 11 per second; hears 25 to 100 m and shots 0 to 50 m; team noise multipliers big game 0.4, infected 0.6, players 1.0; vision multipliers players and infected 1.0, big game 0.6. Dobermann: vision x18, calm maximum 80, alerted maximum 200 dropping 18; hears 25 to 80 m. Bear: vision x6, noise x1.2, shots x0.5, damage x1,000,000; four levels (25, 50, 75 and 200); hears 20 to 110 m and shots 100 to 300 m. Herbivores: vision x7, noise x1.0, hear 50 to 120 m, shots 0 to 10 m, and a x10 vision multiplier for predators. Ambient animals (hares, chickens): hear 2 to 15 m, shots 100 to 300 m.

**Vision** (the `TargetSystem*` body; the evaluating function is decoded in the addendum below): a cone of angle `visionFov` and range `visionRangeMin` to `visionRangeMax` (standard infected 20 to 40 m, field of view 1.0), a **peripheral** band (2.5 to 20 m, wider angle 2.3), a **close** band (10 m, up to a height of 1.8 m, strength x1.5) and a **proximity** band (2.5 m, strength x2). Strength falls with how fast the target moves (`visionAngularSpeedMin/Max`), is scaled by the target's stance (`visionManSizeStand/Crouch/Prone`: wolf 1.0, 0.8, 0.6; bear and herbivores 1.0, 0.8, 0.5; Dobermann 1.0, 0.7, 0.5; ambient animals 1.5, 0.8, 0.45), by night (x0.3 for infected), rain (x0.6), fog (x0.5) and sandstorm multipliers, and by a per-team multiplier (`VisionTeamMultipliers`).

**What this means for tuning.** The numbers that matter for stealth are the listener's hearing window, the source's `strength` (footsteps 16, 6 and 5 for standing, crouching and prone), obstruction by walls, and the shot-type windows. Config-only mods can change all of them through `CfgAIBehaviours` and the noise templates. Still to confirm: the exact alert rise rate and the use of the noise `radius` fields (the vision formula is in the addendum below).

**6.26 addendum: the vision evaluation** [obs for the code and the offsets, inf for the angle convention]. `AITargetSystem::UpdateTargetVision` is `FUN_1405507c0`; it runs for every tracked target and calls three virtuals of the target system (the DayZ one is `AITargetSystemBase`, `0x1413365b8`): the **maximum sight distance** (`FUN_140c7c290`, slot 4), the **vision strength** (`FUN_140c7c410`, slot 6), and a cone test that is a stub returning true (slot 7). The config offsets are those of the loader `FUN_140c7cc40`: range min/max `0x18`/`0x1c`, field of view `0x20`, peripheral range `0x24`/`0x28`, peripheral field of view `0x2c`, close range `0x30`, close height `0x34`, close strength `0x38`, proximity range `0x3c`, proximity strength `0x40`, angular speed min/max/max-multiplier `0x44`/`0x48`/`0x4c`, night `0x50`/`0x54`, rain `0x58`/`0x5c`, fog `0x60`/`0x64`, sandstorm `0x68`/`0x6c`, team multipliers `0x78`. "Min/Max mult" pairs are blended with a plain lerp `min + (max - min) x intensity`.

**Per tick, per target** (all in `UpdateTargetVision`): skip targets that are not valid; if the squared distance is below the maximum-sight value, do a **ray cast** from the observer's eye to the target with a filter that ignores creatures and the target itself; a blocked ray makes the target not visible (a counter lets the target stay "seen" for a few ticks, with `2` ticks of grace after the last clear ray). If the ray is clear, compute the strength; the target counts as **visible when the strength is above a small epsilon** and the "last seen" time and position are refreshed. So walls and objects block sight completely; there is no partial concealment other than what the strength formula gives.

**Direction convention.** The code compares `2 x x` to the field-of-view values, where `x` is a value that grows from 0 straight ahead to 2 directly behind, which fits `x = 1 - cos(angle)` [inf]. With the field of view 1.0 this gives a central cone of **+-60 degrees** (a 120 degree cone), and with the peripheral field of view 2.3 an outer cone out to about **98.6 degrees** from straight ahead; beyond that only the proximity range works.

**Maximum sight distance** (`FUN_140c7c290`): the horizontal circle test for the close band first (see below); then, depending on the angle: inside the central cone, `visionRangeMax x K`; in the peripheral zone, `visionPeripheralRangeMax x K`; behind, just the proximity range (2.5 m), with no `K`. `K` is the sandstorm factor at the observer (`FUN_140c7cba0`: sandstorm intensity at the position blended between `visionSandstormMinMult` and `MaxMult`, 1.0 when there is no sandstorm).

**Vision strength** (`FUN_140c7c410`, [obs]; the result multiplies the alert rate): with `d` the distance to the target,
1. If the target is behind the peripheral cone and farther than the proximity range: strength 0. Inside the proximity range the starting multiplier is `visionProximityStrengthMult` (2.0 for infected); otherwise 1.0.
2. **Close band:** a circle of radius `visionCloseRange` (10 m) centred `visionCloseRange` metres **in front of** the observer on the ground plane, with a height window of `visionCloseHeight` (1.8 m). A target inside it multiplies the strength by `visionCloseStrengthMult` (1.5).
3. **Distance window:** inside the central cone the window is `[rangeMin, rangeMax]`, in the periphery `[peripheralMin, peripheralMax]`. The maximum is scaled by the target's **stance size** (`visionManSizeStand/Crouch/Prone`, via the target's component: a crouching or prone player is seen from a shorter distance) and by `K`. Beyond the scaled maximum the strength is 0. Between the scaled minimum and maximum the strength is `(maxEff - d) / (maxEff - min x K)`, a straight line from 1 down to 0, which replaces the proximity and close multipliers there.
4. **Team multiplier:** looked up by the target's team in `VisionTeamMultipliers` (1.0 if missing). If the target carries a visibility-modifier flag, an extra factor from the target is applied (not decoded).
5. **Movement:** the target's lateral angular speed seen from the observer, `|v perpendicular| / d` radians per second, scales the strength: below `visionAngularSpeedMin` no change, between min and max a blend toward `visionAngularSpeedMaxMult`, above max the full `MaxMult`; at essentially zero distance the multiplier is applied directly. For standard infected the min and max are 0.1 and 0.5 and the multiplier is 1.0, so **movement makes no difference to infected**; a config with a multiplier above 1 would make moving targets easier to see.
6. **Weather and light:** the result is multiplied by the night, rain and fog factors (each a lerp between its min and max multiplier by the world's night, rain and fog intensity; infected: night down to 0.3, rain 0.6, fog 0.5).
The maximum is therefore `strength = proximity or close multiplier (replaced by the linear distance factor beyond the minimum) x team x movement x night x rain x fog`, in the range 0 to roughly 2.

**How vision feeds the alert** (`FUN_140554e10`): each tick the alert value changes by `-dropSpeed(current level) x dt` plus, for every tracked target, `vision strength x visionToAlertMultiplier x dt` and a continuous-noise term; instantaneous noise events add a one-off impulse. A standard infected has `visionToAlertMultiplier` 20, so a target at full strength adds up to 20 per second against a Calm maximum of 20 and a Calm drop of 1 per second: **a target seen at full strength tips an infected out of Calm in about a second**, while a target seen only at 10 percent strength (far, crouched, at night, in rain) adds 2 per second and loses 1 per second to the drop, so it takes about 10 seconds. These are worked examples from the formulas, not measured [inf].
