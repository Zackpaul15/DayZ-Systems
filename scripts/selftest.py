"""Regression tests for the project tools, on small made-up fixtures (no game files needed).

usage: py -I scripts\\selftest.py

Covers the defects found in review (CODEX.md): the CSV comparator must see a changed non-first duplicate-key row, a removed
duplicate and an added column; a failed build must adopt nothing; recipe counts must be distinct recipes; the native match
flag needs an accepted class; the config resolver must honour explicit nested parents and refined top-level parents; recipe
methods must be resolved through the class chain. Prints one line per test and exits 1 on any failure.
"""
import csv
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


class CsvDiffTests(unittest.TestCase):
    def setUp(self):
        import csv_diff
        self.cd = csv_diff
        self.tmp = tempfile.mkdtemp()
        self.old = os.path.join(self.tmp, "old.csv")
        self.new = os.path.join(self.tmp, "new.csv")
        write_csv(self.old, ["zone", "hp"], [["Head", "33"], ["Torso", "100"], ["Torso", "125"]])

    def run_diff(self, header, rows):
        write_csv(self.new, header, rows)
        with mock.patch("sys.stdout", new=io.StringIO()):
            return self.cd.compare(self.old, self.new, "zone")

    def test_identical(self):
        self.assertTrue(self.run_diff(["zone", "hp"], [["Head", "33.0"], ["Torso", "100"], ["Torso", "125"]]))

    def test_changed_non_first_duplicate_key_row(self):
        self.assertFalse(self.run_diff(["zone", "hp"], [["Head", "33"], ["Torso", "100"], ["Torso", "999"]]))

    def test_removed_duplicate(self):
        self.assertFalse(self.run_diff(["zone", "hp"], [["Head", "33"], ["Torso", "100"]]))

    def test_added_column(self):
        self.assertFalse(self.run_diff(["zone", "hp", "extra"], [["Head", "33", "x"], ["Torso", "100", "x"], ["Torso", "125", "x"]]))

    def test_column_order(self):
        self.assertFalse(self.run_diff(["hp", "zone"], [["33", "Head"], ["100", "Torso"], ["125", "Torso"]]))


class BuildTablesTests(unittest.TestCase):
    def setUp(self):
        import build_tables
        self.bt = build_tables

    def test_failed_build_adopts_nothing(self):
        copies = []
        argv = ["build_tables.py", os.path.join(tempfile.gettempdir(), "boot_x"), "--out", os.path.join(tempfile.gettempdir(), "out_x"),
                "--adopt", "--only", "ammo,food"]
        with mock.patch.object(self.bt, "build", return_value=False), \
                mock.patch.object(self.bt.shutil, "copyfile", side_effect=lambda a, b: copies.append((a, b))), \
                mock.patch.object(self.bt, "make_stage", return_value=os.path.join(tempfile.gettempdir(), "stage_x")), \
                mock.patch.object(self.bt, "discard_stage"), mock.patch.object(self.bt, "validate_staged", return_value=True), mock.patch.object(self.bt, "check", return_value=True), \
                mock.patch.object(self.bt.os.path, "exists", return_value=True), \
                mock.patch("sys.argv", argv), mock.patch("sys.stdout", new=io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                self.bt.main()
        self.assertEqual(copies, [])
        self.assertEqual(cm.exception.code, 1)

    def test_missing_output_blocks_adoption(self):
        copies = []
        with tempfile.TemporaryDirectory() as out, mock.patch.object(self.bt.shutil, "copyfile", side_effect=lambda a, b: copies.append(b)), \
                mock.patch("sys.stdout", new=io.StringIO()):
            open(os.path.join(out, "ammo.csv"), "w").write("a\n1\n")
            self.assertFalse(self.bt.adopt(out, {"ammo", "food"}))
        self.assertEqual(copies, [])

    def test_unknown_table_name_rejected(self):
        with self.assertRaises(SystemExit):
            self.bt.select(["not_a_table"], False)

    def test_explicit_ghidra_table_without_flag_rejected(self):
        with self.assertRaises(SystemExit):
            self.bt.select(["native_api"], False)

    def test_check_fails_on_missing_output(self):
        with tempfile.TemporaryDirectory() as out, mock.patch("sys.stdout", new=io.StringIO()):
            self.assertFalse(self.bt.check(out, {"ammo"}))

    def run_main(self, out, extra, build_effect):
        boot = tempfile.mkdtemp()
        argv = ["build_tables.py", boot, "--out", out, "--only", "ammo"] + extra
        with mock.patch.object(self.bt, "build", side_effect=build_effect), \
                mock.patch.object(self.bt.shutil, "copyfile", side_effect=lambda a, b: self.copies.append(b)), \
                mock.patch("sys.argv", argv), mock.patch("sys.stdout", new=io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                self.bt.main()
        return cm.exception.code

    def test_cleanup_never_touches_unrelated_content(self):
        """CXR-008: an existing --out folder keeps its own CSVs and underscore folders, even when the run fails."""
        self.copies = []
        with tempfile.TemporaryDirectory() as out:
            for name in ("ammo.csv", "unrelated_budget.csv", "keep.txt"):
                open(os.path.join(out, name), "w").write("mine\n")
            os.makedirs(os.path.join(out, "_personal_notes"))
            open(os.path.join(out, "_personal_notes", "n.txt"), "w").write("mine\n")
            before = sorted(os.listdir(out))
            code = self.run_main(out, ["--check"], lambda *a, **k: False)
            self.assertEqual(code, 1)
            self.assertEqual(sorted(os.listdir(out)), before)  # nothing removed, no stage left behind
            self.assertEqual(open(os.path.join(out, "ammo.csv")).read(), "mine\n")
            self.assertTrue(os.path.exists(os.path.join(out, "_personal_notes", "n.txt")))

    def test_stage_is_not_taken_for_a_result(self):
        """A user file named like a table in --out is not mistaken for a generated table."""
        self.copies = []
        with tempfile.TemporaryDirectory() as out:
            open(os.path.join(out, "ammo.csv"), "w").write("a\n1\n")
            code = self.run_main(out, ["--adopt"], lambda *a, **k: True)  # generator "succeeds" but writes nothing
            self.assertEqual(code, 1)
            self.assertEqual(self.copies, [])

    def test_malformed_staged_output_blocks_adoption(self):
        """CXR-009: a regenerated row with the wrong cell count is rejected even in a build that otherwise succeeds."""
        self.copies = []

        def write_bad(boot, stage, game, requested, ghidra):
            with open(os.path.join(stage, "ammo.csv"), "w", newline="") as f:
                f.write("name,value\nA,1\nB,2,EXTRA\n")
            return True
        with tempfile.TemporaryDirectory() as out:
            code = self.run_main(out, ["--adopt"], write_bad)
            self.assertEqual(code, 1)
            self.assertEqual(self.copies, [])
            self.assertEqual(os.listdir(out), [])


class RowWidthTests(unittest.TestCase):
    def setUp(self):
        import csv_diff
        self.cd = csv_diff
        self.tmp = tempfile.mkdtemp()

    def pair(self, old_text, new_text):
        o, n = os.path.join(self.tmp, "o.csv"), os.path.join(self.tmp, "n.csv")
        open(o, "w", newline="").write(old_text)
        open(n, "w", newline="").write(new_text)
        with mock.patch("sys.stdout", new=io.StringIO()):
            return self.cd.compare(o, n, "k")

    def test_extra_cell_is_a_difference(self):
        self.assertFalse(self.pair("k,value\nA,33\n", "k,value\nA,33,EXTRA\n"))

    def test_missing_cell_is_a_difference(self):
        self.assertFalse(self.pair("k,value\nA,\n", "k,value\nA\n"))

    def test_validate_reports_file_and_row(self):
        p = os.path.join(self.tmp, "v.csv")
        open(p, "w", newline="").write("k,value\nA,1\nB\nC,1,2\n")
        bad = self.cd.row_width_problems(p)
        self.assertEqual([b[0] for b in bad], [3, 4])  # 1-based line numbers of the offending rows

    def test_well_formed_passes_and_numbers_still_normalise(self):
        self.assertTrue(self.pair("k,value\nA,33\nB,x\n", "k,value\nB,x\nA,33.0\n"))


class ItemsMasterTests(unittest.TestCase):
    def test_same_item_in_both_slots_counts_once(self):
        import items_master
        with tempfile.TemporaryDirectory() as d:
            cfgdir = os.path.join(d, "cfg")
            os.makedirs(cfgdir)
            json.dump({"CfgVehicles": {"Rag": {"__parent__": "Inventory_Base", "scope": 2},
                                       "Inventory_Base": {"__parent__": ""}}}, open(os.path.join(cfgdir, "a.json"), "w"))
            for n in ("clothing", "weapons", "food"):
                write_csv(os.path.join(d, n + ".csv"), ["name", "displayName"], [])
            for m in ("chernarus", "enoch", "nasdara", "sakhal"):
                write_csv(os.path.join(d, f"loot_types_{m}.csv"), ["name", "nominal", "category", "usage", "value", "lifetime"],
                          [["Rag", "5", "tools", "", "", "100"]])
            write_csv(os.path.join(d, "recipes.csv"), ["class", "registered", "ingredient1", "ingredient2", "results"],
                      [["CraftA", "yes", "Rag", "Rag", "Bandage"], ["CraftB", "yes", "Rag", "Stick", "Torch"],
                       ["CraftC", "no", "Rag", "Rag", "X"]])
            out = os.path.join(d, "im.csv")
            import cfgmodel
            with mock.patch("sys.argv", ["im", d, cfgdir, out]), mock.patch("sys.stdout", new=io.StringIO()),                     mock.patch.object(cfgmodel, "DIRS", [cfgdir]):
                items_master.main()
            row = next(r for r in csv.DictReader(open(out, encoding="utf-8")) if r["name"] == "Rag")
            self.assertEqual(row["recipes_as_ingredient_direct"], "2")  # CraftA once (both slots) + CraftB; CraftC is not live


class NativeApiTests(unittest.TestCase):
    def test_rejected_class_is_not_a_match(self):
        import native_api
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "scripts"))
            open(os.path.join(d, "scripts", "a.c"), "w").write(
                "class Alpha\n{\n proto native void One();\n proto native void Two();\n}\nclass Beta\n{\n proto native void Three();\n}\n")
            dec = os.path.join(d, "dec.txt")
            open(dec, "w").write(
                "\n=== decompile FUN_1aaaaaaaa ===\n"
                "void f(void) { FUN_1402724e0(a,b,\"One\",FUN_10,0); FUN_1402724e0(a,b,\"Two\",FUN_11,0); FUN_1402724e0(a,b,\"Zed1\",FUN_12,0);"
                " FUN_1402724e0(a,b,\"Zed2\",FUN_13,0); FUN_1402724e0(a,b,\"Zed3\",FUN_14,0); FUN_1402724e0(a,b,\"Zed4\",FUN_15,0);"
                " FUN_1402724e0(a,b,\"Zed5\",FUN_16,0); FUN_1402724e0(a,b,\"Zed6\",FUN_17,0); FUN_1402724e0(a,b,\"Zed7\",FUN_18,0);"
                " FUN_1402724e0(a,b,\"Zed8\",FUN_19,0); FUN_1402724e0(a,b,\"Zed9\",FUN_20,0); FUN_1402724e0(a,b,\"Zed10\",FUN_21,0);"
                " FUN_1402724e0(a,b,\"Zed11\",FUN_22,0); FUN_1402724e0(a,b,\"Zed12\",FUN_23,0); }\n"
                "\n=== decompile FUN_1bbbbbbbb ===\n"
                "void g(void) { FUN_1402724e0(a,b,\"Three\",FUN_30,0); FUN_1402724e0(a,b,\"Q1\",FUN_31,0); FUN_1402724e0(a,b,\"Q2\",FUN_32,0);"
                " FUN_1402724e0(a,b,\"Q3\",FUN_33,0); FUN_1402724e0(a,b,\"Q4\",FUN_34,0); FUN_1402724e0(a,b,\"Q5\",FUN_35,0);"
                " FUN_1402724e0(a,b,\"Q6\",FUN_36,0); FUN_1402724e0(a,b,\"Q7\",FUN_37,0); FUN_1402724e0(a,b,\"Q8\",FUN_38,0);"
                " FUN_1402724e0(a,b,\"Q9\",FUN_39,0); FUN_1402724e0(a,b,\"Q10\",FUN_40,0); FUN_1402724e0(a,b,\"Q11\",FUN_41,0);"
                " FUN_1402724e0(a,b,\"Q12\",FUN_42,0); FUN_1402724e0(a,b,\"Q13\",FUN_43,0); }\n")
            strs = os.path.join(d, "str.txt")
            open(strs, "w").write("")
            out = os.path.join(d, "n.csv")
            with mock.patch("sys.argv", ["na", dec, strs, os.path.join(d, "scripts"), out]), mock.patch("sys.stdout", new=io.StringIO()):
                native_api.main()
            with open(out, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            rejected = [r for r in rows if not r["script_class"]]
            self.assertTrue(rejected, "the fixture must produce a rejected attribution")
            for r in rejected:
                self.assertEqual(r["name_in_script_class"], "no", r)


class CfgModelTests(unittest.TestCase):
    def load(self, files):
        import cfgmodel
        d = tempfile.mkdtemp()
        for name, data in files.items():
            json.dump(data, open(os.path.join(d, name), "w"))
        with mock.patch.object(cfgmodel, "DIRS", [d]):
            return cfgmodel, cfgmodel.load()

    def test_explicit_nested_parent_with_inherited_same_name(self):
        cm, S = self.load({"a.json": {
            "CfgVehicles": {"__parent__": "",
                            "Base": {"__parent__": "", "AnimationSources": {"__parent__": "", "Own": {"__parent__": ""}}},
                            "Apple": {"__parent__": "Base", "AnimationSources": {"__parent__": "FoodAnimationSources"}}},
            "FoodAnimationSources": {"__parent__": "", "CS_Raw": {"__parent__": "", "x": 1}}}})
        r = cm.resolve(S["cfgvehicles"], "Apple", {})
        self.assertIn("CS_Raw", r["AnimationSources"])
        self.assertIn("Own", r["AnimationSources"])

    def test_sibling_nested_parent(self):
        cm, S = self.load({"a.json": {"CfgVehicles": {"__parent__": "", "Man": {"__parent__": "", "Zones": {
            "__parent__": "", "LeftArm": {"__parent__": "", "hp": 100}, "RightArm": {"__parent__": "LeftArm"}}}}}})
        r = cm.resolve(S["cfgvehicles"], "Man", {})
        self.assertEqual(r["Zones"]["RightArm"]["hp"], 100)

    def test_refined_top_level_parent(self):
        cm, S = self.load({
            "a.json": {"CfgVehicles": {"__parent__": "", "All": {"__parent__": ""}, "Man": {"__parent__": "All"}}},
            "b.json": {"CfgVehicles": {"__parent__": "", "AllVehicles": {"__parent__": "All", "tBody": 1}, "Man": {"__parent__": "AllVehicles"}}}})
        self.assertEqual(cm.chain(S["cfgvehicles"], "Man"), ["Man", "AllVehicles", "All"])
        self.assertEqual(cm.resolve(S["cfgvehicles"], "Man", {}).get("tBody"), 1)

    def test_unrelated_parents_are_reported(self):
        cm, S = self.load({
            "a.json": {"CfgX": {"__parent__": "", "A": {"__parent__": ""}, "B": {"__parent__": ""}, "K": {"__parent__": "A"}}},
            "b.json": {"CfgX": {"__parent__": "", "K": {"__parent__": "B"}}}})
        self.assertTrue(any(c["kind"] == "parent-unresolved" and c["class"] == "K" for c in cm.CONFLICTS))


class RecipeTests(unittest.TestCase):
    def test_effective_method_through_chain(self):
        import recipes
        classes = {"Base": {"parent": "RecipeBase", "do_body": "x.SetQuantity(1);", "can_body": "return false;"},
                   "Child": {"parent": "Base", "do_body": None, "can_body": None},
                   "Over": {"parent": "Base", "do_body": "super.Do(a); y.Delete();", "can_body": "return true;"}}
        self.assertEqual(recipes.effective(classes, "Child", "do_body", r"super\s*\.\s*Do\s*\(")[0], ["Base"])
        self.assertEqual(recipes.effective(classes, "Over", "do_body", r"super\s*\.\s*Do\s*\(")[0], ["Over", "Base"])
        self.assertEqual(recipes.effective(classes, "Over", "can_body", r"super\s*\.\s*CanDo\s*\(")[0], ["Over"])


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2).result
    sys.exit(0 if result.wasSuccessful() else 1)
