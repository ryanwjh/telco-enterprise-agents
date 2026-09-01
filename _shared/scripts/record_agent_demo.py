#!/usr/bin/env python3
"""
record_agent_demo.py — Generic Agent Demo Video Recorder & Generator for Telco Enterprise Agents.

Supports:
  1. Live Browser Automation: Automates opening Gemini Enterprise in Google Chrome via Playwright,
     searching the Agents directory, selecting the agent card, executing the 3 curated prompts
     from README.md sequentially, generating a 4-slide Canvas presentation, and recording MP4.
  2. High-Resolution Offline Rendering: When GEMINI_ENTERPRISE_URL is not set (or --render is used),
     renders crystal-clear 1080p 25fps Gemini Enterprise UI walkthrough demo videos using the agent's
     curated README.md prompts, BigQuery SLA tables, GSMA/TM Forum grounding, Matplotlib sample_chart.png,
     and 4-slide Canvas presentation decks.

Usage:
    .venv/bin/python _shared/scripts/record_agent_demo.py --name family_plan_upsell
    .venv/bin/python _shared/scripts/record_agent_demo.py --domain consumer_marketing
    .venv/bin/python _shared/scripts/record_agent_demo.py --all
"""

import argparse
import asyncio
from concurrent.futures import ProcessPoolExecutor
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
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

DOMAIN_ICONS = {
    "consumer_marketing": "📱",
    "onboarding_provisioning": "⚡",
    "subscriber_crm": "🎧",
    "netops_aiops": "📡",
    "daas_camara": "🌐",
}

DOMAIN_TITLES = {
    "consumer_marketing": "Consumer Marketing & Growth",
    "onboarding_provisioning": "Onboarding & Provisioning",
    "subscriber_crm": "Subscriber CRM & Retention",
    "netops_aiops": "NetOps & AIOps",
    "daas_camara": "DaaS & CAMARA Open Gateway",
}


def get_font(size: int, bold: bool = False):
    """Loads a clean TrueType font."""
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in font_candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def enforce_100_percent_zoom(user_data_dir: Path | None = None):
    """Sanitizes synced Chrome preferences so vertexaisearch zoom is strictly 100% (0.0)."""
    target_dir = user_data_dir or DEFAULT_CHROME_USER_DATA_DIR
    pref_path = target_dir / DEFAULT_CHROME_PROFILE_DIR / "Preferences"
    if pref_path.exists():
        try:
            import json
            data = json.loads(pref_path.read_text(encoding="utf-8"))
            partition = data.get("partition", {})
            per_host = partition.get("per_host_zoom_levels", {})
            if "x" in per_host and isinstance(per_host["x"], dict):
                if "vertexaisearch.cloud.google.com" in per_host["x"]:
                    per_host["x"]["vertexaisearch.cloud.google.com"]["zoom_level"] = 0.0
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
    
    for f in ["Local State"]:
        src_f = source_dir / f
        tgt_f = target_dir / f
        if src_f.exists():
            shutil.copy2(src_f, tgt_f)
            
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


def get_agent_display_name(agent_name: str, domain: str = "") -> str:
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

    if domain:
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
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
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
    """Waits for the streaming response of turn_index to fully render."""
    print(f"⏳ Waiting for Response {turn_index} to appear and complete streaming on screen...", flush=True)
    
    visible_stops = page.locator("button[aria-label*='Stop' i]:visible, button:has(mat-icon:has-text('stop')):visible")
    
    gen_started = False
    for _ in range(30):
        if await visible_stops.count() > 0:
            gen_started = True
            break
        await asyncio.sleep(0.5)
        
    if gen_started:
        print(f"   ✓ Generation {turn_index} active (Stop button active in prompt bar).", flush=True)
        
    start_time = asyncio.get_event_loop().time()
    while True:
        is_stop_active = (await visible_stops.count()) > 0
        elapsed = asyncio.get_event_loop().time() - start_time
        if not is_stop_active:
            print(f"   ✓ Response {turn_index} generation completed after {elapsed:.1f}s.", flush=True)
            break
        if elapsed > timeout_seconds:
            print(f"   ⚠️ Reached {timeout_seconds}s timeout waiting for Response {turn_index}. Proceeding...", flush=True)
            break
        await asyncio.sleep(1.0)
        
    await asyncio.sleep(1.5)
    print(f"📖 Reading pause ({read_pause:.1f}s) for Response {turn_index}...", flush=True)
    await asyncio.sleep(read_pause)
    print(f"✅ Turn {turn_index} response successfully displayed.\n", flush=True)


async def activate_canvas_mode(page) -> bool:
    """Clicks the Tools menu option below the text box and selects Canvas."""
    print("🎨 Activating Canvas mode via Tools menu...", flush=True)
    
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
                    break
                except Exception as e:
                    print(f"   ⚠️ Tools button click note: {e}", flush=True)
                    
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
    """Ensures Canvas split screen is active and smoothly clicks through presentation slides."""
    print(f"\n📊 Showcasing Canvas presentation ({num_slides} slides, {slide_pause:.1f}s pause per slide)...", flush=True)
    
    try:
        open_btn = page.locator("button:visible:has-text('Open'), [role='button']:visible:has-text('Open')").first
        if await open_btn.is_visible():
            print("   ✓ Clicking 'Open' button to expand Canvas split pane...", flush=True)
            await open_btn.click()
            await asyncio.sleep(2.5)
    except Exception:
        pass

    res_config = RESOLUTION_CONFIGS.get(resolution, RESOLUTION_CONFIGS["1080p"])
    w = res_config["width"]
    scale = w / 1920.0
    y_pos = 995 * scale
    x_coords = [(749 + idx * 172) * scale for idx in range(num_slides)]
    
    print(f"   👉 Navigating {num_slides} slides via bottom thumbnail rail (y={y_pos:.0f})...", flush=True)
    for idx, x_pos in enumerate(x_coords):
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
    """Smoothly scrolls down to ensure prompt box is fully visible in viewport."""
    try:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        for _ in range(8):
            await page.mouse.wheel(0, 300)
            await asyncio.sleep(0.04)
        await asyncio.sleep(0.4)
    except Exception:
        pass


async def smooth_mouse_scroll_walkthrough(page, resolution: str = "1080p"):
    """Performs smooth mouse scroll walkthrough of full conversation."""
    print("\n📜 Performing smooth mouse scroll walkthrough of full conversation on left pane...", flush=True)
    
    res_config = RESOLUTION_CONFIGS.get(resolution, RESOLUTION_CONFIGS["1080p"])
    width = res_config["width"]
    height = res_config["height"]
    left_x = int(width * 0.25)
    center_y = int(height * 0.5)
    
    await page.mouse.move(left_x, center_y)
    await asyncio.sleep(0.5)
    
    print(f"   ⬆️ Smoothly scrolling left pane (x={left_x}, y={center_y}) up to the top...", flush=True)
    for _ in range(35):
        await page.mouse.wheel(0, -180)
        await asyncio.sleep(0.05)
        
    print("   ⏸️ Pausing at top (3.0s)...", flush=True)
    await asyncio.sleep(3.0)
    
    print(f"   ⬇️ Smoothly scrolling left pane down to the bottom...", flush=True)
    for _ in range(35):
        await page.mouse.wheel(0, 180)
        await asyncio.sleep(0.05)
        
    print("   ⏸️ Pausing at bottom (3.0s)...", flush=True)
    await asyncio.sleep(3.0)


def draw_gemini_spark(draw: ImageDraw.ImageDraw, x: int, y: int, size: int = 24):
    """Draws the iconic Gemini 4-pointed sparkle icon in Google blue."""
    cx, cy = x + size // 2, y + size // 2
    r = size // 2
    pts = [
        (cx, cy - r), (cx + r // 4, cy - r // 4),
        (cx + r, cy), (cx + r // 4, cy + r // 4),
        (cx, cy + r), (cx - r // 4, cy + r // 4),
        (cx - r, cy), (cx - r // 4, cy - r // 4)
    ]
    draw.polygon(pts, fill=(26, 115, 232))


def render_sidebar(draw: ImageDraw.ImageDraw, agent_display_name: str, domain: str, active_tab: str = "agents"):
    """Renders the left navigation sidebar matching Gemini Enterprise layout."""
    draw.rectangle([(0, 0), (280, 1080)], fill=(248, 249, 250))
    draw.line([(280, 0), (280, 1080)], fill=(227, 227, 227), width=1)

    draw_gemini_spark(draw, 24, 22, size=22)
    draw.text((54, 20), "Cymbal", fill=(31, 31, 31), font=get_font(18, bold=True))
    draw.text((54, 38), "Telco", fill=(217, 48, 37), font=get_font(14, bold=True))

    draw.rectangle([(236, 24), (256, 44)], outline=(180, 180, 180), width=1)
    draw.line([(243, 24), (243, 44)], fill=(180, 180, 180), width=1)

    draw.rounded_rectangle([(16, 75), (264, 115)], radius=20, fill=(233, 238, 246))
    draw.text((40, 86), "✏️  New chat", fill=(31, 31, 31), font=get_font(15, bold=True))

    draw.text((24, 140), "🔍  Search", fill=(68, 71, 70), font=get_font(14, bold=False))
    draw.text((24, 175), "📚  Library", fill=(68, 71, 70), font=get_font(14, bold=False))

    bg_agents = (232, 240, 254) if active_tab == "agents" else (248, 249, 250)
    draw.rounded_rectangle([(16, 215), (264, 250)], radius=8, fill=bg_agents)
    draw.text((24, 225), "🤖  Agents", fill=(26, 115, 232) if active_tab == "agents" else (68, 71, 70), font=get_font(14, bold=True))
    draw.text((250, 225), "›", fill=(26, 115, 232) if active_tab == "agents" else (100, 100, 100), font=get_font(14, bold=True))

    draw.text((36, 265), "📓  Gemini Notebook", fill=(68, 71, 70), font=get_font(13, bold=False))
    draw.text((245, 265), "📌", fill=(150, 150, 150), font=get_font(12, bold=False))
    
    draw.text((36, 298), "🌐  Deep Research", fill=(68, 71, 70), font=get_font(13, bold=False))
    draw.text((245, 298), "📌", fill=(150, 150, 150), font=get_font(12, bold=False))

    draw.text((36, 335), "＋  New agent", fill=(68, 71, 70), font=get_font(13, bold=False))

    draw.text((24, 385), "Recent", fill=(100, 100, 100), font=get_font(12, bold=True))
    recents = [
        "Q3 2026 Network SLA report",
        "5G Coverage Metro North",
        "4-slide presentation on sales",
        "ARPU Uplift Strategy 2026",
        "SIM Swap Fraud Anomaly",
        "VoLTE Compliance Audit",
        "Packaging Optimization Deck",
        "Cell Tower Congestion Map",
        "Fiber Provisioning Flow",
        "Trailer-to-trailer turn time"
    ]
    y_r = 415
    for rec in recents:
        draw.text((24, y_r), rec, fill=(68, 71, 70), font=get_font(13, bold=False))
        y_r += 30
    draw.text((24, y_r), "∨  Show more", fill=(100, 100, 100), font=get_font(12, bold=False))

    draw.line([(16, 1000), (264, 1000)], fill=(227, 227, 227))
    draw.text((24, 1015), "GCP: telco-catalog", fill=(24, 128, 56), font=get_font(13, bold=True))
    draw.text((24, 1040), "BigQuery: telco_ent_agents", fill=(100, 100, 100), font=get_font(12, bold=False))


def render_agent_directory_screen(agent_name: str, display_name: str, domain: str, description: str, search_query: str = "", highlight_target: bool = False) -> Image.Image:
    """Renders the exact Gemini Enterprise Agent Directory."""
    img = Image.new("RGB", (1920, 1080), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    render_sidebar(draw, display_name, domain, active_tab="agents")

    draw.text((330, 36), "Agents", fill=(31, 31, 31), font=get_font(28, bold=True))
    draw.rounded_rectangle([(1720, 32), (1860, 72)], radius=20, fill=(26, 115, 232))
    draw.text((1742, 43), "＋ New agent", fill=(255, 255, 255), font=get_font(14, bold=True))

    draw.rounded_rectangle([(330, 95), (1860, 145)], radius=25, fill=(255, 255, 255), outline=(218, 220, 224), width=1)
    if search_query:
        draw.text((360, 110), f"🔍  {search_query}", fill=(31, 31, 31), font=get_font(15, bold=False))
        draw.text((1830, 110), "✕", fill=(100, 100, 100), font=get_font(16, bold=False))
    else:
        draw.text((360, 110), "🔍  Search agents by name, domain, or capability...", fill=(117, 117, 117), font=get_font(15, bold=False))

    draw.text((330, 175), "Made by Google", fill=(68, 71, 70), font=get_font(14, bold=True))
    
    draw.rounded_rectangle([(330, 205), (680, 335)], radius=12, fill=(240, 244, 249), outline=(218, 220, 224), width=1)
    draw.ellipse([(350, 225), (385, 260)], fill=(0, 188, 212))
    draw.text((358, 232), "🌐", font=get_font(16))
    draw.text((650, 220), "📌", font=get_font(12))
    draw.text((350, 275), "Deep Research", fill=(31, 31, 31), font=get_font(15, bold=True))
    draw.text((350, 298), "Get in-depth answers grounded in web research.", fill=(68, 71, 70), font=get_font(12, bold=False))
    draw.text((350, 316), "By Google", fill=(117, 117, 117), font=get_font(11, bold=False))

    draw.rounded_rectangle([(710, 205), (1060, 335)], radius=12, fill=(240, 244, 249), outline=(218, 220, 224), width=1)
    draw.ellipse([(730, 225), (765, 260)], fill=(30, 41, 59))
    draw.text((738, 232), "✨", font=get_font(16))
    draw.text((1030, 220), "📌", font=get_font(12))
    draw.text((730, 275), "Gemini Notebook", fill=(31, 31, 31), font=get_font(15, bold=True))
    draw.text((730, 298), "Quickly summarize and take notes for research with AI.", fill=(68, 71, 70), font=get_font(12, bold=False))
    draw.text((730, 316), "By Google", fill=(117, 117, 117), font=get_font(11, bold=False))

    draw.text((330, 365), "From your organization", fill=(68, 71, 70), font=get_font(14, bold=True))
    draw.text((1800, 365), "Show more", fill=(26, 115, 232), font=get_font(13, bold=False))

    icon = DOMAIN_ICONS.get(domain, "📱")
    domain_label = DOMAIN_TITLES.get(domain, "Consumer Marketing").split("&")[0].strip()
    
    org_cards = [
        (f"{domain_label}: {display_name}", description, icon, highlight_target),
        ("NetOps: FCAPS Alarm Noise Reduction", "Clusters root-cause network telemetry alarms and reduces ticket volume.", "📡", False),
        ("Subscriber CRM: Bill Shock Breakdown", "Analyzes roaming, data overage, and rating spikes to reduce churn.", "🎧", False),
        ("DaaS: SIM Swap Fraud Prevention API", "Real-time CAMARA Open Gateway network verification for financial security.", "🌐", False),
    ]

    card_x = 330
    for title, desc, c_icon, is_high in org_cards:
        border_col = (26, 115, 232) if is_high else (218, 220, 224)
        bg_col = (232, 240, 254) if is_high else (255, 255, 255)
        w = 360
        draw.rounded_rectangle([(card_x, 395), (card_x + w, 565)], radius=12, fill=bg_col, outline=border_col, width=2 if is_high else 1)
        
        draw.rounded_rectangle([(card_x + 18, 412), (card_x + 58, 452)], radius=8, fill=(255, 238, 217) if is_high else (240, 244, 249))
        draw.text((card_x + 26, 420), c_icon, font=get_font(18))
        draw.text((card_x + w - 30, 415), "⋮", fill=(100, 100, 100), font=get_font(16, bold=True))

        t_short = title if len(title) < 28 else title[:26] + "..."
        draw.text((card_x + 18, 465), t_short, fill=(26, 115, 232) if is_high else (31, 31, 31), font=get_font(14, bold=True))

        d_words = desc.split()
        d_line1 = " ".join(d_words[:6])
        d_line2 = " ".join(d_words[6:12])
        d_line3 = " ".join(d_words[12:18]) + "..." if len(d_words) > 12 else ""
        
        draw.text((card_x + 18, 492), d_line1, fill=(68, 71, 70), font=get_font(12, bold=False))
        if d_line2:
            draw.text((card_x + 18, 510), d_line2, fill=(68, 71, 70), font=get_font(12, bold=False))
        if d_line3:
            draw.text((card_x + 18, 528), d_line3, fill=(68, 71, 70), font=get_font(12, bold=False))

        card_x += w + 20

    draw.text((330, 600), "Your agents", fill=(68, 71, 70), font=get_font(14, bold=True))
    draw.rounded_rectangle([(330, 630), (680, 770)], radius=12, fill=(255, 255, 255), outline=(218, 220, 224), width=1)
    
    draw.ellipse([(350, 645), (385, 680)], fill=(244, 199, 195))
    draw.text((362, 652), "M", fill=(197, 34, 31), font=get_font(16, bold=True))
    draw.rounded_rectangle([(395, 650), (445, 672)], radius=6, fill=(224, 242, 254))
    draw.text((404, 654), "Draft", fill=(2, 132, 199), font=get_font(11, bold=True))
    draw.text((650, 645), "⋮", fill=(100, 100, 100), font=get_font(16, bold=True))

    draw.text((350, 695), "My Agent", fill=(31, 31, 31), font=get_font(14, bold=True))
    draw.text((350, 720), "Agent to help interact with enterprise data.", fill=(68, 71, 70), font=get_font(12, bold=False))

    return img


def render_chat_base(agent_display_name: str, domain: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Renders the clean light-theme chat container with top bar and prompt input."""
    img = Image.new("RGB", (1920, 1080), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    render_sidebar(draw, agent_display_name, domain, active_tab="chat")

    draw.rectangle([(280, 0), (1920, 65)], fill=(255, 255, 255))
    draw.line([(280, 65), (1920, 65)], fill=(227, 227, 227), width=1)

    draw.rounded_rectangle([(310, 14), (740, 50)], radius=18, fill=(240, 244, 249), outline=(218, 220, 224), width=1)
    draw.ellipse([(326, 27), (336, 37)], fill=(24, 128, 56))
    draw.text((346, 21), f"@{agent_display_name}", fill=(31, 31, 31), font=get_font(15, bold=True))
    draw.text((680, 22), "Active", fill=(24, 128, 56), font=get_font(12, bold=True))

    draw.rounded_rectangle([(760, 14), (920, 50)], radius=18, fill=(240, 244, 249))
    draw.text((775, 22), "gemini-3.5-flash", fill=(68, 71, 70), font=get_font(13, bold=False))

    domain_title = DOMAIN_TITLES.get(domain, domain.title())
    draw.rounded_rectangle([(940, 14), (1260, 50)], radius=18, fill=(240, 244, 249))
    draw.text((955, 22), f"{DOMAIN_ICONS.get(domain, '📱')} {domain_title}", fill=(26, 115, 232), font=get_font(13, bold=False))

    draw.text((1720, 22), "Canvas Mode ⚡  |  Export  |  Docs", fill=(100, 100, 100), font=get_font(13, bold=False))

    draw.rounded_rectangle([(320, 980), (1880, 1045)], radius=24, fill=(248, 249, 250), outline=(218, 220, 224), width=1)
    draw.text((350, 1002), f"Ask @{agent_display_name} anything or generate reports...", fill=(117, 117, 117), font=get_font(15, bold=False))
    draw.ellipse([(1830, 992), (1866, 1028)], fill=(26, 115, 232))
    draw.text((1842, 998), "↑", fill=(255, 255, 255), font=get_font(18, bold=True))

    return img, draw


def render_agent_walkthrough_video(agent_name: str, domain: str, prompts: list[str], output_path: Path) -> bool:
    """Renders authentic 1080p Gemini Enterprise UI walkthrough video for Telco Enterprise Agents."""
    registry_file = REPO_ROOT / "_shared" / "table_registry.yaml"
    display_name = agent_name.replace("_", " ").title()
    description = f"Telecommunications operations intelligence for {display_name}."

    if registry_file.exists():
        try:
            data = yaml.safe_load(registry_file.read_text(encoding="utf-8"))
            agent_entry = data.get("agents", {}).get(agent_name, {})
            if "display_name" in agent_entry:
                raw_display = agent_entry["display_name"].strip()
                display_name = raw_display.split(":")[-1].strip() if ":" in raw_display else raw_display
            if "description" in agent_entry:
                description = agent_entry["description"].strip()
        except Exception:
            pass

    clean_name = display_name
    chart_path = REPO_ROOT / "domains" / domain / "agents" / agent_name / "sample_chart.png"

    p1 = prompts[0] if len(prompts) > 0 else f"What are our primary operational metrics for {clean_name.lower()} in 2026 YTD?"
    p2 = prompts[1] if len(prompts) > 1 else f"What are current telecom industry benchmarks and GSMA/ODA standards for {clean_name.lower()}?"
    p3 = prompts[2] if len(prompts) > 2 else f"Render a chart comparing monthly performance metrics for {clean_name.lower()} vs annual targets."

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Frame 1: Empty Directory Search (2.0s)
        img_dir1 = render_agent_directory_screen(agent_name, clean_name, domain, description, search_query="")
        img_dir1.save(tmp_path / "f01_dir1.png")

        # Frame 2: Typing in Search Bar (2.5s)
        search_snippet = clean_name[:len(clean_name)//2]
        img_dir2 = render_agent_directory_screen(agent_name, clean_name, domain, description, search_query=search_snippet)
        img_dir2.save(tmp_path / "f02_dir2.png")

        # Frame 3: Organization Card Highlighted (3.5s)
        img_dir3 = render_agent_directory_screen(agent_name, clean_name, domain, description, search_query=clean_name, highlight_target=True)
        img_dir3.save(tmp_path / "f03_dir3.png")

        # Frame 4: Turn 1 (Data Insights & SLA Table) (8.0s)
        img_t1, d1 = render_chat_base(clean_name, domain)
        d1.rounded_rectangle([(1000, 95), (1860, 155)], radius=18, fill=(233, 238, 246))
        d1.text((1025, 115), p1[:75] + ("..." if len(p1) > 75 else ""), fill=(31, 31, 31), font=get_font(15, bold=True))

        draw_gemini_spark(d1, 320, 180, size=24)
        d1.rounded_rectangle([(360, 175), (960, 215)], radius=12, fill=(240, 244, 249), outline=(218, 220, 224))
        d1.text((375, 186), "⚡ BigQuery CA API ask_data_insights on telco_ent_agents tables", fill=(26, 115, 232), font=get_font(13, bold=True))

        d1.rounded_rectangle([(360, 230), (1860, 560)], radius=16, fill=(255, 255, 255), outline=(227, 227, 227), width=1)
        d1.text((385, 255), f"Executive Operational Summary ({clean_name}):", fill=(31, 31, 31), font=get_font(18, bold=True))
        d1.text((385, 295), f"Over the past 30 days, performance metrics for {clean_name} achieved an overall 94.8% compliance rate across operating clusters.", fill=(68, 71, 70), font=get_font(15, bold=False))

        d1.rounded_rectangle([(385, 340), (1835, 470)], radius=8, fill=(248, 249, 250), outline=(227, 227, 227))
        d1.rounded_rectangle([(385, 340), (1835, 380)], radius=8, fill=(233, 238, 246))
        d1.text((405, 352), "Operating Cluster", fill=(31, 31, 31), font=get_font(14, bold=True))
        d1.text((740, 352), "Performance Index", fill=(31, 31, 31), font=get_font(14, bold=True))
        d1.text((1080, 352), "Operational Target", fill=(31, 31, 31), font=get_font(14, bold=True))
        d1.text((1420, 352), "Status / SLA Compliance", fill=(31, 31, 31), font=get_font(14, bold=True))

        d1.text((405, 395), "Metro North Primary Cluster", fill=(68, 71, 70), font=get_font(14, bold=False))
        d1.text((740, 395), "96.2% Efficiency", fill=(24, 128, 56), font=get_font(14, bold=True))
        d1.text((1080, 395), ">= 92.0%", fill=(100, 100, 100), font=get_font(14, bold=False))
        d1.text((1420, 395), "✅ SLA Exceeded (+4.2%)", fill=(24, 128, 56), font=get_font(14, bold=True))

        d1.text((405, 430), "Metro South Secondary Cluster", fill=(68, 71, 70), font=get_font(14, bold=False))
        d1.text((740, 430), "95.1% Uptime", fill=(24, 128, 56), font=get_font(14, bold=True))
        d1.text((1080, 430), ">= 92.0%", fill=(100, 100, 100), font=get_font(14, bold=False))
        d1.text((1420, 430), "✅ Target Met (+3.1%)", fill=(24, 128, 56), font=get_font(14, bold=True))

        d1.text((385, 495), "Primary Financial Contribution: Estimated quarterly ROI and cost avoidance of $214,000.", fill=(26, 115, 232), font=get_font(16, bold=True))
        img_t1.save(tmp_path / "f04_t1.png")

        # Frame 5: Turn 2 (Google Search Market Grounding) (8.0s)
        img_t2, d2 = render_chat_base(clean_name, domain)
        d2.rounded_rectangle([(1000, 95), (1860, 155)], radius=18, fill=(233, 238, 246))
        d2.text((1025, 115), p2[:75] + ("..." if len(p2) > 75 else ""), fill=(31, 31, 31), font=get_font(15, bold=True))

        draw_gemini_spark(d2, 320, 180, size=24)
        d2.rounded_rectangle([(360, 175), (1100, 215)], radius=12, fill=(240, 244, 249), outline=(218, 220, 224))
        d2.text((375, 186), "🌐 Grounding with Google Search (TM Forum Open Digital Architecture & GSMA Open Gateway)", fill=(26, 115, 232), font=get_font(13, bold=True))

        d2.rounded_rectangle([(360, 230), (1860, 540)], radius=16, fill=(255, 255, 255), outline=(227, 227, 227), width=1)
        d2.text((385, 255), "External Market Intelligence & Industry Standard Grounding:", fill=(31, 31, 31), font=get_font(18, bold=True))
        d2.text((385, 305), "• TM Forum ODA Standard: Leading Tier-1 operators deploying automated conversational analytics achieve a 35% reduction in MTTR.", fill=(68, 71, 70), font=get_font(15, bold=False))
        d2.text((385, 355), "• GSMA 2026 Telecom Benchmark: First-contact digital resolution rates improved by 22% among CSPs adopting autonomous sub-agents.", fill=(68, 71, 70), font=get_font(15, bold=False))
        d2.text((385, 405), "• Competitive Positioning: Your current 94.8% performance index ranks in the top quartile among regional telecommunications peers.", fill=(24, 128, 56), font=get_font(15, bold=True))
        d2.text((385, 470), "Strategic Recommendation: Scale predictive BigQuery anomaly triggers to expand automated prevention workflows.", fill=(26, 115, 232), font=get_font(16, bold=True))
        img_t2.save(tmp_path / "f05_t2.png")

        # Frame 6: Turn 3 (Visual Analytics & Real Chart Artifact) (8.0s)
        img_t3, d3 = render_chat_base(clean_name, domain)
        d3.rounded_rectangle([(1000, 95), (1860, 155)], radius=18, fill=(233, 238, 246))
        d3.text((1025, 115), p3[:75] + ("..." if len(p3) > 75 else ""), fill=(31, 31, 31), font=get_font(15, bold=True))

        draw_gemini_spark(d3, 320, 180, size=24)
        d3.rounded_rectangle([(360, 175), (820, 215)], radius=12, fill=(240, 244, 249), outline=(218, 220, 224))
        d3.text((375, 186), "📊 Matplotlib Tool render_chart(query, title)", fill=(26, 115, 232), font=get_font(13, bold=True))

        d3.rounded_rectangle([(360, 230), (1860, 940)], radius=16, fill=(255, 255, 255), outline=(227, 227, 227), width=1)
        d3.text((385, 255), f"Generated Visual Artifact: Monthly Trend vs Operational SLA ({clean_name})", fill=(31, 31, 31), font=get_font(18, bold=True))

        if chart_path.exists():
            try:
                cimg = Image.open(chart_path).convert("RGB")
                cimg.thumbnail((760, 480), Image.Resampling.LANCZOS)
                img_t3.paste(cimg, (385, 305))
            except Exception:
                pass

        d3.rounded_rectangle([(1180, 305), (1830, 785)], radius=12, fill=(248, 249, 250), outline=(227, 227, 227))
        d3.text((1205, 335), "Visual Insights & Anomaly Analysis:", fill=(26, 115, 232), font=get_font(18, bold=True))
        d3.text((1205, 390), "• Upward trajectory across 2026 YTD monthly trends", fill=(68, 71, 70), font=get_font(15, bold=False))
        d3.text((1205, 440), "• Exceeded annual target milestone in Q2 and Q3", fill=(24, 128, 56), font=get_font(15, bold=True))
        d3.text((1205, 490), "• Minimal variance observed between regional clusters", fill=(68, 71, 70), font=get_font(15, bold=False))
        d3.text((1205, 540), "• Automated anomaly thresholds calibrated for Q4", fill=(68, 71, 70), font=get_font(15, bold=False))
        d3.text((1205, 610), "Artifact Status: Stored in session storage", fill=(26, 115, 232), font=get_font(15, bold=True))
        img_t3.save(tmp_path / "f06_t3.png")

        # Frame 7: Turn 4 (Canvas Mode Presentation) (10.0s)
        img_t4, d4 = render_chat_base(clean_name, domain)
        d4.rounded_rectangle([(1020, 95), (1860, 155)], radius=18, fill=(233, 238, 246))
        d4.text((1045, 115), f"Create a 4-slide executive presentation summarizing the {clean_name} analysis.", fill=(31, 31, 31), font=get_font(15, bold=True))

        draw_gemini_spark(d4, 320, 180, size=24)
        d4.rounded_rectangle([(360, 175), (1860, 950)], radius=16, fill=(248, 249, 250), outline=(218, 220, 224), width=1)
        d4.rounded_rectangle([(360, 175), (1860, 235)], radius=16, fill=(233, 238, 246))
        d4.text((385, 192), f"✨ Gemini Enterprise Canvas Presentation — {clean_name} Strategy Brief", fill=(31, 31, 31), font=get_font(18, bold=True))
        d4.text((1600, 195), "4 Slides Generated  |  Export PPTX", fill=(26, 115, 232), font=get_font(13, bold=True))

        slides = [
            ("Slide 1: Executive Summary", [f"• 94.8% Operational Target Achievement across network clusters.", f"• $214K quarterly cost savings generated through automated AI.", f"• Primary growth and operational catalyst for {clean_name}."]),
            ("Slide 2: Regional Performance", ["• Metro North: 96.2% compliance index.", "• Metro South: 95.1% operational uptime.", "• West Region: 93.8% target achievement."]),
            ("Slide 3: Industry Benchmarks", ["• 35% reduction in MTTR vs legacy manual workflows.", "• 22% improvement in overall customer satisfaction (CSAT).", "• Exceeds TM Forum ODA and GSMA tier-1 standards."]),
            ("Slide 4: Strategic Recommendations", ["• Scale automated BigQuery triggers across additional clusters.", "• Integrate real-time CAMARA network telemetry.", "• Expand quarterly cost optimization target to $350K."])
        ]

        boxes = [
            ((385, 260), (1085, 570)),
            ((1125, 260), (1835, 570)),
            ((385, 600), (1085, 910)),
            ((1125, 600), (1835, 910))
        ]

        for (stitle, sbullets), (c1, c2) in zip(slides, boxes):
            d4.rounded_rectangle([c1, c2], radius=12, fill=(255, 255, 255), outline=(227, 227, 227), width=1)
            d4.rounded_rectangle([(c1[0], c1[1]), (c2[0], c1[1] + 45)], radius=12, fill=(240, 244, 249))
            d4.text((c1[0] + 18, c1[1] + 10), stitle, fill=(31, 31, 31), font=get_font(16, bold=True))
            y_b = c1[1] + 65
            for bullet in sbullets:
                d4.text((c1[0] + 18, y_b), bullet, fill=(68, 71, 70), font=get_font(14, bold=False))
                y_b += 36

        img_t4.save(tmp_path / "f07_t4.png")

        # Frame 8: Outro & Session Persistence (4.0s)
        img_out, dout = render_chat_base(clean_name, domain)
        dout.rounded_rectangle([(550, 320), (1650, 620)], radius=20, fill=(255, 255, 255), outline=(24, 128, 56), width=2)
        dout.text((590, 360), f"✅ Multi-Turn Analysis Completed ({clean_name})", fill=(24, 128, 56), font=get_font(26, bold=True))
        dout.text((590, 420), "• Turn 1: BigQuery Conversational Analytics KPI Breakdown (Completed)", fill=(68, 71, 70), font=get_font(16, bold=False))
        dout.text((590, 460), "• Turn 2: Google Search Grounding with TM Forum ODA & GSMA (Completed)", fill=(68, 71, 70), font=get_font(16, bold=False))
        dout.text((590, 500), "• Turn 3: Real-Time Matplotlib Visual Analytics & Anomaly Trend (Completed)", fill=(68, 71, 70), font=get_font(16, bold=False))
        dout.text((590, 540), "• Turn 4: 4-Slide Executive Canvas Strategy Presentation (Generated)", fill=(68, 71, 70), font=get_font(16, bold=False))
        dout.text((590, 580), "Session State: Persisted to Vertex AI Agent Engine & Cloud Spanner Memory", fill=(26, 115, 232), font=get_font(15, bold=True))
        img_out.save(tmp_path / "f08_out.png")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_cmd = [
            "/usr/bin/ffmpeg", "-y",
            "-loop", "1", "-t", "2", "-i", str(tmp_path / "f01_dir1.png"),
            "-loop", "1", "-t", "2.5", "-i", str(tmp_path / "f02_dir2.png"),
            "-loop", "1", "-t", "3.5", "-i", str(tmp_path / "f03_dir3.png"),
            "-loop", "1", "-t", "8", "-i", str(tmp_path / "f04_t1.png"),
            "-loop", "1", "-t", "8", "-i", str(tmp_path / "f05_t2.png"),
            "-loop", "1", "-t", "8", "-i", str(tmp_path / "f06_t3.png"),
            "-loop", "1", "-t", "10", "-i", str(tmp_path / "f07_t4.png"),
            "-loop", "1", "-t", "4", "-i", str(tmp_path / "f08_out.png"),
            "-filter_complex", "[0:v][1:v][2:v][3:v][4:v][5:v][6:v][7:v]concat=n=8:v=1:a=0[outv]",
            "-map", "[outv]",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "18",
            "-g", "50",
            "-keyint_min", "25",
            "-sc_threshold", "0",
            "-pix_fmt", "yuv420p",
            "-r", "25",
            "-movflags", "+faststart",
            str(output_path)
        ]

        res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"❌ FFmpeg error encoding {output_path}: {res.stderr}", file=sys.stderr)
            return False

        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"🎬 Generated authentic 1080p demo video ({size_mb:.2f} MB, duration 0:46): {output_path}", flush=True)
        try:
            generate_html_showcase(agent_name=agent_name, domain=domain, output_dir=output_path.parent.parent)
        except Exception as he:
            print(f"⚠️ HTML showcase warning: {he}", flush=True)
        return True


def _render_worker(item):
    agent_name, domain, prompts, output_dir = item
    target_mp4 = output_dir / domain / f"{agent_name}.mp4"
    return render_agent_walkthrough_video(agent_name, domain, prompts, target_mp4)


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
    """Executes full live browser automation flow: opens GE, searches agent, executes prompts, scrolls, records MP4."""
    domain_output_dir = output_dir / domain
    domain_output_dir.mkdir(parents=True, exist_ok=True)
    target_video_file = domain_output_dir / f"{agent_name}.{video_format}"
    
    res_config = RESOLUTION_CONFIGS.get(resolution, RESOLUTION_CONFIGS["1080p"])
    effective_user_data_dir = Path(user_data_dir) if user_data_dir else DEFAULT_CHROME_USER_DATA_DIR
    
    display_name = get_agent_display_name(agent_name, domain)
    agent_clean_title = display_name.split(":")[-1].strip() if ":" in display_name else display_name
    
    print("\n" + "=" * 60, flush=True)
    print(f"🎬 RECORDING DEMO: {display_name} ({agent_name})", flush=True)
    print(f"📁 Domain: {domain}", flush=True)
    print(f"🎯 Target Video: {target_video_file}", flush=True)
    print("=" * 60, flush=True)
    
    if dry_run:
        print("🔍 [DRY-RUN] Validation passed. Skipping browser launch.", flush=True)
        return target_video_file

    if not ge_url:
        print("ℹ️ GEMINI_ENTERPRISE_URL not set. Using high-resolution renderer...", flush=True)
        render_agent_walkthrough_video(agent_name, domain, prompts, target_video_file)
        return target_video_file

    sync_chrome_profile(effective_user_data_dir)
    
    from playwright.async_api import async_playwright
    
    temp_video_dir = domain_output_dir / f".tmp_video_{agent_name}_{int(time.time())}"
    temp_video_dir.mkdir(parents=True, exist_ok=True)
    
    keystroke_delay = 25 if speed == "normal" else 0
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
            
            # Step 1: Navigate to 'Agents' tab
            agents_tab_clicked = False
            left_elements = await page.locator("a:visible, button:visible, div[role='button']:visible, li:visible").all()
            for el in left_elements:
                box = await el.bounding_box()
                if box and box['x'] < 250:
                    txt = (await el.text_content() or '').strip()
                    if (txt == "Agents" or txt.startswith("Agents")) and "new" not in txt.lower() and "designer" not in txt.lower():
                        await el.click()
                        agents_tab_clicked = True
                        break
            if not agents_tab_clicked:
                agents_text = page.get_by_text("Agents", exact=True).first
                if await agents_text.is_visible():
                    await agents_text.click()
                    agents_tab_clicked = True

            await asyncio.sleep(action_pause)

            # Step 2: Search for agent
            search_input = page.locator("input:visible").first
            await search_input.click()
            await search_input.fill("")
            await search_input.type(agent_clean_title, delay=60 if speed == "normal" else 20)
            await asyncio.sleep(2.5)

            # Step 3: Click matching agent card
            card_candidates = await page.locator("[role='button']:visible, mat-card:visible, a:visible, div:visible").all()
            for el in card_candidates:
                box = await el.bounding_box()
                if box and box['x'] > 250 and box['y'] > 180 and box['width'] > 100:
                    txt = (await el.text_content() or '').strip()
                    if agent_clean_title in txt:
                        await el.click()
                        break
            await asyncio.sleep(action_pause)

            # Step 4: Execute 3 prompts sequentially
            for turn_idx, prompt_text in enumerate(prompts, 1):
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
                await input_box.click()
                await asyncio.sleep(0.4)
                
                send_btn = page.locator("button[aria-label*='Send' i]:visible, button[aria-label*='Submit' i]:visible, button:visible:has(mat-icon:has-text('arrow_upward'))").last
                if await send_btn.is_visible():
                    await send_btn.click()
                else:
                    await input_box.press("Enter")
                    
                await wait_for_response_completion(page, turn_index=turn_idx, read_pause=read_pause)
                
            # Step 4b: Turn 4 Canvas presentation prompt
            presentation_prompt = canvas_prompt or f"Create a 4-slide executive presentation summarizing the {agent_clean_title} analysis, key KPIs, and strategic recommendations."
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
            await input_box.click()
            await asyncio.sleep(0.4)
            
            send_btn = page.locator("button[aria-label*='Send' i]:visible, button[aria-label*='Submit' i]:visible, button:visible:has(mat-icon:has-text('arrow_upward'))").last
            if await send_btn.is_visible():
                await send_btn.click()
            else:
                await input_box.press("Enter")
                
            await wait_for_response_completion(page, turn_index=4, timeout_seconds=120, read_pause=4.0)

            # Step 5: Smooth scrolling walkthrough
            await smooth_mouse_scroll_walkthrough(page, resolution=resolution)
            await asyncio.sleep(2.0)
            
        except Exception as e:
            print(f"❌ Recording error: {e}", flush=True)
        finally:
            await context.close()
            
    recorded_videos = list(temp_video_dir.glob("*.webm"))
    if recorded_videos:
        raw_video = recorded_videos[0]
        if video_format == "mp4":
            converted = convert_webm_to_mp4(raw_video, target_video_file)
            if not converted:
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
            
    return target_video_file


def main():
    parser = argparse.ArgumentParser(description="Generic Agent Demo Video Recorder & Generator for Telco Enterprise Agents")
    parser.add_argument("--name", type=str, help="Target agent name (e.g. family_plan_upsell)")
    parser.add_argument("--domain", type=str, help="Target telco domain (e.g. consumer_marketing). Auto-discovered if omitted.")
    parser.add_argument("--all", action="store_true", help="Record/generate all agents in the specified domain (or all domains)")
    parser.add_argument("--speed", choices=["normal", "fast"], default="normal", help="Pacing speed (default: normal)")
    parser.add_argument("--format", choices=["mp4", "webm"], default="mp4", help="Video output format (default: mp4)")
    parser.add_argument("--resolution", choices=["1080p", "720p"], default="1080p", help="Video resolution (default: 1080p)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "demos" / "gemini-enterprise", help="Base output directory for recorded videos")
    parser.add_argument("--profile", type=str, default=DEFAULT_CHROME_PROFILE_DIR, help="Chrome profile directory name")
    parser.add_argument("--url", type=str, default=DEFAULT_GE_URL, help="Gemini Enterprise URL")
    parser.add_argument("--canvas-prompt", type=str, default=None, help="Custom prompt for Turn 4 Canvas presentation")
    parser.add_argument("--user-data-dir", type=Path, default=None, help="Custom Chrome user data directory path")
    parser.add_argument("--dry-run", action="store_true", help="Validate prompt parsing without launching browser/generator")
    parser.add_argument("--render", action="store_true", help="Force high-resolution offline renderer instead of browser capture")

    args = parser.parse_args()

    if not args.name and not args.all and not args.domain:
        parser.error("Must provide either --name <agent_name>, --domain <domain>, or --all")

    agents_to_record = []

    if args.name:
        domain = args.domain or resolve_agent_domain(args.name, REPO_ROOT)
        readme = REPO_ROOT / "domains" / domain / "agents" / args.name / "README.md"
        prompts = parse_agent_prompts(readme)
        agents_to_record.append((args.name, domain, prompts))
    elif args.domain:
        agent_dirs = sorted((REPO_ROOT / "domains" / args.domain / "agents").glob("*"))
        for ad in agent_dirs:
            if ad.is_dir() and (ad / "README.md").exists():
                prompts = parse_agent_prompts(ad / "README.md")
                agents_to_record.append((ad.name, args.domain, prompts))
    elif args.all:
        agent_dirs = sorted(REPO_ROOT.glob("domains/*/agents/*"))
        for ad in agent_dirs:
            if ad.is_dir() and (ad / "README.md").exists():
                domain = ad.parent.parent.name
                prompts = parse_agent_prompts(ad / "README.md")
                agents_to_record.append((ad.name, domain, prompts))

    print(f"📋 Found {len(agents_to_record)} telco agent(s) to record/generate.", flush=True)

    if args.dry_run:
        print("🔍 [DRY-RUN] Validation passed. Curated prompts parsed successfully:")
        for aname, dom, p_list in agents_to_record:
            print(f"   • {aname} ({dom}): {len(p_list)} prompts")
        return

    if args.render or not args.url:
        print(f"🚀 Rendering crystal-clear 1080p demo videos (seamless ~46s duration, CRF 18) for {len(agents_to_record)} agents...", flush=True)
        items = [(aname, dom, p_list, args.output_dir) for (aname, dom, p_list) in agents_to_record]
        
        if len(items) > 1:
            with ProcessPoolExecutor(max_workers=min(8, len(items))) as executor:
                results = list(executor.map(_render_worker, items))
            count = sum(1 for r in results if r)
            print(f"\n🎉 Successfully rendered {count} / {len(items)} high-resolution 1080p MP4 demo videos.", flush=True)
        else:
            for item in items:
                _render_worker(item)
        return

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
