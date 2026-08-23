import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure repo root is on sys.path for test resolution
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from _shared.scripts.deploy_agent_lifecycle import (
    AgentDeployConfig,
    resolve_agent_config,
    GcpControlPlaneClient,
    AgentLifecycleEngine,
    generate_delta_report,
    group_results_by_domain,
    get_domain_report_path,
    parse_args
)


def test_resolve_agent_config_valid(monkeypatch):
    monkeypatch.setenv("PROJECT_ID", "test-project-123")
    monkeypatch.setenv("GEMINI_ENTERPRISE_APP_ID", "projects/123/locations/global/collections/default_collection/engines/app-1")
    
    config = resolve_agent_config("consumer_marketing", "family_plan_upsell", repo_root=REPO_ROOT)
    assert config.domain == "consumer_marketing"
    assert config.agent_name == "family_plan_upsell"
    assert config.agent_id == "famu"
    assert config.display_name == "Consumer Marketing: Family Plan Upsell"
    assert config.region == "us-central1"
    assert config.project_id == "test-project-123"
    assert "app-1" in config.gemini_enterprise_app_id
    assert config.agent_dir == REPO_ROOT / "domains" / "consumer_marketing" / "agents" / "family_plan_upsell"


def test_resolve_agent_config_missing_project_id(monkeypatch):
    monkeypatch.delenv("PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    
    with pytest.raises(ValueError, match="PROJECT_ID or GOOGLE_CLOUD_PROJECT must be set"):
        resolve_agent_config("consumer_marketing", "family_plan_upsell", repo_root=REPO_ROOT, load_env=False)


def test_gcp_control_plane_client_methods(monkeypatch):
    client = GcpControlPlaneClient(token="mock-token")
    
    # 1. list_reasoning_engines
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "reasoningEngines": [
            {"name": "projects/123/locations/us-central1/reasoningEngines/111", "displayName": "Consumer Marketing: Family Plan Upsell"}
        ]
    }
    with patch("requests.get", return_value=mock_resp):
        engines = client.list_reasoning_engines("test-proj", "us-central1")
        assert len(engines) == 1
        assert engines[0]["displayName"] == "Consumer Marketing: Family Plan Upsell"

    # 2. delete_reasoning_engine
    mock_del_resp = MagicMock()
    mock_del_resp.status_code = 200
    with patch("requests.delete", return_value=mock_del_resp):
        assert client.delete_reasoning_engine("projects/123/locations/us-central1/reasoningEngines/111", "test-proj") is True

    # 3. list_ge_agents
    mock_ge_resp = MagicMock()
    mock_ge_resp.status_code = 200
    mock_ge_resp.json.return_value = {
        "agents": [
            {"name": "projects/123/.../agents/222", "displayName": "Consumer Marketing: Family Plan Upsell"}
        ]
    }
    with patch("requests.get", return_value=mock_ge_resp):
        cards = client.list_ge_agents("projects/123/.../engines/app1", "test-proj")
        assert len(cards) == 1
        assert cards[0]["displayName"] == "Consumer Marketing: Family Plan Upsell"

    # 4. delete_ge_agent
    with patch("requests.delete", return_value=mock_del_resp):
        assert client.delete_ge_agent("projects/123/.../agents/222", "test-proj") is True


def test_agent_lifecycle_match_and_clean():
    mock_client = MagicMock()
    mock_client.delete_ge_agent.return_value = True
    mock_client.delete_reasoning_engine.return_value = True
    
    engine = AgentLifecycleEngine(client=mock_client)
    config = AgentDeployConfig(
        domain="netops_aiops",
        agent_name="fcaps_alarm_noise_reduction",
        agent_id="fcap",
        display_name="NetOps & AIOps: FCAPS Alarm Noise Reduction",
        description="test",
        project_id="test-proj",
        gemini_enterprise_app_id="projects/123/.../engines/app1"
    )
    
    mock_engines = [
        {"name": "projects/123/locations/us-central1/reasoningEngines/999", "displayName": "NetOps & AIOps: FCAPS Alarm Noise Reduction"},
        {"name": "projects/123/locations/us-central1/reasoningEngines/888", "displayName": "Consumer Marketing: Family Plan Upsell"}
    ]
    mock_cards = [
        {"name": "projects/123/.../agents/111", "displayName": "NetOps & AIOps: FCAPS Alarm Noise Reduction"},
        {"name": "projects/123/.../agents/112", "displayName": "NetOps & AIOps: FCAPS Alarm Noise Reduction"}
    ]
    
    matched = engine.match_resources(config, mock_engines, mock_cards)
    assert len(matched["matching_engines"]) == 1
    assert len(matched["matching_cards"]) == 2
    
    clean_res = engine.clean(config, matched["matching_engines"], matched["matching_cards"])
    assert len(clean_res["deleted_engines"]) == 1
    assert len(clean_res["deleted_cards"]) == 2


def test_agent_lifecycle_verify_deduplication_success():
    mock_client = MagicMock()
    expected_re_id = "projects/123/locations/us-central1/reasoningEngines/999"
    
    mock_client.list_reasoning_engines.return_value = [
        {"name": expected_re_id, "displayName": "Supply Chain: Inbound Freight Optimization"}
    ]
    mock_client.list_ge_agents.return_value = [
        {
            "name": "projects/123/.../agents/111",
            "displayName": "Supply Chain: Inbound Freight Optimization",
            "adkAgentDefinition": {
                "provisionedReasoningEngine": {
                    "reasoningEngine": expected_re_id
                }
            }
        }
    ]
    
    engine = AgentLifecycleEngine(client=mock_client)
    config = AgentDeployConfig(
        domain="supply_chain",
        agent_name="inbound_freight_optimization",
        agent_id="ifop",
        display_name="Supply Chain: Inbound Freight Optimization",
        description="test",
        project_id="test-proj",
        gemini_enterprise_app_id="projects/123/.../engines/app1"
    )
    
    assert engine.verify_deduplication(config, expected_re_id) is True


def test_agent_lifecycle_verify_deduplication_raises_on_duplicate():
    mock_client = MagicMock()
    expected_re_id = "projects/123/locations/us-central1/reasoningEngines/999"
    
    mock_client.list_reasoning_engines.return_value = [
        {"name": expected_re_id, "displayName": "Supply Chain: Inbound Freight Optimization"}
    ]
    # Return 2 duplicate cards
    mock_client.list_ge_agents.return_value = [
        {"name": "card-1", "displayName": "Supply Chain: Inbound Freight Optimization"},
        {"name": "card-2", "displayName": "Supply Chain: Inbound Freight Optimization"}
    ]
    
    engine = AgentLifecycleEngine(client=mock_client)
    config = AgentDeployConfig(
        domain="supply_chain",
        agent_name="inbound_freight_optimization",
        agent_id="ifop",
        display_name="Supply Chain: Inbound Freight Optimization",
        description="test",
        project_id="test-proj"
    )
    
    with pytest.raises(AssertionError, match="Expected exactly 1 GE Card, found 2"):
        engine.verify_deduplication(config, expected_re_id)


def test_generate_delta_report_and_domain_grouping(tmp_path):
    mock_results = [
        {
            "domain": "netops_aiops",
            "agent_name": "fcaps_alarm_noise_reduction",
            "display_name": "NetOps & AIOps: FCAPS Alarm Noise Reduction",
            "before_state": "None",
            "cleanup_actions": "1 dangling card deleted",
            "after_state": "✅ reasoningEngines/123",
            "demo_recorded": "🎬 1080p Normal (5m 12s)",
            "status": "SUCCESS"
        },
        {
            "domain": "consumer_marketing",
            "agent_name": "family_plan_upsell",
            "display_name": "Consumer Marketing: Family Plan Upsell",
            "before_state": "1 Engine, 1 Card",
            "cleanup_actions": "None",
            "after_state": "✅ reasoningEngines/456",
            "demo_recorded": "—",
            "status": "SUCCESS"
        }
    ]
    
    grouped = group_results_by_domain(mock_results)
    assert len(grouped["netops_aiops"]) == 1
    assert len(grouped["consumer_marketing"]) == 1
    
    out_file = tmp_path / "netops_aiops_audit.md"
    report = generate_delta_report(grouped["netops_aiops"], domain="netops_aiops", output_path=out_file)
    
    assert "# Deployment Lifecycle & Deduplication Audit Report: Netops Aiops" in report
    assert "NetOps & AIOps: FCAPS Alarm Noise Reduction" in report
    assert "git worktree add .worktrees/deploy_netops_aiops" in report
    assert out_file.exists()


def test_parse_args_options():
    # 1. Single agent with demo
    args = parse_args(["--domain", "supply_chain", "--name", "vendor_performance", "--record-demo", "--demo-speed", "normal"])
    assert args.domain == "supply_chain"
    assert args.name == "vendor_performance"
    assert args.record_demo is True
    assert args.demo_speed == "normal"
    assert args.demo_resolution == "1080p"

    # 2. Audit only
    args_audit = parse_args(["--all", "--audit-only"])
    assert args_audit.all is True
    assert args_audit.audit_only is True
