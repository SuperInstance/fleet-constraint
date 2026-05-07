"""Tests for GuardRuntime — parsing and evaluation."""

import pytest
from fleet_constraint.guard_runtime import (
    parse_guard_line,
    GuardLine,
    GuardRuntime,
    ConstraintStatus,
    ConstraintResult,
)


class TestParseGuardLine:
    def test_basic_guard_line(self):
        line = parse_guard_line("h1_guard:h1:<:0.95:10")
        assert line.name == "h1_guard"
        assert line.var == "h1"
        assert line.op == "<"
        assert line.value == 0.95
        assert line.priority == 10
        assert line.condition == ""

    def test_guard_line_with_condition(self):
        line = parse_guard_line("zhc_guard:zhc:>=:0.85:5:if_phase_SYNC")
        assert line.name == "zhc_guard"
        assert line.var == "zhc"
        assert line.op == ">="
        assert line.value == 0.85
        assert line.priority == 5
        assert line.condition == "if_phase_SYNC"

    def test_guard_line_with_textual_ops(self):
        line = parse_guard_line("tempo_check:tempo:gt:0.5:3")
        assert line.op == ">"

    def test_guard_line_with_eq_ne(self):
        line_eq = parse_guard_line("phase_check:phase:eq:2:1")
        assert line_eq.op == "=="

        line_ne = parse_guard_line("mode_check:mode:ne:0:1")
        assert line_ne.op == "!="

    def test_guard_line_comment_skipped(self):
        # parse_guard_line raises on comment lines
        with pytest.raises(ValueError):
            parse_guard_line("# this is a comment")

    def test_guard_line_empty_raises(self):
        with pytest.raises(ValueError):
            parse_guard_line("")

    def test_guard_line_invalid_fields_raises(self):
        with pytest.raises(ValueError):
            parse_guard_line("only_one_field")

    def test_guard_line_invalid_value_raises(self):
        with pytest.raises(ValueError):
            parse_guard_line("bad_val:x:>:not_a_number:1")

    def test_guard_line_invalid_op_raises(self):
        with pytest.raises(ValueError):
            parse_guard_line("bad_op:y:~:0.5:1")


class TestGuardRuntime:
    def test_load_file(self, tmp_path):
        guard_file = tmp_path / "test.guard"
        guard_file.write_text(
            "h1_guard:h1:<:0.95:10\n"
            "# comment line\n"
            "zhc_guard:zhc:>=:0.85:5:if_phase_SYNC\n"
        )
        runtime = GuardRuntime()
        lines = runtime.load_file(str(guard_file))
        assert len(lines) == 2
        assert lines[0].name == "h1_guard"
        assert lines[1].name == "zhc_guard"

    def test_evaluate_satisfied(self):
        runtime = GuardRuntime()
        lines = [
            GuardLine(name="tempo_check", var="tempo", op=">", value=0.5, priority=1, condition=""),
        ]
        context = {"tempo": 0.8}
        results = runtime.evaluate(lines, context)
        assert len(results) == 1
        assert results[0][0].name == "tempo_check"
        assert results[0][1] is True

    def test_evaluate_violated(self):
        runtime = GuardRuntime()
        lines = [
            GuardLine(name="tempo_check", var="tempo", op=">", value=0.5, priority=1, condition=""),
        ]
        context = {"tempo": 0.3}
        results = runtime.evaluate(lines, context)
        assert results[0][1] is False

    def test_evaluate_missing_var_pending(self):
        runtime = GuardRuntime()
        lines = [
            GuardLine(name="drift_check", var="drift", op="<", value=0.1, priority=1, condition=""),
        ]
        # drift not in context
        context = {"tempo": 0.8}
        results = runtime.evaluate(lines, context)
        # Missing variable treated as not satisfied (pending)
        assert results[0][1] is False

    def test_compile_to_fluxc(self):
        runtime = GuardRuntime()
        lines = [
            GuardLine(name="h1_check", var="h1", op="<", value=0.95, priority=3, condition=""),
        ]
        ops = runtime.compile_to_fluxc(lines)
        assert "LOAD h1" in ops
        assert "PUSH 0.95" in ops
        assert "CHECK <" in ops


class TestConstraintResult:
    def test_satisfied(self):
        cr = ConstraintResult(name="test", status=ConstraintStatus.SATISFIED, tick=1)
        assert cr.satisfied() is True
        assert cr.violated() is False
        assert cr.pending() is False

    def test_violated(self):
        cr = ConstraintResult(name="test", status=ConstraintStatus.VIOLATED, tick=1)
        assert cr.satisfied() is False
        assert cr.violated() is True

    def test_pending(self):
        cr = ConstraintResult(name="test", status=ConstraintStatus.PENDING, tick=1)
        assert cr.pending() is True
