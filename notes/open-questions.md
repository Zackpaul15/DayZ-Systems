# Backlog and open questions

Part of the DayZ static analysis notes (see `README.md` in this folder for the map). Section numbers are the original ones, so cross-references such as "see 6.10" still resolve.

## 7. Backlog and open questions

Cost key: **S** = script or file reading only (minutes); **G** = needs a Ghidra pass (about 8 to 10 minutes per query, one at a time). All items below are static analysis of the shipped files.

### 7.1 Enabler (do first if wanted)

| # | Task | Why | Cost |
|---|---|---|---|
| 0 | Raise the MCP tool-call timeout (and `REA_GHIDRA_STARTUP_TIMEOUT_MS`) for the `rea` server so queries run through the normal REA tools instead of a CLI re-import each time | Each engine question currently costs a full 8-minute re-analysis; with a longer timeout the first query pays once and later ones should be fast while the session stays open. **Applied but not effective.** Added `REA_GHIDRA_STARTUP_TIMEOUT_MS=3600000` to the `rea` server's `env` in `~/.claude.json` and `MCP_TOOL_TIMEOUT=3600000` to `env` in `~/.claude/settings.json` (backups next to each, `.bak-before-rea-timeout`). After a restart, MCP calls still timed out at about a minute, so Ghidra queries were run through the `rea` CLI in the background instead (see 7.6) | one-time |

### 7.2 Finish the player and survival picture (scripts, all S)

| # | Task | Notes |
|---|---|---|
| 1 | Stamina handler, shock handler, unconsciousness | **Done**, see 6.11 |
| 2 | Bleeding sources, broken legs and arms, injury and hit reactions | **Done**, see 6.12. Sewing wounds and ragdoll: see 6.18 |
| 3 | Item temperature simulation and the clothing isolation function | **Done**, see 6.14. Cooking temperature path, fireplace and stove heating, food stages and rotting: see 6.20 |
| 4 | Heavy metal, contamination, silicosis and sandstorm | **Done**, see 6.15. Follow-ups: engine-side storm shape, effect particles and post-processing |

### 7.3 Gameplay systems (scripts, S, each large; can be split)

| # | Task | Size hint |
|---|---|---|
| 5 | Inventory and item framework (`ItemBase`, hands, attachments, cargo) and the action system | **Done**, see 5.2. Follow-ups: item-specific actions (fireplaces, gardening, base building), the container UI side |
| 6 | Crafting recipes | **Done**, see 5.8 and `data\recipes.csv` (234 recipe classes, 143 live). What each custom `Do` changes: see 6.22. Soft skills: see 6.19 (dormant) |
| 7 | Firearms: weapon state machines, recoil, ammo, damage | **Done**, see 5.3. Melee: 6.16. Grenades and flares: 6.17. Follow-ups: per-mechanism transition tables; engine-side ballistics is partly traced (4.6, 4.7) |
| 8 | Infected and animals: behaviour, `ZombieBase`, `AIAgent`, the bot framework | **Done**, see 5.4. The bot framework is a player test-bot, not creature AI. Follow-ups: how the engine uses the perception numbers, infected sounds, ambient animals |
| 9 | Vehicles and base building | **Done**, see 5.7 (vehicles, construction model, decay, fireplaces). Follow-ups: `Hologram` placement checks, tents and gardening are now in 5.9; still open: vehicle door and wheel state machines, boats, the gardening and tent action classes |
| 10 | Server config: `CfgGameplayHandler`, restricted areas, bunker broadcast | **Done**, see 5.6 (`cfggameplay.json` and the rest of the server mission). Follow-up done in 5.10: restricted areas and the bunker broadcast. Not read: the bunker door interaction code |

### 7.4 Data (no Ghidra)

| # | Task | Why |
|---|---|---|
| 11 | Write a reader for `config.bin` (rapified config, starts with `raP`) in `scripts.pbo` and the addons | **Done**, see 5.1 and the tools in section 8. Nested-class inheritance (including parents that are root-level classes) is handled by the merge tool; food stages are in 6.20 and `data/food_stages.csv`. Follow-up: vehicles, buildings and sound sections are parsed but not analyzed |
| 12 | List the contents of all 158 addon PBOs (headers only) and classify file types | **Done**, see 1.2 and `data\archives.csv` |
| 13 | Decode the language stringtables (`languagecore.pbo`) | **Done**, see 5.5; `displayName` column added to the clothing, weapons and food tables |

### 7.5 Engine and client (Ghidra and managed code)

| # | Task | Cost |
|---|---|---|
| 14 | Map the 154 message IDs to message types by parsing the saved decompile of `FUN_140929c50` (already on disk) | **Done**, see 4.1. Follow-up done in 4.2: all 155 IDs named (`data/message_ids.csv`). Still open: what fills `DAT_144a8d1d0` at run time |
| 15 | `DayZLauncher.exe` (managed): namespaces, endpoints and what it does, using the managed-member tools | **Done**, see 1.1. Follow-up: decompile selected launcher methods (the game start logic, BattlEye handling) |
| 16 | Finish BattlEye wiring: reload caller `0x14092e677`, the two callbacks `FUN_14092ec40` and `FUN_140932a40`, the `Init` structure fields | **Done**, see 4.0 (4 Ghidra queries). Understanding only. Follow-ups G1d and G1e done in 4.5 (game-info string, disconnect message, unused slots). Not examined: anything inside `BEClient_x64.dll` |
| 17 | Compare strings of `DayZDiag_x64.exe` with retail to find debug-only features | **Done**, see 3.1 (done as a plain string diff, no Ghidra). Follow-ups: whether the retail statistics service is enabled and what it sends (G); the `TD` endpoint |
| 18 | Map the engine API: link the `proto` script declarations to native registrations in the exe | **Pilot done**, see 4.4 and `data/native_api.csv`: 3,191 registrations, 77% of 3,545 script declarations matched. Open: the 821 unmatched, and per-subsystem naming of the native functions (G4) |

### 7.6 Suggested order and how to run them

- Order: the first pass is finished (items 1 to 17 were all worked through). What to do next, with task IDs and sequencing, is in `PLAN.md` (Phase 0 enablers, then four parallel workstreams).
- Items in 7.2 to 7.4 touch only extracted files and can run in parallel as separate sessions, but they all append to this one file. If run in parallel, give each its own notes file under a `notes/` folder and merge later.
- The Ghidra items (16, 17, 18) must run one at a time; parallel runs failed earlier.
- **Tool timeout (item 0):** the settings added in `~/.claude.json` and `~/.claude/settings.json` did not lift the roughly one-minute limit on `rea` MCP calls in the desktop app (a call timed out about a minute in and the session was lost). What works: run the `rea` CLI in the background (`rea decompile EXE ADDRESS --snapshot FILE --format json`, with `REA_GHIDRA_STARTUP_TIMEOUT_MS=3600000`, `GHIDRA_INSTALL_DIR`, `JAVA_HOME` set), one process at a time. Each run took 595 to 617 s even with a snapshot, so the snapshot saves analysis but not the import.
- The extracted script source lives in the temporary scratchpad, not in this project. It will need re-extracting from `scripts.pbo` in a new session (about a minute).

### 7.7 Smaller open questions

Resolved:
- **Does `PlayerBase.m_Agents` reach other clients?** Almost certainly not. It is set and marked dirty by `PlayerAgentPool`, but no script registers it for network sync (see 6.9).
- **When does a heat source override ambient temperature?** When `U x (U - T) > 0` for source average `U` and ambient `T`: warmer-than-air positive sources and colder-than-air negative sources win (see 6.10).

Still open:
- **Do `int`-typed constants holding fractions truncate in Enforce?** Not provable from the scripts alone, but the evidence leans yes. The pattern `const int X = 0.35;` appears in the heat-stroke water drains (0.35, 0.5, 0.75), in the vehicle leak constants (`CARS_LEAK_TICK_MIN/MAX` 0.02 and 0.05, `CARS_LEAK_THRESHOLD` 0.5), in the fever blur and severe-HMP timings (1.5, 2.5 and so on) and in `HEIGHT_DIFF_LIMIT_METERS` 1.0. In the car code the developers replaced the constants with literal `0.02, 0.05` and `0.5` and left the constant names in comments, which is what you would do if the int constants had read as 0. If truncation is real, heat-stroke phases 1 to 3 drain no water and the fever blur lasts 1 to 2 s instead of 1.5 to 2.5 s. Settling it needs either a runtime test (not done, nothing here is executed) or the compiler code in the exe.

### Int-constant truncation (G2): answered, likely yes [obs for the converter, inf for the constant path]
The first lead was wrong (the string "Cannot convert to int" belongs to a JSON parser, `FUN_140aa9d80`). The real evidence is the engine's generic **value converter** `FUN_14026e380(context, value, fromType, result, toType)`, which converts a stored script value from one type to another. For the three scalar type tags (1 and 2 = the integer-like types, 3 = float) it does: int-like to int-like or float to float, a plain copy; **float to int-like: `CVTTSS2SI`, a truncation toward zero** (address `0x14026e6e8`); int-like to float: `CVTDQ2PS` (`0x14026e71e`). Other branches handle vectors, strings and class references. The float-to-int truncation is therefore what the engine does when a float value is converted to an int-typed slot, and the scripts show constant declarations that depend on it: `const int CARS_LEAK_TICK_MIN = 0.02` (0), `CARS_LEAK_THRESHOLD = 0.5` (0), and the script code that needs the real numbers uses literals with the constant name in a comment (`CarScript.c`). The remaining step, that the compiler routes `const int X = <float literal>` through this function, was not traced; it is the natural reading [inf].
Constants affected in the scripts (declared `int` with a fractional value, so they are most likely truncated):
- `GameConstants.CARS_LEAK_TICK_MIN` 0.02 and `MAX` 0.05, `CARS_LEAK_THRESHOLD` 0.5 (all become 0; the code uses literals instead).
- `HeatStroke` phase water drain 0.35, 0.5 and 0.75 per tick (become 0, so heat stroke phases 1 to 3 would not drain water; used as `-CONSTANT x deltaT`).
- `FeverBlurState` blur duration 1.5 and 2.5 (become 1 and 2), and the time between effects 25 and 35 (unchanged); `HMPSevere` 24 and 30 (unchanged).
- `CCTWaterSurface.HEIGHT_DIFF_LIMIT_METERS` 1.0 (unchanged).
This settles the question left in 6.x (heat stroke) and in the `ItemBase` comment "implicit cast to int". A runtime test on a server (for example reading the water stat during heat stroke) would confirm it; static analysis cannot.
