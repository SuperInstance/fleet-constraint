"""Tests for SafetyWatcher — monitoring logic."""

import pytest
from fleet_constraint.safety_watcher import SafetyWatcher
from fleet_constraint.guard_runtime import ConstraintResult, ConstraintStatus


class TestSafetyWatcher:
    def test_all_clear(self):
        """When no constraints violated and H1/ZHC are fine, should return None."""
        watcher = SafetyWatcher()
        results = []
        fleet_state = {"h1": 0.1, "zhc": 0.9, "phase": "GUARD"}
        alert = watcher.monitor(results, fleet_state)
        assert alert is None

    def test_constraint_violated_alert(self):
        """Should return CONSTRAINT_VIOLATED when a constraint is violated."""
        watcher = SafetyWatcher()
        results = [
            ConstraintResult(name="h1_guard", status=ConstraintStatus.VIOLATED, tick=1),
        ]
        fleet_state = {"h1": 0.3, "zhc": 0.9, "phase": "GUARD"}
        alert = watcher.monitor(results, fleet_state)
        assert alert == "CONSTRAINT_VIOLATED: h1_guard"

    def test_premature_emergence_alert(self):
        """Should return PREMATURE_EMERGENCE when H1 rising but ZHC not established."""
        watcher = SafetyWatcher()
        results = []  # no constraint violations
        fleet_state = {"h1": 0.8, "zhc": 0.5, "phase": "EMERGE"}
        alert = watcher.monitor(results, fleet_state)
        assert alert == "PREMATURE_EMERGENCE: phase anomaly"

    def test_h1_at_threshold_but_zhc_ok(self):
        """H1 at threshold with ZHC established should be clear."""
        watcher = SafetyWatcher(h1_rising_threshold=0.5, zhc_consensus_threshold=0.8)
        results = []
        fleet_state = {"h1": 0.5, "zhc": 0.9, "phase": "GUARD"}
        alert = watcher.monitor(results, fleet_state)
        assert alert is None

    def test_multiple_violations_reports_first(self):
        """Multiple violations — should report the first one found."""
        watcher = SafetyWatcher()
        results = [
            ConstraintResult(name="first", status=ConstraintStatus.VIOLATED, tick=1),
            ConstraintResult(name="second", status=ConstraintStatus.VIOLATED, tick=1),
        ]
        fleet_state = {"h1": 0.3, "zhc": 0.9, "phase": "GUARD"}
        alert = watcher.monitor(results, fleet_state)
        assert "first" in alert
