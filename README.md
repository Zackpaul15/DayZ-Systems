# DayZ reverse-engineering findings

Static analysis of `F:\SteamLibrary\steamapps\common\DayZ` (game build 1.30.164.200). Nothing was executed. Everything here was read from the shipped files, with each claim tagged as observed, inferred or unknown in the notes.

## Files

| Path | What it is |
|---|---|
| [DayZ-analysis-notes.md](DayZ-analysis-notes.md) | Short index of the write-up. |
| [notes/](notes/README.md) | The write-up, split by workstream (engine-network, player-survival, weapons-combat, items-actions-ai, world-vehicles, data-config, open-questions) plus `verification.md`, the list of statements that only a running game can confirm. Section numbers are the original ones; `notes/README.md` maps each number to its file. Start there. |
| [PLAN.md](PLAN.md) | Where the project stands, the review findings, and the next steps in order. The earlier plan is in `notes/plan-history.md`. |
| `scripts/` | My own tools: `rap_reader.py` (reads binary `config.bin`), `pbo_config_dump.py` (finds and parses every config in every archive), `cfgmodel.py` (merges them and follows inheritance), `pbo_unpack.py` (lists or extracts a small archive), `stringtable.py` (reads the language table and adds a `displayName` column to CSVs), `pbo_inventory.py` (header-only archive inventory), `recipes.py` (crafting recipe scripts to a table), `exe_strings.py` (strings of a PE and a diff of two), `find_strings.py` (strings of the main executable with virtual addresses, for Ghidra xrefs), `bootstrap.py` (regenerates all extracted game data outside the project), `native_api.py` (joins engine native registrations with script proto declarations), `native_gaps.py` (explains the unmatched ones), `ce_types.py` (Central Economy tables per map), `items_master.py` (the joined item table), `food_stages.py` (food stage table), `actions.py`, `weapon_states.py`, `vehicles.py`, `catching.py`, `penetration.py`, `ai_perception.py`, `noise_sources.py`, `config_tables.py` (ammo, clothing, weapons, food, melee, recoil and other config tables), `build_tables.py` (rebuilds and checks every table in `data/`) and `csv_diff.py` (exact table comparison), `check_notes.py` (consistency check of the whole folder) and `selftest.py` (24 regression tests on small fixtures) (the tables of the same names) and `ghidra/` (batch runner for the persistent Ghidra project). All read-only on the game files. |
| `data/` | **Where each table comes from, and how to rebuild all of them: `data/PROVENANCE.md`.** Derived tables as CSV (list below): `clothing`, `weapons`, `ammo`, `food`, `recoil` (the first three with English display names), `message_map` (network message IDs), `script_decls` (every script class, its parent and file), `archives` (all 158 archives: size, prefix, file types), `loot_types_chernarus`, `loot_types_enoch`, `loot_types_nasdara`, `loot_types_sakhal` (loot types from each server mission) and `maps_compare` (the four maps side by side), `recipes` (all 234 crafting recipe classes), `message_ids` (all 155 network message IDs) `native_api` (3,191 engine native script methods) and `native_unmatched` (the 730 script declarations without a match, with a reason) and `ammo_physics` (flight, deflection and tracer fields of all 254 ammo classes) `body_zones` (damage zones of the player, infected and animal base classes) `explosives` (25 explosive ammo classes), `melee` (178 items with their own melee modes and damage) and `items_master` (2,508 items with stats, loot on all four maps and recipe usage) `food_stages` (65 foods, 317 stage rows with cooking thresholds, nutrition and transitions), `actions` (342 registered actions), `weapon_states` and `weapon_transitions` (82 stable states, 1,410 transitions) `vehicles` (28 cars, motorbikes and boats) and `catching_items` (53 items with fishing or trapping values) `penetration_materials` (51 bullet penetration materials), `ai_perception` (vision, noise and alert settings of 36 AI behaviours) and `noise_sources` (851 noise definitions). |

## Map of the notes

Section numbers refer to the files in `notes/` (see `notes/README.md` for which file holds which number).

| Section | Topic |
|---|---|
| 1, 1.1, 1.2 | Install layout; the launcher; what the 158 archives contain |
| 2 | Main executable overview (68,913 procedures) |
| 3, 3.1 | String survey (engine, scripts, networking, anti-cheat); the Diag executable compared with retail |
| 4, 4.0, 4.1 | How the client starts BattlEye; the rest of the BattlEye wiring (state object, callbacks, reload); the client network message ID map |
| 5 | Enforce script source: layers, classes, lifecycle |
| 5.1 | Binary configs and the real numbers (clothing, weapons, ammo, health, food) |
| 5.2 | Inventory, items and actions |
| 5.3 | Firearms and recoil |
| 5.4 | Infected and animals |
| 5.5 | Language table and in-game names |
| 5.6 | Server mission data: gameplay config and the Central Economy (loot, events) |
| 5.7 | Vehicles, base building and fireplaces |
| 5.8 | Crafting recipes |
| 5.9 | Placement hologram, tents and gardening |
| 6.1 to 6.15 | Player survival: stats, modifiers, stomach, notifiers, symptoms, sync, agents and diseases, temperature and heat, stamina and shock, bleeding and injuries, item temperature and clothing isolation, heavy metal / contamination / silicosis / sandstorms |
| 7 | Backlog (what is done, what is next) |
| 8 | How to reproduce, and tool usage |

## Not included on purpose

The game's own files (extracted scripts, raw config dumps, string dumps). They are game content, are large, and can be regenerated from the install with the scripts in `scripts/`. See section 8 (in `notes/data-config.md`) and `scripts/bootstrap.py`.

## Regenerating the data

1. Parse every config: `py -I scripts\pbo_config_dump.py OUT_DIR <game>\Addons <game>\dta <game>\nasdara\addons <game>\sakhal\Addons`
2. Point the merge tool at it: set `DAYZ_CFG_JSON` to `OUT_DIR`, then import `cfgmodel` and call `load()`.
3. Unpack the scripts: `py -I scripts\pbo_unpack.py <game>\dta\scripts.pbo DEST_DIR`.

Engine-level analysis (the `DayZ_x64.exe` findings) uses a persistent headless Ghidra project with the batch runner in `scripts/ghidra/` (a query takes seconds to a minute once the project exists); section 8 in `notes/data-config.md` describes how it is run. The earlier REA route (one ten-minute analysis per query) is no longer used.
