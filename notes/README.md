# DayZ notes: map

The write-up is split by workstream. **Section numbers are the original ones**, so a reference such as "see 6.10" or "section 4.1" resolves through the table at the bottom.

| File | What it holds |
|---|---|
| [engine-network.md](engine-network.md) | The launcher (1.1), the main executable (2), the string survey and the Diag-vs-retail comparison (3, 3.1), how the client hosts BattlEye and the message ID map (4, 4.0, 4.1) |
| [player-survival.md](player-survival.md) | The player survival model: stats, modifiers, environment, injuries, item temperature, contamination, cooking, soft skills (6 to 6.15, 6.18 to 6.21) |
| [weapons-combat.md](weapons-combat.md) | Firearms and recoil (5.3), melee, grenades, weapon state tables (6.16, 6.17, 6.24) |
| [items-actions-ai.md](items-actions-ai.md) | Inventory, actions and the action catalog (5.2, 6.23), recipes (6.22), infected, animals, AI helpers and perception (5.4, 6.25, 6.26) |
| [world-vehicles.md](world-vehicles.md) | Server mission data and the Central Economy (5.6), vehicles, base building and fireplaces (5.7), placement hologram, tents and gardening (5.9) |
| [data-config.md](data-config.md) | Install layout and archive inventory (1, 1.2), script layers (5), binary configs and real item numbers (5.1), language table (5.5), crafting recipes (5.8), how to reproduce (8) |
| [open-questions.md](open-questions.md) | The backlog (7.1 to 7.6) and the smaller open questions (7.7). The forward plan is in `../PLAN.md` |
| [verification.md](verification.md) | The statements that only a running game can confirm, each with what to observe and the predicted result (V1 to V21). |
| [plan-history.md](plan-history.md) | The planning document used until 2026-10-24 (task IDs H, G, S, W, D, Q cited in the notes). The current plan is `PLAN.md` in the parent folder. |

Confidence tags used throughout: **[obs]** read directly from the files, **[inf]** inferred, **[?]** unknown.

## Rules for parallel sessions
- Each session writes only its own workstream file and adds new files under `../data/` or `../scripts/`.
- Only the data-config session edits `../scripts/cfgmodel.py` and `../scripts/rap_reader.py`; everyone else imports them.
- Only the engine session runs Ghidra or REA, and only one process at a time.
- Keep the original section numbers when adding to a section; add new sections as the next free number or as a lettered addendum (for example 5.3a).
- Do not copy game content (extracted scripts, raw config dumps, string dumps) into this folder. Regenerate it with `../scripts/bootstrap.py`.

## Section map

| Section | Title | File |
|---|---|---|
| 1 | Install layout | [data-config.md](data-config.md) |
| 1.1 | The launcher (`DayZLauncher.exe`) | [engine-network.md](engine-network.md) |
| 1.2 | What the 158 archives contain | [data-config.md](data-config.md) |
| 2 | Main executable overview | [engine-network.md](engine-network.md) |
| 3 | String survey | [engine-network.md](engine-network.md) |
| 3.1 | The Diag executable compared with retail | [engine-network.md](engine-network.md) |
| 4 | How the client starts BattlEye | [engine-network.md](engine-network.md) |
| 4.0 | The rest of the wiring (item 16) | [engine-network.md](engine-network.md) |
| 4.1 | Client message ID map | [engine-network.md](engine-network.md) |
| 4.2 | The complete message ID table | [engine-network.md](engine-network.md) |
| 4.3 | The retail statistics service | [engine-network.md](engine-network.md) |
| 4.4 | The engine's native script API table | [engine-network.md](engine-network.md) |
| 4.5 | BattlEye hosting: remaining details | [engine-network.md](engine-network.md) |
| 4.6 | Ballistics from the engine side | [engine-network.md](engine-network.md) |
| 4.7 | Firing a shot: ammo type to projectile | [engine-network.md](engine-network.md) |
| 4.8 | Projectile flight, ricochet, penetration and damage | [engine-network.md](engine-network.md) |
| 5 | Enforce script source (`dta/scripts.pbo`) | [data-config.md](data-config.md) |
| 5.1 | The binary config (`config.bin`) and the real item numbers | [data-config.md](data-config.md) |
| 5.2 | Inventory, items and actions | [items-actions-ai.md](items-actions-ai.md) |
| 5.3 | Firearms and recoil | [weapons-combat.md](weapons-combat.md) |
| 5.4 | Infected and animals | [items-actions-ai.md](items-actions-ai.md) |
| 5.5 | The language table and in-game names | [data-config.md](data-config.md) |
| 5.6 | Server mission data: gameplay config and the Central Economy | [world-vehicles.md](world-vehicles.md) |
| 5.7 | Vehicles, base building and fireplaces | [world-vehicles.md](world-vehicles.md) |
| 5.7a | Vehicle table from the configs | [world-vehicles.md](world-vehicles.md) |
| 5.8 | Crafting recipes | [data-config.md](data-config.md) |
| 5.9 | Placement hologram, tents and gardening | [world-vehicles.md](world-vehicles.md) |
| 5.9a | Gardening and tent actions | [world-vehicles.md](world-vehicles.md) |
| 5.7b | Vehicle scripts: start, battery, crashes, boats, motorbikes | [world-vehicles.md](world-vehicles.md) |
| 5.13 | Fishing and trapping | [world-vehicles.md](world-vehicles.md) |
| 5.10 | Restricted areas and the bunker broadcast | [world-vehicles.md](world-vehicles.md) |
| 5.11 | The Central Economy on all four maps | [world-vehicles.md](world-vehicles.md) |
| 5.12 | The cross-linked item table | [data-config.md](data-config.md) |
| 5.14 | The Central Economy inside the engine | [world-vehicles.md](world-vehicles.md) |
| 6 | Player survival systems (from the scripts) | [player-survival.md](player-survival.md) |
| 6.1 | Big picture | [player-survival.md](player-survival.md) |
| 6.2 | Tick model | [player-survival.md](player-survival.md) |
| 6.3 | Stats (`PlayerStats`) | [player-survival.md](player-survival.md) |
| 6.4 | Modifiers (`ModifiersManager`, `ModifierBase`) | [player-survival.md](player-survival.md) |
| 6.5 | Stomach | [player-survival.md](player-survival.md) |
| 6.6 | Notifiers (`NotifiersManager`, `NotifierBase`) | [player-survival.md](player-survival.md) |
| 6.7 | Symptoms (`SymptomManager` in `StateManager.c`) | [player-survival.md](player-survival.md) |
| 6.8 | How state reaches clients | [player-survival.md](player-survival.md) |
| 6.9 | Transmission agents and the immune system | [player-survival.md](player-survival.md) |
| 6.10 | Environment, heat comfort, wetness, heat buffer, thermal bias and heat stroke | [player-survival.md](player-survival.md) |
| 6.11 | Stamina, shock and unconsciousness | [player-survival.md](player-survival.md) |
| 6.12 | Bleeding, hits, broken legs and injury state | [player-survival.md](player-survival.md) |
| 6.13 | Not covered yet | [player-survival.md](player-survival.md) |
| 6.14 | Item temperature and clothing isolation | [player-survival.md](player-survival.md) |
| 6.15 | Heavy metal, contamination, silicosis and sandstorms | [player-survival.md](player-survival.md) |
| 6.16 | Melee combat | [weapons-combat.md](weapons-combat.md) |
| 6.17 | Grenades and other explosives | [weapons-combat.md](weapons-combat.md) |
| 6.18 | Sewing wounds and ragdoll | [player-survival.md](player-survival.md) |
| 6.19 | The soft-skills system | [player-survival.md](player-survival.md) |
| 6.20 | Cooking, food stages and rotting | [player-survival.md](player-survival.md) |
| 6.21 | Stat levels (health, blood, energy, water, immunity) | [player-survival.md](player-survival.md) |
| 6.22 | What recipe `Do` methods change | [items-actions-ai.md](items-actions-ai.md) |
| 6.23 | The action catalog | [items-actions-ai.md](items-actions-ai.md) |
| 6.24 | Weapon state machine tables | [weapons-combat.md](weapons-combat.md) |
| 6.25 | Animals and AI helper classes | [items-actions-ai.md](items-actions-ai.md) |
| 6.26 | AI perception: noise, vision, alert | [items-actions-ai.md](items-actions-ai.md) |
| 7 | Backlog and open questions | [open-questions.md](open-questions.md) |
| 7.1 | Enabler (do first if wanted) | [open-questions.md](open-questions.md) |
| 7.2 | Finish the player and survival picture (scripts, all S) | [open-questions.md](open-questions.md) |
| 7.3 | Gameplay systems (scripts, S, each large; can be split) | [open-questions.md](open-questions.md) |
| 7.4 | Data (no Ghidra) | [open-questions.md](open-questions.md) |
| 7.5 | Engine and client (Ghidra and managed code) | [open-questions.md](open-questions.md) |
| 7.6 | Suggested order and how to run them | [open-questions.md](open-questions.md) |
| 7.7 | Smaller open questions | [open-questions.md](open-questions.md) |
| 8 | Reproducing | [data-config.md](data-config.md) |
