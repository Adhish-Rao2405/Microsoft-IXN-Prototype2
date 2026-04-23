"""Tests for src.brain.action_schema – schema definitions & validation."""

import unittest

from src.brain.action_schema import (
    ALLOWED_TOOLS,
    ALLOWED_WORKCELL_ACTIONS,
    TOOL_SCHEMAS,
    WORKCELL_ACTION_SCHEMAS,
    schema_prompt_block,
    validate_plan,
    validate_workcell_plan,
)


class TestToolSchemas(unittest.TestCase):
    """Verify the schema catalogue is internally consistent."""

    EXPECTED_TOOLS = {
        "move_ee", "open_gripper", "close_gripper",
        "pick", "place", "reset", "describe_scene",
    }

    def test_allowed_tools_match_schemas(self):
        self.assertEqual(ALLOWED_TOOLS, set(TOOL_SCHEMAS.keys()))

    def test_expected_tools_present(self):
        self.assertEqual(self.EXPECTED_TOOLS, ALLOWED_TOOLS)

    def test_each_schema_has_description(self):
        for name, info in TOOL_SCHEMAS.items():
            self.assertIn("description", info, f"{name} missing description")

    def test_each_schema_has_args_dict(self):
        for name, info in TOOL_SCHEMAS.items():
            self.assertIsInstance(info.get("args"), dict, f"{name} args must be a dict")


class TestSchemaPromptBlock(unittest.TestCase):
    def test_contains_all_tool_names(self):
        block = schema_prompt_block()
        for name in ALLOWED_TOOLS:
            self.assertIn(name, block)


class TestValidatePlanSingleAction(unittest.TestCase):
    """Validation of single-action payloads."""

    def test_valid_move_ee(self):
        raw = {"tool": "move_ee", "args": {"target_xyz": [0.5, 0.0, 0.5]}}
        result = validate_plan(raw)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tool"], "move_ee")
        self.assertEqual(result[0]["args"]["target_xyz"], [0.5, 0.0, 0.5])

    def test_valid_pick(self):
        raw = {"type": "action", "tool": "pick", "args": {"object": "cube_1"}}
        result = validate_plan(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result[0]["args"]["object"], "cube_1")

    def test_valid_reset(self):
        result = validate_plan({"tool": "reset", "args": {}})
        self.assertIsNotNone(result)
        self.assertEqual(result[0]["tool"], "reset")

    def test_valid_describe_scene(self):
        result = validate_plan({"tool": "describe_scene", "args": {}})
        self.assertIsNotNone(result)

    def test_open_gripper_defaults(self):
        result = validate_plan({"tool": "open_gripper", "args": {}})
        self.assertIsNotNone(result)
        self.assertEqual(result[0]["args"]["width"], 0.04)

    def test_close_gripper_custom_force(self):
        result = validate_plan({"tool": "close_gripper", "args": {"force": 60.0}})
        self.assertIsNotNone(result)
        self.assertEqual(result[0]["args"]["force"], 60.0)


class TestValidatePlanMultiStep(unittest.TestCase):
    """Validation of multi-step plan payloads."""

    def test_valid_plan(self):
        raw = {
            "type": "plan",
            "actions": [
                {"tool": "describe_scene", "args": {}},
                {"tool": "pick", "args": {"object": "cube_1"}},
                {"tool": "place", "args": {"target_xyz": [0.3, 0.2, 0.65]}},
            ],
        }
        result = validate_plan(raw)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)

    def test_plan_rejects_if_any_action_invalid(self):
        raw = {
            "type": "plan",
            "actions": [
                {"tool": "pick", "args": {"object": "cube_1"}},
                {"tool": "fly_away", "args": {}},  # unknown tool
            ],
        }
        self.assertIsNone(validate_plan(raw))


class TestValidatePlanRejections(unittest.TestCase):
    """Payloads that must be rejected."""

    def test_unknown_tool(self):
        self.assertIsNone(validate_plan({"tool": "explode", "args": {}}))

    def test_missing_required_arg(self):
        self.assertIsNone(validate_plan({"tool": "pick", "args": {}}))

    def test_wrong_xyz_length(self):
        raw = {"tool": "move_ee", "args": {"target_xyz": [0.5, 0.0]}}
        self.assertIsNone(validate_plan(raw))

    def test_non_dict_input(self):
        self.assertIsNone(validate_plan(42))

    def test_string_json_input(self):
        import json
        raw = json.dumps({"tool": "reset", "args": {}})
        result = validate_plan(raw)
        self.assertIsNotNone(result)

    def test_invalid_json_string(self):
        self.assertIsNone(validate_plan("{not valid json"))

    def test_non_dict_args(self):
        self.assertIsNone(validate_plan({"tool": "reset", "args": "bad"}))

    def test_plan_with_non_list_actions(self):
        self.assertIsNone(validate_plan({"type": "plan", "actions": "bad"}))


if __name__ == "__main__":
    unittest.main()


# ── Workcell schema tests (Phase 3) ─────────────────────────────────


class TestWorkcellActionSchemas(unittest.TestCase):
    EXPECTED_ACTIONS = {
        "inspect_workcell", "start_conveyor", "stop_conveyor",
        "wait", "pick_target", "place_in_bin", "reset_workcell",
    }

    def test_expected_actions_present(self):
        self.assertEqual(self.EXPECTED_ACTIONS, ALLOWED_WORKCELL_ACTIONS)

    def test_allowed_set_matches_schema_dict(self):
        self.assertEqual(ALLOWED_WORKCELL_ACTIONS, set(WORKCELL_ACTION_SCHEMAS.keys()))

    def test_each_schema_has_description(self):
        for name, info in WORKCELL_ACTION_SCHEMAS.items():
            self.assertIn("description", info, f"{name} missing description")

    def test_each_schema_has_required_params_list(self):
        for name, info in WORKCELL_ACTION_SCHEMAS.items():
            self.assertIsInstance(info.get("required_params"), list, f"{name} missing required_params")

    def test_each_schema_has_param_types_dict(self):
        for name, info in WORKCELL_ACTION_SCHEMAS.items():
            self.assertIsInstance(info.get("param_types"), dict, f"{name} missing param_types")

    def test_workcell_actions_not_in_legacy_tools(self):
        self.assertTrue(ALLOWED_WORKCELL_ACTIONS.isdisjoint(ALLOWED_TOOLS))


class TestValidateWorkcellPlanValid(unittest.TestCase):
    def test_inspect_workcell(self):
        raw = {"actions": [{"action": "inspect_workcell", "parameters": {}}]}
        result = validate_workcell_plan(raw)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["action"], "inspect_workcell")
        self.assertEqual(result[0]["parameters"], {})

    def test_start_conveyor(self):
        raw = {"actions": [{"action": "start_conveyor", "parameters": {"speed": 0.5}}]}
        result = validate_workcell_plan(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result[0]["parameters"]["speed"], 0.5)

    def test_stop_conveyor(self):
        raw = {"actions": [{"action": "stop_conveyor", "parameters": {}}]}
        self.assertIsNotNone(validate_workcell_plan(raw))

    def test_wait(self):
        raw = {"actions": [{"action": "wait", "parameters": {"seconds": 2.0}}]}
        result = validate_workcell_plan(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result[0]["parameters"]["seconds"], 2.0)

    def test_pick_target(self):
        raw = {"actions": [{"action": "pick_target", "parameters": {"object_id": "obj_1"}}]}
        result = validate_workcell_plan(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result[0]["parameters"]["object_id"], "obj_1")

    def test_place_in_bin(self):
        raw = {"actions": [{"action": "place_in_bin", "parameters": {"bin_id": "bin_a"}}]}
        result = validate_workcell_plan(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result[0]["parameters"]["bin_id"], "bin_a")

    def test_reset_workcell(self):
        raw = {"actions": [{"action": "reset_workcell", "parameters": {}}]}
        self.assertIsNotNone(validate_workcell_plan(raw))

    def test_multi_action_plan(self):
        raw = {"actions": [
            {"action": "stop_conveyor", "parameters": {}},
            {"action": "pick_target", "parameters": {"object_id": "obj_1"}},
            {"action": "place_in_bin", "parameters": {"bin_id": "bin_a"}},
            {"action": "start_conveyor", "parameters": {"speed": 0.3}},
        ]}
        result = validate_workcell_plan(raw)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 4)

    def test_speed_coerced_to_float(self):
        raw = {"actions": [{"action": "start_conveyor", "parameters": {"speed": 1}}]}
        result = validate_workcell_plan(raw)
        self.assertIsNotNone(result)
        self.assertIsInstance(result[0]["parameters"]["speed"], float)

    def test_seconds_coerced_to_float(self):
        raw = {"actions": [{"action": "wait", "parameters": {"seconds": 3}}]}
        result = validate_workcell_plan(raw)
        self.assertIsNotNone(result)
        self.assertIsInstance(result[0]["parameters"]["seconds"], float)


class TestValidateWorkcellPlanRejections(unittest.TestCase):
    def test_unknown_action(self):
        raw = {"actions": [{"action": "fly_away", "parameters": {}}]}
        self.assertIsNone(validate_workcell_plan(raw))

    def test_missing_required_param_speed(self):
        raw = {"actions": [{"action": "start_conveyor", "parameters": {}}]}
        self.assertIsNone(validate_workcell_plan(raw))

    def test_missing_required_param_seconds(self):
        raw = {"actions": [{"action": "wait", "parameters": {}}]}
        self.assertIsNone(validate_workcell_plan(raw))

    def test_missing_required_param_object_id(self):
        raw = {"actions": [{"action": "pick_target", "parameters": {}}]}
        self.assertIsNone(validate_workcell_plan(raw))

    def test_missing_required_param_bin_id(self):
        raw = {"actions": [{"action": "place_in_bin", "parameters": {}}]}
        self.assertIsNone(validate_workcell_plan(raw))

    def test_extra_key_in_action(self):
        raw = {"actions": [{"action": "stop_conveyor", "parameters": {}, "sneaky": True}]}
        self.assertIsNone(validate_workcell_plan(raw))

    def test_extra_parameter_key(self):
        raw = {"actions": [{"action": "stop_conveyor", "parameters": {"extra": 1}}]}
        self.assertIsNone(validate_workcell_plan(raw))

    def test_empty_actions_list(self):
        raw = {"actions": []}
        self.assertIsNone(validate_workcell_plan(raw))

    def test_missing_actions_key(self):
        raw = {"action": "stop_conveyor", "parameters": {}}
        self.assertIsNone(validate_workcell_plan(raw))

    def test_non_dict_input(self):
        self.assertIsNone(validate_workcell_plan(42))

    def test_invalid_json_string(self):
        self.assertIsNone(validate_workcell_plan("{bad json"))

    def test_one_invalid_action_rejects_whole_plan(self):
        raw = {"actions": [
            {"action": "stop_conveyor", "parameters": {}},
            {"action": "explode", "parameters": {}},
        ]}
        self.assertIsNone(validate_workcell_plan(raw))

    def test_non_dict_parameters(self):
        raw = {"actions": [{"action": "stop_conveyor", "parameters": "bad"}]}
        self.assertIsNone(validate_workcell_plan(raw))

    def test_rejects_string_speed(self):
        raw = {"actions": [{"action": "start_conveyor", "parameters": {"speed": "1.0"}}]}
        self.assertIsNone(validate_workcell_plan(raw))

    def test_rejects_string_seconds(self):
        raw = {"actions": [{"action": "wait", "parameters": {"seconds": "2"}}]}
        self.assertIsNone(validate_workcell_plan(raw))
