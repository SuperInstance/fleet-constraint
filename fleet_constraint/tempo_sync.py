"""TempoSync — wraps crystal_sync via subprocess + JSON interface."""

import json
import subprocess
import os
from typing import Dict, Optional


CRYSTAL_SYNC_BIN = os.environ.get("CRYSTAL_SYNC_BIN", "crystal_sync")


class TempoSync:
    """
    Time synchronization wrapper that calls crystal_sync as a subprocess.

    crystal_sync is expected to emit JSON on stdout when invoked with
    appropriate subcommands (phase-offsets, coherence, etc.).

    If crystal_sync is not available, returns sensible defaults (no drift).

    Usage:
        ts = TempoSync()
        offsets = ts.read_phase_offsets()
        drift = ts.check_coherence(offsets)
    """

    def __init__(self, crystal_sync_path: Optional[str] = None):
        self.crystal_path = crystal_sync_path or CRYSTAL_SYNC_BIN

    def _run(self, *args: str) -> Optional[Dict]:
        """Run crystal_sync with given arguments, return parsed JSON or None."""
        try:
            result = subprocess.run(
                [self.crystal_path] + list(args),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None
            return json.loads(result.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            return None

    def read_phase_offsets(self) -> Dict[str, int]:
        """
        Read phase offsets for all agents from crystal_sync.

        Returns:
            Dict mapping agent_id -> phase offset (int64 microseconds).
            Returns empty dict if crystal_sync is unavailable.
        """
        result = self._run("phase-offsets", "--format", "json")
        if result and "offsets" in result:
            return result["offsets"]
        # Return empty/default if crystal_sync unavailable
        return {}

    def check_coherence(self, offsets: Dict[str, int]) -> float:
        """
        Compute phase coherence drift across all agents.

        Args:
            offsets: Dict mapping agent_id -> phase offset (microseconds)

        Returns:
            Float >= 0.0 indicating max drift between any two agents.
            0.0 = perfect coherence (no drift).
            > 0 = drift detected.
        """
        if not offsets:
            return 0.0
        values = list(offsets.values())
        if len(values) <= 1:
            return 0.0
        return float(max(values) - min(values)) / 1e6  # convert µs to seconds
