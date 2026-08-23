"""Unit tests for _shared/scripts/generate_demo_html.py."""

import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from _shared.scripts.generate_demo_html import (
    generate_html_showcase,
    get_agent_info,
    DOMAIN_ICONS,
    DOMAIN_TITLES,
)


def test_domain_constants():
    assert "consumer_marketing" in DOMAIN_ICONS
    assert "netops_aiops" in DOMAIN_ICONS
    assert DOMAIN_ICONS["consumer_marketing"] == "📱"
    assert "Consumer Marketing" in DOMAIN_TITLES["consumer_marketing"]


def test_get_agent_info_existing_agent():
    info = get_agent_info("family_plan_upsell", "consumer_marketing")
    assert "Family Plan Upsell" in info["display_name"]
    assert len(info["subtitle"]) > 10


def test_generate_html_showcase_output(tmp_path):
    output_dir = tmp_path / "demos"
    html_file = generate_html_showcase(
        agent_name="family_plan_upsell",
        domain="consumer_marketing",
        output_dir=output_dir,
        duration_text="5:11 (Normal Pacing)",
    )
    
    assert html_file.exists()
    content = html_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "Family Plan Upsell" in content
    assert "family_plan_upsell.mp4" in content
    assert "1080p Full HD" in content
    assert 'id="demoVideo"' in content
    assert "family_plan_upsell.mp4#t=10" in content
    assert "timeupdate" in content
    assert 'target="_blank"' not in content

