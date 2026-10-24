# Where each table in data\ comes from

Every table is derived from the shipped files (never edited by hand). To rebuild them all:

```
py -I scripts\bootstrap.py <folder outside the project>          # extracts scripts, configs, economy files, language table, penetration materials
py -I scripts\build_tables.py <that folder> --check              # rebuild into <folder>\tables and compare with data\
py -I scripts\build_tables.py <that folder> --adopt              # same, then copy the rebuilt tables into data\
py -I scripts\build_tables.py <that folder> --only native_api,native_unmatched --ghidra --check   # the Ghidra-based tables (several minutes)
```

`--check` compares every row and the whole schema of each requested table (rows with a repeated key are compared whole; an added, removed or reordered column fails) and reports IDENTICAL or DIFFERENT. `--adopt` copies tables only when every generator succeeded and every requested table was produced by that run; it never copies a partial result. After a game update, run `--check` and read the differences before trusting the notes. Last verified against build 1.30.164.200 with the complete comparator: all 29 rebuilt tables identical to the committed ones.

| Table | Rows | Generator | Source |
|---|---|---|---|
| `ammo`, `ammo_physics`, `explosives`, `body_zones`, `clothing`, `food`, `weapons`, `melee`, `recoil`, `script_decls` | 251, 254, 25, 19, 899, 151, 136, 178, 55, 7,577 | `config_tables.py` | merged configs and the unpacked scripts |
| `items_master` | 2,508 | `items_master.py` | the tables above plus the loot tables and recipes |
| `loot_types_chernarus`, `loot_types_enoch`, `loot_types_nasdara`, `loot_types_sakhal`, `maps_compare` | 2,382 / 2,391 / 2,411 / 2,404 / 4 | `ce_types.py` | the four mission economy folders |
| `recipes` | 234 | `recipes.py` | recipe scripts and the language table |
| `food_stages` | 317 | `food_stages.py` | merged configs |
| `actions` | 342 | `actions.py` | action scripts |
| `weapon_states`, `weapon_transitions` | 82, 1,410 | `weapon_states.py` | firearm scripts |
| `vehicles`, `catching_items`, `ai_perception`, `noise_sources` | 28, 53, 36, 851 | `vehicles.py`, `catching.py`, `ai_perception.py`, `noise_sources.py` | merged configs |
| `penetration_materials` | 51 | `penetration.py` | the penetration material files in dz.pbo |
| `archives` | 158 | `pbo_inventory.py` | archive headers |
| `native_api`, `native_unmatched` | 3,191, 730 | `native_api.py`, `native_gaps.py` | Ghidra output for the registration functions (task lists in `scripts\ghidra\tasks`) plus the proto declarations in the scripts |
| `message_ids`, `message_map` | 155, 78 | **not regenerated** | read by hand from the network message factory and the client dispatcher (notes 4.1, 4.2); the message-factory function and the ID order are described there |

## Column notes for the older tables

- `ammo`: `type` is the DamageApplied type; `health`, `blood`, `shock` the damage of each; `bleedThr` the bleeding threshold; `v0` initSpeed; `typ` typicalSpeed; `friction` airFriction; `uncon` the unconscious refill modifier; `pellets` projectilesCount; `deflect` the deflecting angle in degrees. One row per ammo class that has a DamageApplied body, including classes that inherit it.
- `clothing`: `heat` heat isolation, `absorb` absorbency, `wetmax` the maximum wetness, `vis` the visibility modifier, `bio` and `chem` the protection values, `hp` the global hit points, `p_*` and `m_*` the projectile and melee armour multipliers (health and shock); classes that inherit the armour now show the inherited values.
- `weapons`: `family` from the base-class chain; `mags` the number of compatible magazines; `chamber` the first ammo that can be chambered; `rpm` the highest rate of fire over the modes; `ammo`, `hp`, `blood`, `shock`, `initSpeed` from the ammo that chamber type fires.
- `food`: the Nutrition body of the item (`full` = fullnessIndex, `nut` = nutritionalIndex, `dig` = digestibility).
- `melee`: the three melee modes and the damage of each mode's ammo.

## What changed when the tables were first rebuilt (2026-10-24)

Before this, ten of the tables had no generator in `scripts\` (they were produced by one-off code). Rebuilding them showed that they predated the nested-class inheritance fix (D1), so some columns were blank where a class inherits a value. The rebuilt tables are the corrected ones:

- `ammo`: 251 rows instead of 213 (classes that inherit DamageApplied are now included) and `bleedThr` filled for 33 more rows.
- `clothing`: armour columns (`p_*`, `m_*`) now filled for the 826 pieces that inherit the default multipliers of 1; `bio`, `chem`, `hp` filled where inherited.
- `weapons`: ammo columns filled for 61 more weapons; a rate of fire added for three sawn-off pistols.
- `script_decls`: 1,268 base classes that were missing now filled; 12 more declarations found.
- `recoil`: two profile names now use the script class names (`Cz61Recoil`, `PM73RakRecoil`).
- `melee`, `weapons`, `items_master`: 37 and 1 display names that were blank are now filled.
- `food`: unchanged apart from one weight kept as written (`200g`).

The other 19 tables came out identical.

## Corrections after the Codex review (2026-10-24)

- `recipes`: `custom_do`, `extra_condition` and `do_effects` now follow the recipe class chain (the nearest `CanDo` or `Do`, combined with the parent's when the child calls `super`); new columns `can_declared_in` and `do_declared_in`. 14 classes changed (the seed-cutting and animal and fish preparing families); registered recipes with an effective `Do` went from 60 to 68, with an extra condition from 69 to 82.
- `items_master`: the recipe columns count distinct recipe classes instead of ingredient slots (12 direct counts and 55 via-ancestor counts changed, for example Rag 8 to 6).
- `native_api`: the match flag now requires an accepted class, so the matched count is 2,809 (not 2,810) and 2,809 plus the 730 unmatched equals the 3,539 declarations.
- `cfgmodel.py`: explicit nested parents and conflicting top-level parents are now resolved as described in `notes/data-config.md` (5.1 addendum); no published table value changed.

## Corrections after the second Codex review (2026-10-24)

- `csv_diff.py` was replaced by a complete comparison (CXR-006): the earlier version dropped rows that repeated a key and ignored added columns, so its "identical" results were not established. Re-run with the complete comparator, all 29 tables are identical to the committed ones.
- `build_tables.py` now deletes leftover outputs before a run, adopts nothing unless the whole build succeeded and every requested table was produced, validates `--only` names, and refuses to skip an explicitly requested Ghidra table (CXR-007).
- `scripts/selftest.py` holds the regression tests for these and the earlier defects.
- Third review (CXR-008, CXR-009): `build_tables.py` now builds in a fresh `stage_XXXX` folder and never deletes anything already in `--out`; staged tables and compared files must have rows as wide as their header.
