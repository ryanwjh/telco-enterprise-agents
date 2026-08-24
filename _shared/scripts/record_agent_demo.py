#!/usr/bin/env python3
"""Generic Agent Demo Video Recorder for Gemini Enterprise.

Automates opening Gemini Enterprise in Google Chrome using an authenticated Chrome profile,
focuses on the main prompt input box, types '@' followed by the agent name, selects the agent
card that appears above the prompt box, executes the 3 curated prompts from the agent's
README.md sequentially (waiting for each full response to appear on screen before proceeding),
performs a smooth mouse scroll to the top and all the way to the bottom, and records a 1080p demo
video saved as MP4 under demos/gemini-enterprise/<domain>/<agent_name>.mp4.
"""

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from _shared.scripts.prompt_parser import parse_agent_prompts, resolve_agent_domain
from _shared.scripts.generate_demo_html import generate_html_showcase

# Load environment configuration
load_dotenv(REPO_ROOT / "_shared" / ".env")
load_dotenv(REPO_ROOT / ".env")
DEFAULT_GE_URL = os.getenv("GEMINI_ENTERPRISE_URL", "")
DEFAULT_BASE_CHROME_DIR = Path.home() / ".config" / "google-chrome-demo-recorder"
DEFAULT_CHROME_USER_DATA_DIR = Path(os.getenv("CHROME_USER_DATA_DIR", str(DEFAULT_BASE_CHROME_DIR)))
DEFAULT_SOURCE_CHROME_DIR = Path.home() / ".config" / "google-chrome"
DEFAULT_CHROME_PROFILE_DIR = os.getenv("CHROME_PROFILE_DIR", "Profile 2")
DEFAULT_CHROME_PROFILE_NAME = os.getenv("CHROME_PROFILE_NAME", "Default Profile")

RESOLUTION_CONFIGS = {
    "1080p": {"width": 1920, "height": 1080},
    "720p": {"width": 1280, "height": 720},
}


def enforce_100_percent_zoom(user_data_dir: Path | None = None):
    """Sanitizes synced Chrome preferences so vertexaisearch zoom is strictly 100% (0.0)."""
    target_dir = user_data_dir or DEFAULT_CHROME_USER_DATA_DIR
    pref_path = target_dir / DEFAULT_CHROME_PROFILE_DIR / "Preferences"
    if pref_path.exists():
        try:
            import json
            data = json.loads(pref_path.read_text(encoding="utf-8"))
            # 1. Reset per_host_zoom_levels
            partition = data.get("partition", {})
            per_host = partition.get("per_host_zoom_levels", {})
            if "x" in per_host and isinstance(per_host["x"], dict):
                if "vertexaisearch.cloud.google.com" in per_host["x"]:
                    per_host["x"]["vertexaisearch.cloud.google.com"]["zoom_level"] = 0.0
            # 2. Reset default zoom level
            if "profile" in data and isinstance(data["profile"], dict):
                data["profile"]["default_zoom_level"] = 0.0
            pref_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"⚠️ Warning sanitizing preferences: {e}", flush=True)


def sync_chrome_profile(user_data_dir: Path | None = None):
    """Syncs user Chrome profile into demo recorder directory to avoid singleton locks."""
    target_dir = user_data_dir or DEFAULT_CHROME_USER_DATA_DIR
    source_dir = DEFAULT_SOURCE_CHROME_DIR
    
    if source_dir.resolve() == target_dir.resolve():
        return
    
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Sync Local State
    for f in ["Local State"]:
        src_f = source_dir / f
        tgt_f = target_dir / f
        if src_f.exists():
            shutil.copy2(src_f, tgt_f)
            
    # 2. Complete rsync of the profile directory (Cookies, Storage, Auth state)
    p_src = source_dir / DEFAULT_CHROME_PROFILE_DIR
    p_tgt = target_dir / DEFAULT_CHROME_PROFILE_DIR
    if p_src.exists():
        p_tgt.mkdir(parents=True, exist_ok=True)
        cmd = [
            "rsync", "-av", "--delete",
            "--exclude=Singleton*",
            "--exclude=*lock*",
            "--exclude=LOCK*",
            "--exclude=*Cache*",
            "--exclude=*Crash*",
            "--exclude=BrowserMetrics*",
            str(p_src) + "/",
            str(p_tgt) + "/"
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    enforce_100_percent_zoom(target_dir)


def get_agent_display_name(agent_name: str, domain: str) -> str:
    """Gets human-readable display name from table_registry.yaml or root_agent.yaml."""
    registry_file = REPO_ROOT / "_shared" / "table_registry.yaml"
    if registry_file.exists():
        try:
            data = yaml.safe_load(registry_file.read_text(encoding="utf-8"))
            agent_entry = data.get("agents", {}).get(agent_name, {})
            if "display_name" in agent_entry:
                return agent_entry["display_name"].strip()
        except Exception:
            pass

    root_agent_file = REPO_ROOT / "domains" / domain / "agents" / agent_name / "root_agent.yaml"
    if root_agent_file.exists():
        try:
            data = yaml.safe_load(root_agent_file.read_text(encoding="utf-8"))
            if "display_name" in data:
                return data["display_name"].strip()
        except Exception:
            pass
    return agent_name.replace("_", " ").title()


def convert_webm_to_mp4(webm_path: Path, mp4_path: Path) -> bool:
    """Converts recorded webm video to high-quality universal MP4 using ffmpeg."""
    try:
        print(f"🔄 Converting {webm_path.name} to MP4 format...", flush=True)
        cmd = [
            "ffmpeg", "-y",
            "-i", str(webm_path),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            str(mp4_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception as e:
        print(f"⚠️ FFmpeg conversion error: {e}", flush=True)
        return False


async def wait_for_response_completion(
    page,
    turn_index: int,
    timeout_seconds: int = 180,
    read_pause: float = 6.0
):
    """Waits for the streaming response of turn_index to fully render and the Stop button to change back to Action."""
    print(f"⏳ Waiting for Response {turn_index} to appear and complete streaming on screen...", flush=True)
    
    visible_stops = page.locator("button[aria-label*='Stop' i]:visible, button:has(mat-icon:has-text('stop')):visible")
    
    # Phase 1: Wait up to 15s for generation to start (Stop button appears in prompt bar)
    gen_started = False
    for _ in range(30):
        if await visible_stops.count() > 0:
            gen_started = True
            break
        await asyncio.sleep(0.5)
        
    if gen_started:
        print(f"   ✓ Generation {turn_index} active (Stop button active in prompt bar).", flush=True)
        
    # Phase 2: Wait for generation to finish (Stop button disappears / changes back to Action)
    start_time = asyncio.get_event_loop().time()
    while True:
        is_stop_active = (await visible_stops.count()) > 0
        elapsed = asyncio.get_event_loop().time() - start_time
        if not is_stop_active:
            print(f"   ✓ Response {turn_index} generation completed after {elapsed:.1f}s (Stop button returned to Action).", flush=True)
            break
        if elapsed > timeout_seconds:
            print(f"   ⚠️ Reached {timeout_seconds}s timeout waiting for Response {turn_index}. Proceeding...", flush=True)
            break
        await asyncio.sleep(1.0)
        
    # Phase 3: Short DOM stabilization
    await asyncio.sleep(1.5)
    
    # Phase 4: Reading pause
    print(f"📖 Reading pause ({read_pause:.1f}s) for Response {turn_index}...", flush=True)
    await asyncio.sleep(read_pause)
    print(f"✅ Turn {turn_index} response successfully displayed.\n", flush=True)


async def activate_canvas_mode(page) -> bool:
    """Clicks the Tools menu option below the text box (to the right of +) and selects Canvas."""
    print("🎨 Activating Canvas mode via Tools menu...", flush=True)
    
    # 1. Click Tools button (to the right of the + button)
    tools_button_selectors = [
        "button[aria-label*='tool' i]:visible",
        "button:visible:has(mat-icon:has-text('tune'))",
        "button:visible:has(mat-icon:has-text('handyman'))",
        "button:visible:has-text('Tools')",
        "button:visible:has-text('Add tool')",
        "button[aria-label*='Add' i]:visible",
        "button:visible:has(mat-icon:has-text('add'))",
        "[data-test-id*='tools-button']:visible",
        "[class*='tools-button']:visible"
    ]
    
    tools_clicked = False
    for sel in tools_button_selectors:
        btns = page.locator(sel)
        count = await btns.count()
        if count > 0:
            btn = btns.last
            if await btn.is_visible():
                print(f"   ✓ Clicking Tools menu button ({sel})...", flush=True)
                try:
                    await btn.click()
                    await asyncio.sleep(1.5)
                    tools_clicked = True
                    break
                except Exception as e:
                    print(f"   ⚠️ Tools button click note: {e}", flush=True)
                    
    # 2. Select Canvas option from the opened menu
    try:
        if hasattr(page, "get_by_text"):
            canvas_item = page.get_by_text("Canvas", exact=True).first
            if await canvas_item.is_visible():
                print("   ✓ Found Canvas menu option via get_by_text. Clicking...", flush=True)
                await canvas_item.click()
                await asyncio.sleep(1.5)
                print("   ✅ Canvas mode successfully activated from Tools menu.", flush=True)
                return True
    except Exception as e:
        print(f"   ⚠️ get_by_text search note: {e}", flush=True)
        
    # 3. Fallback: scan overlay menu items
    menu_locators = page.locator(
        ".cdk-overlay-container [role='menuitem']:visible, "
        ".cdk-overlay-container mat-menu-item:visible, "
        ".cdk-overlay-container button:visible, "
        "[role='menu'] [role='menuitem']:visible, "
        "[role='menu'] button:visible, "
        ".mat-mdc-menu-item:visible, "
        ":visible:has-text('Canvas')"
    )
    
    try:
        count = await menu_locators.count()
        if count > 0:
            print(f"   📋 Scanning {count} open menu options in overlay...", flush=True)
            for idx in range(count):
                item = menu_locators.nth(idx)
                txt = (await item.text_content() or "").strip()
                if "canvas" in txt.lower():
                    print(f"   ✓ Found matching option: '{txt}'. Clicking...", flush=True)
                    await item.click()
                    await asyncio.sleep(1.5)
                    print("   ✅ Canvas mode successfully activated from Tools menu.", flush=True)
                    return True
    except Exception as e:
        print(f"   ⚠️ Menu scanning note: {e}", flush=True)
        
    print("   ℹ️ Canvas option not found in dropdown menu. Proceeding with presentation prompt...", flush=True)
    return False


async def showcase_canvas_presentation(page, num_slides: int = 4, slide_pause: float = 2.5, resolution: str = "1080p"):
    """Ensures Canvas split screen is active and smoothly clicks through presentation slides via the bottom thumbnail rail."""
    print(f"\n📊 Showcasing Canvas presentation ({num_slides} slides, {slide_pause:.1f}s pause per slide)...", flush=True)
    
    # 1. Ensure the Canvas split screen is open
    try:
        open_btn = page.locator("button:visible:has-text('Open'), [role='button']:visible:has-text('Open')").first
        if await open_btn.is_visible():
            print("   ✓ Clicking 'Open' button to expand Canvas split pane...", flush=True)
            await open_btn.click()
            await asyncio.sleep(2.5)
    except Exception:
        pass

    # 2. Smoothly glide cursor and click through each thumbnail in the bottom rail
    res_config = RESOLUTION_CONFIGS.get(resolution, RESOLUTION_CONFIGS["1080p"])
    w = res_config["width"]
    scale = w / 1920.0
    y_pos = 995 * scale
    x_coords = [(749 + idx * 172) * scale for idx in range(num_slides)]
    
    print(f"   👉 Navigating {num_slides} slides via bottom thumbnail rail (y={y_pos:.0f})...", flush=True)
    for idx, x_pos in enumerate(x_coords):
        print(f"   👉 Moving smoothly to Slide {idx + 1}/{num_slides} at ({x_pos:.0f}, {y_pos:.0f})...", flush=True)
        try:
            await page.mouse.move(x_pos, y_pos, steps=15)
            await asyncio.sleep(0.4)
            await page.mouse.click(x_pos, y_pos)
            print(f"   ✓ Selected Slide {idx + 1}. Pausing {slide_pause:.1f}s to showcase content...", flush=True)
        except Exception as ce:
            print(f"      (thumbnail click note: {ce})", flush=True)
        await asyncio.sleep(slide_pause)
        
    print(f"   ✅ Finished showcasing {num_slides} presentation slides.\n", flush=True)



async def scroll_to_bottom_prompt_box(page):
    """Smoothly scrolls down to ensure the prompt box and input controls are fully visible in viewport."""
    try:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        for _ in range(8):
            await page.mouse.wheel(0, 300)
            await asyncio.sleep(0.04)
        await asyncio.sleep(0.4)
    except Exception:
        pass


async def smooth_mouse_scroll_walkthrough(page, resolution: str = "1080p"):
    """Performs a smooth mouse scroll to the top of the conversation and then down to the bottom specifically on the left conversation pane."""
    print("\n📜 Performing smooth mouse scroll walkthrough of full conversation on left pane...", flush=True)
    
    res_config = RESOLUTION_CONFIGS.get(resolution, RESOLUTION_CONFIGS["1080p"])
    width = res_config["width"]
    height = res_config["height"]
    left_x = int(width * 0.25)
    center_y = int(height * 0.5)
    
    # Position mouse firmly over left conversation pane
    await page.mouse.move(left_x, center_y)
    await asyncio.sleep(0.5)
    
    print(f"   ⬆️ Smoothly scrolling left pane (x={left_x}, y={center_y}) up to the top...", flush=True)
    for _ in range(35):
        await page.mouse.wheel(0, -180)
        await asyncio.sleep(0.05)
        
    print("   ⏸️ Pausing at top (3.0s) to showcase agent pill and Turn 1 response...", flush=True)
    await asyncio.sleep(3.0)
    
    print(f"   ⬇️ Smoothly scrolling left pane down to the bottom...", flush=True)
    for _ in range(35):
        await page.mouse.wheel(0, 180)
        await asyncio.sleep(0.05)
        
    print("   ⏸️ Pausing at bottom (3.0s) to showcase final charts and recommendations...", flush=True)
    await asyncio.sleep(3.0)


async def record_single_agent_demo(
    agent_name: str,
    domain: str,
    prompts: list[str],
    output_dir: Path,
    speed: str = "normal",
    video_format: str = "mp4",
    resolution: str = "1080p",
    headless: bool = False,
    chrome_profile_dir: str = DEFAULT_CHROME_PROFILE_DIR,
    ge_url: str = DEFAULT_GE_URL,
    canvas_prompt: str | None = None,
    user_data_dir: Path | str | None = None,
    dry_run: bool = False
) -> Path:
    """Executes full flow: opens GE, types @agent, selects card above prompt box, executes 3 prompts with response sync, scrolls top to bottom, records MP4."""
    domain_output_dir = output_dir / domain
    domain_output_dir.mkdir(parents=True, exist_ok=True)
    target_video_file = domain_output_dir / f"{agent_name}.{video_format}"
    
    res_config = RESOLUTION_CONFIGS.get(resolution, RESOLUTION_CONFIGS["1080p"])
    effective_user_data_dir = Path(user_data_dir) if user_data_dir else DEFAULT_CHROME_USER_DATA_DIR
    
    display_name = get_agent_display_name(agent_name, domain)
    # Extract search title without domain prefix
    agent_clean_title = display_name.split(":")[-1].strip() if ":" in display_name else display_name
    keywords = [w for w in agent_name.split("_") if len(w) > 2]
    mention_keyword = keywords[0].title() if keywords else agent_clean_title
    
    print("\n" + "=" * 60, flush=True)
    print(f"🎬 RECORDING DEMO: {display_name} ({agent_name})", flush=True)
    print(f"📁 Domain: {domain}", flush=True)
    print(f"🎯 Target Video: {target_video_file}", flush=True)
    print(f"👤 Chrome Profile: {chrome_profile_dir} ({DEFAULT_CHROME_PROFILE_NAME})", flush=True)
    print(f"📁 User Data Dir: {effective_user_data_dir}", flush=True)
    print(f"⚡ Pacing Speed: {speed}", flush=True)
    print(f"📺 Resolution: {resolution} ({res_config['width']}x{res_config['height']})", flush=True)
    print(f"🎞️ Output Format: {video_format.upper()}", flush=True)
    print("📝 Prompts to Execute:", flush=True)
    for idx, p in enumerate(prompts, 1):
        print(f"   {idx}. {p}", flush=True)
    print("=" * 60, flush=True)
    
    if dry_run:
        print("🔍 [DRY-RUN] Validation passed. Skipping browser launch.", flush=True)
        return target_video_file

    sync_chrome_profile(effective_user_data_dir)
    
    from playwright.async_api import async_playwright
    
    temp_video_dir = domain_output_dir / f".tmp_video_{agent_name}_{int(time.time())}"
    temp_video_dir.mkdir(parents=True, exist_ok=True)
    
    keystroke_delay = 25 if speed == "normal" else 0
    mention_delay = 60 if speed == "normal" else 10
    read_pause = 6.0 if speed == "normal" else 2.5
    action_pause = 2.0 if speed == "normal" else 0.8

    async with async_playwright() as p:
        print(f"🌐 Launching Google Chrome with authenticated session ({effective_user_data_dir})...", flush=True)
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(effective_user_data_dir),
            channel="chrome",
            headless=headless,
            record_video_dir=str(temp_video_dir),
            record_video_size=res_config,
            viewport=res_config,
            device_scale_factor=1.0,
            ignore_default_args=["--password-store=basic", "--use-mock-keychain"],
            args=[
                f"--profile-directory={chrome_profile_dir}",
                "--password-store=detect",
                "--force-device-scale-factor=1.0",
                "--disable-blink-features=AutomationControlled",
                "--no-default-browser-check",
                f"--window-size={res_config['width']},{res_config['height']}"
            ]
        )
        
        await context.grant_permissions(["clipboard-read", "clipboard-write"])
        page = context.pages[0] if context.pages else await context.new_page()
        
        try:
            print(f"🔗 Navigating to Gemini Enterprise: {ge_url}", flush=True)
            await page.goto(ge_url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(4.0)
            
            # --- STEP 1: Navigate to 'Agents' tab in the left sidebar ---
            print("👉 Step 1: Navigating to 'Agents' tab in left sidebar...", flush=True)
            agents_tab_clicked = False
            
            left_elements = await page.locator("a:visible, button:visible, div[role='button']:visible, li:visible").all()
            for el in left_elements:
                box = await el.bounding_box()
                if box and box['x'] < 250:
                    txt = (await el.text_content() or '').strip()
                    if (txt == "Agents" or txt.startswith("Agents")) and "new" not in txt.lower() and "designer" not in txt.lower():
                        print(f"   ✓ Clicking 'Agents' tab in sidebar: '{txt}' at ({box['x']}, {box['y']})...", flush=True)
                        await el.click()
                        agents_tab_clicked = True
                        break
                        
            if not agents_tab_clicked:
                agents_text = page.get_by_text("Agents", exact=True).first
                if await agents_text.is_visible():
                    print("   ✓ Clicking 'Agents' via get_by_text(exact=True)...", flush=True)
                    await agents_text.click()
                    agents_tab_clicked = True

            assert agents_tab_clicked, "Could not locate 'Agents' tab in left sidebar"
            await asyncio.sleep(action_pause)

            # --- STEP 2: Find search input/icon in center of screen & filter by agent name ---
            print(f"👉 Step 2: Searching for '{agent_clean_title}' in center of screen...", flush=True)
            search_input = None
            candidate_inputs = await page.locator("input:visible").all()
            for inp in candidate_inputs:
                box = await inp.bounding_box()
                if box and box['x'] > 250 and box['y'] < 350:
                    search_input = inp
                    break
                    
            if not search_input:
                center_buttons = await page.locator("button:visible, [role='button']:visible, mat-icon:visible, [aria-label*='Search' i]:visible").all()
                for btn in center_buttons:
                    box = await btn.bounding_box()
                    if box and box['x'] > 250 and box['y'] < 350:
                        aria = (await btn.get_attribute("aria-label") or "").lower()
                        txt = (await btn.text_content() or "").lower()
                        classes = (await btn.get_attribute("class") or "").lower()
                        if "search" in aria or "search" in txt or "search" in classes or "mat-icon" in classes:
                            print(f"   ✓ Clicking center search button at ({box['x']}, {box['y']})...", flush=True)
                            await btn.click()
                            await asyncio.sleep(1.0)
                            break
                search_input = page.locator("input:visible").first

            assert search_input, "Could not find center search input on Agents page"
            await search_input.click()
            await asyncio.sleep(0.5)
            
            print(f"   ⌨️ Typing search query: \"{agent_clean_title}\"...", flush=True)
            await search_input.fill("")
            await search_input.type(agent_clean_title, delay=60 if speed == "normal" else 20)
            await asyncio.sleep(2.5)

            # --- STEP 3: Click on the single matching agent card below search ---
            print(f"👉 Step 3: Finding agent card for '{agent_clean_title}'...", flush=True)
            card_clicked = False
            
            card_candidates = await page.locator("[role='button']:visible, mat-card:visible, a:visible, div:visible").all()
            for el in card_candidates:
                box = await el.bounding_box()
                if box and box['x'] > 250 and box['y'] > 180 and box['width'] > 100:
                    txt = (await el.text_content() or '').strip()
                    if agent_clean_title in txt:
                        print(f"   ✓ Found matching agent card at ({box['x']}, {box['y']}): '{txt[:40]}...'. Clicking...", flush=True)
                        await el.click()
                        card_clicked = True
                        break

            if not card_clicked:
                first_card = page.locator("mat-card:visible, [class*='card']:visible, [role='listitem']:visible").first
                if await first_card.is_visible():
                    print("   ✓ Clicking first filtered card result...", flush=True)
                    await first_card.click()
                    card_clicked = True

            assert card_clicked, f"Could not click agent card for '{agent_clean_title}'"
            await asyncio.sleep(action_pause)
            print(f"   ✓ Dedicated agent chat successfully opened for {display_name}.", flush=True)

            # --- STEP 4: Execute 3 prompts sequentially with response sync ---
            print("👉 Step 4: Executing 3 prompts sequentially with response synchronization...", flush=True)
            for turn_idx, prompt_text in enumerate(prompts, 1):
                print(f"\n--- Turn {turn_idx}/3 ---", flush=True)
                print(f"💬 Typing Prompt {turn_idx}: \"{prompt_text}\"", flush=True)
                
                # Scroll down so prompt input box is fully in view
                await scroll_to_bottom_prompt_box(page)
                
                input_box = page.locator("div[contenteditable='true']:visible, textarea:visible").last
                await input_box.wait_for(state="visible", timeout=25000)
                await input_box.click()
                await asyncio.sleep(0.5)
                
                if speed == "normal":
                    await input_box.press_sequentially(prompt_text, delay=keystroke_delay)
                else:
                    await input_box.fill(prompt_text)
                    
                await asyncio.sleep(0.8)
                
                # Left-click prompt box to maintain active focus
                print("👉 Putting mouse focus on prompt input box...", flush=True)
                await input_box.click()
                await asyncio.sleep(0.4)
                
                print(f"📤 Submitting Prompt {turn_idx}...", flush=True)
                send_btn = page.locator("button[aria-label*='Send' i]:visible, button[aria-label*='Submit' i]:visible, button:visible:has(mat-icon:has-text('arrow_upward'))").last
                if await send_btn.is_visible():
                    await send_btn.click()
                else:
                    await input_box.press("Enter")
                
                # Immediately re-focus prompt box during generation so it stays visible
                await asyncio.sleep(0.8)
                input_box_after = page.locator("div[contenteditable='true']:visible, textarea:visible").last
                if await input_box_after.is_visible():
                    try:
                        await input_box_after.click()
                    except Exception:
                        pass
                
                # Active wait for response to appear on screen and finish streaming
                await wait_for_response_completion(page, turn_index=turn_idx, read_pause=read_pause)
                print(f"✅ Turn {turn_idx} response successfully displayed.", flush=True)
                
            print("\n🎉 All 3 agent responses have been received and verified on screen!", flush=True)
            
            # --- STEP 4b: Turn 4 (Generate 4-Slide Executive Text in Agent Chat) ---
            presentation_prompt = canvas_prompt or f"Create a 4-slide executive presentation summarizing the {agent_clean_title} analysis, key KPIs, and strategic recommendations."
            print(f"\n--- Turn 4/4 (Executive Slide Synthesis) ---", flush=True)
            print(f"💬 Typing Slide Synthesis Prompt: \"{presentation_prompt}\"", flush=True)
            
            await scroll_to_bottom_prompt_box(page)
            input_box = page.locator("div[contenteditable='true']:visible, textarea:visible").last
            await input_box.wait_for(state="visible", timeout=25000)
            await input_box.click()
            await asyncio.sleep(0.5)
            
            if speed == "normal":
                await input_box.press_sequentially(presentation_prompt, delay=keystroke_delay)
            else:
                await input_box.fill(presentation_prompt)
                
            await asyncio.sleep(0.8)
            print("👉 Putting mouse focus on prompt input box...", flush=True)
            await input_box.click()
            await asyncio.sleep(0.4)
            
            print("📤 Submitting Slide Synthesis Prompt...", flush=True)
            send_btn = page.locator("button[aria-label*='Send' i]:visible, button[aria-label*='Submit' i]:visible, button:visible:has(mat-icon:has-text('arrow_upward'))").last
            if await send_btn.is_visible():
                await send_btn.click()
            else:
                await input_box.press("Enter")
                
            await wait_for_response_completion(page, turn_index=4, timeout_seconds=120, read_pause=4.0)
            print("✅ Turn 4 slide content successfully generated by agent.", flush=True)

            # --- STEP 5: Visual Copy Action (Clipboard Capture) ---
            print("\n👉 Step 5: Finding and clicking Copy button on Turn 4 response...", flush=True)
            copy_buttons = await page.locator("button[aria-label*='Copy' i]:visible, button:has(mat-icon:has-text('content_copy')):visible, button:has([data-icon*='copy']):visible").all()
            copied_text = ""
            if copy_buttons:
                last_copy_btn = copy_buttons[-1]
                box = await last_copy_btn.bounding_box()
                if box:
                    print(f"   ✓ Clicking Copy button at ({box['x']:.0f}, {box['y']:.0f})...", flush=True)
                    await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=10)
                    await asyncio.sleep(0.3)
                    await last_copy_btn.click()
                    await asyncio.sleep(1.0)
                    
            try:
                copied_text = await page.evaluate("navigator.clipboard.readText()")
                if copied_text:
                    print(f"   📋 Successfully read {len(copied_text)} chars from clipboard!", flush=True)
            except Exception as e:
                print(f"   ℹ️ Clipboard read fallback note: {e}", flush=True)
                
            if not copied_text:
                response_containers = await page.locator("[class*='response'], [class*='message-content'], [class*='model-turn']").all()
                if response_containers:
                    copied_text = (await response_containers[-1].text_content() or "").strip()
                    print(f"   📋 Extracted {len(copied_text)} chars from response container.", flush=True)

            # --- STEP 6: Transition to 'New chat' ---
            print("\n👉 Step 6: Clicking 'New chat' on top-left sidebar...", flush=True)
            new_chat_clicked = False
            new_chat_elements = await page.locator("a:visible, button:visible, div[role='button']:visible").all()
            for el in new_chat_elements:
                box = await el.bounding_box()
                if box and box['x'] < 250 and box['y'] < 140:
                    txt = (await el.text_content() or '').strip()
                    if "new chat" in txt.lower():
                        print(f"   ✓ Clicking 'New chat' at ({box['x']:.0f}, {box['y']:.0f})...", flush=True)
                        await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=10)
                        await asyncio.sleep(0.3)
                        await el.click()
                        new_chat_clicked = True
                        break
                        
            if not new_chat_clicked:
                new_chat_btn = page.get_by_text("New chat", exact=False).first
                if await new_chat_btn.is_visible():
                    await new_chat_btn.click()
                    new_chat_clicked = True

            await asyncio.sleep(3.0)

            # --- STEP 7: Select 'Canvas' Mode in Fresh Chat ---
            print("\n👉 Step 7: Activating 'Canvas' mode via Tools menu in fresh chat...", flush=True)
            await activate_canvas_mode(page)

            # --- STEP 8: Paste Slide Synthesis & Submit Presentation Prompt ---
            print("\n👉 Step 8: Pasting slide content and submitting Canvas presentation prompt...", flush=True)
            canvas_input = page.locator("div[contenteditable='true']:visible, textarea:visible").last
            await canvas_input.wait_for(state="visible", timeout=15000)
            await canvas_input.click()
            await asyncio.sleep(0.5)

            full_canvas_prompt = f"create a 4 slide presentation with below content:\n\n{copied_text}"
            print(f"   📋 Pasting {len(full_canvas_prompt)} chars into Canvas prompt box...", flush=True)
            await canvas_input.fill(full_canvas_prompt)
            await asyncio.sleep(1.5)

            submit_btn = page.locator("button[aria-label*='Send' i]:visible, button[aria-label*='Submit' i]:visible, button:visible:has(mat-icon:has-text('arrow_upward'))").last
            if await submit_btn.is_visible():
                await submit_btn.click()
            else:
                await canvas_input.press("Enter")

            # Active wait for Canvas presentation generation
            print("⏳ Waiting for Canvas presentation to generate...", flush=True)
            await wait_for_response_completion(page, turn_index=2, timeout_seconds=150, read_pause=5.0)

            # --- STEP 9: Showcase 4 Slides in Canvas View via Bottom Thumbnail Rail ---
            await showcase_canvas_presentation(page, num_slides=4, slide_pause=2.5, resolution=resolution)

            print("\n🎉 Multi-turn responses and Canvas presentation completed on screen!", flush=True)

            # --- STEP 10: Mouse scroll walkthrough of conversation and Canvas artifact ---
            await smooth_mouse_scroll_walkthrough(page, resolution=resolution)

            print("\n🏁 Finalizing video recording session...", flush=True)
            await asyncio.sleep(2.0)
            
        except Exception as e:
            print(f"❌ Recording error: {e}", flush=True)
        finally:
            await context.close()
            print("🚪 Browser closed.", flush=True)
            
    recorded_videos = list(temp_video_dir.glob("*.webm"))
    if recorded_videos:
        raw_video = recorded_videos[0]
        if video_format == "mp4":
            converted = convert_webm_to_mp4(raw_video, target_video_file)
            if not converted:
                print("⚠️ Falling back to raw WebM file.", flush=True)
                shutil.move(str(raw_video), str(domain_output_dir / f"{agent_name}.webm"))
                target_video_file = domain_output_dir / f"{agent_name}.webm"
        else:
            shutil.move(str(raw_video), str(target_video_file))
            
        shutil.rmtree(str(temp_video_dir), ignore_errors=True)
        print(f"\n🎥 Video successfully saved to: {target_video_file} ({target_video_file.stat().st_size / 1024 / 1024:.2f} MB)", flush=True)
        try:
            generate_html_showcase(agent_name=agent_name, domain=domain, output_dir=output_dir)
        except Exception as he:
            print(f"⚠️ Warning generating HTML demo showcase: {he}", flush=True)
    else:
        print("⚠️ No video file generated.", flush=True)
        
    return target_video_file


def main():
    parser = argparse.ArgumentParser(description="Generic Agent Demo Video Recorder for Gemini Enterprise")
    parser.add_argument("--name", type=str, help="Target agent name (e.g. cart_checkout_analytics)")
    parser.add_argument("--domain", type=str, help="Target retail domain (e.g. e_commerce). Auto-discovered if omitted.")
    parser.add_argument("--all", action="store_true", help="Record all agents in the specified domain (or all domains)")
    parser.add_argument("--speed", choices=["normal", "fast"], default="normal", help="Pacing speed (default: normal)")
    parser.add_argument("--format", choices=["mp4", "webm"], default="mp4", help="Video output format (default: mp4)")
    parser.add_argument("--resolution", choices=["1080p", "720p"], default="1080p", help="Video recording resolution (default: 1080p)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (default is headed)")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "demos" / "gemini-enterprise", help="Base output directory for recorded videos")
    parser.add_argument("--profile", type=str, default=DEFAULT_CHROME_PROFILE_DIR, help="Chrome profile directory name (default: Profile 2)")
    parser.add_argument("--url", type=str, default=DEFAULT_GE_URL, help="Gemini Enterprise URL (default: GEMINI_ENTERPRISE_URL env var)")
    parser.add_argument("--canvas-prompt", type=str, default=None, help="Custom prompt for Turn 4 Canvas presentation (default: dynamic template based on agent title)")
    parser.add_argument("--user-data-dir", type=Path, default=None, help="Custom Chrome user data directory path for parallel worker isolation (default: ~/.config/google-chrome-demo-recorder)")
    parser.add_argument("--dry-run", action="store_true", help="Validate prompt parsing without launching the browser")
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.url:
        parser.error("GEMINI_ENTERPRISE_URL must be set in .env or passed via --url")
        
    if not args.name and not args.all:
        parser.error("Must provide either --name <agent_name> or --all")
        
    agents_to_record = []
    
    if args.name:
        domain = args.domain or resolve_agent_domain(args.name, REPO_ROOT)
        readme = REPO_ROOT / "domains" / domain / "agents" / args.name / "README.md"
        prompts = parse_agent_prompts(readme)
        agents_to_record.append((args.name, domain, prompts))
    elif args.all:
        if args.domain:
            agent_dirs = sorted((REPO_ROOT / "domains" / args.domain / "agents").glob("*"))
            for ad in agent_dirs:
                if ad.is_dir() and (ad / "README.md").exists():
                    prompts = parse_agent_prompts(ad / "README.md")
                    agents_to_record.append((ad.name, args.domain, prompts))
        else:
            agent_dirs = sorted(REPO_ROOT.glob("domains/*/agents/*"))
            for ad in agent_dirs:
                if ad.is_dir() and (ad / "README.md").exists():
                    domain = ad.parent.parent.name
                    prompts = parse_agent_prompts(ad / "README.md")
                    agents_to_record.append((ad.name, domain, prompts))
                    
    print(f"📋 Found {len(agents_to_record)} agent(s) to record.", flush=True)
    
    for agent_name, domain, prompts in agents_to_record:
        asyncio.run(
            record_single_agent_demo(
                agent_name=agent_name,
                domain=domain,
                prompts=prompts,
                output_dir=args.output_dir,
                speed=args.speed,
                video_format=args.format,
                resolution=args.resolution,
                headless=args.headless,
                chrome_profile_dir=args.profile,
                ge_url=args.url,
                canvas_prompt=args.canvas_prompt,
                user_data_dir=args.user_data_dir,
                dry_run=args.dry_run
            )
        )


if __name__ == "__main__":
    main()
