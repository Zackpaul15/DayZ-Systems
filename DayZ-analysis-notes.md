# DayZ static analysis notes

Target: `F:\SteamLibrary\steamapps\common\DayZ` (game build 1.30.164.200, launcher 1.6.164.64).
Method: static only. Nothing was executed and no anti-cheat code was touched. Tools: REA 6.7.0 with Ghidra 12.1.4, plus small PBO and config readers in `scripts/`.
Confidence tags: **[obs]** read directly from the files, **[inf]** inferred, **[?]** unknown.

**This file is now an index.** The write-up was split by workstream into `notes/` (section numbers unchanged). Start with [notes/README.md](notes/README.md), which has the full section map. The forward plan is [PLAN.md](PLAN.md); the folder index is [README.md](README.md).

| Read this | For |
|---|---|
| [notes/engine-network.md](notes/engine-network.md) | launcher, main exe, strings, Diag vs retail, BattlEye hosting, network message IDs |
| [notes/survival-combat.md](notes/survival-combat.md) | items and actions, firearms, infected and animals, the player survival model |
| [notes/world-vehicles.md](notes/world-vehicles.md) | Central Economy and server mission data, vehicles, base building, tents and gardening |
| [notes/data-config.md](notes/data-config.md) | install layout, archive inventory, script layers, configs and real numbers, language table, recipes, reproduction steps |
| [notes/open-questions.md](notes/open-questions.md) | backlog status and open questions |

The original single-file version had 1,306 lines; the split keeps every line (checked: same non-blank lines and heading count).
