# PLAN v3: where the DayZ project stands and what to do next

Written 2026-10-30 after a review of the whole folder. Build 1.30.164.200 (checked against the installed `DayZ_x64.exe` on 2026-10-30), install `F:\SteamLibrary\steamapps\common\DayZ`. v3 replaces PLAN v2 (2026-10-24) and keeps its task IDs (E, S, M), which the notes cite; v2 is in the git history (commit 541daaf). The first plan (task IDs H, G, S, W, D, Q, also cited in the notes) is in [notes/plan-history.md](notes/plan-history.md). Note that the old S and the v2/v3 S IDs are different series: the notes say which plan they mean.

**Goals (unchanged from the first plan):** a modding and server-configuration reference, and complete documentation of the game's systems.

**Rules that do not change.** Static analysis only; nothing is executed and the game files stay read-only. No work on `BEClient_x64.dll` internals and nothing aimed at bypassing or evading anti-cheat (section 4 of the notes is the limit). Tag findings [obs] / [inf] / [?]. Do not copy game content into the project (extracted scripts, raw config dumps, string dumps, decompiled text); regenerate it with `scripts/bootstrap.py` into a folder outside the project. Notes and tools go in the game's subfolder. One Ghidra process at a time.

## 1. What exists

| Part | Size | What it is |
|---|---|---|
| `notes/` | 10 files, about 364 KB, 71 numbered sections | The write-up. `engine-network.md` (1.1 to 4.9.1), `player-survival.md`, `weapons-combat.md`, `items-actions-ai.md`, `world-vehicles.md` (5.6 to 5.14), `data-config.md`, `open-questions.md`, `verification.md` (V1 to V21, things only a running game can confirm), `plan-history.md`; `notes/README.md` maps each section number to its file. |
| `data/` | 31 CSV tables | Derived numbers (items, loot on four maps, weapons, ammo, recipes, actions, weapon states, vehicles, AI perception, noise, message IDs, native API and more). All but `message_ids` and `message_map` rebuild with `scripts/build_tables.py`; sources in `data/PROVENANCE.md`. |
| `scripts/` | 27 Python tools and the Ghidra batch runner | All read-only on the game. `bootstrap.py` regenerates the extracted game data outside the project; `check_notes.py` and `selftest.py` guard the notes and the table tools. |
| Ghidra project | outside the folder (`...\Code stuff\tools\ghidra_projects\DayZ`) | Persistent analysed `DayZ_x64.exe`; `scripts\ghidra\run_batch.ps1 TASKS.txt OUT.txt` answers a whole task file in seconds. |
| `CODEX.md` | review tracker | Codex reviews CXR-001 to CXR-009, all fixed and verified; no open findings. |

Health on 2026-10-30: `check_notes.py` 0 errors, 6 warnings; `selftest.py` 24 tests OK; working tree matches `origin/main` (private repo `Zackpaul15/DayZ-Systems`).

## 2. What is done (by area)

| Area | State | Where |
|---|---|---|
| Install layout, archives, configs, string table, recipes | complete for what was planned | 1, 1.2, 5, 5.1, 5.5, 5.8 |
| Player survival (stats, modifiers, stomach, agents, temperature, stamina, shock, bleeding, injuries, cooking, rotting) | complete on the script side | 6.1 to 6.15, 6.20, 6.21 |
| Combat on the script side (melee, grenades, wounds, firearms, recoil, weapon state tables) | complete | 5.3, 6.16 to 6.19, 6.24 |
| Combat on the engine side (shot creation, flight, ricochet, penetration, damage, armour, hit curves, materials) | done (E4) | 4.6 to 4.8 |
| Infected and animals (config, perception, noise, alert, vision) | done; only the consumer of the noise `radius` fields is [?] | 5.4, 6.25, 6.26 |
| Vehicles, boats, motorbikes, base objects, gardening, fishing, trapping | done on the script side; engine physics not opened | 5.7, 5.7a, 5.7b, 5.9, 5.9a, 5.13 |
| Server data and the Central Economy | tables on four maps done; engine side mostly done (E1) | 5.6, 5.10, 5.11, 5.14 |
| Network: message IDs, native API, BattlEye hosting (understanding only), statistics service | done to the structure level | 4 to 4.5 |
| Network synchronisation | mostly done (E3): registration, range storage, script RPC and juncture paths, the bit-stream serialiser | 4.9, 4.9.1 |
| Project hygiene (regeneration, checker, verification list, notes split, git) | done (v2 H1 to H5) | `scripts/`, `notes/verification.md` |

## 3. Review findings (2026-10-30)

1. **Stale planning text.** PLAN v2 still listed H4 and H5 as open and its "suggested order" still started with H1 to H3; `notes/open-questions.md` 7.1 and 7.6 still describe the REA command-line workaround (about 10 minutes per query) that the persistent Ghidra project replaced. Fixed for the plan by this rewrite; the notes part is task C2.
2. **The untracked `Dayz Plan.md`** was the plan-mode draft of the first plan. Its body was already in `notes/plan-history.md`; its preamble was appended there and the file removed.
3. **Checker warnings (6).** Section 5.1 is detected twice because the D1 addendum uses a `### 5.1 addendum` heading; three "not decoded" and two "not yet traced" phrases need re-checking against later addenda (some are true, some may be stale). Task C3.
4. **Session start cost.** The extracted game data lives outside the project, so every new session must run `bootstrap.py` first (about 3 s). Not a defect; listed so it is not forgotten.
5. **Balance of work.** The research is well ahead of the deliverables: none of M1 to M4 has started, although the goals are a modding and server reference. v3 moves the deliverables forward.
6. **Remaining gaps** (from the v2 coverage review, still valid): `5_Mission/GUI` (menus and HUD), `PluginBase` (admin and debug plugins), many `ItemBase` families (locks, territory flag, barrels, tents, generators, radios, lights), the inventory engine (`DayZPlayerInventory`, hand state machines), world buildings (bunkers, warhead storage), area damage and effect areas; on the engine side physics, sound, animation, terrain and weather.

## 4. Tasks

Cost: **S** = scripts and config only, **G** = Ghidra; hours are rough session time.

### Phase 0: cleanup (one short session, do first)
| ID | Task | Cost | Output |
|---|---|---|---|
| C1 | ~~Rewrite the plan as v3; archive the old untracked plan~~ **Done 2026-10-30.** | S | this file, `notes/plan-history.md` appendix |
| C2 | ~~Refresh `open-questions.md` 7.1 and 7.6~~ **Done 2026-10-30.** 7.1 item 0 now records the persistent Ghidra project as the route that worked; 7.6 points at this plan and the current way of running sessions; the cost key no longer says 8 to 10 minutes per query. | S | edited notes |
| C3 | ~~Clear the checker warnings~~ **Done 2026-10-30: 0 warnings.** The 5.1 addendum heading became a bold addendum line. Of the five flagged phrases, two were stale and now point at their answers (stats payload keys in 4.8 addendum 5; the sweeper passes in 5.14). The other three are still open and now say exactly what is [?]: the stats file name and defaults (4.3), the vision visibility-modifier factor (6.26), and the area-flag layout and its placement test (5.11/5.14). | S | 0 warnings |
| C4 | Optional CODEX follow-ups still listed as not done: archive hashes as an input baseline for `build_tables.py`; per-generator tests on small shipped examples; rollback (or narrower wording) for `adopt()` on a mid-copy failure | S, 2 h | tool changes plus `selftest.py` cases |

### Track A: engine (Ghidra; one process at a time)
| ID | Task | Why | Cost |
|---|---|---|---|
| E1 | **Mostly done** (notes 5.14). Open: the per-object lifetime rule behind vtable slots 0x30/0xA0 and the forwarder at `0x1402cdaf0` | completes the Central Economy picture for server owners | G, 1 to 2 h |
| E2 | **Physics**: `DayZPhysics` natives, ragdoll, vehicle simulation inputs (what the engine does with the values in `vehicles.csv`) | completes the vehicle and combat pictures | G, 4 to 6 h |
| E3 | **Done 2026-10-30** (notes 4.9 first, second and third pass). The third pass traced the RPC send path (serialisation, target check, server broadcast and client "too early" guard) and the dirty flag (`SetSynchDirty` sets entity flag `0x10`, queues kind 2 on the server only, one update per flush through `GetNMType`; nothing on a client). Still [?]: bit 63 of the network id, the update rate, the deferred object lookup callback, `DAT_144a8d1d0`. Runtime checks V22, V23 | ready for M1 | |
| E4 | **Done** (notes 4.8 addenda 4 and 5, 6.26). Only the consumer of the noise `radius` fields stays [?] | | |
| E5 | The 730 unmatched native declarations: rebuild the class attribution using the script inheritance chain | finishes `data/native_api.csv` | S, 2 h (no Ghidra needed; can run beside Track A) |
| E6 | `.p3d` damage-zone reader feasibility spike: read the first bytes of 50 models, decide if the format can be parsed | links config damage zones to model geometry | S, 1 h to decide |

### Track B: script gaps (no Ghidra; can run beside Track A)
| ID | Task | Cost | Priority |
|---|---|---|---|
| S1 | Base building and locks: `CodeLock`, `CombinationLock`, `Totem` (flag and territory), barrels, tents, fences and watchtowers (`BaseBuilding`), with a table of build parts, materials and times | S, 4 h | high (feeds M2) |
| S6 | Remaining `ItemBase` families: tools, electronics and the energy component, radios, lights, canned food, fireworks; one table per family | S, 6 h | medium |
| S2 | Inventory engine: `DayZPlayerInventory`, hand states and guards, drag and drop rules, juncture handling | S, 4 h | medium (feeds M1) |
| S3 | World buildings: underground complex, warhead storage, power stations, generators, doors (ties to the bunker broadcast, 5.10) | S, 3 h | medium |
| S4 | Area damage, contaminated and effect areas, geysers, oil pits, the Halloween area; sound events | S, 3 h | medium |
| S7 | Admin and developer plugins (`PluginBase`): what a server operator or modder gets from them | S, 2 h | low |
| S8 | Bot framework summary; console service classes (one line each) | S, 1 h | low |
| S5 | User interface map: HUD, inventory screens, menus, server browser; what a mod can configure | S, 4 to 6 h | optional |

### Track C: deliverables (what the goals ask for)
| ID | Task | Depends on | Cost |
|---|---|---|---|
| M3 | `scripts/lookup.py`: search items, actions, recipes, ammo, vehicles and noise sources by name or substring across the CSVs and print the joined record | nothing | S, 2 h |
| M2 | **Server-owner guide**: every `cfggameplay.json` field, `globals.xml` variable, `types.xml` and `events.xml` setting with its effect, default and the notes section it comes from | E1 remainder helps; S1 for base building | S, 4 h |
| M1 | **Modding cheat sheet**: for each kind of mod (config only, script, loot, vehicle, recipe, AI tuning) the files, sections, safe hooks and limits, with a worked example per kind | E3 remainder, S2 helps | S, 3 h |
| M4 | Calculators on the decoded formulas: penetration by material and ammo, vehicle crash damage, noise audibility by distance, food rot time, bite chance; clearly labelled as formula-based estimates | M3 | S, 4 h |

## 5. Suggested order

1. **Phase 0:** C1 to C3 done 2026-10-30; C4 whenever the table tools are next touched.
2. **Then two sessions in parallel** (they write different files): Track A runs the E3 remainder; Track B runs S1. E5 can fill gaps in either, because it needs no Ghidra.
3. **Deliverables next:** M3 (cheap, helps everything after it), then M2 (after S1), then M1 (after the E3 remainder).
4. **Afterwards:** E1 remainder, E2; S2, S6, S3, S4; M4; E6 spike. S5, S7, S8 only if they serve the goals.

**Parallel-session rule:** each session writes only its own notes file and new files in `data/`; one owner per shared tool (`cfgmodel.py`, `rap_reader.py`, `build_tables.py`, `scripts/ghidra/*`). Only one session uses Ghidra at a time.

## 6. How each task runs

1. **Start:** run `py -I scripts\bootstrap.py OUT_DIR` into a folder outside the project (the extracted data does not survive between sessions); for Ghidra work, check that no other Ghidra process is running.
2. **Work:** Ghidra questions are batched in one task file per question (`dayz-ghidra-batch` skill); findings go in as addenda to the existing section, or a new numbered section mapped in `notes/README.md` (`re-notes-writer` skill). Anything only a running game can confirm goes in `notes/verification.md`.
3. **Close:** `re-task-closeout` skill: `check_notes.py` (0 errors), `selftest.py` after any table-tool change, re-read `CODEX.md` and handle new findings, update the task row and section 8 of this file, then commit and push.

## 7. Risks and limits

- Static analysis cannot show timing, balance feel, or anything decided at run time; `notes/verification.md` lists the inferences worth testing in game.
- Some engine paths go through virtual calls and runtime tables that the decompiler cannot resolve; expect [?] items to remain (for example `DAT_144a8d1d0`, filled at run time).
- Game updates change addresses and numbers. Every note carries the build number. After an update: re-run `bootstrap.py`, re-import the Ghidra project, run `build_tables.py --check` and the checker, and diff the tables before trusting the notes.
- The modding material describes what the shipped scripts and configs allow; mod loading, signing and server rules are outside what was analysed.

## 8. Single best next step

Phase 0 done except the optional C4 (C1 to C3, 2026-10-30; checker at 0 errors, 0 warnings). E3 done (2026-10-30, notes 4.9 third pass). Next: S1 (Track B), then M3; on Track A, the E1 remainder or E2.

## Standing step: Codex review tracker
After every task, re-read `CODEX.md` (maintained by Codex), assess new or open findings, fix the valid ones, and record the disposition and the check result in that file. Reviews CXR-001 to CXR-009 are all fixed and verified. Run `py -I scripts\selftest.py` after any change to the table tools.
