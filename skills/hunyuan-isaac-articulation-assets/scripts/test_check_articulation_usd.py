#!/usr/bin/env python3
"""Fast, dependency-free tests for the checker’s graph and report helpers.

Full USD fixtures must be run with Isaac Kit Python because this machine does
not ship the ``pxr`` modules.  These tests still catch topology regressions
without requiring an Isaac installation.
"""

import importlib.util
import sys
import unittest
from collections import defaultdict
from pathlib import Path


SCRIPT = Path(__file__).with_name("check_articulation_usd.py")
SPEC = importlib.util.spec_from_file_location("check_articulation_usd", str(SCRIPT))
CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKER
SPEC.loader.exec_module(CHECKER)


class CheckerHelperTests(unittest.TestCase):
    def test_valid_tree_is_acyclic_and_reachable(self):
        children = defaultdict(list)
        children["/Asset/Base"].extend(["/Asset/Door", "/Asset/Panel"])
        children["/Asset/Panel"].append("/Asset/Button")
        nodes = {"/Asset/Base", "/Asset/Door", "/Asset/Panel", "/Asset/Button"}

        cycle, cycle_nodes = CHECKER.detect_cycle(nodes, children)

        self.assertFalse(cycle)
        self.assertEqual(cycle_nodes, [])
        self.assertEqual(CHECKER.reachable_from("/Asset/Base", children), nodes)

    def test_cycle_is_detected(self):
        children = defaultdict(list)
        children["/Asset/A"].append("/Asset/B")
        children["/Asset/B"].append("/Asset/C")
        children["/Asset/C"].append("/Asset/A")

        cycle, cycle_nodes = CHECKER.detect_cycle(
            {"/Asset/A", "/Asset/B", "/Asset/C"}, children
        )

        self.assertTrue(cycle)
        self.assertTrue(cycle_nodes)

    def test_scope_boundary_is_exact(self):
        self.assertTrue(CHECKER.within_scope("/World/Asset/Links/Base", "/World/Asset"))
        self.assertTrue(CHECKER.within_scope("/World/Asset", "/World/Asset"))
        self.assertFalse(CHECKER.within_scope("/World/Asset2/Links/Base", "/World/Asset"))

    def test_negative_scale_components(self):
        self.assertEqual(CHECKER.scalar_components((-1, 2, 3)), [-1.0, 2.0, 3.0])
        self.assertEqual(CHECKER.scalar_components(2), [2.0])
        self.assertEqual(CHECKER.scalar_components(None), [])

    def test_report_shape_is_stable(self):
        report = CHECKER.new_report("/World/Asset", "fixed")
        self.assertEqual(
            set(report),
            {
                "status",
                "asset_root",
                "mode",
                "articulation_root_count",
                "articulation_root",
                "checks",
                "metrics",
            },
        )
        self.assertEqual(report["status"], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
