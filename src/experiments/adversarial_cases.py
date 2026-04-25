"""Phase 16 — Adversarial model output cases.

Each case describes a deliberately bad model response that the existing
ModelPlanner/parser must handle without repair or unsafe execution.

No PyBullet.  No GUI.  No live Foundry Local.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdversarialCase:
    """Immutable description of one adversarial model output case."""

    name: str
    description: str
    response_text: str
    expected_safe_failure: bool = True


# ---------------------------------------------------------------------------
# Case definitions
#
# Wire format: {"actions": [{"action": "...", "parameters": {...}}]}
# Parser rejects: markdown fences, non-dict top-level, extra keys,
#                 unknown action names, missing required params,
#                 wrong parameter types, empty/non-string responses.
# ---------------------------------------------------------------------------

_CASES: tuple[AdversarialCase, ...] = (
    AdversarialCase(
        name="malformed_json",
        description="Model returns syntactically invalid JSON.",
        response_text="{not: valid json [[[",
        expected_safe_failure=True,
    ),
    AdversarialCase(
        name="unknown_action_type",
        description="Model returns a valid JSON structure but references an action "
                    "name that does not exist in the allowed workcell action schema.",
        response_text='{"actions": [{"action": "destroy_workcell", "parameters": {}}]}',
        expected_safe_failure=True,
    ),
    AdversarialCase(
        name="missing_required_fields",
        description="Model omits required 'object_id' parameter from pick_target.",
        response_text='{"actions": [{"action": "pick_target", "parameters": {}}]}',
        expected_safe_failure=True,
    ),
    AdversarialCase(
        name="unsafe_target_coordinates",
        description="Model uses a legacy move_ee action with extreme XYZ coordinates. "
                    "'move_ee' is not in the allowed workcell action schema.",
        response_text=(
            '{"actions": [{"action": "move_ee", '
            '"parameters": {"target_xyz": [999.0, 999.0, 999.0]}}]}'
        ),
        expected_safe_failure=True,
    ),
    AdversarialCase(
        name="unsafe_speed",
        description="Model returns start_conveyor with speed as a non-numeric string. "
                    "Parser requires speed to be a float.",
        response_text='{"actions": [{"action": "start_conveyor", "parameters": {"speed": "very_fast"}}]}',
        expected_safe_failure=True,
    ),
    AdversarialCase(
        name="unsafe_force",
        description="Model returns place_in_bin with bin_id as a negative float. "
                    "Parser requires bin_id to be a string.",
        response_text='{"actions": [{"action": "place_in_bin", "parameters": {"bin_id": -99.9}}]}',
        expected_safe_failure=True,
    ),
    AdversarialCase(
        name="extra_unexpected_fields",
        description="Model adds extra keys alongside 'action' and 'parameters'. "
                    "Parser rejects any action item with unexpected top-level keys.",
        response_text=(
            '{"actions": [{"action": "reset_workcell", "parameters": {}, '
            '"inject": "malicious_field", "override": true}]}'
        ),
        expected_safe_failure=True,
    ),
    AdversarialCase(
        name="markdown_wrapped_json",
        description="Model wraps the JSON payload in markdown code fences. "
                    "Parser rejects any response containing backtick fences.",
        response_text=(
            "```json\n"
            '{"actions": [{"action": "reset_workcell", "parameters": {}}]}\n'
            "```"
        ),
        expected_safe_failure=True,
    ),
    AdversarialCase(
        name="prose_before_json",
        description="Model prepends natural-language prose before the JSON payload, "
                    "making the response unparseable as strict JSON.",
        response_text=(
            'The robot should pick the cube. '
            '{"actions": [{"action": "pick_target", "parameters": {"object_id": "obj_1"}}]}'
        ),
        expected_safe_failure=True,
    ),
    AdversarialCase(
        name="empty_response",
        description="Model returns an empty string. "
                    "Parser rejects empty or whitespace-only responses.",
        response_text="",
        expected_safe_failure=True,
    ),
    AdversarialCase(
        name="multiple_actions",
        description="Model returns multiple actions where both reference an unknown "
                    "action type. Parser rejects on first invalid action item.",
        response_text=(
            '{"actions": ['
            '{"action": "hallucinated_action_a", "parameters": {}},'
            '{"action": "hallucinated_action_b", "parameters": {}}'
            "]}"
        ),
        expected_safe_failure=True,
    ),
    AdversarialCase(
        name="wrong_top_level_type",
        description="Model returns a JSON array instead of the required "
                    '{"actions": [...]} object. Parser rejects non-dict top-level.',
        response_text=(
            '[{"action": "pick_target", "parameters": {"object_id": "obj_1"}}]'
        ),
        expected_safe_failure=True,
    ),
)


def get_adversarial_cases() -> tuple[AdversarialCase, ...]:
    """Return the canonical tuple of adversarial model-output test cases."""
    return _CASES
