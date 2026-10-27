#!/usr/bin/env python3
"""Master test runner for Axioma Go verifying full application integrity.

Includes:
1. Core Go engine invariants (bounds, suicide, Ko rule, captures)
2. Functorial undo reversibility
3. All 6 canonical capturing showcases execution
4. Sovereign HTTP Server REST API endpoints
5. Telemetry dashboard integrity (HERM-005, zero-CDN, zero placeholder UUIDs)
"""

import unittest
from pathlib import Path
import sys

APP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = None
for parent in Path(__file__).resolve().parents:
    if (parent / "generations").is_dir() and (parent / "apps").is_dir():
        REPO_ROOT = parent
        break

for p in [APP_DIR, REPO_ROOT]:
    if p and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tests.test_go_engine import (
    TestCoordinatesAndBounds,
    TestOverlapAndSuicideInvariants,
    TestKoRuleLockout,
    TestCanonicalShowcasesExecution,
    TestFunctorialUndoReversibility,
    TestRestApiIntegration,
)
from tests.test_showcases import (
    TestShowcase01Snapback,
    TestShowcase02Ladder,
    TestShowcase03Geta,
    TestShowcase04CranesNest,
    TestShowcase05DoubleAtari,
    TestShowcase06IshiNoShita,
    TestShowcaseCatalogAndAPI,
    TestBuildShowcaseBoardAtStep,
)
from tests.test_server_and_ui import TestAxiomaGoServer
from tests.test_dashboard_integrity import TestGoDashboardIntegrity


def suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestCoordinatesAndBounds))
    suite.addTests(loader.loadTestsFromTestCase(TestOverlapAndSuicideInvariants))
    suite.addTests(loader.loadTestsFromTestCase(TestKoRuleLockout))
    suite.addTests(loader.loadTestsFromTestCase(TestCanonicalShowcasesExecution))
    suite.addTests(loader.loadTestsFromTestCase(TestFunctorialUndoReversibility))
    suite.addTests(loader.loadTestsFromTestCase(TestRestApiIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestShowcase01Snapback))
    suite.addTests(loader.loadTestsFromTestCase(TestShowcase02Ladder))
    suite.addTests(loader.loadTestsFromTestCase(TestShowcase03Geta))
    suite.addTests(loader.loadTestsFromTestCase(TestShowcase04CranesNest))
    suite.addTests(loader.loadTestsFromTestCase(TestShowcase05DoubleAtari))
    suite.addTests(loader.loadTestsFromTestCase(TestShowcase06IshiNoShita))
    suite.addTests(loader.loadTestsFromTestCase(TestShowcaseCatalogAndAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestBuildShowcaseBoardAtStep))
    suite.addTests(loader.loadTestsFromTestCase(TestAxiomaGoServer))
    suite.addTests(loader.loadTestsFromTestCase(TestGoDashboardIntegrity))
    return suite


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite())
    sys.exit(0 if result.wasSuccessful() else 1)
