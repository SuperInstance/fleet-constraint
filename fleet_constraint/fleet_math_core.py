"""FleetMathCore — Python wrapper around fleet_agent.fleet_math primitives."""

from typing import Tuple, List
import numpy as np

from fleet_agent.fleet_math import (
    EmergenceDetector,
    HolonomyConsensus,
    encode_pythagorean48,
    decode_pythagorean48,
)


class FleetMathCore:
    """
    Unified wrapper for fleet-agent math primitives.

    Wraps:
    - EmergenceDetector: H1 cohomological emergence detection
    - HolonomyConsensus: zero-holonomy consensus computation
    - encode/decode_pythagorean48: trust vector encoding

    Usage:
        core = FleetMathCore()
        h1, zhc_ok, p48 = core.evaluate(V=10, E=17, trust_vector=[0.9, 0.1, ...])
    """

    def __init__(self):
        self.emergence_detector = EmergenceDetector()
        self.holonomy_consensus = HolonomyConsensus()

    def evaluate(
        self,
        V: int,
        E: int,
        trust_vector: List[float],
    ) -> Tuple[float, bool, str]:
        """
        Evaluate fleet math primitives for a given graph state.

        Args:
            V: number of vertices in the fleet graph
            E: number of edges (connections) in the fleet graph
            trust_vector: list of trust values, one per vertex (0.0–1.0)

        Returns:
            Tuple of:
            - h1: H1 cohomology score (emergence indicator)
            - zhc_ok: True if zero-holonomy consensus is reached
            - pythagorean48_encoded: base64-ish string encoding of the trust vector
        """
        # Build the fleet graph from V and E
        # Generate synthetic edges for the detector
        vertices = [f"agent-{i}" for i in range(V)]
        # Generate E edges in a round-robin fashion (simple connectivity model)
        edges: List[Tuple[str, str]] = []
        for i in range(E):
            a = vertices[i % V]
            b = vertices[(i + 1) % V]
            edges.append((a, b))

        # Update emergence detector
        self.emergence_detector.update(vertices, edges)
        h1 = float(self.emergence_detector.h1)

        # Update holonomy consensus
        # Map trust_vector to tile holonomy values
        self.holonomy_consensus.tiles.clear()
        for i, tv in enumerate(trust_vector[:V]):
            tile_id = i
            holonomy = tv  # trust maps directly to holonomy
            self.holonomy_consensus.add_tile(tile_id, holonomy)

        # Check consensus on trivial cycles (all vertices connected)
        cycles: List[List[int]] = [[i for i in range(V)]]
        zhc_ok = self.holonomy_consensus.check_consensus(cycles)

        # Encode trust vector as Pythagorean48
        if trust_vector:
            # Take first two dimensions for Pythagorean48 encoding
            x = trust_vector[0] if len(trust_vector) > 0 else 0.0
            y = trust_vector[1] if len(trust_vector) > 1 else 0.0
            pyth_idx = encode_pythagorean48(x, y)
        else:
            pyth_idx = 0

        pyth_decoded = decode_pythagorean48(pyth_idx)
        pyth_str = f"{pyth_idx}@({pyth_decoded[0]:.4f},{pyth_decoded[1]:.4f})"

        return h1, zhc_ok, pyth_str
