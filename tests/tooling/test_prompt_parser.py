"""Unit tests for prompt_parser.py."""

import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from _shared.scripts.prompt_parser import parse_agent_prompts, resolve_agent_domain

def test_resolve_agent_domain_success():
    domain = resolve_agent_domain("family_plan_upsell", REPO_ROOT)
    assert domain == "consumer_marketing"
    
    domain_net = resolve_agent_domain("fcaps_alarm_noise_reduction", REPO_ROOT)
    assert domain_net == "netops_aiops"

def test_resolve_agent_domain_nonexistent():
    with pytest.raises(ValueError, match="Could not find agent 'non_existent_agent'"):
        resolve_agent_domain("non_existent_agent", REPO_ROOT)

def test_parse_agent_prompts_consumer_marketing():
    readme = REPO_ROOT / "domains" / "consumer_marketing" / "agents" / "family_plan_upsell" / "README.md"
    prompts = parse_agent_prompts(readme)
    assert len(prompts) == 3
    assert all(isinstance(p, str) and len(p) > 10 for p in prompts)
    assert "metrics" in prompts[0].lower() or "family" in prompts[0].lower() or "plan" in prompts[0].lower()

def test_parse_agent_prompts_across_all_domains():
    readmes = sorted(REPO_ROOT.glob("domains/*/agents/*/README.md"))
    assert len(readmes) == 45
    for r in readmes:
        prompts = parse_agent_prompts(r)
        assert len(prompts) == 3, f"Agent {r.parent.name} must yield 3 prompts"
