"""SafetyWatcher — monitors constraint results and fleet state for safety violations."""

from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from fleet_constraint.guard_runtime import ConstraintResult


class SafetyWatcher:
    """
    Safety monitor that watches constraint evaluation results and fleet state.

    Detects two critical conditions:
    1. PREMATURE_EMERGENCE: H1 is rising but ZHC (zero-homology consensus)
       has not yet been established — the fleet is forming but not coherent.
    2. CONSTRAINT_VIOLATED: any guard constraint has been violated.

    Usage:
        watcher = SafetyWatcher()
        alert = watcher.monitor(results, fleet_state)
        if alert:
            print(f"ALERT: {alert}")
    """

    def __init__(self, h1_rising_threshold: float = 0.5, zhc_consensus_threshold: float = 0.8):
        """
        Args:
            h1_rising_threshold: H1 value above which emergence is considered rising.
            zhc_consensus_threshold: ZHC value required for consensus to be established.
        """
        self.h1_rising_threshold = h1_rising_threshold
        self.zhc_consensus_threshold = zhc_consensus_threshold

    def monitor(
        self,
        constraint_results: List["ConstraintResult"],
        fleet_state: dict,
    ) -> Optional[str]:
        """
        Check constraint results and fleet state for safety violations.

        Args:
            constraint_results: List of ConstraintResult from GuardRuntime evaluation.
            fleet_state: Dict containing fleet state fields. Expected keys:
                - h1: H1 cohomology emergence score (float)
                - zhc: Zero-holonomy consensus value (float, 0.0–1.0)
                - phase: Current phase name (str)

        Returns:
            None if all clear.
            "PREMATURE_EMERGENCE: phase anomaly" if H1 rising but ZHC not established.
            "CONSTRAINT_VIOLATED: {name}" if a constraint is violated.
        """
        # Check constraint violations first
        for result in constraint_results:
            if result.violated():
                return f"CONSTRAINT_VIOLATED: {result.name}"

        # Check for premature emergence: H1 rising but ZHC not established
        h1 = fleet_state.get("h1", 0.0)
        zhc = fleet_state.get("zhc", 1.0)
        phase = fleet_state.get("phase", "UNKNOWN")

        h1_rising = h1 >= self.h1_rising_threshold
        zhc_established = zhc >= self.zhc_consensus_threshold

        if h1_rising and not zhc_established:
            return "PREMATURE_EMERGENCE: phase anomaly"

        return None
