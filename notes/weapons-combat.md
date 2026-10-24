# Weapons and combat (scripts)

Part of the DayZ static analysis notes (see `README.md` in this folder for the map). Firearms and recoil, melee, grenades and explosives, the weapon state machine tables. Sections 5.3, 6.16, 6.17, 6.24. Section numbers are the original ones, so cross-references such as "see 6.10" still resolve.

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

### 6.24 Weapon state machine tables (task S7, addendum to 5.3) [obs]
`scripts/weapon_states.py` reads every firearm mechanism's `InitStateMachine()` and writes `data/weapon_states.csv` (the **82 stable states** with their flags: bullet in chamber, magazine attached, jammed, bolt open, and the muzzle state `E` empty / `L` loaded / `F` fired-out) and `data/weapon_transitions.csv` (**1,410 transitions** in 18 mechanism classes: from-state, event, to-state, guard). All from and to states resolved to a class; for transitions that combine guards (`GuardAnd`, `GuardNot`) only the outermost guard class is recorded.

Transitions per mechanism (stable states declared in that class in brackets): `Pistol_Base` 239 (10), `RifleBoltLock_Base` 182 (8), `BoltActionRifle_ExternalMagazine_Base` 177 (8), `RifleBoltFree_Base` 125 (6), `OpenBolt_Base` 122 (7), `DoubleBarrel_Base` 88 (8), `SKS_Base` 61 (4), `ChamberFirst_InnerMagazine_SemiAutomatic_Base` 59 (4), `Repeater_Base` 57 (5), `Mp133Shotgun_Base` 53 (4), `BoltActionRifle_InnerMagazine_Base` 51 (4), `RifleSingleShotManual_Base` 42, `RifleSingleShot_Base` 40 (4), `Crossbow_Base` 38 (3), `SingleShotPistol_Base` 30 (3), `Flaregun` 26 (3), `Magnum_Base` 17 (1), `Rifle_Base` 3. Mechanisms with no stable states of their own reuse a parent's.

The pattern is the same everywhere. A stable state is entered by the **end** of an action: "human command action finished" (490 transitions) or "aborted" (512) take an action state (charging, chambering, reloading, firing, unjamming) back to a stable one, and the guards pick which one from the real contents of the weapon. Other events start actions: trigger 91, mechanism (charge) 72, dry-fire timeout 59, load one bullet 51, reload timeout 43, swap, detach and attach magazine 20, 20 and 19, unjam 17, trigger-to-jam 16. Most common guards: current chamber empty 138, has magazine 94, weapon open 40, chamber fired-out 36, jammed 32.

Action states used as targets, by count: dry fire 60, charging 43, chambering 26, unjamming 17, attach magazine 16, replace magazine and chamber next 16, detach magazine 16, charge inner magazine 16, fire-to-jam 13, fire 12, fire last 10, eject bullet 5, multi-muzzle fire 4, fire and chamber next 4. State IDs follow the pattern in 5.3 (`BAREM_CLO_BU1_MA1` = bolt-action rifle with external magazine: closed, bullet, magazine). Use the CSVs to answer "what can happen to a loaded Mosin with a jammed round" by filtering on `from_class`.
