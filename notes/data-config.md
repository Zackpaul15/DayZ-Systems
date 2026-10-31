# Data, configs, archives, recipes and how to reproduce

Part of the DayZ static analysis notes (see `README.md` in this folder for the map). Section numbers are the original ones, so cross-references such as "see 6.10" still resolve.

## 1. Install layout [obs]

| Part | Notes |
|---|---|
| `DayZ_x64.exe` (24.8 MB) | Retail game, native x64, SHA-256 `c6709ece...99f933` |
| `DayZDiag_x64.exe` (27.4 MB) | Diagnostic build, same version. Compared with retail by strings only (3.1); not decompiled |
| `DayZLauncher.exe` | Managed .NET Framework 4.5 (x86). Uses Json.NET, protobuf-net, log4net, Xceed WPF toolkit |
| `BattlEye/` | `BEClient_x64.dll`, `BEService_x64.exe`, `DayZ_BE.exe` launcher. Not analyzed |
| `Addons/` | 118 PBO archives (20.6 GB), each with a `.bisign` signature. Prefixes: `structures`, `characters`, `gear`, `weapons`, `sounds`, `worlds`, `vehicles` |
| `dta/` | 7 engine and script archives (308 MB): `scripts.pbo`, `core.pbo`, `system.pbo`, `gui.pbo`, `graphics.pbo`, `bin.pbo`, `languagecore.pbo` |
| `nasdara/addons/`, `sakhal/Addons/` | Map content: 24 archives (7.1 GB) and 9 archives (3.3 GB). The scripts define world-data classes (temperature tables and so on) for ChernarusPlus, Enoch, Nasdara and Sakhal, so these are maps [obs] |

Across all four archive folders there are **158 archives, 31.3 GB, 135,353 entries**: see 1.2.

### 1.2 What the 158 archives contain [obs, from archive headers only]

`scripts\pbo_inventory.py` reads only each archive's header (names and sizes), so it is fast and never touches the bulk data. Output: `data\archives.csv`.

| Folder | Archives | Size |
|---|---|---|
| `Addons` | 118 | 20.6 GB |
| `dta` | 7 | 0.3 GB |
| `nasdara\addons` | 24 | 7.1 GB |
| `sakhal\Addons` | 9 | 3.3 GB |

By file type, over the 135,353 entries: **40,894 `.rvmat`** (materials), **38,277 `.paa`** (textures), **28,445 `.ogg`** (sound, all of it Ogg; no `.wss`), **10,638 `.p3d`** (models), 9,113 `.anm` (animations), 3,062 `.c` (script files, 3,056 of them in `scripts.pbo`), 502 `.edds` and 382 `.bin` (configs and other binaries). Everything is stored uncompressed.

By name family (the part before the first underscore):

| Family | Archives | Size | Entries |
|---|---|---|---|
| structures (buildings, wrecks, props) | 37 | 13.7 GB | 24,414 |
| worlds (map data, navigation, economy) | 14 | 4.7 GB | 43,284 |
| characters (bodies, clothing, zombies) | 16 | 4.1 GB | 5,621 |
| gear (items) | 16 | 1.3 GB | 5,065 |
| plants | 4 | 1.3 GB | 3,496 |
| weapons / weapon (parts) | 15 / 7 | 1.7 GB | 3,064 |
| vehicles | 5 | 1.1 GB | 2,040 |
| sounds | 9 | 0.7 GB | 28,453 |
| surfaces, rocks, animals, anims, water | 18 | 2.1 GB | | 
| engine and small archives (gui, dz, graphics, system, scripts, core, language, data, bin, ai, ui, server, modules) | 17 | 0.4 GB | |

The biggest archive is `structures_sakhal.pbo` (1.8 GB). The sounds are concentrated in `sounds_characters` (12,808 files), `sounds_weapons` (7,642) and `sounds_ai` (4,780). **Each map has the same four-part world set:** the base map archive, `_data` (textures), `_nav` (navigation meshes; the biggest is `worlds_nasdara_nav.pbo` at 830 MB) and `_ce` (the Central Economy and server mission template, covered in 5.6). Retail (`Addons` and `dta`) is 20.9 GB across 125 archives; the two map folders are 10.4 GB across 33.

## 5. Enforce script source (`dta/scripts.pbo`) [obs]

The archive is uncompressed: 3,076 files, 13.5 MB, about 460,000 lines in 3,056 `.c` files. Properties: product `dayz`, prefix `scripts`, version 127662.
A `config.bin` (binarized config) and a documentation file (`staticDefinesDoc.c`) are also inside.

### Layers (compile order matches the five module names in the exe)

| Layer | Files | Lines | Classes | Role |
|---|---|---|---|---|
| `1_Core` | 58 | 11.0k | 119 | Base types, math, param, physics, debug text |
| `2_GameLib` | 13 | 1.7k | 56 | Thin library layer |
| `3_Game` | 440 | 82.1k | 824 | `DayZGame`, entities base, GUI, effects, post-process, systems |
| `4_World` | 2,318 | 284.8k | 5,611 | Gameplay: items, player, creatures, actions, recipes |
| `5_Mission` | 219 | 80.4k | 256 | Mission flow and GUI |

- 6,876 classes, 432 enums, 258 typedefs. Only 3 `modded` classes, so this is vanilla code with no mods layered on.
- About 3,770 declarations are engine-bound (`proto`): `1_Core` 1,079, `2_GameLib` 125, `3_Game` 2,358, `4_World` 208, `5_Mission` 0. That is the visible boundary between script and native engine.
- Largest groupings in `4_World`: `ItemBase` (678 files), user actions (509), recipes (237), firearms (113), buildings (80), player modifiers (63), recoil (56).

### Class backbone (all [obs])

- `CGame` > `DayZGame` (`3_Game\DayZGame.c`, 107 KB).
- `MissionBase` > `MissionServer` and `MissionGameplay` (`5_Mission\mission\`). Server and client run different mission classes.
- Entities: `EntityAI` > `ItemBase` (via `InventoryItem`), `DayZCreature`, `Building`.
- Player: `DayZPlayer` > `DayZPlayerImplement` > `ManBase` > `PlayerBase`.
- Creatures: `ZombieBase` (from `DayZInfected`), `AnimalBase` (from `DayZAnimal`).
- Vehicles: `Transport` > `Car` > `CarScript`.
- Most common base classes: `RecipeBase` (218 subclasses), `ActionContinuousBaseCB` (173), `ItemBase` (100), `Edible_Base` (87).

### Server-side player lifecycle (`MissionServer.OnEvent`)

Handled event types: `ClientPrepare`, `ClientNew`, `ClientReady`, `ClientRespawn`, `ClientReconnect`, `ClientDisconnected`, `LogoutCancel`.
- Prepare: sends gameplay config, restricted-area and bunker-broadcast data to the client.
- New: creates the character (`CreateCharacter`, `EquipCharacter`, `StartingEquipSetup`), announces the player list, syncs lighting and underground areas.
- Ready, respawn and disconnect are handled separately. Logout uses a timed scheduler (`UpdateLogoutPlayers`, `HandleBody`, `InsertCorpse`).

### Client side

`MissionGameplay` owns inventory, HUD, chat, vehicle info, crosshair and input suppression and exclusion handling.

### Gameplay systems (names only)

- **Player stats** (`PlayerModifiers`, about 63): hunger, thirst, stomach, health regen, bleeding, shock, fever, wetness, broken legs and arms, plus diseases such as cholera, influenza and pneumonia and contamination levels. `PlayerNotifiers` (about 17) drive the HUD icons.
- **Symptoms** (`PlayerSymptoms`): cough, sneeze, vomit, faint, blur and similar effects.
- **Crafting:** `RecipeBase` subclasses. **Actions:** continuous, instant, interact and single-use bases.
- **Networking glue:** `ERPCs` enum (193 entries) for script RPCs, plus `ScriptRPC`, `Param` and `JsonSerializer`.
- **Other:** fishing and trap catching (`CatchingContext*`), arrows, temperature, dynamic music, a bot framework (`Bot*`, state machine), and Xbox/Bios console services.

### Build-time defines (from the shipped doc)

`DEVELOPER`, `RELEASE`, `SERVER`, `NO_GUI`, `BULDOZER`, `WORKBENCH` and platform defines select code per build. Retail client uses `RELEASE`. Retail server uses `RELEASE` + `SERVER` + `NO_GUI`.

### 5.1 The binary config (`config.bin`) and the real item numbers [obs unless noted]

The scripts refer to many numbers that live in the game's binary configs: item weights, clothing warmth, armor multipliers, ammo damage. Those configs are "rapified" `config.bin` files (they start with `\0raP`). I wrote a reader for them (in `scripts/`, see section 8) and ran it over the whole install. The derived tables (clothing, weapons, ammo, food, recoil) are saved as CSV in `data/`.

**Coverage.** 267 `config.bin` files in 142 of the 158 archives (the other 16 hold no config), including nested ones such as `weapons_firearms.pbo` > `ak74\config.bin`. All parsed with **0 errors**. Merged and inheritance-resolved: `CfgVehicles` 6,789 classes (items, clothing, food, creatures, buildings), `CfgWeapons` 215, `CfgMagazines` 131, `CfgAmmo` 254, plus sound, surface and world sections.

**How I counted.** "Spawnable" means `scope = 2`. Base classes (`scope` 0 or 1) are templates. Inheritance is resolved by name through the parent chain. My tool merges same-named classes but does not resolve inheritance *inside* nested classes, so some right-side body zones show empty (they mirror the left). Values like 0.6000000238 are 32-bit floats and are rounded below.

| Family | All classes | Spawnable |
|---|---|---|
| Inventory items (`Inventory_Base`) | 2,537 | 2,000 |
| Clothing (`Clothing_Base`) | 1,067 | 899 |
| Food and drink (`Edible_Base`) | 165 | 151 |
| Weapons (`Weapon_Base` in `CfgWeapons`) | 214 | 136 |
| Infected (`ZombieBase`) | 372 | |
| Animals (`AnimalBase`) | 50 | |
| Vehicles (`Transport`) | 52 | |

**Clothing** (899 spawnable items). `heatIsolation` is the warmth value used by the heat-comfort calculation in 6.10. Per slot:

| Slot | Items | Warmth min / avg / max | Weight g min / avg / max |
|---|---|---|---|
| Headgear | 229 | 0.10 / 0.47 / 1.00 | 80 / 584 / 5,250 |
| Body | 200 | 0.05 / 0.52 / 1.00 | 110 / 1,455 / 10,000 |
| Legs | 111 | 0.10 / 0.41 / 1.00 | 150 / 571 / 8,000 |
| Back | 80 | 0.10 / 0.59 / 1.00 | 300 / 1,446 / 3,300 |
| Feet | 77 | 0.05 / 0.53 / 1.00 | 200 / 742 / 2,000 |
| Vest | 43 | 0.00 / 0.51 / 1.00 | 200 / 3,061 / 12,000 |
| Gloves | 38 | 0.05 / 0.68 / 1.00 | 100 / 207 / 454 |
| Mask | 31 | 0.00 / 0.62 / 1.00 | 4 / 233 / 1,090 |
| Armband, eyewear, hips, holsters | 84 | about 0 | |

- Warmest (1.0): mountain backpacks, ghillie suits, leather gloves, balaclava. Coolest non-zero (0.05): surgical gloves, hockey mask, ballerinas. Heaviest: plate carrier 12,000 g, chainmail 10,000 g and chainmail leggings 8,000 g.
- Each item also has `varWetMax` (the most wet it can get): average 0.71, from 0.05 to 1.0. **The orange raincoat, Mich 2001 helmet, NBC jacket and Gorka jacket I checked all have 0.249**, just under the 0.25 "wet" threshold in 6.10, so they can never make the player "wet" [inf; I did not check every item].
- Examples:

| Item | Slot | Weight | Warmth | Max wetness | Notes |
|---|---|---|---|---|---|
| Jeans_Blue | Legs | 470 g | 0.60 | 0.79 | 140 hp; melee armor x0.90 |
| Hoodie_Blue | Body | 850 g | 0.60 | 1.0 | |
| MilitaryBoots_Black | Feet | 1,100 g | 0.90 | 0.49 | 180 hp |
| Raincoat_Orange | Body | 1,700 g | 0.25 | 0.249 | |
| BalaclavaMask_Black | Mask | 130 g | 1.0 | 1.0 | biological protection 0.25 |
| Mich2001Helmet | Headgear | 1,200 g | 0.25 | 0.249 | projectile armor: health x0.25, shock x0.5 |
| PlateCarrierVest | Vest | 12,000 g | 0.80 | 0.49 | 225 hp; projectile health x0.3, blood x0, shock x0.6; melee and infected health x0.3, shock x0.25; frag health x0.5 |

- **Armor.** 73 items carry projectile-armor entries; the best health multiplier is **0.25** (helmets: Mich 2001, ballistic, Gorka, Ssh68, T56 tanker). Armor entries are multipliers on incoming damage per damage type and per meter (health, blood, shock). The plate carrier's blood multiplier is 0, so a projectile hitting a zone it covers deals no blood damage; by the script rule in 6.12 that would also mean no bleeding source [inf].
- **Protection against agents.** 85 items give biological or chemical protection: gas mask 1.0 / 1.0, winter coif 0.5 / 0.6, NBC gloves and hoods chemical 1.0, Gorka jacket chemical 0.25, balaclava biological 0.25. These feed the airborne-agent protection in 6.9.

**Weapons** (136 spawnable): 60 rifles (including auto rifles and SMGs), 31 bolt-action, 24 pistols, 8 bows and crossbows, 7 shotguns, 3 launchers and 3 non-lethal. 36 can fire full auto. Weights run from 350 g to 7,500 g. Rate of fire is `60 / reloadTime` of the fastest mode (my arithmetic); semi-auto and bolt modes show their cycle cap.

| Weapon | Weight | Rate | Ammo | Health / blood / shock | Muzzle speed m/s | Barrel armor | Speed mult. |
|---|---|---|---|---|---|---|---|
| M4A1 | 2,276 g | 923 | 5.56x45 | 110 / 100 / 110 | 850 | 2.5 | 0.90 |
| AKM | 2,140 g | 612 | 7.62x39 | 110 / 100 / 110 | 640 | 4.44 | 0.90 |
| AK74 | 3,070 g | 612 | 5.45x39 | 115 / 100 / 115 | 880 | 2.74 | 0.70 |
| SCAR-H | 3,700 g | 612 | .308 Win | 150 / 100 / 150 | 770 | 2.6 | 0.93 |
| SVD | 3,700 g | 500 | 7.62x54R | 150 / 100 / 150 | 785 | 1.6 | 1.0 |
| MP5K | 1,840 g | 923 | 9x19 | 40 / 100 / 40 | 350 | 1.25 | 1.05 |
| UMP45 | 2,500 g | 612 | .45 ACP | 40 / 100 / 40 | 260 | 0.9 | 1.05 |
| VSS | 2,600 g | 923 | 9x39 | 75 / 100 / 75 | 280 | 2.4 | 1.0 |
| Ruger 10/22 | 2,300 g | 600 | .22 | 20 / 100 / 20 | 370 | 2.0 | 1.15 |
| CZ527 (bolt) | 2,720 g | 60 | 7.62x39 | 110 / 100 / 110 | 640 | 1.11 | 1.2 |
| FNX45 | 950 g | 462 | .45 ACP | 40 / 100 / 40 | 260 | 1.7 | 1.0 |
| Glock 19 | 1,000 g | 462 | 9x19 | 40 / 100 / 40 | 350 | 1.5 | 1.0 |
| Deagle | 1,500 g | 375 | .357 | 65 / 100 / 90 | 440 | 0.8 | 1.0 |

(Mosin, SKS, B95, Izh-18, Winchester 70, MP-133 and the crossbow have no magazine list that my tool followed, so the table does not link them to an ammo class [inf: they chamber loose ammo].) All weapons show the same `dispersion` of 0.002 and use a named recoil profile, for example `recoil_m4`.

**Ammo** (`CfgAmmo`, damage as applied before armor and zone multipliers, against a 100-point health and shock meter):

| Round | Health | Blood | Shock | Muzzle speed | Knock-out refill mult. |
|---|---|---|---|---|---|
| .22 | 20 | 100 | 20 | 370 | 6 |
| .380 | 35 | 100 | 35 | 300 | 6 |
| 9x19, .45 ACP | 40 | 100 | 40 | 350 / 260 | 6 |
| 9x39 / 9x39 AP | 75 | 100 | 75 | 280 / 320 | 4 |
| .357 | 65 | 100 | 90 | 440 | 2.75 |
| 5.56x45 | 110 | 100 | 110 | 850 | 4 |
| 7.62x39 | 110 | 100 | 110 | 640 | 4 |
| 5.45x39 | 115 | 100 | 115 | 880 | 4 |
| .308 Win, 7.62x54R | 150 | 100 | 150 | 770 / 785 | 2.75 |
| 12 gauge slug | 110 | 100 | 110 | 380 | 1.75 |
| 12 gauge pellet (8 per shot) | 35 each | 100 | 35 each | 340 | 1.75 |
| 12 gauge rubber slug / beanbag | 0 | 0 | 150 / 100 | 60 / 240 | 1.75 |
| Hunting bolt / improvised bolts | 125 | 100 | 95 / 85 | 85 to 105 | 1.19 to 3.1 |

- Every real bullet has blood damage 100 and `bleedThreshold` 1.0, which under the rule in 6.12 means a hit that deals any blood damage creates a bleeding source. Bolts, flares and rubber rounds have a threshold of 0.
- The last column is the config value read by `PlayerBase.EEHitBy` as `unconRefillModifier` and multiplied into unconscious shock regeneration in 6.11 [inf: smaller bullets recover faster after a knock-out].
- Melee has 171 damage classes. Examples (health / blood / shock): axe 15 / 100 / 25 (heavy 40 / 100 / 40), baseball bat 20 / 0 / 30 (heavy 30 / 0 / 40), nailed bat 20 / 100 / 30, bear 25 / 100 / 35, and a bear "shock" attack 25 / 100 / 110.
- Magazines: 127 have a count and ammo link. The biggest are a 200-round M249 box, a 75-round AKM drum, a 64-round PP-19 and a 60-round coupled STANAG. A standard STANAG holds 30 rounds and weighs 90 g.

**Health pools** (`DamageSystem`). The player has global **health 100, blood 5,000, shock 100**, matching the thresholds in 6.3 and 6.12. Per zone: head health 33, brain 100, torso 100, arms 100, hands 100, left leg and foot 125 (the right side mirrors it), each with blood 100 and shock 0. Infected: global health 100, head 30, torso, legs and feet 100, and no armor. Animals (health): red deer 400, cow 500, brown bear 800 (with 5,000 shock), wolf 200, boar 350, chicken 15.

**Food.** 151 edible items; only **52 define a `Nutrition` class** in config. Examples (energy / water, quantity): cola 50 / 90 (330), rice 100 / 0 (500), lassi and ayran 20 / 100, cereal and powdered milk energy 400, candy canes 4,500 energy. Fresh fruit and meat (apple, pear, banana, steaks) have no Nutrition in config, so their values come from the script side [inf]. The only agent bits configured on nutrition are 4 (salmonella) and 16 (food poisoning), matching the agent IDs in 6.9. The heaviest items are base-building objects at 100,000 g (fence, watchtower, shelter site, territory flag, garden plot).

**Not done.** Only the base rapify features that appear in this install were needed; I did not decode config expressions or the `enum` table (empty here). Vehicles, buildings and sound sections were parsed but not analyzed, and zone mirroring for the right side of bodies needs nested-inheritance support in my tool.

### 5.5 The language table and in-game names [obs unless noted]

Source: `dta\languagecore.pbo`, which holds one file, `stringtable.csv` (5 MB, UTF-8). The `scripts\stringtable.py` tool reads it straight from the archive and resolves config names.

**Format.** A header row, then one row per text key. Columns: the key, `original`, `english`, and 13 translations (Czech, German, Russian, Polish, Hungarian, Italian, Spanish, French, Chinese, Japanese, Portuguese, simplified Chinese). **7,034 rows, 7,031 unique keys.**

**Key conventions.**
- Config names are written `$STR_<something>`; the key is the same text without the `$`, case-insensitive.
- For items the suffix `0` is the **display name** and `1` is the **description**, for example `STR_cfgWeapons_M4A10` gives "M4-A1" and `STR_cfgWeapons_M4A11` gives its description. 2,394 keys are `cfgVehicles` entries, 202 magazines and 193 weapons.
- Script action labels use a `#key` form, for example `#treat_wound` resolves to "Treat my wound" (used by the bandage action in 5.2).
- **1,449 English entries start with `$UNT$`**, a marker for placeholder text: the entry exists but its wording is not final (for example an unused `Jeans_Blue` entry and the name of the trumpet).

**Translation coverage.** Most non-English columns have 13 empty cells (Hungarian has 252). The number of cells identical to the English text, a sign of an untranslated entry, is about 1,770 to 2,000 for most languages (Chinese 1,800, Japanese 1,769, Russian 1,847, German 1,998). **Hungarian is mostly untranslated**: 6,253 cells identical to English and 252 empty.

**The game renames most real-world weapons.** Class names in the notes are the internal ones; the in-game names are different:

| Class | In-game name | Class | In-game name |
|---|---|---|---|
| M4A1 | M4-A1 | Glock19 | Mlock-91 |
| AKM | KA-M | Colt1911 | Kolt 1911 |
| AK74 | KA-74 | FNX45 | FX-45 |
| AK101 | KA-101 | Deagle | Deagle |
| SCARH | SCR 17 | CZ527 | CR-527 |
| SVD | VSD | Cz75 | CR-75 |
| MP5K | SG5-K | Izh18 | BK-18 |
| UMP45 | USG-45 | Mp133Shotgun | BK-133 |
| Ruger1022 | Sporter 22 | Winchester70 | M70 Tundra |
| B95 | Blaze | SV98 | VS-89 |
| SKS | SK 59/66 | Saiga | Vaiga |
| FAL | LAR | Aug | AUR AX |
| PP19 | Bizon | Scout | Pioneer |
| Famas | LE-MAS | Magnum | Revolver |
| Mosin9130 | Mosin 91/30 | VSS, M79, Longhorn, Crossbow | unchanged |

Other items from the notes:

| Class | In-game name | Class | In-game name |
|---|---|---|---|
| Mich2001Helmet | Tactical Helmet | MountainBag_Red | Mountain Backpack |
| GorkaHelmet | Assault Helmet | CoyoteBag_Brown | Tactical Backpack |
| Ssh68Helmet | Combat Helmet | AssaultBag_Ttsko | Assault Backpack |
| GasMask | Combat Gas Mask | TaloonBag_Blue | Hiking Backpack |
| BalaclavaMask_Black | Ski Mask | MilitaryBoots_Black | Assault Boots |
| GorkaEJacket_Summer | Patrol Jacket | PartyTent | Canopy Tent |
| NBCJacketGray | NBC Jacket | BandageDressing | Bandage |
| PlateCarrierVest | Plate Carrier | SodaCan_Cola | Nota Cola |
| Ballerinas_Blue | Flat Shoes | BoxCerealCrunchin | Cereals |
| Animal_CervusElaphus | Stag | Animal_BosTaurus_Brown | Bull |
| Animal_SusScrofa | Wild Boar | Animal_GallusGallusDomesticus | Rooster |
| Animal_UrsusArctos | Brown Bear | Animal_CanisFamiliaris_Dobermann_Brown | Doberman |
| ZmbM_takiCitizenUrbanA_Black | Infected | DeerSteakMeat | Venison Steak |

The `data\clothing.csv`, `weapons.csv` and `food.csv` tables now have a `displayName` column (899 of 899 clothing, 131 of 136 weapons and 149 of 151 food items resolved). I did not copy the language table itself into this folder; it is the game's text and regenerates from the archive.

### 5.8 Crafting recipes [obs unless noted]

Source: `4_World\Classes\Recipes\RecipeBase.c`, the manager `PluginRecipesManager.c`, the registration list in `Recipes\PluginRecipesManagerBase.c`, and one script per recipe in `Recipes\` (234 recipe classes in 234 files). All rows are in `data\recipes.csv`, produced by `scripts\recipes.py`; this section summarizes them.

**The model.** A recipe is **always two ingredients** (`MAX_NUMBER_OF_INGREDIENTS` = 2) and up to 10 results. Each ingredient slot holds a list of acceptable item classes (a class name matches the item or any subclass); the two items you combine are matched against the two slots in either order. Craft time is `m_AnimationLength` x 4 s (`CRAFTING_TIME_UNIT_SIZE`).

Per recipe the script sets:
- *Conditions:* minimum and maximum quantity and maximum damage level per ingredient. The damage limit is 3 on nearly every recipe, so a ruined item (level 4) cannot be used; three recipes disable the check. For the minimum quantity of ingredient 1: 95 recipes do not check it, 31 require at least 1, 4 require at least 2, and the rest are 0 or unset.
- *Effect on each ingredient:* destroy it, change its quantity (negative values consume stack count, charges or liquid, in the item's own unit), change its health, or set its health. This is how tools wear out: for example a knife or saw loses 2 to 12 health per use.
- *Results:* class names to spawn; whether each is set to full quantity, a fixed quantity or a fixed health; whether it inherits health from one ingredient or the average (-2); whether it takes the ingredient's `color` config value as a class-name suffix; where it appears (ground, inventory, or swapping with an ingredient); and whether it takes over an ingredient's variables and attachments (used for upgrades).
- *Skill hooks:* `m_Specialty` is a weight for the soft-skills system (positive = "roughness", negative = "precision"; values are -0.02, 0, 0.01, 0.02 or 0.03). The soft-skills code itself is separate.
- *Extra rules:* a script may override `CanDo` (a final yes/no check) and `Do` (extra work on completion). Without an override, the base `CanDo` refuses any ingredient that has attachments.

**Flow** (server): `PerformRecipe` re-checks the recipe, spawns the results (`SpawnItems`), applies result changes, applies ingredient changes, calls the recipe's `Do`, then deletes the destroyed ingredients. Recipes are indexed by ingredient class in a cache built at start-up so the inventory UI can quickly list what two items can do (`GetValidRecipes`); a performed recipe is sanity-checked on the server (items not owned by another live player and within 5 m of the player).

**What is in the table.**

| Group | Count | Notes |
|---|---|---|
| Registered and live | **143** | `RegisterRecipe(new X)` outside comments |
| Registered but commented out | 74 | 62 paint-job recipes (weapon, magazine, helmet and ghillie recolours) plus 12 others: improvised arrows, fishing bait, camo net shelter, rag cleaning and repair, patching, torch refuel, eye-patch repair, the Gorka helmet assembly and sawing off a painted Mosin. The source says commented-out recipes are "usually commented out for a reason", so treat them as removed |
| Defined but never registered | 14 | Dead code: `DrainLiquid`, `PourLiquid`, `LoadMagazine`, `CraftBow`, `SharpenStick`, `WriteLetter`, `RecipeTest`, `AttachHolster`, `AttachPouch` and the `DeCraft` bow, armband and plate-carrier recipes. Nothing else in the scripts references them [inf: liquid transfer and magazine loading are done by actions instead] |
| Base classes | 3 | `PrepareAnimal`, `PrepareFish`, `CutOutSeeds`: shared setup for the animal, fish and seed recipes |

Of the 143 live recipes: **62 "Craft" and 25 "DeCraft"** (take apart: ghillie pieces, traps, spear, splint, hand drill, waterskin, backpacks, wooden crate, cooking stand, detonator and so on), 9 animal and fish preparations, 8 repair recipes, 8 saw recipes (7 sawing off a firearm barrel, 1 sawing a log), 4 seed extractions, 4 splits (firewood, broom, long stick, stones), 3 open-container recipes (can, gun case, briefcase), 3 sharpening, and 17 others (2 each for attach, close, fill and torch upgrade, and single recipes for disinfect, purify water, blood test, chelate water, fuel chainsaw, clean weapon, extinguish torch, peel potato and poke holes in a barrel).

**Timing.** Craft times: 2 s (18 recipes), 4 s (72), 6 s (31), 7.2 s (2: armbands from a flag or raincoat), 8 s (19: cooking stand, fish trap, improvised bags, improvised explosive, wooden crate and others), and 12 s (1: repairing chainmail with pliers). None is instant, and only `CraftTannedLeather` can be done with the items anywhere in the inventory rather than in hands.

**Ingredient effects (live recipes).**
- Ingredient 1 is usually the consumed material: destroyed in 74 recipes (58 outright, 16 together with a quantity or health change), quantity reduced in about 30 more (19 of them by 1), and kept in 34.
- Ingredient 2 is usually the tool: kept in 23, destroyed in 27, and health-damaged in 70 (5 health in 14 recipes, 12 in 12, 4 in 8, 10 in 7, 0.5, 2 or 6 in 5 each).
- 82 live recipes have an extra `CanDo` rule, declared by the recipe itself (69) or inherited from a parent recipe class (13); 32 have no spawned result because they change an existing item (repairs, sawing off a barrel, opening a case, purifying water, torch upgrades, tanning a pelt).
- 7 recipes pick the result's colour variant from an ingredient (the armbands, Christmas light headband, drysack, witch hood, barrel holes and metal wire).

**The "any sharp tool" lists.** Cutting recipes accept a long shared tool list. **51 live recipes** accept a kukri knife, and the same ~50 blades (sickle, Fange knife, kitchen knife, steak knife, stone knife, cleaver, combat and hunting knives, machetes, swords, bayonets, Akinaka, Jambiya, scimitar, doner knife and others). The hacksaw is accepted by 60 recipes, the hatchet by 54, the wood axe and firefighter axe by 53 each, the hand saw by 49. Used as ingredient 2, the tool loses a few health points per craft.

**Examples** (ingredient 1 + ingredient 2 -> result, seconds):

| Recipe | Inputs | Result | s |
|---|---|---|---|
| Craft fireplace | a fuel or tinder item (stick, firewood, rag, bandage dressing, paper, book, bark, leaflets) + a different one | Fireplace; both inputs become attachments | 4 |
| Craft torch | rag + wooden stick or sharp stick (uses 1 of the stick) | Torch | 2 |
| Craft stone knife | small stone (destroyed) + small stone or stone | Stone knife | 6 |
| Craft bone knife | bone (uses 1) + stone or small stone | Bone knife | 6 |
| Craft splint | rag, dressing, duct tape or shemag + wooden sticks (uses 2) | Splint | 4 |
| Craft metal wire | barbed wire (destroyed) + pliers (-0.5 health) | Metal wire | 4 |
| Craft rope | rag (6) + rag (6) | Rope | 6 |
| Craft fishing rod | rope + long or sharp stick (both destroyed) | Improvised fishing rod | 6 |
| Craft cooking stand | wooden stick (2) + long or sharp stick | Cooking stand | 8 |
| Craft tripwire | wooden stick (2) + metal wire | Tripwire trap | 4 |
| Craft ghillie suit | netting (4) + burlap strips (10) | Ghillie suit (tan) | 4 |
| Craft leather sack | tanned leather (2) + leather sewing kit (10) | Leather sack | 6 |
| Craft wooden crate | planks (8) + nails (16) | Wooden crate | 8 |
| Craft improvised explosive | small protector case (destroyed) + electronic repair kit (destroyed) | Improvised explosive | 8 |
| Split stones | stone + pickaxe, sledgehammer, hammer or mace (-4 health) | 3 small stones | 6 |
| Saw off a Mosin | Mosin 9130 + hacksaw (-10 health) | no spawned item; the rifle is changed by the recipe's `Do` [inf] | 8 |
| Repair chainmail | pliers + chainmail piece | no spawned item; the piece is repaired [inf] | 12 |

**Caveats.** The CSV records what the `Init` functions assign, followed through `super.Init()` for the fish, animal and seed families. Quantities are the raw script numbers; what "-25" or "-10" means depends on the item's own unit (for kits and liquids it is a fraction of the capacity). Two live recipes (`AttachHolsterPouch`, `AttachPouchesHolster`) have a name key missing from the language table, and `CraftWoodenCrate` builds its name by concatenating two strings in the script ("oink, create proper string" in the source comment).

## 8. Reproducing

- **Engine queries** use a persistent headless Ghidra 12.1.4 project (`...\Code stuff\tools\ghidra_projects\DayZ`, program `DayZ_x64.exe`). `powershell -ExecutionPolicy Bypass -File scripts\ghidra\run_batch.ps1 TASKS.txt OUT.txt` runs a task file (lines `decompile`, `xrefs`, `bytes`, `string`, `symbols`, `vtable`, `instrscan TEXT START END`, `funcs START END`) in seconds to a minute. Run one Ghidra process at a time. The older REA route (a ten-minute re-import per query, an MCP time-out of about a minute) is no longer used.
- **Regenerating everything**: `bootstrap.py OUT_DIR` extracts the scripts, the configs, the economy files, the language table and the penetration materials outside the project; `build_tables.py OUT_DIR --check` rebuilds every table in `data\` and compares it with the committed one (`--adopt` copies the result, `--ghidra` also rebuilds the native-API tables); `check_notes.py` checks the notes, the section map, the tables and the README for consistency; `selftest.py` runs regression tests on small made-up fixtures (comparator and malformed rows, staging/adoption gating, recipe counting, native match flag, config resolver, recipe inheritance). `data\PROVENANCE.md` lists the generator of every table.
- PBOs are plain archives; a small reader (entry table, then stored data) was enough for `scripts.pbo`.
- **Config tools** (my own code, in `scripts/` next to these notes; read-only on the game files; run with `py -I`):
  - `pbo_unpack.py ARCHIVE.pbo [DEST]` lists or extracts a PBO. It reads the whole archive into memory, so use it on small ones such as `scripts.pbo`.
  - `rap_reader.py config.bin` parses one rapified config into nested dicts (class bodies, scalars, arrays, extern and delete entries, array append).
  - `pbo_config_dump.py OUT_DIR PBO_DIR ...` finds every `config.bin` (any depth) in every PBO in the folders, seeking past the large data, and writes one JSON per config plus `_summary.json`. For this install: `Addons`, `dta`, `nasdara\addons`, `sakhal\Addons`. It takes about two seconds.
  - `cfgmodel.py` merges the JSON into sections, resolves parent chains and lists descendants. Set `DAYZ_CFG_JSON` to the output folder.
  - `stringtable.py LANGUAGECORE_PBO CONFIG_JSON_DIR CSV ...` reads `stringtable.csv` from `languagecore.pbo` and adds an English `displayName` column to CSVs that have a `name` column. It also works as a module (`load`, `english`).
  - `pbo_inventory.py OUT_CSV PBO_DIR ...` writes one row per archive (size, prefix, entry count, file-type counts) from the headers only.
  - `recipes.py SCRIPTS_DIR OUT_CSV [LANGUAGECORE_PBO]` parses the crafting recipe scripts (following `super.Init()`) and the registration list into one row per recipe class.
- Format notes: header `\0raP`, two integers (0 and 8), the enum table offset, then the root class at offset 16; class bodies are a parent name, a compressed count, then entries (class with body offset, scalar, array, extern, delete, array append); counts use a 7-bit continuation encoding.

**5.1 addendum: nested-class inheritance is now resolved (task D1)** [obs]

`scripts\cfgmodel.py` used to drop the parent named by a nested class (for example `class RightArm: LeftArm` inside `DamageZones`), so right-side body zones and some creature values came out empty (see the limitation in 5.1). The new `resolve_nested` lays each nested class over its named sibling (inherited or defined earlier in the same class) before applying its own entries. **Regression check against the old tool, over all 30,539 classes in every config section: 0 keys lost, 0 values changed, 25,554 keys gained in 2,126 classes** (mostly `DamageSystem` 8,902, `AnimationSources` 6,128, `AttackActions` 4,430, `Construction` 2,522, and smaller counts for `BehaviourHLZombie`, `DamageApplied` and `SimulationModule`). Nested dicts keep a `__parent__` marker so `is_cls()` still works; the nested parent names themselves are no longer kept in the output.

**Correction after the Codex review (CXR-001, CXR-002).** The first version only looked up a nested parent when the class had no same-named class already inherited, and it kept the first parent of a class that several archives declare. Both are fixed in `cfgmodel.py`: (1) an explicit nested parent is now always resolved (as a sibling, else as a root-level class) and laid **under** the same-named class inherited from the parent chain (for example `Apple >> AnimationSources: FoodAnimationSources` now has the six `CS_*` classes of the root class; Plum and Pear likewise); (2) when archives declare different parents for a top-level class, the parent that is a descendant of the other wins (`Man`: `All` in `bin.pbo`, `AllVehicles` in `characters_data.pbo` and `dz.pbo` gives the chain `Man, AllVehicles, All`). Situations that cannot be settled by these rules are collected in `cfgmodel.CONFLICTS` instead of being decided silently: after resolving every class there are 8 unrelated-parent conflicts (all in `CfgLocationTypes`, which no table uses), 20 places where an explicit nested parent and the inherited class disagree on a value (all `SawedoffMagnum` muzzle classes; the inherited value is kept) and 231 nested parents that were not found in scope (for example `SoundVoiceEvent` in `SurvivorBase`; those classes keep only their own entries). What is **assumed, not established**: the engine's real rule for a nested class that has both an explicit parent and an inherited same-named class, and its archive load order. Effect on published numbers: rebuilding all 27 tables with the corrected resolver changed **no value** (the cases found so far concern animation, sound and muzzle fields that no table uses), so the earlier 0-values-changed comparison still holds, now against the corrected rules.

**Body zones** (`data\body_zones.csv`, 19 rows for the player, infected and animal base classes). The player (`SurvivorBase`) has global health 100, blood 5,000 and shock 100, and 11 damage zones:

| Zone | Hit points | Fatal-injury coefficient | Transfers to |
|---|---|---|---|
| Head | 33 | 0.1 | |
| Brain | 100 | 1 | |
| Torso | 100 | -1 | |
| LeftArm, RightArm | 100 | -1 | |
| LeftHand, RightHand | 100 | -1 | the arm, coefficient 0.1 |
| LeftLeg, RightLeg | 125 | -1 | |
| LeftFoot, RightFoot | 125 | -1 | the leg, coefficient 0.2 |

The right side is identical to the left, as expected, and a fatal-injury coefficient of -1 means the zone is not itself fatal. [obs for the numbers; inf for the meaning of -1] The infected base class has global health 100 and no blood or shock entry. The tables `clothing.csv`, `weapons.csv` and `ammo.csv` were **not** regenerated (their generating queries are not in the project), so any of their blank columns that came from nested classes can still be empty. [?]

### 5.12 The cross-linked item table (task D3) [obs]

`data\items_master.csv` (2,508 items, one row per class name, built by `scripts\items_master.py`) joins the separate tables on the lower-cased class name:
- **Identity:** class, English display name, parent class, kind, clothing slot, weight in grams.
- **Economy:** nominal count on each of the four maps (`nominal_chernarus`, `_livonia`, `_nasdara`, `_sakhal`), plus category, usage tags, tier tags and lifetime from the first map that lists the item, and how many maps list it.
- **Recipes:** `recipes_as_ingredient_direct` (distinct live recipes that name the item's own class in either slot), `recipes_as_ingredient_via_ancestor` (distinct recipes that name an ancestor class and not the item itself; a first version counted ingredient slots, so a recipe naming an item twice counted twice, CODEX.md CXR-004; this is about 10 for nearly every item because generic bases such as `Inventory_Base` appear in tool-repair recipes, so treat it as background) and `recipes_as_result`.
- **Flags** for which of the clothing, weapon and food tables the item also appears in.

**Contents.** 1,095 items are in the vehicles config section (most ordinary items live there, not only vehicles), 899 clothing, 151 food, 136 weapons, 131 building or object names (`Land_*`), 87 magazines and 9 names that are in a loot table but in no parsed config section (`unknown`). 2,449 items have loot on at least one map; 212 are named directly in a live recipe. 251 have no display name (mostly world objects and wrecks).

**Checks.** The row count equals the number of distinct names across the inputs (2,508 unique); 40 random rows were compared with the four loot tables with no mismatch in any map; direct recipe counts match the earlier tool counts (hatchet 54, kitchen knife 51 recipes). Example row: the kitchen knife has nominals 60 / 35 / 50 / 30 on Chernarus, Livonia, Nasdara and Sakhal and is the ingredient in 51 live recipes.

**Limits.** Recipes that name a class family and create a coloured variant (the armbands) are not linked to the individual colours as results. Ammunition classes (`bullet_*`) are not in this table; see `data\ammo.csv` and `data\ammo_physics.csv`.
