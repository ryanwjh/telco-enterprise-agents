"""Regression tests guarding the shared instruction fragments' required content.

These fragments get concatenated at scaffold time (Task 3) into every logical
agent's instruction text. If a required line disappears here, every future
scaffolded agent silently loses that behavior — these tests exist to catch that.
"""
from pathlib import Path

INSTRUCTIONS_DIR = Path(__file__).resolve().parents[2] / "_shared" / "instructions"


def test_persona_fragment_exists_and_has_required_content():
    content = (INSTRUCTIONS_DIR / "persona_telco_analyst.md").read_text()
    assert "senior telecommunications domain specialist" in content


def test_safety_fragment_exists_and_has_required_content():
    content = (INSTRUCTIONS_DIR / "safety_and_grounding_rules.md").read_text()
    assert "Never fabricate a number" in content


def test_safety_fragment_has_current_date_placeholder():
    # Without this, every agent's instruction would have no way to resolve relative date
    # references (e.g. "last two months") against the real invocation-time date -- the LLM
    # would guess "today" from training data instead. The placeholder is filled in by
    # tools/callbacks.py's before_agent_callback, registered on every scaffolded root_agent.yaml.
    content = (INSTRUCTIONS_DIR / "safety_and_grounding_rules.md").read_text()
    assert "{temp:current_date}" in content


def test_output_formatting_fragment_exists_and_has_required_content():
    content = (INSTRUCTIONS_DIR / "output_formatting.md").read_text()
    assert "Respond in plain text" in content
