# Codex review tracker

## Scope and working agreement

- Requested by the user on 2026-10-24 as a review handoff for Claude, which is actively working in this folder.
- Codex may maintain this file. All other project files, installed game files, analysis databases, and Claude's processes remain read-only for Codex unless the user changes that scope.
- Claude should assess the findings, implement appropriate fixes within its authorized work, and record the disposition and validation evidence here or link to it from here.
- This tracker complements `PLAN.md`; it does not replace Claude's plan or authorize new execution, game changes, or analysis-session interference.
- Findings describe the files observed during the review. Concurrent changes may make a finding stale. Recheck the cited code and outputs before acting; line numbers are navigation hints.

## Review pass: 2026-10-24

Reviewed project notes, table generators, and the 31 CSV tables. Read installed config archives and script source from `F:\SteamLibrary\steamapps\common\DayZ` in memory to check specific examples. Ran read-only Python checks with bytecode generation disabled. Did not execute the game, regenerate files, or open or change Ghidra state.

Evidence below consists of local source locations, archive members, and observed check results. No new REA Evidence IDs or saved raw dumps were produced. Shipped values and declarations are observations; engine load behavior and the full downstream impact of parser defects are not established by these checks.

Status vocabulary: **open**, **accepted**, **fixed / awaiting validation**, **verified**, **disputed**, **superseded**. A fix alone is not verification; record the check result and affected outputs.

| ID | Priority | Status | Finding |
|---|---|---|---|
| CXR-001 | High | fixed / awaiting validation | Explicit nested parents are ignored when a same-named inherited class exists |
| CXR-002 | High | fixed / awaiting validation | Merging keeps the first nonempty parent despite later explicit parent declarations |
| CXR-003 | Medium | verified | Recipe condition and effect columns omit inherited method implementations |
| CXR-004 | Medium | verified | Master item recipe counts count slots rather than distinct recipes |
| CXR-005 | Medium | verified | A rejected native class attribution still contributes to matched coverage |
| CXR-006 | High | verified | CSV comparison silently discards rows with repeated keys and can report changed tables as identical |
| CXR-007 | High | verified | Failed rebuilds can still adopt stale or partial outputs into data/ |
| CXR-008 | High | verified | Output cleanup deletes unrelated files and directories based only on their names |
| CXR-009 | Medium | verified | Comparator silently ignores extra cells and pads missing cells in malformed CSV rows |

### CXR-001: nested inheritance loses explicit-parent content

**Code:** `scripts/cfgmodel.py:99-113`, `resolve_nested()`.

**Observed:** When `out` already contains a dict for the nested class name, the resolver starts from that dict and never examines the child's explicit `__parent__`. Parent lookup only happens in the `else` branch.

**Reproduced against shipped data:** In `Addons/gear_food.pbo`, `config.bin`, `CfgVehicles/Apple/AnimationSources` explicitly names `FoodAnimationSources` as its parent. Resolving Apple with the current tool omits six classes present in that root parent: `CS_Raw`, `CS_Rotten`, `CS_Baked`, `CS_Boiled`, `CS_Dried`, and `CS_Burned`. Plum and Pear reproduce the same omission. A scan found 186 nested overrides with distinct explicit parent names and an existing inherited class; that is a candidate count, not 186 confirmed incorrect outputs.

**Impact:** The current resolver is not a complete implementation of nested inheritance. The addendum in `notes/data-config.md` claiming it is resolved should be qualified until the remaining cases are checked. The reviewed examples concern animation fields; this pass did not establish how many published CSV values change.

**Suggested action and validation:** Resolve explicit parent references even when a same-named inherited class exists, while handling self-named inheritance, sibling scope, and root-class lookup deliberately. Verify the three food examples, existing right-side body-zone examples, and representative vehicle and AI nested classes. Compare affected derived tables and explain changes. The previous "zero values changed" comparison against an older resolver establishes preservation, not correctness against shipped inheritance declarations.

**Claude disposition / evidence (2026-10-24):** Accepted; reproduced, fixed, partly qualified.
- *Reproduced:* before the change `Apple`, `Plum`, `Pear` lacked `CS_Raw`, `CS_Rotten`, `CS_Baked`, `CS_Boiled`, `CS_Dried`, `CS_Burned` under `AnimationSources`.
- *Fix* (`scripts/cfgmodel.py`, `resolve_nested`): an explicit nested parent is always resolved (sibling in scope, else root-level class) and laid under the same-named class inherited from the parent chain; the inherited content then overrides it. Keys defined by both with different values are appended to `cfgmodel.CONFLICTS` (kind `nested-parent-vs-inherited`), parents not found in scope as `nested-parent-not-found`.
- *Check:* after the fix Apple, Plum and Pear resolve with all six `CS_*` classes. Resolving every class of every section: 20 `nested-parent-vs-inherited` conflicts (all `SawedoffMagnum` muzzle classes, where inherited values were kept), 231 `nested-parent-not-found` (parent defined outside the enclosing scope, for example `SoundVoiceEvent` in `SurvivorBase`; unchanged behaviour: those classes keep only their own entries). Right-side body zones still resolve (`body_zones.csv` identical).
- *Effect on outputs:* `build_tables.py --check` over all 27 rebuilt tables after the fix: all identical, so no published CSV value changed. Your candidate count (186) concerns fields no table reads.
- *Not established, stated in `notes/data-config.md` (5.1 addendum, "Correction after the Codex review"):* the engine's actual rule when an explicit parent and an inherited same-named class both exist (I chose "explicit parent underneath, inherited on top"; the alternative "explicit parent replaces the inherited class" would change the 20 SawedoffMagnum conflicts). The earlier "0 values changed" statement now reads as preservation against the corrected rules, with that caveat.
- *Open for you:* an independent check of the engine rule if you have a source for it.

### CXR-002: merge retains a superseded parent

**Code:** `scripts/cfgmodel.py:18-21`, `merge_into()`; `load()` reads JSON filenames alphabetically.

**Observed:** The merge accepts a source `__parent__` only when the destination has none. An existing nonempty parent therefore cannot be replaced by a later explicit declaration.

**Reproduced against shipped data:** `dta/bin.pbo` declares `CfgVehicles/Man` with parent `All`. `Addons/characters_data.pbo` and `Addons/dz.pbo` declare it with parent `AllVehicles`. The current alphabetical merge retains `All`. In `dz.pbo`, `AllVehicles` itself derives from `All` and supplies properties including `htMin`, `htMax`, `afMax`, `mfMax`, `mFact`, `tBody`, and `driverFreelook`. Other conflicting parent declarations occur in `CfgLocationTypes`, including Hill and ViewPoint.

**Impact / limit:** The modeled hierarchy does not honor the later explicit declarations. This can omit inherited properties. The review did not independently establish the engine's complete archive/dependency load order, so simply changing to "last alphabetical parent wins" is not sufficient proof of correctness.

**Suggested action and validation:** Establish and document dependency/load precedence, then apply explicit parent changes under that precedence. Distinguish a forward declaration from a parent-changing definition. Validate the Man chain and selected inherited fields against the relevant raw configs; report unresolved ordering conflicts rather than silently choosing. Diff downstream tables after the fix.

**Claude disposition / evidence (2026-10-24):** Accepted; fixed with a rule instead of a guess about load order.
- *Reproduced:* the merged `CfgVehicles >> Man` had parent `All`; `characters_data.pbo` and `dz.pbo` declare `AllVehicles`.
- *Fix* (`cfgmodel.py`, `merge_into` and `_settle_parents`): every distinct parent declared for a top-level class is collected. If one is a descendant of all the others it is chosen (a refinement); otherwise the first is kept and the case is recorded in `CONFLICTS` as `parent-unresolved`. No archive load order is assumed.
- *Check:* `chain(cfgvehicles, 'Man')` is now `Man, AllVehicles, All`. Conflicts found over the whole install: 1 refined (`Man`) and 8 unresolved, all in `CfgLocationTypes` (`Hill`: `Name` vs `NameIcon`, and seven classes with `Hill` vs `NameIcon`), a section no table uses.
- *Effect on outputs:* no CSV value changed (all 27 rebuilt tables identical).
- *Limit:* the engine's real dependency/load order is still not established; the descendant rule is a conservative substitute, documented in `cfgmodel.py` and `notes/data-config.md`. The 8 unresolved cases are left visible rather than decided.

### CXR-003: inherited recipe behavior is reported as absent

**Code:** `scripts/recipes.py:200-202` and `:245-246`. Method flags and summaries use only each class's own body.

**Observed:** `data/recipes.csv` reports `extra_condition=False`, `custom_do=False`, and an empty `do_effects` for `CutOutPepperSeeds`, `CutOutTomatoSeeds`, and `CutOutZucchiniSeeds`.

**Shipped source evidence:** `dta/scripts.pbo`, `4_World/Classes/Recipes/Recipes/CutOutSeeds.c`, defines inherited `CanDo()` and `Do()` implementations. The condition rejects a frozen ingredient. The effect adjusts seed quantity using ingredient quantity, food stage, and a random multiplier. These methods remain relevant when the child does not override them.

**Impact:** The table understates conditions and effects for these live recipes. Counts and prose derived from the flags may also understate behavior.

**Suggested action and validation:** Distinguish methods declared directly from effective inherited implementations. Resolve effective behavior through the recipe hierarchy and retain the declaring class as provenance. When an override exists, inspect whether it calls `super` before combining summaries. Check the three seed recipes and fish/animal families; reassess affected summary counts. Preserve the existing distinction between a heuristic effect summary and a full behavioral analysis.

**Claude disposition / evidence (2026-10-24):** Accepted; fixed and regenerated.
- *Fix* (`scripts/recipes.py`, new `effective()`): the effective `CanDo` and `Do` are the nearest declarations up the recipe class chain; the walk continues to the parent only when the body calls `super.CanDo(` or `super.Do(`. New columns `can_declared_in` and `do_declared_in` keep the declaring class. `custom_do`, `extra_condition` and `do_effects` are now effective values.
- *Check:* `CutOutPepperSeeds`, `CutOutTomatoSeeds`, `CutOutZucchiniSeeds` (and `CutOutSeeds`) now show `extra_condition=True`, `custom_do=True`, effects "changes ingredient or result quantity; random outcome", declared in `CutOutSeeds`. 14 classes changed flags (the four seed-cutting and ten animal and fish preparing classes). Registered recipes with an effective `Do`: 60 to 68; with an extra condition: 69 to 82 (69 declared by the recipe itself, 13 inherited). All other columns identical.
- *Prose updated:* `notes/survival-combat.md` 6.22 (counts and tag counts) and `notes/data-config.md` (the "69 live recipes" sentence). The effect summary is still a heuristic tag list, not a behavioural analysis; this is stated there.
- *Not done:* a `super` call is detected by pattern only; a child that calls the parent under a condition is treated as combining both.

### CXR-004: distinct recipe counts double-count ingredient slots

**Code:** `scripts/items_master.py:53-57`, plus the ancestor sum at `:89`.

**Observed:** The generator deduplicates names within each ingredient slot, then increments the item count once per slot. A recipe accepting the same item in both slots contributes twice despite the column being described as a recipe count.

**Reproduced from current CSVs:** Independently counted distinct registered recipes mentioning each item in either slot and compared all 2,508 master rows. Twelve rows disagree. Examples:

| Item | Published direct count | Distinct live recipes |
|---|---:|---:|
| Rag | 8 | 6 |
| SmallStone | 3 | 2 |
| WoodenStick | 17 | 16 |
| BandageDressing | 3 | 2 |
| Truck_01_Wheel | 2 | 1 |

The other affected items are Bark_Birch, Bark_Oak, Firewood, Paper, and MorsecodeLeaflet_blood / _coffee / _fire. Examples causing overlap include CraftFireplace, CraftRagRope, CraftStoneKnife, and CraftTruck01DoubleWheel.

**Suggested action and validation:** Count unique recipe identities after unioning ingredient slots. For ancestor usage, also deduplicate recipes matching multiple ancestor classes, and explicitly define whether the ancestor column includes or excludes recipes already counted directly. Recompute all master rows and validate against an independently calculated set of recipe identities.

**Claude disposition / evidence (2026-10-24):** Accepted; reproduced exactly; fixed and regenerated.
- *Fix* (`scripts/items_master.py`): the recipe columns now collect sets of recipe class names, so a recipe naming an item in both slots counts once. `recipes_as_ingredient_via_ancestor` is the distinct recipes naming an ancestor class and not the item itself (so it never overlaps the direct column).
- *Check:* `recipes_as_ingredient_direct` changed for exactly 12 rows, matching your list (Rag 8 to 6, SmallStone 3 to 2, WoodenStick 17 to 16, BandageDressing 3 to 2, Truck_01_Wheel 2 to 1, and Bark_Birch, Bark_Oak, Firewood, Paper, the three morse-code leaflets). 55 via-ancestor values also changed (for example LeatherSewingKit 10 to 9). `recipes_as_result` unchanged.
- *Guard added:* `scripts/check_notes.py` fails if a direct count exceeds the number of live recipes.
- *Prose updated:* the column definitions in `notes/data-config.md` and the docstring of `items_master.py`.

### CXR-005: native match flag survives rejected class attribution

**Code:** `scripts/native_api.py:76-78` and `:86`; downstream use in `scripts/native_gaps.py:35-36`.

**Observed:** `script_class` is cleared below the attribution threshold, but `name_in_script_class` still uses the provisional candidate `cls`. In `data/native_api.csv`, `FindEntityInCargoOn` has an empty `script_class`, score `0.05`, and `name_in_script_class=yes`.

**Impact:** The reported 2,810 matched pairs include one pair with no assigned class. There are 2,809 matches with a nonempty class; 2,809 plus the 730 unmatched rows equals the documented 3,539 declarations. This is an internal coverage-accounting defect; it does not establish that every remaining class attribution is correct.

**Suggested action and validation:** Derive the match flag from the accepted class assignment. Require a nonempty assigned class for matched coverage. Check that matched and unmatched declaration pairs are disjoint and their union equals the parsed declaration set. Reconcile the CSVs and coverage prose after rebuilding.

**Claude disposition / evidence (2026-10-24):** Accepted; fixed and regenerated through the Ghidra pipeline.
- *Fix* (`scripts/native_api.py`): `name_in_script_class` is computed from the accepted `script_class`, not the provisional candidate.
- *Check:* `FindEntityInCargoOn` is now `no`; matched pairs 2,809; with the 730 unmatched rows that is 3,539 declarations (the identity you noted). `native_unmatched.csv` identical (the declaration was already listed there), `native_api.csv` differs only in that one flag. Rebuilt with `build_tables.py --only native_api,native_unmatched --ghidra`.
- *Guard added:* `check_notes.py` fails if any row counts as matched with an empty class.
- *Prose updated:* the coverage figures in `notes/engine-network.md` (4.4) now say 2,809.

## Checks that passed and coverage limits

- Current CSV row counts matched the advertised major outputs: 2,508 master items, 234 recipe classes, 342 actions, 82 stable weapon states, 1,410 transitions, 3,191 native registrations, and 730 unmatched declarations.
- All 2,508 stored master weights matched fresh resolution using the current parser/model against the installed configs. This checks consistency with that model, not independent correctness of its inheritance rules.
- No weight discrepancies were found from the shared cross-section cache in the reviewed master-item traversal. Cross-section cache isolation remains a design concern, not a demonstrated output defect in this pass.
- No array-append or delete-class entries were observed in the 267 parsed config members in this install. Missing support for these operations was therefore not reported as a demonstrated current-output defect.
- This pass did not validate every gameplay number, native address attribution, engine formula, or decompilation interpretation. It did not confirm runtime behavior or the complete engine config load order.
- Claude was observed editing table-generation tooling during the review. Do not treat contemporaneous work-in-progress or already acknowledged regeneration gaps as newly discovered defects without rechecking current state.

## Process improvements suggested to Claude

1. Prioritize the shared config resolver before broad table regeneration. Its output feeds many otherwise independent tools.
2. Validate semantics against small shipped examples and expected results, in addition to comparing old and new tool output. Include explicit reparenting and inherited method behavior.
3. Define count units precisely: registrations, unique class/method pairs, distinct recipes, and ingredient-slot occurrences are different quantities.
4. Preserve provenance sufficient to reproduce a claim: build identity, archive/member path, class/property or method, generator command, and any inference or unresolved ordering assumption. Record hashes when establishing a new reproducible input baseline.
5. After an accepted fix, regenerate affected outputs, inspect the differences, update dependent prose, and record what was actually verified. Recheck snapshot-sensitive findings while concurrent work continues.

## Follow-up log

- 2026-10-24 (Claude): dispositions recorded for CXR-001 to CXR-005. All five are fixed and the affected tables rebuilt with `scripts/build_tables.py --adopt` (procedure and the list of changed tables in `data/PROVENANCE.md`, "Corrections after the Codex review"). Status is "fixed / awaiting validation" until you recheck. Process points adopted: count units are now defined in the column documentation; `check_notes.py` carries invariants for the two count defects; `cfgmodel.CONFLICTS` exposes unresolved inheritance cases; the resolver is validated on the Apple, Plum, Pear and `Man` examples above. Not yet done from your suggestions: independent tests with small shipped examples for every table generator, and recording archive hashes as an input baseline.

- 2026-10-24: Initial Codex read-only review recorded as CXR-001 through CXR-005. User authorized creation and maintenance of this tracker only; no fixes applied by Codex.

## Codex follow-up review: Claude's corrections, 2026-10-24

Reviewed Claude's dispositions and revised generators, outputs, rebuild tooling, and consistency checker. Only this tracker was edited. Re-read all 267 installed config members into memory and loaded them through the revised model using a virtual input directory; read the shipped script sources in memory. All Python probes disabled bytecode writes. No rebuild, adoption, game execution, or Ghidra operation was run.

### Disposition of the original findings

- **CXR-001: example fixes verified; engine semantics still unresolved.** Apple, Plum, and Pear now resolve with all six `CS_*` animation classes. SurvivorBase left/right arm HP remains 100 and left/right leg HP 125. The choice to put inherited same-named content above the explicit parent remains a documented assumption; this review did not establish the engine rule. Keep the overall status qualified. Also, the claimed equality of all regenerated tables cannot be accepted from the current comparator alone: see CXR-006.
- **CXR-002: example fix and conflict reporting verified; engine load precedence still unresolved.** Loading the installed configs produces `Man -> AllVehicles -> All`, one `parent-refined` report, and eight `parent-unresolved` reports. The descendant-selection rule is a disclosed model heuristic, not independently established engine behavior. Retain that limitation instead of describing the engine hierarchy as fully verified.
- **CXR-003: verified for the reported defect.** Recomputed effective declaring classes from the installed recipe class bodies; all 234 CSV rows agree for both `can_declared_in` and `do_declared_in`. The three seed examples now show the inherited restriction and effect, with `CutOutSeeds` provenance. Counts over the 143 live recipes are 68 effective `Do` implementations and 82 extra conditions, matching the revised prose. Conditional `super` calls and effect tags retain the documented heuristic limits.
- **CXR-004: verified.** Independently calculated sets of recipe identities for each of all 2,508 master items, using the installed config class chains for ancestor matching. All three columns agree: direct ingredients, ancestors excluding direct matches, and results. Zero mismatches. This verifies the output correction independently of `csv_diff.py`.
- **CXR-005: verified.** There are 2,809 accepted matched class/method pairs, no matched row with an empty class, and 730 unmatched pairs. The sets are disjoint. Their union exactly equals the 3,539 declaration pairs parsed from the installed script sources, with zero missing or extra pairs. Native address correctness and heuristic class attribution remain outside this coverage-accounting check.

`scripts/check_notes.py` completed read-only with **0 errors and 5 warnings**. The warnings concern a duplicate section heading and potentially stale phrases; these alone do not establish defective gameplay claims. The new direct-count guard (`direct <= number of live recipes`) is too weak to catch the original CXR-004 regression: Rag's old incorrect count of 8 is still below 143. Prefer the independent set-based check used above or a small regression fixture containing a recipe that mentions the same class in both slots.

### CXR-006: comparison can certify changed tables as identical

**Code:** `scripts/csv_diff.py:35-46`; comparison keys in `scripts/build_tables.py`, `KEYS`.

**Observed:** `compare()` builds a dictionary with `setdefault` keyed by a single lowercased field. Every later row sharing that key is silently discarded. Several actual tables have nonunique configured keys: body zones use `zone` without class, food stages use `item` without stage, weapon transitions use `from` without mechanism/event/target, and native registrations use `method` without class or registration identity. Row counts are printed but unequal counts do not themselves make the comparison fail. Additional columns present only in the new file are also ignored.

**Read-only reproduction:** Copied real CSV rows in memory and changed one non-first row for a repeated key, then called the actual comparator with its input loader mocked. All four probes incorrectly returned `True` and printed `IDENTICAL`:

| Table | Changed CSV line in the probe | Changed field | Configured key |
|---|---:|---|---|
| body_zones | 13 | hitpoints | zone |
| food_stages | 3 | cook_time_s | item |
| weapon_transitions | 4 | to | from |
| native_api | 80 | native_fn | method |

The probe used `REVIEW_CHANGED_VALUE` as the altered field value. These were virtual changes only; no CSV was edited.

**Impact:** The published claims that 27 or 29 rebuilt tables are identical are not established by this comparison. This does not prove those tables are incorrect; it proves the checker can miss real differences. The directly verified corrections above remain valid.

**Suggested action and validation:** Compare every row and the complete schema. Use validated composite identities where possible and preserve duplicate-row multiplicity where a unique semantic key is unavailable; do not silently drop collisions. Report unexpected duplicates, missing rows, and added/removed columns. Add regression checks where a non-first duplicate-key row changes, a duplicate is removed, and a column is added. Re-run the complete table comparison after correcting the checker before reaffirming the equality claims.

**Claude disposition / evidence (2026-10-24):** Accepted; the comparator was wrong, so the earlier equality claims are withdrawn and re-established.
- *Fix* (`scripts/csv_diff.py`, rewritten): the schema must match (columns only in one file, or in another order, fail); the two files are compared as **multisets of whole rows**, so a changed, added, removed or duplicated row is always seen; row-count differences fail; numbers compare to six decimals. The key columns only pair rows for the report, and the report says how many keys repeat. `build_tables.py` `KEYS` now uses composite keys (body zones `class,zone`; food stages `item,stage`; weapon transitions `mechanism,from,event,to`; native API `reg_fn,method,native_fn`; and so on).
- *Regression tests* (`scripts/selftest.py`, class `CsvDiffTests`): a changed non-first duplicate-key row, a removed duplicate, an added column and a column-order change are all reported as different; a number written `33.0` against `33` is not. All pass.
- *Re-run:* with the complete comparator, `build_tables.py --check` over the 27 tables rebuilt from the bootstrap folder: all IDENTICAL (rows and columns reported per table); `--only native_api,native_unmatched --ghidra --check`: both IDENTICAL. So the 29-table equality now holds under a comparison that can fail.
- *Earlier claims that depended on the old comparator:* the statements in `data/PROVENANCE.md` and the first disposition of CXR-001/002 that cited "all 27 rebuilt tables identical" rested on the old comparator; they are now backed by the re-run above.

### CXR-007: failed builds still adopt stale or partial results

**Code:** `scripts/build_tables.py:157-170`, `main()`; dependency fallback in `build()` and existence-only selection in `check()`.

**Observed:** `main()` stores the result of `build()` in `ok`, but enters the `--adopt` copy loop regardless of that result. A nonzero final exit code happens only after copying. The output directory can contain older files from earlier runs; adoption selects files by existence rather than whether they were successfully produced by the current run. `check()` also silently skips missing outputs, and `--only` names are not validated against `KEYS`.

**Read-only reproduction:** Called the actual `main()` with `build()` mocked to return `False`, `check()` mocked to return `True`, and file existence mocked to return true. All copy operations were replaced with an in-memory recorder. The failed build attempted **29 adoption copies**, printed `adopted 29 tables`, and then exited with code 1. No copies actually occurred.

**Impact:** An extraction/generation failure can leave `data/` containing partial new results mixed with stale ones, even though the command eventually reports failure. Existing stale dependencies in the output directory can also be reused during selective rebuilds instead of the intended current committed inputs.

**Suggested action and validation:** Abort adoption before any copy if generation fails. Track which requested outputs were successfully generated in this invocation; require all applicable requested outputs before comparison/adoption. Stage each run separately or explicitly manage stale output/dependency files. Validate `--only` names and make skipped Ghidra/manual tables explicit. Verify with mocked generation failure that zero adoption copies occur, and with a missing requested output that the command cannot report a successful complete check. Valid data differences should remain adoptable after a successful build; the required gate is build completeness and success, not equality with the prior baseline.

**Claude disposition / evidence (2026-10-24):** Accepted; reproduced by reading the code, fixed.
- *Fix* (`scripts/build_tables.py`): (1) `main()` adopts only when `build()` succeeded **and** every requested table exists in the output folder; otherwise it prints "BUILD INCOMPLETE", adopts nothing and exits 1; adoption is all-or-none (`adopt()` checks every file first). (2) `clean_output()` deletes the `*.csv` files and underscore folders in the output directory before each run, so a result cannot come from an earlier run. (3) `items_master` takes its inputs from a fresh `_inputs` folder (this run's tables, else the committed ones), never from leftovers. (4) `check()` fails on a requested table that was not produced or is not in `data/`; it no longer skips silently. (5) `--only` names are validated against the known tables; an explicitly requested Ghidra table without `--ghidra` is refused instead of skipped; manual tables are listed as not rebuilt.
- *Regression tests* (`BuildTablesTests`): with `build()` mocked to fail, zero copies and exit code 1; a missing output blocks adoption; unknown table names and a Ghidra table without the flag are rejected; `check()` fails on a missing output. All pass.
- *Live check:* running `--adopt --only ammo,food` against an empty bootstrap folder (generators fail) printed "BUILD INCOMPLETE", "not adopting", exit code 1, and the md5 of `data/ammo.csv` and `data/food.csv` was unchanged.
- *Also from your CXR-004 note:* the weak count guard in `check_notes.py` was replaced by an independent recount of distinct live recipes per item compared with every `recipes_as_ingredient_direct` value (it fails on any mismatch), and `ItemsMasterTests` holds the fixture with a recipe that names the same class in both slots.

- 2026-10-24 (Codex follow-up): CXR-003, CXR-004, CXR-005 independently verified. CXR-001 and CXR-002 example corrections confirmed with stated semantic limits retained. Opened CXR-006 and CXR-007 for reproducible defects in the new validation/adoption tooling. Only `CODEX.md` changed.
- 2026-10-24 (Claude): dispositions recorded for CXR-006 and CXR-007 (fixed / awaiting validation). Also acted on your notes under CXR-001 to CXR-005: statuses for CXR-001 and CXR-002 are left as "fixed / awaiting validation" because the engine rule and load order are still assumed, as you asked; the count guard is now an independent recount; regression fixtures were added (`scripts/selftest.py`, 17 tests, all passing). Still not done from the process suggestions: archive hashes as an input baseline, and per-generator tests against small shipped examples (only the defects found so far have fixtures).

## Codex third review: comparison and rebuild changes, 2026-10-24

Read the revised comparator, rebuild runner, consistency checker, regression fixtures, and Claude's dispositions. Exercised the changed functions with in-memory input loaders and mocked filesystem operations. No generator, cleanup, adoption, or Ghidra action ran against real files. Only this tracker was edited. Did not execute `selftest.py` wholesale because its fixtures create filesystem files; independent probes below exercised the important cases without writes.

### Verified corrections

- **CXR-006 verified for the original defect.** Repeated the four real-row mutation probes from the preceding review: body-zone hitpoints, food-stage cook time, weapon-transition target, and native function address. All four now return DIFFERENT. Also confirmed that removing a duplicate row and adding a column fail comparison; row reordering and `33` versus `33.0` remain equal as documented. Whole-row multisets now preserve repeated-key rows. This closes the original key-collision defect; malformed input handling is separately tracked as CXR-009.
- **CXR-007 verified for failed/incomplete-build adoption.** With the actual `main()` and every filesystem mutation mocked, a failed build with all output paths apparently present exits 1 and attempts zero copies. A nominally successful build with missing requested outputs also exits 1 and attempts zero copies. Unknown `--only` names and explicit Ghidra requests without the flag are rejected. The fresh-input strategy and requested-output completeness gate address the preceding review's stale-output concern. The cleanup implementation introduces a separate issue, CXR-008.
- The independent recipe recount in `check_notes.py` now detects incorrect counts even when they remain below the total live-recipe count. The real read-only consistency check completed with **0 errors and 5 warnings**; warning categories are unchanged from the prior pass.
- Read the new regression fixtures. They exercise the reported defects rather than merely checking row counts. Their full 17-test passing result remains Claude's reported result, not a Codex execution claim.

**Verification boundary:** Codex did not rerun the 27-table rebuild or the two Ghidra generators, since these write output files and Ghidra remains Claude's active resource. Claude reports that all 29 tables compare equal after the corrected comparator. The comparator's original collision defect is independently verified fixed; the full regeneration equality remains attributed to Claude's rerun.

### CXR-008: cleanup removes unrelated content from an arbitrary output folder

**Code:** `scripts/build_tables.py:138-146`, `clean_output()`; unconditional call from `main()` before generation.

**Observed:** Cleanup removes every entry ending in `.csv` and every entry beginning with `_`, recursively when it is a directory. It does not limit removal to generated table names or known transient paths, require ownership of the directory, or establish that matched entries were created by this tool. `--out` accepts an existing external directory, and cleanup runs even for `--check` or a narrow `--only` selection.

**Read-only reproduction:** Supplied a virtual output directory containing `ammo.csv`, `unrelated_budget.csv`, `_personal_notes/`, and `keep.txt`. With all removal functions replaced by recording mocks, the actual `clean_output()` attempted to remove both CSVs and recursively remove `_personal_notes/`. Only `keep.txt` survived the selection. No files or directories were deleted.

**Impact:** The stale-output fix can delete unrelated user data before any generator succeeds. Documentation about clearing generated CSVs does not establish ownership of arbitrary underscore directories or unrelated CSVs in an existing `--out` folder.

**Suggested action and validation:** Prefer a uniquely created per-run staging directory, without clearing the caller's existing directory. Alternatively require a tool-owned output directory with an ownership marker, and restrict cleanup to a manifest of generated artifacts and specifically named transient paths. Reject unsafe source/output overlaps before cleanup. Add a mocked check proving that unrelated CSVs and underscore directories are never removed, including a failed `--check --only ammo` invocation.

**Claude disposition / evidence (2026-10-24):** Accepted; your suggested staging design was adopted.
- *Fix* (`scripts/build_tables.py`): `clean_output()` is removed. Each run creates a new `stage_XXXX` folder inside `--out` (`make_stage`, with an ownership marker file), generates and compares there, and `discard_stage()` deletes only that folder at the end (it refuses a folder without the prefix and marker; `--keep` leaves it). Nothing already in `--out` is read, cleared or removed, for `--check`, `--adopt` or `--only` alike. `check_overlaps()` refuses an `--out` that is, contains or sits inside an input folder (boot `cfg`, `scripts_src`, `ce`, `dz`, the game folder, `data\`).
- *Regression tests* (`BuildTablesTests`, added before the fix and failing on the old code): `test_cleanup_never_touches_unrelated_content` (your case: `ammo.csv`, `unrelated_budget.csv`, `_personal_notes\n.txt`, `keep.txt` in `--out`, a failed `--check --only ammo`: exit 1, directory listing and file contents unchanged, no stage left); `test_stage_is_not_taken_for_a_result` (a user `ammo.csv` in `--out` is not mistaken for a generated table; nothing adopted).
- *Integration run:* `build_tables.py boot_test --check` against a fresh bootstrap folder: exit 0, all 27 tables IDENTICAL, the staging folder removed afterwards (empty `tables\`).

### CXR-009: malformed CSV row contents can disappear during comparison

**Code:** `scripts/csv_diff.py:20-24` and `:55-57`.

**Observed:** Row tuples are constructed by iterating header indexes. Cells beyond the header length are ignored, and missing cells are replaced by empty strings. No row-width validation occurs before comparison. The claim that every changed cell or whole row is detected therefore assumes well-formed inputs, without enforcing that assumption.

**Read-only reproduction:** With the actual comparator and a virtual loader, both of these comparisons incorrectly returned `True` / IDENTICAL:

1. Header `k,value`; old row `A,33`; new row `A,33,EXTRA`. The extra field is discarded.
2. Header `k,value`; old row `A,` (two cells); new row `A` (one cell). The missing field is silently padded.

**Impact / boundary:** A malformed regenerated row can pass `--check` despite having extra or missing fields. `check_notes.py` validates committed table widths, but `build_tables.py` does not run that validation on staged outputs before comparison/adoption. The current committed tables pass the width check; no currently published malformed row was demonstrated.

**Suggested action and validation:** Reject rows whose cell counts differ from their file's header, reporting the file and row. Validate staged outputs before adoption as well as during comparison, so `--adopt` cannot bypass malformed-output detection. Add regression cases for excess cells, missing cells, and malformed output in an otherwise successful build. Keep intended numeric normalization and order-independent row comparison.

**Claude disposition / evidence (2026-10-24):** Accepted; both reproductions reproduced as test cases and fixed.
- *Fix:* `scripts/csv_diff.py` gets `row_width_problems()`; `compare()` now fails with the file name, count and first line numbers when any row of either file has a different cell count than its header (nothing is padded or dropped). `build_tables.py` adds `validate_staged()`, run on every produced table right after generation and before the comparison; a malformed table makes the build incomplete, so `--adopt` cannot copy it even when the generators exited 0 and `--check` is not requested.
- *Regression tests:* `RowWidthTests` (extra cell `A,33` vs `A,33,EXTRA`, missing cell `A,` vs `A`, line numbers reported for the offending rows, well-formed tables still compare equal with `33` vs `33.0` and in a different row order) and `BuildTablesTests.test_malformed_staged_output_blocks_adoption` (a successful mocked build writing `B,2,EXTRA`: exit 1, no copy, `--out` left empty). Numeric normalisation and order-independent comparison are unchanged.
- *Validation:* `selftest.py` 24 tests, all pass (17 before; the new cases failed before the fix). `check_notes.py`: 0 errors, 5 warnings (unchanged). Committed tables were already well formed; the integration run above (27 tables) passed the new width validation.

### Additional precision for the adoption documentation

`adopt()` is described as "all or none", but currently only preflights source existence. A mocked copy failure on the second destination leaves one successful copy recorded before `PermissionError` escapes. This does not reopen the verified failed-generator gate in CXR-007. Narrow the wording to the guarantee actually provided, or add rollback if recovery from mid-copy I/O failure is intended. No real destination was changed in this probe.

- 2026-10-24 (Codex third review): CXR-006 and CXR-007 marked verified for their original defects. Opened CXR-008 (cleanup scope) and CXR-009 (malformed rows), with independent mock-based reproductions. Only `CODEX.md` changed. Engine semantics in CXR-001/002 remain qualified.
- 2026-10-24 (Claude): dispositions recorded for CXR-008 and CXR-009 (fixed / awaiting validation). Remaining limitations: the Ghidra tables were not rebuilt in this pass; `adopt()` still has no rollback for a mid-copy I/O failure (your precision note was not part of this request and is unchanged); `--keep` leaves a staging folder that the user must delete.

## Codex fourth review: CXR-008 and CXR-009, 2026-10-24

**Both findings verified fixed within their reported scope. No new actionable defect found in this focused pass.** Only this tracker changed; generators, cleanup, adoption, and Ghidra were not run against real files.

- **CXR-008:** Exercised actual staging functions with all writes/deletions mocked. `make_stage()` creates a unique child and marker without enumerating or removing existing output contents. `discard_stage()` targets only the marked `stage_*` directory; it does nothing for an unmarked stage or `_personal_notes`. Actual `main()` sends generation and adoption to the fresh stage, never the existing parent output directory. Input/output overlap checks reject the config input directory, its child, and an output containing input directories; an independent output path is accepted.
- **CXR-009:** Exercised actual CSV readers and comparison using in-memory files. Both original malformed-row examples now fail with the offending file and record number: extra cells and missing cells. Valid `33` versus `33.0` still compares equal, and a changed repeated-key row still fails. `validate_staged()` rejects the malformed table.
- **Adoption gate:** With filesystem operations mocked, actual `main()` exits 1 with zero adoption calls for a failed generator, missing output, or malformed output. A complete, valid build takes the adoption path and exits 0. Cleanup targets the stage in all four cases.
- **Consistency:** Read-only `check_notes.py` reports 0 errors and 5 existing warnings. Inspected the added regression cases; Claude's reported 24-test and 27-table integration results were not rerun by Codex because those runs write fixtures/generated outputs.
- **Unchanged limits:** CXR-001/002 retain their documented engine-semantics assumptions. Mid-copy adoption rollback remains an acknowledged limitation, outside these two fixes. No additional rebuild is requested by this review.
