"""
Tests for Phase 3 unified skill interface + planner (core/capabilities/skills.py).
"""

import pytest

from core.capabilities.skills import (
    FunctionSkill,
    PlanExecution,
    Skill,
    SkillPlan,
    SkillPlanner,
    SkillRegistry,
    SkillResult,
)


class UpperSkill(Skill):
    name = "upper"
    description = "uppercases text"

    def can_handle(self, request, context):
        return 1.0 if "upper" in request.lower() else 0.0

    def run(self, request, context):
        text = context.get("previous_output", request)
        return SkillResult(self.name, True, output=str(text).upper())


class ReverseSkill(Skill):
    name = "reverse"

    def can_handle(self, request, context):
        return 1.0 if "reverse" in request.lower() else 0.0

    def run(self, request, context):
        text = context.get("previous_output", request)
        return SkillResult(self.name, True, output=str(text)[::-1])


@pytest.fixture
def registry():
    r = SkillRegistry()
    r.register(UpperSkill())
    r.register(ReverseSkill())
    return r


class TestRegistry:
    def test_register_and_get(self, registry):
        assert registry.get("upper").name == "upper"
        assert len(registry.all()) == 2

    def test_match_ranks(self, registry):
        ranked = registry.match("please upper this")
        assert ranked[0][0].name == "upper"

    def test_best(self, registry):
        assert registry.best("reverse it").name == "reverse"

    def test_no_match(self, registry):
        assert registry.best("something unrelated") is None

    def test_unregister(self, registry):
        registry.unregister("upper")
        assert registry.get("upper") is None

    def test_register_requires_name(self):
        bad = UpperSkill()
        bad.name = ""
        with pytest.raises(ValueError):
            SkillRegistry().register(bad)


class TestFunctionSkill:
    def test_wraps_function(self):
        skill = FunctionSkill("echo", lambda req, ctx: req, keywords=["echo"])
        assert skill.can_handle("echo this", {}) > 0
        res = skill.run("echo this", {})
        assert res.success and res.output == "echo this"

    def test_function_error_is_caught(self):
        def boom(req, ctx):
            raise RuntimeError("nope")
        skill = FunctionSkill("boom", boom, keywords=["boom"])
        res = skill.run("boom", {})
        assert not res.success and "nope" in res.message


class TestPlanner:
    def test_single_step_plan(self, registry):
        planner = SkillPlanner(registry)
        plan = planner.plan("upper this")
        assert isinstance(plan, SkillPlan)
        assert len(plan) == 1
        assert plan.steps[0].skill == "upper"

    def test_multi_step_chain(self, registry):
        planner = SkillPlanner(registry)
        plan = planner.plan("upper the text then reverse it")
        assert len(plan) == 2
        assert plan.steps[0].skill == "upper"
        assert plan.steps[0].feed_forward is True
        assert plan.steps[1].skill == "reverse"

    def test_execute_feeds_output_forward(self, registry):
        planner = SkillPlanner(registry)
        execution = planner.run("upper hello then reverse it")
        assert isinstance(execution, PlanExecution)
        assert execution.success
        # "upper hello" -> "UPPER HELLO" -> reversed
        assert execution.final_output == "UPPER HELLO"[::-1]

    def test_execution_stops_on_failure(self, registry):
        class FailSkill(Skill):
            name = "fail"

            def can_handle(self, request, context):
                return 1.0 if "fail" in request else 0.0

            def run(self, request, context):
                return SkillResult(self.name, False, message="boom")

        registry.register(FailSkill())
        planner = SkillPlanner(registry)
        execution = planner.run("fail now then upper this")
        assert not execution.success
        assert len(execution.results) == 1

    def test_empty_plan_when_no_skill_matches(self, registry):
        planner = SkillPlanner(registry)
        plan = planner.plan("nothing matches here")
        assert len(plan) == 0
