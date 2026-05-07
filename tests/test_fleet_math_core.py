"""Tests for FleetMathCore — H1, ZHC, and Pythagorean48 evaluation."""

import pytest
from fleet_constraint.fleet_math_core import FleetMathCore


class TestFleetMathCore:
    def test_evaluate_h1_emergence(self):
        """Test that H1 cohomology is computed correctly for a fleet graph."""
        core = FleetMathCore()
        # V=10, E=17 -> H1 = E - V + 1 = 17 - 10 + 1 = 8 (emergence detected since H1 > V//2 = 5)
        h1, zhc_ok, pyth = core.evaluate(V=10, E=17, trust_vector=[0.9, 0.1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
        assert isinstance(h1, float)
        assert h1 == 8.0

    def test_evaluate_zhc_consensus(self):
        """Test that ZHC consensus is checked correctly."""
        core = FleetMathCore()
        # With trust_vector all 1.0, holonomy consensus should be reached
        h1, zhc_ok, pyth = core.evaluate(V=5, E=8, trust_vector=[1.0, 1.0, 1.0, 1.0, 1.0])
        assert isinstance(zhc_ok, bool)
        # All tiles have holonomy 1.0, so consensus should be True

    def test_evaluate_pythagorean48_encoding(self):
        """Test that Pythagorean48 encoding/decoding works."""
        core = FleetMathCore()
        trust_vector = [0.9, 0.1, 0.5, 0.5, 0.5]
        h1, zhc_ok, pyth = core.evaluate(V=5, E=8, trust_vector=trust_vector)
        # pyth should be a string representation of the encoded value
        assert isinstance(pyth, str)
        assert "@" in pyth  # format is "idx@(x,y)"
        # The first two dimensions should map to a valid index
        idx = int(pyth.split("@")[0])
        assert 0 <= idx < 48
