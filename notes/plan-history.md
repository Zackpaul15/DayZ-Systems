# Plan history (superseded)

This is the planning document used from the start of the project until 2026-10-24. Its task IDs (H, G, S, W, D, Q) are referenced in the notes; the current plan is `PLAN.md`.

# PLAN: continuing the DayZ project

## Phase 0 status (updated 2026-10-23, paused)

| Task | State |
|---|---|
| H4 stale text | **Done** (altitude and isolation notes, 7.6, section 8, README) |
| H1 notes split | **Done**: `notes/` has 5 workstream files plus `notes/README.md`; checked equal non-blank lines (1,009) and heading count (50); no unresolved "see N.N" references |
| H2 `scripts/bootstrap.py` | **Done and tested**: regenerates scripts (3,056 `.c`), 267 config JSONs, the four `_ce` mission folders and `stringtable.csv` in about 3 s into a folder outside the project; refuses an output folder inside the project; writes `STAMP.json` (build string 1.30.164200.56, Steam build id) |
| H3 persistent Ghidra project | **Import and analysis succeeded** (19:20 to 19:29, 571 s, "Save succeeded for /DayZ_x64.exe") in `...\Code stuff\tools\ghidra_projects\DayZ` (project name `DayZ`, program `/DayZ_x64.exe`). The log showed non-fatal warnings (some decompiler "unable to read bytes" and "out of address spaces" messages during analysis). **Verified.** `scripts/ghidra/BatchDecompile.java` plus `run_batch.ps1` run a task file (`decompile`, `xrefs`, `bytes`, `string` lines) against the project in about **8 seconds** instead of about 10 minutes. `FUN_14092ec40` (275 lines) and `FUN_140932a40` (21 lines) are line-for-line identical to the saved REA output, so addresses and names match. Usage: `powershell -File scripts\ghidra\run_batch.ps1 TASKS.txt OUT.txt` (one Ghidra process at a time) |

**Phase 0 is complete.** Next: Phase 1. The engine session can now run G1 to G3 as task files in seconds; the other three sessions start with `scripts/bootstrap.py`.

Build 1.30.164.200. Static analysis only; game files read-only; nothing executed. No work on `BEClient_x64.dll` internals and nothing aimed at bypassing anti-cheat (section 4 of the notes is the limit). Tag findings [obs] / [inf] / [?]. Don't copy game content into the project; regenerate it.

**Priorities chosen:** modding and server-config reference first, then complete documentation. Ghidra effort is moderate and batched through a persistent project (item 18 only as a pilot). Notes are split first, then work runs in parallel sessions. Extras: Livonia and Sakhal economy data, and a `.p3d` damage-zone reader.

## 0. Findings this plan relies on (checked read-only while planning)
- **Altitude unit (6.10) is answerable now.** `WorldData.c:230` computes `max(0, terrainHeight x m_TemperaturePerHeightReductionModifier)`. The modifier is per map (default 0.02; Chernarus 0.012, Enoch 0.01, Nasdara 0.005). The height is in metres, so the unit is degrees per metre (Chernarus about 1.2 degrees per 100 m); the "per 100 m" comment in the constants is stale. [obs formula, inf unit]
- 6.10 still says "I did not read the function that applies" the isolation factors; 6.14 now documents it. Stale.
- The `rea` CLI has no batch command and every call re-imports (about 10 min); the MCP route times out at about 60 s. `analyzeHeadless` and PyGhidra exist in `tools\ghidra_12.1.4_PUBLIC`, so a persistent Ghidra project with batch scripts looks feasible. [?] untested.
- The scripts hold hints for the int-truncation question: `ItemBase.c:1552` says "implicit cast to int", and the car code replaced int constants with literals.

## Overnight queue (started 2026-10-24, user asleep; all static, run in order)

| # | Task | State |
|---|---|---|
| 1 | G4 ballistics step 2: shot list iterator, per-step flight, impact, damage | **Partly done**: leads ruled out (see 4.7 addendum); flight and damage code still not located |
| 2 | D1 nested-class inheritance in `cfgmodel.py` | **Done** (notes 5.1 addendum): 30,539 classes compared, 0 lost, 0 changed, 25,554 gained; `data/body_zones.csv`; old tables not regenerated |
| 3 | W4 restricted areas and bunker broadcast | **Done** (notes 5.10, `world-vehicles.md`) |
| 4 | W5 Livonia and Sakhal economy data | **Done** (notes 5.11; `scripts/ce_types.py`, `data/loot_types_{enoch,nasdara,sakhal}.csv`, `data/maps_compare.csv`) |
| 5 | D3 cross-linked item master table | **Done** (notes 5.12; `scripts/items_master.py`, `data/items_master.csv`, 2,508 items) |

## Phase 1 progress: engine (G1)

| Part | State |
|---|---|
| G1a message IDs | **Done**: all 155 IDs named from the message factory `FUN_140994790` (`data/message_ids.csv`, notes 4.2); all 18 create and 29 update IDs cross-checked |
| G1b `DAT_144a8d1d0` | **Partly**: it is in zero-filled `.data`, so it is filled at run time; writer not found |
| G1c statistics service | **Second pass done** (notes 4.3): created by default on a normal client (flag statically 1, not proven never cleared); the JSON is a per-user local settings file with revision 164200; file path, default values, active sender and `TD` endpoint still open |
| G1d game-info and disconnect strings, G1e slots `0x12`/`0x14` | **Done** (notes 4.5): game-info string `DayZ 1.30.164200.56`; disconnect text `STR_BATTLEYE_INIT_FAILED` ("BattlEye initialization failed"); slots `0x12`/`0x14` only zeroed, never called in the networking range |
| G3 item 18 pilot | **Done** (notes 4.4): registration mechanism found (two registrars, 197 per-class functions); `data/native_api.csv` with 3,191 rows; 77% of script `proto` declarations matched; class attribution is by name overlap; 3 spot checks passed. Tool: `scripts/native_api.py` |
| G4 ballistics slice | **First pass** (notes 4.6): `...Bullet` natives are Bullet-physics queries, not projectiles; engine ammo loader `FUN_140a35e70` field list; `data/ammo_physics.csv` (254 classes). Second pass (notes 4.7): shot factory, spawn function with spread and velocity, RNG found. Per-step flight, impact handling and damage code still not located |
| Tooling | `scripts/ghidra/BatchDecompile.java` now also supports `symbols <substring>` and `vtable <addr> <count>` |

## 1. Status audit

### 1.1 "Done" items with open follow-ups

| Item | Marked Done | Still open (deduplicated) | Task |
|---|---|---|---|
| 0 | "Applied but not effective" | MCP timeout never lifted; CLI re-import costs about 10 min per query | H3 |
| 2 | Bleeding, injuries | ragdoll; sewing wounds | S3 |
| 3 | Item temperature | cooking temperature path; fireplace to item temperatures | S5 |
| 4 | Contamination, sandstorm | engine-side storm shape; particle and post-process effects | G5 (defer) |
| 5 | Inventory, actions | item-specific actions; container UI; action catalog | S8 |
| 6 | Crafting | what each custom `Do` changes; soft-skills system | S10, S4 |
| 7 | Firearms | per-mechanism transition tables; weapon-manager juncture handling; melee; grenades and flares; engine ballistics | S7, S1, S2, G4 |
| 8 | Infected, animals | engine use of perception numbers; infected sounds; ambient animals; `3_Game\AI` helpers; bot framework | S9, G4 |
| 9 | Vehicles, base building | door and wheel state machines; boats (`HelicopterScript` is a 35-line stub); tent and garden action classes; tent navmesh; animals and traps | W1, W2, W3 |
| 10 | Server config | restricted areas; bunker broadcast | W4 |
| 11 | Config reader | vehicles, buildings, sound sections unanalysed; nested-class inheritance; food `Stages`; expressions and the `enum` table | D1, D2, S5 |
| 14 | Message map | 47 create/update IDs unnamed; what `DAT_144a8d1d0` holds | G1 |
| 15 | Launcher | method bodies not decompiled; `SteamLayerWrap.dll`, `steam_api.dll` not analysed | G6 (defer) |
| 16 | BattlEye wiring | game-info string content; disconnect string; callers of table slots `0x12`/`0x14` (DLL internals are out of scope) | G1 |
| 17 | Diag vs retail | is the statistics service enabled and what it sends; the `TD` endpoint | G1 |

### 1.2 Stale or inconsistent text found
- 6.10 isolation sentence ("did not read the function"): resolved by 6.14. 6.10 altitude note: resolved (section 0). Both go in H4.
- 7.6 "Suggested order" and section 8 timeout advice are out of date; the README map lacks 4.0.
- Unverified side claims to settle cheaply: `varWetMax` "did not check every item" (5.1), head-wash action not traced (6.10), shock pulse "looks backwards" (6.11), proto-declaration count (notes say 3,770; a quick grep for `proto native` gives 2,889 lines, a different metric; reconcile before G4).

### 1.3 Remaining work by workstream
Engine/network G1 to G6; survival and combat S1 to S10; world and vehicles W1 to W6; data D1 to D7; open questions Q1 to Q3; housekeeping H1 to H4. Tables below.

## 2. Tasks

Cost: **S** = scripts/config only; **G** = Ghidra. Times are my estimates of effort in session time.

### 2.0 Housekeeping and enablers (do first)

| ID | Goal | Method | Cost | Output | Verify |
|---|---|---|---|---|---|
| H1 | Split the notes | Cut `DayZ-analysis-notes.md` by section into `notes/engine-network.md` (1.1, 2, 3, 3.1, 4, 4.0, 4.1), `notes/survival-combat.md` (5.2, 5.3, 5.4, 6.1 to 6.15), `notes/world-vehicles.md` (5.6, 5.7, 5.9), `notes/data-config.md` (1, 1.2, 5, 5.1, 5.5, 5.8, 8), `notes/open-questions.md` (7, 7.7 and this plan's status). **Keep section numbers** so "see 6.10" still resolves; `notes/README.md` maps number to file. Keep `DayZ-analysis-notes.md` as a short index pointing to `notes/`. | S, 1 h | `notes/*.md`, index | heading count equal before and after; total non-blank lines equal; script checks every "see N.N" resolves |
| H2 | One-command regeneration | New `scripts/bootstrap.py OUT_DIR`: unpack `scripts.pbo`, run `pbo_config_dump`, extract the four `_ce` mission folders, extract `stringtable.csv`, write a `STAMP` with build and date. Output goes outside the project (session scratchpad). | S, 1 to 2 h | `scripts/bootstrap.py` | run it in a fresh dir; file counts match the notes (3,056 `.c` files, 268 config JSONs, 61 events) |
| H3 | Persistent Ghidra project and batch runner | Run `analyzeHeadless` once (import `DayZ_x64.exe`, full analysis, about 10 to 15 min, background) into a project folder under `...\Code stuff\tools\ghidra_projects\DayZ`. Then batch runs use `-process DayZ_x64.exe -noanalysis -postScript` with a script that takes a task file (decompile list, xref list, byte reads, string xrefs) and writes JSON/text. Write `scripts/ghidra/batch_decompile.*`. Check disk space first. [?] untested; fallback is one `rea decompile` CLI call per question (about 10 min each). | G, setup 15 min + 1 to 2 h scripting | project folder, `scripts/ghidra/*` | decompile `FUN_14092ec40` and diff against the saved REA output (`dec_cbA`); function addresses must match |
| H4 | Fix stale text | Apply 1.2 items; resolve altitude and isolation notes; refresh 7.6 and section 8; add 4.0 to README map | S, 30 min | edited notes | grep for removed phrases |

### 2.1 Engine and network (G, serialized; one Ghidra process at a time)

| ID | Goal | Inputs | Method | Cost | Deps | Output | Verify |
|---|---|---|---|---|---|---|---|
| G1 | **Batch 1 (one run):** (a) name the 47 create/update message IDs; (b) read `DAT_144a8d1d0`; (c) retail statistics service; (d) game-info string, disconnect string; (e) callers of BattlEye table slots `0x12`/`0x14` | saved `FUN_140929c50` decompile; `.rea-snapshot`; string list | (a) for each of the 18 create IDs decompile the callback and read its `::vftable` RTTI name; for the 29 update IDs find how ID maps to type via the table in (b). (b) `read-bytes` of 155 entries plus xrefs of writers and readers. (c) xrefs to "statsDisabled", the `...iegcom.com/dayz/prod/report` URL, "Initializing stats manager"; decompile the service init, sender and config loading; find the source of the `TD` endpoint and any command-line switch. (d) read the strings at `DAT_141153720`, `DAT_141833330`; decompile the singleton vtable targets. (e) instruction search for table offsets `+0x90`/`+0xA0`. | G, one 10 to 15 min run (H3) or about 8 REA CLI calls; analysis 2 h | H3 | updated `data/message_map.csv` (all 154 named), notes in `engine-network.md` | every handled ID has a type; create and update counts reconcile with the roughly 40 RTTI `NetworkMessage*` names from section 3; stats claims confirmed by two independent paths (URL xref and sender decompile) |
| G2 | **Batch 2:** settle int-constant truncation from the compiler and VM | strings `enf_scriptcompiler.cpp`, "Cannot convert to int" (`0x1412df960`) | find constant-initialiser and implicit-conversion code; look for float-to-int conversion instructions (`cvttss2si` means truncation, `cvtss2si` means rounding) on the path used for `const int X = 0.35`; trace one const initialiser end to end | G, 1 run + 2 h | H3 | answer in `open-questions.md`; list of affected constants | evidence = the specific instruction and the call path; cross-check with script comments (`ItemBase.c:1552`) and the car-code literals; mark [obs] only if the const path is traced, otherwise [inf] |
| G3 | **Batch 3, item 18 pilot:** find the `proto native` registration mechanism | three sample natives (for example `GetHealth01`, `RegisterNetSyncVariableInt`, one `DayZPhysics` call) | string xrefs to the sample names, find the registration function and table layout, dump the (name, address) table | G, 1 run + 3 h | H3 | `data/native_api.csv` (class, method, address), notes | table row count compared with the `proto` count in `script_decls.csv`; spot-check 10 entries by decompiling |
| G4 | Item 18 slices: name engine functions per subsystem (ballistics first, then AI perception and noise, then physics) | `native_api.csv` | decompile and annotate top functions per slice | G, 1 run per slice | G3, decision after pilot | `notes/engine-network.md` sections | each slice names at least the functions called by the matching script classes |
| G5 | Engine-side sandstorm shape and effects | | defer | G | G3 | | |
| G6 | Launcher method bodies; Steam wrapper DLLs | | defer; needs a managed decompiler | G | | | |

### 2.2 Survival and combat scripts (S, parallel)

| ID | Goal | Inputs | Method | Cost | Deps | Output | Verify |
|---|---|---|---|---|---|---|---|
| S1 | Melee | `DayZPlayerImplementMeleeCombat.c` (891 lines), melee ammo configs (171 damage classes) | read the state flow, hit detection, block, finisher; join to damage tables | S, 3 h | H2 | `survival-combat.md` 5.3a, `data/melee.csv` | table totals match the 5.2 counts |
| S2 | Grenades and flares | `Grenade_Base.c` (305), `Grenade_ChemGas.c`, flare classes, explosion ammo configs | timers, damage, contamination link | S, 2 h | H2 | section + `data/explosives.csv` | |
| S3 | Ragdoll and sewing wounds | refs in `DayZPlayerImplement`, `PlayerBase`, `ActionSewSelf/Target` (60 and 69 lines), bleeding code | trace both flows | S, 2 h | H2 | section | |
| S4 | Soft-skills system | `SoftSkillsManager.c` (636), `m_Specialty` in `data/recipes.csv`, `ActionBurnSewSelf` | document levels, weights, effects | S, 2 h | H2 | section | recipe specialties all appear |
| S5 | Cooking temperature path, food stages, fireplace to item temperatures | `Cooking.c` (561), `FoodStage.c`, `CAContinuousTimeCooking`, `FireplaceBase` item-heat part, config `Stages` | read and tabulate stage thresholds and times | S, 3 to 4 h | D1 helps | section + `data/food_stages.csv` | covers the 151 food items |
| S6 | Stamina `StatLevel` formulas | `PlayerBase`, stamina handler | read | S, 1 h | | 6.11 addendum | |
| S7 | Weapon FSM transition tables and manager juncture | weapon state classes | generate per-mechanism tables | S, 3 to 4 h | | section + CSV | state counts match 5.3 |
| S8 | Action catalog and item-specific actions, container UI | `ActionConstructor.c` registration list, all action classes | CSV of action, base type, target, conditions | S, 3 h | H2 | `data/actions.csv`, section | row count equals registered actions |
| S9 | Infected and animal leftovers | `3_Game\AI`, ambient animals, infected sound configs, bot framework summary | read and tabulate | S, 2 h | D1 (soldier values) | section | |
| S10 | What each recipe `Do` changes | recipe `.c` files | extend `recipes.py` to list calls and side effects per `Do` | S, 2 h | | `data/recipes.csv` new column | 32 no-result recipes each get a description |

### 2.3 World and vehicles (S, parallel)

| ID | Goal | Inputs | Method | Cost | Deps | Output | Verify |
|---|---|---|---|---|---|---|---|
| W1 | Vehicle doors, seats and wheels | `CarScript`, `ActionCarDoors*`, `VehicleAnimInstances`, config animation sources and hit points | state machine tables | S, 3 h | D2 helps | section | doors and wheels per car class counted |
| W2 | Boats, motorbikes, helicopter stub | `BoatScript.c` (908), motorbike, `HelicopterScript.c` | read | S, 2 h | | section | |
| W3 | Tent, dig, plant, fertilize, water actions | `ActionDigGardenPlot`, `ActionPlantSeed`, `ActionFertilizeSlot`, `ActionWaterPlant`, tent pitch and pack | action conditions and effects | S, 2 h | S8 | 5.9 addendum | |
| W4 | **Restricted areas and bunker broadcast** | `CfgPlayerRestrictedAreaHandler.c` (265), `CfgBunkerBroadcastHandler.c` (87), `BunkerBroadcastHandler.c` (684), `BunkerBroadcastComponent.c` (281), `MorseCodeConverter`, client message IDs 13 to 19, `cfggameplay.json` fields | read config schema, runtime behaviour, how a server owner sets them | S, 3 h | | section + example config table | every JSON field documented |
| W5 | **Livonia and Sakhal economy data** (Nasdara falls out for free) | `worlds_enoch_ce.pbo`, `worlds_sakhal_ce.pbo` (same layout as 5.6) | rerun the 5.6 pipeline per map; compare | S, 2 to 3 h | H2 | `data/loot_types_enoch.csv`, `data/loot_types_sakhal.csv`, `data/maps_compare.csv`, section | type counts and nominal sums reported per map; spot-check 5 items |
| W6 | Tent navmesh, animals and traps | | low priority | S | | | |

### 2.4 Data

| ID | Goal | Inputs | Method | Cost | Deps | Output | Verify |
|---|---|---|---|---|---|---|---|
| D1 | **Nested-class inheritance in `cfgmodel.py`** | `scripts/cfgmodel.py`, parsed JSON | resolve inner `__parent__` chains per class body | S, 2 to 4 h | H2 | fixed tool, regenerated tables | right-side body zones appear; soldier-infected AI values fill in; all other tables unchanged except new values |
| D2 | Unanalysed config sections | vehicles, buildings, sound in the merged config | extract per-class tables | S, 4 h | D1 | `data/vehicles.csv`, `data/buildings.csv`, sound summary | row counts vs class counts |
| D3 | **Cross-linked master table** | all CSVs | join on class name: item, display name, slot, weight, loot nominal and usage, recipes as ingredient or result | S, 2 h | D1 optional | `data/items_master.csv` | row count equals the union of keys; 20 random rows hand-checked |
| D4 | `.p3d` damage-zone reader (feasibility spike first) | model files in structures, characters, weapons archives | read the first bytes of 50 files to identify the format version; if documented and stable, parse zone names | S, 1 h spike, 4 to 8 h build | | `scripts/p3d_zones.py`, `data/model_zones.csv` | zone names match the config zone tables (5.1, 6.12) for 10 models |
| D5 | Food stages on the script side | see S5 | merged into S5 | | | | |
| D6 | Config expressions and `enum` table | | low priority | | | | |
| D7 | Side claims | `varWetMax` all items; proto count reconcile | query CSVs | S, 30 min | H2 | notes edits | |

### 2.5 Open questions

| ID | Question | Status | How to settle |
|---|---|---|---|
| Q1 | Do `int` constants holding fractions truncate? | answered: the engine converter truncates float to int (`CVTTSS2SI`); the compiler path to it is inferred | G2: instruction-level evidence on the const path; script-side hints already in notes |
| Q2 | Altitude unit | **resolved in this plan** | formula and per-map modifier (section 0); write into 6.10 under H4 |
| Q3 | Is the statistics service enabled and what does it send? | open | G1(c) |

## 3. Sequencing

**Phase 0 (one session, about half a day):** H4, H1, H2 in that order; start H3's import in the background first (it needs no attention) so it overlaps.

**Phase 1 (parallel sessions; each writes only its own `notes/` file and new files in `data/`; one owner per shared tool):**

| Session | Tasks in order | Owns |
|---|---|---|
| A: data-config | D1, D3, D2, D7, D4 spike | `data-config.md`; the only session that edits `cfgmodel.py` and `rap_reader.py` |
| B: world-servers | W4, W5, S8 (action catalog, needed by W3), W3, W1, W2 | `world-vehicles.md` |
| C: survival-combat | S6, S3, S4, S5, S2, S1, S10, S7, S9 | `survival-combat.md` |
| D: engine (the only Ghidra session) | G1, G2, G3, then G4 slices | `engine-network.md`; all `scripts/ghidra/*` |

**Ghidra rules:** one Ghidra process at a time, across all sessions (only session D uses it). Batch by question, not by function: with the persistent project (H3) G1 to G3 are each one script run answering their whole question list. If H3 fails, fall back to the REA CLI and spend the 10-minute runs on, in order: message-ID callbacks, stats-service init, compiler constant path, native-registration pilot.

**Phase 2 (end):** the coordinating session merges: refresh `notes/open-questions.md` (backlog table), the README index, and decide after G3 whether to commit to full item 18 slicing.

## 4. Quick wins (best value per effort)

1. **H4** (30 min): closes the altitude question and fixes stale text.
2. **W4** restricted areas and bunker broadcast (3 h): directly useful to server owners; the scripts exist and are small.
3. **D1** nested inheritance (2 to 4 h): fixes silent holes in tables already published.
4. **D3** master table (2 h): one cross-linked reference for modding and loot work.
5. **W5** Livonia and Sakhal economy (2 to 3 h): reuses the existing pipeline for two more maps.

## 5. Deferred or not planned
Inside `BEClient_x64.dll`; sandstorm particles (G5); launcher bodies and Steam wrapper DLLs (G6) unless a managed decompiler is available; full item 18 beyond the G3 pilot until the pilot shows the table format; config expressions and enum (D6); UI layouts and non-English language columns (not selected).

## 6. Risks
- H3 may not reproduce REA's function addresses exactly; the verification step catches it. Disk use of the project is unknown; check free space before the import.
- Parallel sessions can collide on shared tools; the "owner" rule above prevents it.
- `p3d` format may be undocumented or version-dependent; the spike decides.

## 7. Single best next step
Phase 0: kick off the H3 import in the background, then do H4, H1 and H2. It unblocks every parallel session and costs the least.

## Progress: survival and combat follow-ups
| Task | State | Where |
|---|---|---|
| S1 melee | done | notes 6.16, `data/melee.csv` |
| S2 grenades and flares | done | notes 6.17, `data/explosives.csv` |
| S3 sewing wounds, ragdoll | done | notes 6.18 |
| S4 soft skills | done (system dormant) | notes 6.19 |
| S5 cooking, food stages, rotting | done (script side) | notes 6.20, `data/food_stages.csv`, `scripts/food_stages.py`; `cfgmodel.py` now resolves nested parents that are root-level classes |
| S6 stat-level formulas | done (it is the `GetStatLevel*` mapping, not stamina) | notes 6.21 |
| S10 recipe `Do` effects | done (tags; some helper bodies not read) | notes 6.22, `data/recipes.csv` columns `custom_do`, `do_effects` |

## Progress: engine follow-ups
| Task | State | Where |
|---|---|---|
| Projectile flight, ricochet, penetration, damage (G4 slice 1b) | done for the code paths; field meanings partly open | notes 4.8 |
| Native declarations without a match (821) | done: parser fixed, 730 left and explained | notes 4.4 addendum, `data/native_unmatched.csv` |
| Int-constant truncation (G2) | answered (converter `FUN_14026e380` truncates; 12 affected constants listed) | notes/open-questions.md |
| Stats service details | not started | |
| Script-side items S7-S9, W1-W3, D2 | not started | |

## Progress: script-side items
| Task | State | Where |
|---|---|---|
| S8 action catalog | done | notes 6.23, `data/actions.csv`, `scripts/actions.py` |
| W3 garden and tent actions | done (tent navmesh and stash digging not read) | notes 5.9a |
| S7 weapon state tables | done | notes 6.24, `data/weapon_states.csv`, `data/weapon_transitions.csv`, `scripts/weapon_states.py` |
| D2 vehicles | vehicles done; buildings and sound not done | notes 5.7a, `data/vehicles.csv`, `scripts/vehicles.py` |
| W1 vehicles (start, battery, crashes) | done | notes 5.7b |
| W2 boats and motorbikes | done (helicopter is a stub) | notes 5.7b |
| S9 animals and AI helpers | done | notes 6.25 |
| W6 animals and traps | fishing and trapping done | notes 5.13, data/catching_items.csv |
| DamageApplied fields, damage curve, armour (4.8 addendum 2) | done | notes 4.8 |
| Penetration materials (4.8 addendum 3) | done | notes 4.8, `data/penetration_materials.csv`, `scripts/penetration.py` |
| AI perception (noise, alert, vision config) | hearing formula and config done; vision evaluation and alert rate partly open | notes 6.26, data/ai_perception.csv, data/noise_sources.csv |
| Stats service details (3 services, what is sent, TD disabled) | done at structure level; event payload fields not decoded | notes 4.3 addendum |
| Vision evaluation | done (formula in 6.26 addendum) | notes 6.26 |
