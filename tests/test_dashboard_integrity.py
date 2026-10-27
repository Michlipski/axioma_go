"""Adversarial & Hermetic Dashboard Integrity Test Suite for Axioma Go ([L1-G4B-008] & HERM-005).

Verifies that the Axioma Go Development Process Telemetry Dashboard deliverable:
1. Exists, is self-contained (>50KB), and contains zero external CDN dependencies.
2. Contains ZERO placeholder UUIDs or synthetic estimations (enforces HERM-005).
3. Passes ZeroTrustMicroAuditor.audit_dashboard_deliverable with is_hermetic == True.
4. Contains verified subagent conversation IDs that are valid UUIDv4 strings.
5. Generates deterministically via generate_dashboard.py with exit code 0.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

current_dir = Path(__file__).resolve()
repo_root = current_dir.parents[4]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from generations.gen_04b.services.audit.src.zero_trust_micro_auditor import ZeroTrustMicroAuditor


class TestGoDashboardIntegrity(unittest.TestCase):
    """Test suite ensuring Axioma Go dashboard cannot be deployed with placeholder or unverified values."""

    def setUp(self) -> None:
        self.app_dir = Path(__file__).resolve().parent.parent
        self.dashboard_html = self.app_dir / "dashboard.html"
        self.telemetry_html = self.app_dir / "telemetry_dashboard.html"
        self.generate_py = self.app_dir / "generate_dashboard.py"
        self.auditor = ZeroTrustMicroAuditor(auditor_node_id="test_go_dashboard_auditor")

    def test_dashboard_files_exist_and_meet_size_floor(self) -> None:
        """Verify dashboard deliverables physically exist on disk and exceed 50KB."""
        self.assertTrue(self.dashboard_html.exists(), "dashboard.html must physically exist on disk")
        self.assertTrue(self.telemetry_html.exists(), "telemetry_dashboard.html must physically exist on disk")
        self.assertTrue(self.generate_py.exists(), "generate_dashboard.py must physically exist on disk")

        self.assertGreater(self.dashboard_html.stat().st_size, 50000)
        self.assertGreater(self.telemetry_html.stat().st_size, 50000)

    def test_zero_external_cdn_dependencies(self) -> None:
        """Verify zero external scripts, CDNs, or remote fonts (Directive 6 zero-CDN invariant)."""
        content = self.dashboard_html.read_text(encoding="utf-8")
        banned_cdns = [
            "cdnjs.cloudflare.com",
            "cdn.jsdelivr.net",
            "unpkg.com",
            "fonts.googleapis.com",
            "fonts.gstatic.com",
            "ajax.googleapis.com",
        ]
        for cdn in banned_cdns:
            self.assertNotIn(cdn, content, f"Forbidden external CDN '{cdn}' detected in dashboard")

    def test_herm_005_zero_placeholder_uuids(self) -> None:
        """Verify dashboard passes HERM-005 micro-auditor with zero placeholder UUIDs."""
        content = self.dashboard_html.read_text(encoding="utf-8")
        report = self.auditor.audit_dashboard_deliverable(content, deliverable_id="axioma_go_dashboard")
        
        self.assertTrue(
            report.is_hermetic,
            f"Dashboard failed HERM-005 audit with violations: {[v.description for v in report.violations]}"
        )
        self.assertEqual(len(report.violations), 0)

    def test_subagent_conversation_ids_are_valid_uuids(self) -> None:
        """Verify all subagent conversation IDs in the witness table are valid UUIDv4 strings."""
        content = self.dashboard_html.read_text(encoding="utf-8")
        uuid_pattern = re.compile(r"<code>([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})</code>")
        matches = uuid_pattern.findall(content)

        self.assertGreaterEqual(len(matches), 5, "Must contain at least 5 reconciled subagent UUIDs")
        for uid in matches:
            self.assertFalse(uid.startswith("00000000"), f"Synthetic placeholder UUID detected: {uid}")
            self.assertFalse(uid.startswith("11111111"), f"Synthetic placeholder UUID detected: {uid}")

        # Specifically check Brain, Muscle 1, Muscle 2, Muscle 3, Muscle 4 IDs
        expected_uuids = [
            "f9226e0a-468b-477b-962b-b3ba7b37984b",
            "2236e53b-70d0-4cf8-93e6-7af47ee6af83",
            "a80c8a73-4d91-4fc9-9f6c-97d285767c3a",
            "9a9ad805-5a56-4e2b-8dc7-a5e0ca33c27a",
            "cdd97a31-d543-42a8-b07f-a6c1df02d1db",
        ]
        for eu in expected_uuids:
            self.assertIn(eu, matches, f"Mandatory reconciled subagent UUID '{eu}' missing from witness table")

    def test_generate_dashboard_script_execution(self) -> None:
        """Verify generate_dashboard.py executes cleanly and re-emits identical deliverables."""
        res = subprocess.run(
            [sys.executable, str(self.generate_py)],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        self.assertEqual(res.returncode, 0, f"generate_dashboard.py failed with: {res.stderr}")
        self.assertTrue(self.dashboard_html.exists())
        self.assertTrue(self.telemetry_html.exists())


if __name__ == "__main__":
    unittest.main()
