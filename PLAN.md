# PLAN v2: where the DayZ project stands and what to do next

Written 2026-10-24 after a review of the whole folder. Build 1.30.164.200, install `F:\SteamLibrary\steamapps\common\DayZ`. The earlier plan (task IDs H, G, S, W, D, Q, which the notes still cite) is kept in [notes/plan-history.md](notes/plan-history.md).

**Rules that do not change.** Static analysis only; nothing is executed and the game files stay read-only. No work on `BEClient_x64.dll` internals and nothing aimed at bypassing or evading anti-cheat (section 4 of the notes is the limit). Tag findings [obs] / [inf] / [?]. Do not copy game content into the project (extracted scripts, raw config dumps, string dumps); regenerate it with `scripts/bootstrap.py` into a folder outside the project. Notes and tools go in the game's subfolder.

## 1. What exists

| Part | Size | What it is |
|---|---|---|
| `notes/` | 8 files, about 300 KB, 69 numbered sections | The write-up. `engine-network.md` (sections 1.1 to 4.8), `player-survival.md`, `weapons-combat.md` and `items-actions-ai.md` (5.2 to 5.4, 6 to 6.26; split from the former 128 KB `survival-combat.md` in H4), `world-vehicles.md` (5.6 to 5.13), `data-config.md` (1 to 8), `open-questions.md`, `plan-history.md`; `notes/README.md` maps each section number to its file. |
| `data/` | 31 CSV tables, 3.4 MB for the whole project | Derived numbers: items (2,508 rows joined with loot on four maps and recipe use), clothing, weapons, ammo, ammo physics, recoil, food and food stages, recipes (234), melee, explosives, actions (342), weapon states (82) and transitions (1,410), vehicles (28), penetration materials (51), AI perception (36 behaviours), noise sources (851), catching items (53), message IDs (155), native API (3,191 methods) and the 730 unmatched declarations, archives (158). |
| `scripts/` | 21 Python tools and the Ghidra batch runner | All read-only on the game. `bootstrap.py` regenerates the extracted game data outside the project. |
| Ghidra project | outside the folder (`...\tools\ghidra_projects\DayZ`) | Persistent analysed `DayZ_x64.exe`; a task file of `decompile`, `xrefs`, `bytes`, `string`, `symbols`, `vtable`, `instrscan` and `funcs` lines runs in seconds to a minute. |

## 2. What is done (by area)

| Area | State | Where |
|---|---|---|
| Install layout, archives, configs, string table, recipes | complete for what was planned | 1, 1.2, 5, 5.1, 5.5, 5.8 |
| Player survival (stats, modifiers, stomach, agents, temperature, stamina, shock, bleeding, injuries, stat levels, cooking, rotting) | complete on the script side | 6.1 to 6.15, 6.20, 6.21 |
| Combat on the script side (melee, grenades, wounds, firearms and recoil, weapon state tables) | complete | 5.3, 6.16 to 6.19, 6.24 |
| Combat on the engine side (shot creation, flight, ricochet, penetration, damage, armour, hit curves, materials) | done for the main path; some constants and the armour threshold are inferred | 4.6 to 4.8 |
| Infected and animals: config, perception, noise, alert, vision | done; alert rise rate and noise radius fields open | 5.4, 6.25, 6.26 |
| Vehicles, boats, motorbikes (start, battery, fluids, crashes), base objects and gardening, fishing and trapping | done | 5.7, 5.7a, 5.7b, 5.9, 5.9a, 5.13 |
| Server data: gameplay config, Central Economy tables on four maps, restricted areas, bunker broadcast | done at table level; how the engine runs the Central Economy is not covered | 5.6, 5.10, 5.11 |
| Network: 155 message IDs, native API, BattlEye hosting (understanding only), statistics service | done to the structure level | 4 to 4.5 |
| Question G2 (do `int` constants holding fractions truncate) | answered: yes, the engine converter truncates | open-questions.md |

## 3. Review findings

**Fixed during this review:** the README still described the old REA workflow (now the Ghidra batch runner); two sections still said "not decoded" for things later decoded (vision, stats service) and now point at their addenda; the first-pass native coverage figure now points at the corrected one; one wrong cross-reference ("6.1x") in 6.22.

**Checked and fine:** every numbered section is in the map, every table and script is named in `README.md`, no unresolved cross-references remain (the check is in section 4, item H2).

**Still open:**
1. **No version control or backup.** The project is plain files; a bad edit or disk problem loses everything. (A `git init` plus a backup copy is cheap; it needs your go-ahead because it adds a hidden folder.)
2. ~~`bootstrap.py` does not rebuild the derived tables.~~ **Done (H1, 2026-10-24).** `build_tables.py` rebuilds all 29 tables; ten of them had no generator at all and now have one (`config_tables.py`). They turned out to predate the nested-class inheritance fix, so the corrected tables replaced them (details in `data/PROVENANCE.md`). Only `message_ids` and `message_map` are still hand-built.
3. ~~`survival-combat.md` is 128 KB~~ Split in H4 (done) into `player-survival.md`, `weapons-combat.md` and `items-actions-ai.md`; section numbers kept.
4. **Inference density.** Roughly 55 [inf] tags against 95 [obs] tags (many sections carry one tag for the whole section); several inferences are testable in-game (list in H3). Static analysis cannot confirm them.
5. **Coverage gaps** (crude measure: script files whose class names are mentioned in the notes: 14% of the 3,056 files and 31% of the 460,000 lines; the true figure is higher because tables such as `actions.csv` cover files whose names are not in the prose, but the picture of where the gaps are is reliable):
   - `5_Mission/GUI` (203 files, 74,000 lines): menus, HUD, inventory screens, server browser, script console. Almost untouched.
   - `4_World/Plugins/PluginBase` (59 files, 24,000 lines): developer and diagnostic plugins; probably not gameplay, but they show admin and debug tools.
   - `4_World/Entities/ItemBase` (678 files, 43,000 lines; 31% by lines): the per-item classes not covered yet include locks (`CodeLock`, `CombinationLock`), `Totem` (territory flag), barrels, traps, fireworks, canned food, tents, generators, radios and lights.
   - `4_World/Systems/Inventory` (`DayZPlayerInventory.c`, 5,000 lines) and `3_Game/Systems` hand and inventory state machines: the inventory engine, described only at overview level in 5.2.
   - `4_World/Entities/Building` (80 files): the underground bunkers, the warhead storage, power stations and similar world buildings.
   - Smaller: area damage (21 files), contaminated and effect areas (14), sound events (21), ambient effects, particles and post-process (PPE) managers (visual), the bot framework (21), console services (Xbox, PlayStation).
6. **Engine areas never opened:** physics (ragdoll, vehicle and body simulation natives), the Central Economy engine (how loot and events are placed and removed), the networking and synchronisation protocol (RPC, sync variables, junctures), the sound system, the animation system, and terrain and weather simulation.

## 4. Next steps

Cost: **S** = scripts and config only, **G** = Ghidra, hours are rough session time.

### Hygiene (do first; small and they protect everything else)
| ID | Task | Cost | Output |
|---|---|---|---|
| H1 | ~~One-command regeneration~~ **Done.** `bootstrap.py` (new `dz` step), `build_tables.py` (`--check`, `--adopt`, `--ghidra`), `config_tables.py`, `csv_diff.py`, `data/PROVENANCE.md`, saved Ghidra task lists in `scripts/ghidra/tasks/`. All 29 tables rebuild identically (27 from the bootstrap folder, the 2 native-API tables through Ghidra). | S, done | |
| H2 | ~~Check script~~ **Done.** `scripts/check_notes.py`: section map, cross-references, README and PROVENANCE coverage, table shape, control characters, game-content and signature guards; warns about stale phrases. Currently 0 errors, 5 warnings. | S, done | |
| H3 | ~~Verification list~~ **Done.** `notes/verification.md`: 21 statements (V1 to V21) with what to observe and the predicted result. | S, done | |
| H4 | Split `survival-combat.md` into player survival, weapons and combat, and infected and animals, keeping section numbers; update the map | S, 1 h | three smaller files |
| H5 | Version control or backup of the project folder (your decision) | S, 15 min | safety |

### Engine (one Ghidra process at a time)
| ID | Task | Why | Cost |
|---|---|---|---|
| E1 | **Central Economy engine side**: how `types.xml` fields (nominal, min, lifetime, restock, cost, quantmin and quantmax, flags) and `events.xml` are used; the loot spawn and cleanup loop; `LootDepleteAndDamage` and related natives | the most useful engine area for server owners; the data side is already tabulated | G, 4 to 6 h |
| E2 | **Physics**: `DayZPhysics` natives, ragdoll, vehicle simulation inputs (the config values in `vehicles.csv` and what the engine does with them) | completes the vehicle and combat pictures | G, 4 to 6 h |
| E3 | **Network synchronisation**: net-sync variable registration and encoding, RPC dispatch, juncture messages; connects the message IDs in 4.2 to script-level sync | needed to know what a mod can safely add | G, 3 to 5 h |
| E4 | Close the open details: alert rise rate and the noise `radius` fields (6.26), the armour threshold test and ricochet constants (4.8), statistics event payloads (4.3), `deflection` for terrain surfaces | removes the remaining [inf] on the AI and ballistics pictures | G, 3 h |
| E5 | The rest of the 730 unmatched native declarations (mostly base-class attribution): rebuild the attribution using the script inheritance chain | finishes the native API table | S, 2 h |
| E6 | A `.p3d` damage-zone reader feasibility spike (read the first bytes of 50 models, decide if the format can be parsed) | links config zones to model geometry | S, 1 h to decide |

### Script gaps (parallel, no Ghidra)
| ID | Task | Cost |
|---|---|---|
| S1 | Base building and locks: `CodeLock`, `CombinationLock`, `Totem` (flag and territory), barrels, tents, fences and watchtowers (`BaseBuilding`), with a table of build parts, materials and times | S, 4 h |
| S2 | Inventory engine: `DayZPlayerInventory`, hand states and guards, drag and drop rules, juncture handling | S, 4 h |
| S3 | World buildings: underground complex, warhead storage, power stations, generators, doors and their scripts (ties to the bunker broadcast, 5.10) | S, 3 h |
| S4 | Area damage, contaminated and effect areas, geysers, oil pits and the Halloween area; sound events | S, 3 h |
| S5 | User interface map: the in-game HUD, inventory screens, menus, server browser; what is configurable by a mod | S, 4 to 6 h (large, optional) |
| S6 | Remaining `ItemBase` families: tools, electronics and the energy component, radios, lights, canned food, fireworks, tents; one table per family | S, 6 h |
| S7 | Admin and developer plugins (`PluginBase`): what a server operator or modder gets from them | S, 2 h |
| S8 | Bot framework summary; console service classes (one-line description each) | S, 1 h |

### Deliverables for people who want to use this (the "what can we build with it" items)
| ID | Task | Cost |
|---|---|---|
| M1 | **Modding cheat sheet**: for each kind of mod (config only, script, loot, vehicle, recipe, AI tuning) the files, sections, safe hooks and limits, with a worked example per kind | S, 3 h |
| M2 | **Server-owner guide**: every `cfggameplay.json` field, `globals.xml` variable and `events.xml` setting with its effect, default and where in the notes it comes from | S, 4 h |
| M3 | `scripts/lookup.py`: search items, actions, recipes, ammo, vehicles and noise sources by name or substring across the CSVs and print the joined record | S, 2 h |
| M4 | Calculators built on the decoded formulas: penetration depth by material and ammo, vehicle crash damage, noise audibility by distance, food rot time, bite chance | S, 4 h; clearly labelled as formula-based estimates |

## 5. Suggested order

1. **This week:** H1, H2, H3 (a regenerable, checkable project and a list of things to test), then H4 and H5 if you agree.
2. **Engine track (one Ghidra session):** E1 (Central Economy), then E4 (close open details), then E2 (physics), then E3 (network sync).
3. **Script track (can run alongside):** S1 (base building and locks), S6, S2, S3, S4; S5 only if the interface matters for your goals.
4. **Deliverables:** M2 and M1 after E1 and S1, M3 and M4 any time after H1.

## 6. Risks and limits

- Static analysis cannot show timing, balance feel, or anything decided at run time; H3 exists to turn the important inferences into observations.
- Some engine paths go through virtual calls and runtime tables that the decompiler cannot resolve; expect [?] items to remain.
- The game updates change addresses and numbers. Every note carries the build number; after an update, re-run `bootstrap.py`, `build_tables.py` (once it exists) and the check script, and diff the tables before trusting the notes.
- The modding section of the notes describes what the shipped scripts and configs allow; mod loading, signing and server rules are outside what was analysed.

## 7. Single best next step

H1 to H5 are done (H4 split the survival notes; H5 put the project in a private GitHub repo, `Zackpaul15/DayZ-Systems`). Next, the engine track starting with E1 (Central Economy).

## Standing step: Codex review tracker
After every task, re-read `CODEX.md` (maintained by Codex), assess new or open findings, fix the valid ones, and record the disposition and the check result in that file. The first review (CXR-001 to CXR-005, 2026-10-24) is fixed and awaiting Codex's validation; see `CODEX.md` and `data/PROVENANCE.md`.
The second Codex pass (CXR-006 comparator, CXR-007 adoption gating) is also fixed; `scripts/selftest.py` holds the regression tests and should be run (`py -I scripts\selftest.py`) after any change to the table tools.
