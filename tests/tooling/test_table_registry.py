"""Guards against duplicate/malformed agent_ids and domain_ids in the shared table registry — a
collision or bad format here would silently defeat the table-name-prefixing collision prevention
the registry exists for (see _shared/table_registry.yaml's header comment).
"""
import re
from pathlib import Path

import yaml

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "_shared" / "table_registry.yaml"
FOUR_LOWERCASE_LETTERS = re.compile(r"^[a-z]{4}$")


def test_every_agent_has_a_nonempty_agent_id():
    registry = yaml.safe_load(REGISTRY_PATH.read_text())

    for agent_name, entry in registry["agents"].items():
        assert entry.get("agent_id"), f"Agent '{agent_name}' is missing an agent_id in {REGISTRY_PATH}"


def test_all_agent_ids_are_unique_across_every_domain():
    registry = yaml.safe_load(REGISTRY_PATH.read_text())
    agent_ids = [entry["agent_id"] for entry in registry["agents"].values()]

    assert len(agent_ids) == len(set(agent_ids)), (
        f"Duplicate agent_id in {REGISTRY_PATH}: {agent_ids} — "
        "table names would collide across agents despite prefixing"
    )


def test_agent_id_is_exactly_four_lowercase_letters():
    registry = yaml.safe_load(REGISTRY_PATH.read_text())

    for agent_name, entry in registry["agents"].items():
        agent_id = entry.get("agent_id", "")
        assert FOUR_LOWERCASE_LETTERS.match(agent_id), (
            f"Agent '{agent_name}' has agent_id '{agent_id}' in {REGISTRY_PATH} — "
            "must be exactly 4 lowercase letters"
        )


def test_every_domain_has_a_nonempty_domain_id():
    registry = yaml.safe_load(REGISTRY_PATH.read_text())

    for domain_name, entry in registry["domains"].items():
        assert entry.get("domain_id"), f"Domain '{domain_name}' is missing a domain_id in {REGISTRY_PATH}"


def test_domain_id_is_exactly_four_lowercase_letters():
    registry = yaml.safe_load(REGISTRY_PATH.read_text())

    for domain_name, entry in registry["domains"].items():
        domain_id = entry.get("domain_id", "")
        assert FOUR_LOWERCASE_LETTERS.match(domain_id), (
            f"Domain '{domain_name}' has domain_id '{domain_id}' in {REGISTRY_PATH} — "
            "must be exactly 4 lowercase letters"
        )


def test_all_domain_ids_are_unique():
    registry = yaml.safe_load(REGISTRY_PATH.read_text())
    domain_ids = [entry["domain_id"] for entry in registry["domains"].values()]

    assert len(domain_ids) == len(set(domain_ids)), (
        f"Duplicate domain_id in {REGISTRY_PATH}: {domain_ids} — "
        "table names would collide across domains despite prefixing"
    )


def test_every_domain_has_a_nonempty_display_name():
    # Source of truth for the "<domain display_name>: <agent display name>" naming convention
    # applied to Agent Engine/Gemini Enterprise display names at deploy time -- see this file's
    # header comment.
    registry = yaml.safe_load(REGISTRY_PATH.read_text())

    for domain_name, entry in registry["domains"].items():
        assert entry.get("display_name"), (
            f"Domain '{domain_name}' is missing a display_name in {REGISTRY_PATH}"
        )


def test_every_agent_domain_field_resolves_to_a_registered_domain():
    registry = yaml.safe_load(REGISTRY_PATH.read_text())
    registered_domains = set(registry["domains"].keys())

    for agent_name, entry in registry["agents"].items():
        domain = entry.get("domain")
        assert domain in registered_domains, (
            f"Agent '{agent_name}' has domain '{domain}' in {REGISTRY_PATH}, which has no "
            "matching entry under 'domains:' — the loader's domain_id lookup would fail"
        )


def test_all_five_domains_are_registered():
    registry = yaml.safe_load(REGISTRY_PATH.read_text())
    expected_domains = {
        "consumer_marketing",
        "onboarding_provisioning",
        "subscriber_crm",
        "netops_aiops",
        "daas_camara",
    }
    registered_domains = set(registry["domains"].keys())
    assert registered_domains == expected_domains, (
        f"Domain mismatch in {REGISTRY_PATH}. Missing: {expected_domains - registered_domains}, "
        f"Unexpected: {registered_domains - expected_domains}"
    )


def test_all_agents_are_registered():
    registry = yaml.safe_load(REGISTRY_PATH.read_text())
    agents = registry["agents"]
    assert len(agents) == 45, f"Expected 45 registered agents in {REGISTRY_PATH}, found {len(agents)}"


def test_every_agent_has_at_least_three_tables():
    registry = yaml.safe_load(REGISTRY_PATH.read_text())
    for agent_name, entry in registry["agents"].items():
        tables = entry.get("tables", [])
        assert isinstance(tables, list) and len(tables) >= 3, (
            f"Agent '{agent_name}' must have at least 3 logical tables in {REGISTRY_PATH}, found {len(tables)}"
        )


def test_every_agent_has_a_valid_display_name():
    registry = yaml.safe_load(REGISTRY_PATH.read_text())
    for agent_name, entry in registry["agents"].items():
        display_name = entry.get("display_name")
        assert display_name, f"Agent '{agent_name}' is missing a display_name in {REGISTRY_PATH}"
        assert ":" in display_name, f"Agent '{agent_name}' display_name '{display_name}' must follow '<Domain>: <Agent Name>'"
        prefix, clean_title = display_name.split(":", 1)
        assert prefix.strip(), f"Agent '{agent_name}' display_name missing domain prefix"
        assert clean_title.strip(), f"Agent '{agent_name}' display_name missing clean agent title"


