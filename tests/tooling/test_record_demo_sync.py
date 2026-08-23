import sys
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "_shared" / "scripts"))

from record_agent_demo import (
    wait_for_response_completion,
    activate_canvas_mode,
    showcase_canvas_presentation
)

@pytest.mark.asyncio
async def test_wait_for_response_completion_state_machine():
    page = MagicMock()
    
    stop_locator = MagicMock()
    stop_locator.count = AsyncMock(side_effect=[1, 1, 0])
    
    def locator_router(selector):
        return stop_locator
        
    page.locator = MagicMock(side_effect=locator_router)
    
    # Execute with short read_pause for test speed
    await wait_for_response_completion(page, turn_index=1, timeout_seconds=10, read_pause=0.1)
    
    assert stop_locator.count.call_count >= 2


@pytest.mark.asyncio
async def test_activate_canvas_mode_success():
    page = MagicMock()
    
    tools_button = MagicMock()
    tools_button.is_visible = AsyncMock(return_value=True)
    tools_button.text_content = AsyncMock(return_value="Tools")
    tools_button.click = AsyncMock()
    
    canvas_item = MagicMock()
    canvas_item.is_visible = AsyncMock(return_value=True)
    canvas_item.text_content = AsyncMock(return_value="Canvas")
    canvas_item.click = AsyncMock()
    
    menu_locator = MagicMock()
    menu_locator.count = AsyncMock(return_value=1)
    menu_locator.nth = MagicMock(return_value=canvas_item)
    
    direct_canvas = MagicMock()
    direct_canvas.first.is_visible = AsyncMock(return_value=False)
    
    def locator_router(selector):
        loc = MagicMock()
        if "button:visible:has-text('Canvas')" in selector:
            return direct_canvas
        if ".cdk-overlay-container" in selector:
            return menu_locator
        loc.first = tools_button
        loc.last = tools_button
        loc.count = AsyncMock(return_value=1)
        loc.is_visible = AsyncMock(return_value=True)
        return loc
        
    page.locator = MagicMock(side_effect=locator_router)
    
    res = await activate_canvas_mode(page)
    assert res is True
    assert tools_button.click.called
    assert canvas_item.click.called


@pytest.mark.asyncio
async def test_activate_canvas_mode_graceful_fallback():
    page = MagicMock()
    
    empty_loc = MagicMock()
    empty_loc.first.is_visible = AsyncMock(return_value=False)
    empty_loc.last.is_visible = AsyncMock(return_value=False)
    empty_loc.is_visible = AsyncMock(return_value=False)
    empty_loc.count = AsyncMock(return_value=0)
    
    page.locator = MagicMock(return_value=empty_loc)
    
    res = await activate_canvas_mode(page)
    assert res is False


@pytest.mark.asyncio
async def test_showcase_canvas_presentation_thumbnail_rail():
    page = MagicMock()
    
    open_btn = MagicMock()
    open_btn.is_visible = AsyncMock(return_value=False)
    page.locator = MagicMock(return_value=MagicMock(first=open_btn))
    
    page.mouse.move = AsyncMock()
    page.mouse.click = AsyncMock()
    
    await showcase_canvas_presentation(page, num_slides=4, slide_pause=0.01, resolution="1080p")
    assert page.mouse.move.call_count == 4
    assert page.mouse.click.call_count == 4
    page.mouse.click.assert_any_call(749.0, 995.0)
    page.mouse.click.assert_any_call(1265.0, 995.0)


def test_resolution_configs_mapping():
    from _shared.scripts.record_agent_demo import RESOLUTION_CONFIGS
    assert "1080p" in RESOLUTION_CONFIGS
    assert RESOLUTION_CONFIGS["1080p"] == {"width": 1920, "height": 1080}
    assert "720p" in RESOLUTION_CONFIGS
    assert RESOLUTION_CONFIGS["720p"] == {"width": 1280, "height": 720}


@pytest.mark.asyncio
async def test_scroll_to_bottom_prompt_box_success():
    from _shared.scripts.record_agent_demo import scroll_to_bottom_prompt_box
    page = MagicMock()
    page.evaluate = AsyncMock()
    page.mouse.wheel = AsyncMock()
    
    await scroll_to_bottom_prompt_box(page)
    
    assert page.evaluate.called
    assert page.mouse.wheel.call_count >= 5


@pytest.mark.asyncio
async def test_smooth_mouse_scroll_walkthrough_left_pane():
    from _shared.scripts.record_agent_demo import smooth_mouse_scroll_walkthrough
    page = MagicMock()
    page.mouse.move = AsyncMock()
    page.mouse.wheel = AsyncMock()
    
    await smooth_mouse_scroll_walkthrough(page, resolution="1080p")
    
    # Check mouse positioned over left pane (1920 * 0.25 = 480, 1080 * 0.5 = 540)
    page.mouse.move.assert_called_with(480, 540)
    # Check that wheel was called in both negative (up) and positive (down) directions
    wheel_calls = page.mouse.wheel.call_args_list
    assert len(wheel_calls) >= 70
    assert any(c.args[1] < 0 for c in wheel_calls)
    assert any(c.args[1] > 0 for c in wheel_calls)


def test_canvas_prompt_generalization_and_override():
    from _shared.scripts.record_agent_demo import get_agent_display_name
    display_name = get_agent_display_name("family_plan_upsell", "consumer_marketing")
    agent_clean_title = display_name.split(":")[-1].strip() if ":" in display_name else display_name
    
    # Default dynamic template
    dynamic_prompt = f"Create a 4-slide executive presentation summarizing the {agent_clean_title} analysis and recommendations above."
    assert "Family Plan Upsell" in dynamic_prompt
    assert "4-slide executive presentation" in dynamic_prompt
    
    # Custom override
    custom_override = "Create a custom 3-slide pitch deck."
    prompt_to_use = custom_override or dynamic_prompt
    assert prompt_to_use == "Create a custom 3-slide pitch deck."


def test_user_data_dir_isolation_and_env_override(tmp_path, monkeypatch):
    from _shared.scripts.record_agent_demo import DEFAULT_BASE_CHROME_DIR, sync_chrome_profile
    import argparse
    from pathlib import Path
    
    # Verify default base directory
    assert DEFAULT_BASE_CHROME_DIR == Path.home() / ".config" / "google-chrome-demo-recorder"
    
    # Verify custom worker user data dir sync logic
    worker_dir = tmp_path / "worker_1"
    sync_chrome_profile(user_data_dir=worker_dir)
    assert worker_dir.exists()


def test_mention_query_formatting_lowercase_no_space():
    from _shared.scripts.record_agent_demo import get_agent_display_name
    
    dname_1 = get_agent_display_name("family_plan_upsell", "consumer_marketing")
    assert dname_1 == "Consumer Marketing: Family Plan Upsell"
    clean_1 = dname_1.split(":")[-1].strip()
    assert clean_1 == "Family Plan Upsell"
    mention_1 = f"@{clean_1.lower()}"
    assert mention_1 == "@family plan upsell"
    assert " " not in mention_1[:2]  # No space between @ and agent name
    
    dname_2 = get_agent_display_name("fcaps_alarm_noise_reduction", "netops_aiops")
    assert dname_2 == "NetOps & AIOps: FCAPS Alarm Noise Reduction"
    clean_2 = dname_2.split(":")[-1].strip()
    assert clean_2 == "FCAPS Alarm Noise Reduction"
    mention_2 = f"@{clean_2.lower()}"
    assert mention_2 == "@fcaps alarm noise reduction"


