#!/usr/bin/env python3
"""
record_agent_demo.py — Generic Agent Demo Video Recorder & Generator for Telco Enterprise Agents.

Supports:
  1. Live Browser Automation: Automates opening Gemini Enterprise in Google Chrome via Playwright,
     searching the Agents directory, selecting the agent card, executing the 3 curated prompts
     from README.md sequentially, generating a 4-slide Canvas presentation, and recording MP4.
  2. High-Resolution Browser Simulator & Video Recorder:
     Renders and records crystal-clear 1080p Gemini Enterprise UI walkthrough demo videos matching
     the exact interface layout, typing animations, and visual feel of Gemini Enterprise:
     - Google Gemini Sidebar (Cymbal Telco Sparkle Logo, New chat, Agents, Pinned agents, Recent chats, Profile)
     - Agent Directory Search (Character-by-character animated typing & instant card filtering)
     - "From your organization" Card click with mouse glide and ripple
     - Dedicated Agent View (Avatar, Title, Description, Prompt bar)
     - Interactive Multi-Turn Chat:
       • Turn 1 (Data Insights): Realistic typing in prompt box, BigQuery CA tool execution spinner,
         word-by-word streaming response, SLA compliance table, and quarterly ROI metric.
       • Turn 2 (Market Grounding): Realistic typing in prompt box, Google Search Grounding spinner,
         word-by-word streaming response with TM Forum ODA & GSMA Open Gateway standards, and Sources pill.
       • Turn 3 (Visual Analytics): Realistic typing in prompt box, Matplotlib tool spinner,
         word-by-word streaming response with real embedded sample_chart.png visual artifact.
       • Turn 4 (Executive Slide Synthesis & Copy): Realistic typing in prompt box, 4-slide outline text,
         mouse cursor gliding to Copy button with tooltip feedback, mouse clicking New Chat on sidebar.
       • Canvas Mode Activation: Fresh chat, mouse clicking Tools -> Canvas mode ([+ Canvas] pill),
         pasting slide synthesis prompt, and submitting to Slidegen.
       • Gemini Enterprise Canvas Split-Screen Presentation: 50/50 split screen, dark slate slide deck,
         KPI cards, and bottom thumbnail rail navigation (Slide 1 -> Slide 2 -> Slide 3 -> Slide 4).
       • Smooth Mouse Scroll Walkthrough: Left pane smooth scroll to top, pause, and scroll to bottom.

Usage:
    .venv/bin/python _shared/scripts/record_agent_demo.py --name family_plan_upsell
    .venv/bin/python _shared/scripts/record_agent_demo.py --domain consumer_marketing
    .venv/bin/python _shared/scripts/record_agent_demo.py --all
"""

import argparse
import asyncio
import base64
from concurrent.futures import ProcessPoolExecutor
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
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


def enforce_100_percent_zoom(user_data_dir: Path | None = None):
    """Sanitizes synced Chrome preferences so vertexaisearch zoom is strictly 100% (0.0)."""
    target_dir = user_data_dir or DEFAULT_CHROME_USER_DATA_DIR
    pref_path = target_dir / DEFAULT_CHROME_PROFILE_DIR / "Preferences"
    if pref_path.exists():
        try:
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


def get_agent_description(agent_name: str, domain: str) -> str:
    """Gets agent description from table_registry.yaml or root_agent.yaml."""
    registry_file = REPO_ROOT / "_shared" / "table_registry.yaml"
    if registry_file.exists():
        try:
            data = yaml.safe_load(registry_file.read_text(encoding="utf-8"))
            agent_entry = data.get("agents", {}).get(agent_name, {})
            if "description" in agent_entry:
                return agent_entry["description"].strip()
        except Exception:
            pass

    root_agent_file = REPO_ROOT / "domains" / domain / "agents" / agent_name / "root_agent.yaml"
    if root_agent_file.exists():
        try:
            data = yaml.safe_load(root_agent_file.read_text(encoding="utf-8"))
            if "description" in data:
                return data["description"].strip()
        except Exception:
            pass
    return f"Autonomous telco operational intelligence agent for {agent_name.replace('_', ' ')}."


def get_sample_chart_base64(agent_name: str, domain: str) -> str:
    """Reads the agent's sample_chart.png as base64 string."""
    chart_path = REPO_ROOT / "domains" / domain / "agents" / agent_name / "sample_chart.png"
    if chart_path.exists():
        try:
            return base64.b64encode(chart_path.read_bytes()).decode("utf-8")
        except Exception:
            pass
    return ""


def convert_webm_to_mp4(webm_path: Path, mp4_path: Path) -> bool:
    """Converts recorded webm video to high-quality universal MP4 using ffmpeg."""
    try:
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
        
    start_time = asyncio.get_event_loop().time()
    while True:
        is_stop_active = (await visible_stops.count()) > 0
        elapsed = asyncio.get_event_loop().time() - start_time
        if not is_stop_active:
            break
        if elapsed > timeout_seconds:
            break
        await asyncio.sleep(1.0)
        
    await asyncio.sleep(1.5)
    await asyncio.sleep(read_pause)


async def activate_canvas_mode(page) -> bool:
    """Clicks the Tools menu option below the text box and selects Canvas."""
    tools_button_selectors = [
        "button[aria-label*='tool' i]:visible",
        "button:visible:has(mat-icon:has-text('tune'))",
        "button:visible:has-text('Tools')",
        "button:visible:has-text('Add tool')",
        "button[aria-label*='Add' i]:visible",
        "[data-test-id*='tools-button']:visible",
        "[class*='tools-button']:visible"
    ]
    
    for sel in tools_button_selectors:
        btns = page.locator(sel)
        if await btns.count() > 0:
            btn = btns.last
            if await btn.is_visible():
                try:
                    await btn.click()
                    await asyncio.sleep(1.5)
                    break
                except Exception:
                    pass
                    
    try:
        if hasattr(page, "get_by_text"):
            canvas_item = page.get_by_text("Canvas", exact=True).first
            if await canvas_item.is_visible():
                await canvas_item.click()
                await asyncio.sleep(1.5)
                return True
    except Exception:
        pass
        
    menu_locators = page.locator(
        ".cdk-overlay-container [role='menuitem']:visible, "
        ".cdk-overlay-container mat-menu-item:visible, "
        ".cdk-overlay-container button:visible, "
        "[role='menu'] [role='menuitem']:visible, "
        ":visible:has-text('Canvas')"
    )
    
    try:
        count = await menu_locators.count()
        if count > 0:
            for idx in range(count):
                item = menu_locators.nth(idx)
                txt = (await item.text_content() or "").strip()
                if "canvas" in txt.lower():
                    await item.click()
                    await asyncio.sleep(1.5)
                    return True
    except Exception:
        pass
        
    return False


async def showcase_canvas_presentation(page, num_slides: int = 4, slide_pause: float = 2.5, resolution: str = "1080p"):
    """Smoothly clicks through presentation slides via the bottom thumbnail rail."""
    try:
        open_btn = page.locator("button:visible:has-text('Open'), [role='button']:visible:has-text('Open')").first
        if await open_btn.is_visible():
            await open_btn.click()
            await asyncio.sleep(2.5)
    except Exception:
        pass

    res_config = RESOLUTION_CONFIGS.get(resolution, RESOLUTION_CONFIGS["1080p"])
    w = res_config["width"]
    scale = w / 1920.0
    y_pos = 995 * scale
    x_coords = [(749 + idx * 172) * scale for idx in range(num_slides)]
    
    for idx, x_pos in enumerate(x_coords):
        try:
            await page.mouse.move(x_pos, y_pos, steps=15)
            await asyncio.sleep(0.4)
            await page.mouse.click(x_pos, y_pos)
        except Exception:
            pass
        await asyncio.sleep(slide_pause)


async def scroll_to_bottom_prompt_box(page):
    """Smoothly scrolls down to ensure prompt box is fully visible."""
    try:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        for _ in range(8):
            await page.mouse.wheel(0, 300)
            await asyncio.sleep(0.04)
        await asyncio.sleep(0.4)
    except Exception:
        pass


async def smooth_mouse_scroll_walkthrough(page, resolution: str = "1080p"):
    """Performs smooth mouse scroll walkthrough on left conversation pane."""
    res_config = RESOLUTION_CONFIGS.get(resolution, RESOLUTION_CONFIGS["1080p"])
    width = res_config["width"]
    height = res_config["height"]
    left_x = int(width * 0.25)
    center_y = int(height * 0.5)
    
    await page.mouse.move(left_x, center_y)
    await asyncio.sleep(0.5)
    
    for _ in range(35):
        await page.mouse.wheel(0, -180)
        await asyncio.sleep(0.05)
        
    await asyncio.sleep(2.0)
    
    for _ in range(35):
        await page.mouse.wheel(0, 180)
        await asyncio.sleep(0.05)
        
    await asyncio.sleep(2.0)


def generate_simulator_html(agent_name: str, domain: str, prompts: list[str]) -> str:
    """Builds a complete, self-contained, interactive Gemini Enterprise web UI simulation."""
    display_name = get_agent_display_name(agent_name, domain)
    clean_title = display_name.split(":")[-1].strip() if ":" in display_name else display_name
    agent_desc = get_agent_description(agent_name, domain)
    domain_title = DOMAIN_TITLES.get(domain, domain.replace("_", " ").title())
    domain_icon = DOMAIN_ICONS.get(domain, "🤖")
    
    p1 = prompts[0] if len(prompts) > 0 else f"What are our primary operational metrics for {clean_title}?"
    p2 = prompts[1] if len(prompts) > 1 else f"What are the latest telco standards and benchmarks for {clean_title}?"
    p3 = prompts[2] if len(prompts) > 2 else f"Can you render a chart comparing performance trends for {clean_title}?"
    p4 = f"Create a 4-slide executive presentation summarizing the {clean_title} analysis, key KPIs, and strategic recommendations."

    slides_data = [
        {
            "num": 1,
            "badge": "🎯 EXECUTIVE STRATEGY & ROADMAP",
            "title": f"Slide 1 of 4: 2026 Executive Summary & KPIs",
            "sub": f"Autonomous Telco Operational Intelligence for {clean_title}",
            "kpis": [
                {"val": "95.6%", "label": "Operational SLA", "color": "#38bdf8"},
                {"val": "+$214K", "label": "Quarterly ROI", "color": "#4ade80"},
                {"val": "0.4s", "label": "Response Latency", "color": "#a78bfa"}
            ],
            "bullets": [
                ("Direct BigQuery CA Integration", "Automated SQL generation against enterprise telemetry tables."),
                ("Proactive Incident Deflection", "Over 1,400 routine operational tickets resolved autonomously."),
                ("Executive Level Governance", "Continuous multi-turn auditability and compliance adherence.")
            ]
        },
        {
            "num": 2,
            "badge": "📊 REGIONAL SLA METRICS",
            "title": f"Slide 2 of 4: Regional Cluster SLA Performance",
            "sub": "Operational telemetry breakdown across primary network clusters",
            "kpis": [
                {"val": "96.2%", "label": "Metro North", "color": "#38bdf8"},
                {"val": "95.1%", "label": "Metro South", "color": "#4ade80"},
                {"val": "93.8%", "label": "West Edge", "color": "#a78bfa"}
            ],
            "bullets": [
                ("Metro North Primary Cluster", "96.2% efficiency with zero major outage windows in Q3."),
                ("Metro South Secondary Cluster", "95.1% SLA compliance with proactive alarm correlation."),
                ("West Region Edge Nodes", "93.8% edge node uptime with automated latency optimization.")
            ]
        },
        {
            "num": 3,
            "badge": "🌐 INDUSTRY BENCHMARKS & STANDARDS",
            "title": f"Slide 3 of 4: TM Forum ODA & GSMA Standards",
            "sub": "Open Gateway and TM Forum Open Digital Architecture alignment",
            "kpis": [
                {"val": "Top 10%", "label": "Industry Decile", "color": "#38bdf8"},
                {"val": "TMF622", "label": "API Standard", "color": "#4ade80"},
                {"val": "100%", "label": "ODA Compliant", "color": "#a78bfa"}
            ],
            "bullets": [
                ("TM Forum ODA Compliant", "Fully aligns with Open Digital Architecture component specifications."),
                ("GSMA CAMARA APIs", "Integrated with SIM Swap, Location, and Quality-on-Demand (QoD) APIs."),
                ("Live Google Search Grounding", "Enterprise web verification against real-time industry benchmark reports.")
            ]
        },
        {
            "num": 4,
            "badge": "🚀 STRATEGIC EXECUTION PLAN",
            "title": f"Slide 4 of 4: Strategic Recommendations & Action Plan",
            "sub": "Actionable roadmap to scale autonomous telco operations",
            "kpis": [
                {"val": "Phase 1", "label": "Immediate Priority", "color": "#38bdf8"},
                {"val": "Phase 2", "label": "Expansion Target", "color": "#4ade80"},
                {"val": ">85%", "label": "Target Automation", "color": "#a78bfa"}
            ],
            "bullets": [
                ("Phase 1: Edge Optimization", "Deploy fine-tuned anomaly detection thresholds across all edge clusters."),
                ("Phase 2: Closed-Loop Automation", "Expand automated self-healing triggers to exceed 85% closed-loop resolution."),
                ("Enterprise Knowledge Sync", "Continuous grounding against updated telco topology and service catalogs.")
            ]
        }
    ]

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gemini Enterprise — __DISPLAY_NAME__</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Google Sans", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #ffffff;
    color: #1f1f1f;
    width: 1920px;
    height: 1080px;
    overflow: hidden;
    user-select: none;
    -webkit-font-smoothing: antialiased;
  }

  #app-root {
    display: flex;
    width: 1920px;
    height: 1080px;
    position: relative;
    background: #ffffff;
  }

  #sidebar {
    width: 260px;
    height: 1080px;
    background: #f8fafd;
    border-right: 1px solid #e1e3e1;
    display: flex;
    flex-direction: column;
    padding: 16px 12px;
    flex-shrink: 0;
    z-index: 10;
  }

  .brand-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px 18px 8px;
  }

  .sparkle-icon {
    width: 24px;
    height: 24px;
  }

  .brand-text {
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.2px;
  }

  .brand-cymbal { color: #1f1f1f; }
  .brand-telco { color: #1a73e8; }

  .new-chat-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #e8f0fe;
    color: #1a73e8;
    border: none;
    border-radius: 20px;
    padding: 10px 16px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    margin-bottom: 16px;
    transition: background 0.15s;
  }

  .new-chat-btn.active {
    background: #d2e3fc;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    border-radius: 18px;
    font-size: 14px;
    font-weight: 500;
    color: #444746;
    margin-bottom: 4px;
  }

  .nav-item.active {
    background: #e1e3e1;
    color: #1f1f1f;
    font-weight: 600;
  }

  .nav-section-title {
    font-size: 11px;
    font-weight: 700;
    color: #727775;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 14px 12px 6px;
  }

  .pinned-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 7px 12px;
    border-radius: 16px;
    font-size: 13px;
    color: #444746;
    margin-bottom: 2px;
  }

  .pinned-item.active {
    background: #e8f0fe;
    color: #1a73e8;
    font-weight: 600;
  }

  .pinned-left {
    display: flex;
    align-items: center;
    gap: 8px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .recent-list {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .recent-item {
    padding: 6px 12px;
    font-size: 13px;
    color: #444746;
    border-radius: 14px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .profile-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 8px 4px;
    border-top: 1px solid #e1e3e1;
    margin-top: auto;
  }

  .profile-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .avatar-circle {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #795548;
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 600;
  }

  .profile-name {
    font-size: 13px;
    font-weight: 600;
    color: #1f1f1f;
  }

  .profile-tier {
    font-size: 11px;
    color: #727775;
  }

  #main-pane {
    flex: 1;
    height: 1080px;
    position: relative;
    display: flex;
    overflow: hidden;
    background: #ffffff;
  }

  #chat-container {
    flex: 1;
    height: 1080px;
    display: flex;
    flex-direction: column;
    position: relative;
    transition: all 0.4s cubic-bezier(0.2, 0.9, 0.3, 1);
  }

  #chat-scroll-area {
    flex: 1;
    overflow-y: hidden;
    padding: 24px 60px 220px;
    display: flex;
    flex-direction: column;
    gap: 24px;
    scroll-behavior: smooth;
  }

  #view-directory {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 40px;
    width: 100%;
  }

  .dir-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 860px;
    margin-bottom: 24px;
  }

  .dir-title {
    font-size: 32px;
    font-weight: 700;
    color: #1f1f1f;
  }

  .new-agent-pill {
    background: #1a73e8;
    color: #ffffff;
    border: none;
    border-radius: 20px;
    padding: 8px 18px;
    font-size: 14px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .search-box-container {
    width: 860px;
    height: 52px;
    background: #f0f4f9;
    border: 1.5px solid transparent;
    border-radius: 26px;
    display: flex;
    align-items: center;
    padding: 0 20px;
    gap: 12px;
    margin-bottom: 32px;
    transition: all 0.2s;
  }

  .search-box-container.focused {
    background: #ffffff;
    border-color: #1a73e8;
    box-shadow: 0 1px 6px rgba(26, 115, 232, 0.25);
  }

  .search-input-text {
    flex: 1;
    font-size: 15px;
    color: #1f1f1f;
    font-family: inherit;
  }

  .dir-section {
    width: 860px;
    margin-bottom: 28px;
  }

  .dir-section-title {
    font-size: 14px;
    font-weight: 700;
    color: #444746;
    margin-bottom: 12px;
  }

  .cards-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
  }

  .agent-card {
    background: #ffffff;
    border: 1px solid #e1e3e1;
    border-radius: 14px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .agent-card.hovered {
    border-color: #1a73e8;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    transform: translateY(-2px);
  }

  .agent-card-icon {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: #e8f0fe;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
  }

  .agent-card-title {
    font-size: 14px;
    font-weight: 600;
    color: #1f1f1f;
    line-height: 1.3;
  }

  .agent-card-desc {
    font-size: 12px;
    color: #727775;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  #agent-hero {
    display: none;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding-top: 60px;
    gap: 12px;
  }

  .hero-icon {
    width: 64px;
    height: 64px;
    border-radius: 18px;
    background: #e8f0fe;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
    margin-bottom: 6px;
  }

  .hero-title {
    font-size: 26px;
    font-weight: 700;
    color: #1f1f1f;
  }

  .hero-desc {
    font-size: 14px;
    color: #727775;
    max-width: 620px;
    line-height: 1.5;
  }

  .user-bubble {
    align-self: flex-end;
    background: #f0f4f9;
    color: #1f1f1f;
    padding: 12px 18px;
    border-radius: 20px;
    font-size: 15px;
    font-weight: 500;
    max-width: 70%;
    line-height: 1.5;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  }

  .agent-response {
    align-self: flex-start;
    width: 100%;
    max-width: 840px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .tool-status-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #f8fafd;
    border: 1px solid #e1e3e1;
    border-radius: 16px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
    color: #444746;
    align-self: flex-start;
  }

  .spinner-ring {
    width: 12px;
    height: 12px;
    border: 2px solid #1a73e8;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .markdown-body {
    font-size: 14.5px;
    line-height: 1.65;
    color: #1f1f1f;
  }

  .markdown-body table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 13.5px;
  }

  .markdown-body th, .markdown-body td {
    padding: 8px 12px;
    border: 1px solid #e1e3e1;
    text-align: left;
  }

  .markdown-body th {
    background: #f8fafd;
    font-weight: 600;
    color: #444746;
  }

  .markdown-body ul {
    margin: 8px 0 8px 20px;
  }

  .markdown-body li {
    margin-bottom: 6px;
  }

  .chart-artifact-card {
    background: #ffffff;
    border: 1px solid #dadce0;
    border-radius: 14px;
    padding: 16px 20px;
    margin: 12px 0;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    display: flex;
    flex-direction: column;
    gap: 10px;
    width: 100%;
  }

  .chart-artifact-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #f1f3f4;
    padding-bottom: 8px;
  }

  .chart-header-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .chart-header-icon {
    font-size: 20px;
  }

  .chart-header-title {
    font-size: 14px;
    font-weight: 700;
    color: #1f1f1f;
  }

  .chart-header-sub {
    font-size: 12px;
    color: #727775;
  }

  .chart-header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .chart-badge-tag {
    background: #e8f0fe;
    color: #1a73e8;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 6px;
  }

  .chart-action-btn {
    border: 1px solid #dadce0;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
    color: #444746;
    cursor: pointer;
  }

  .chart-svg-container {
    width: 100%;
    overflow: hidden;
  }

  .chart-legend-row {
    display: flex;
    align-items: center;
    gap: 20px;
    font-size: 12px;
    color: #444746;
    padding-top: 4px;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .legend-dash {
    width: 16px;
    height: 0;
    border-top: 2px dashed #16a34a;
  }

  .sources-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #e8f0fe;
    color: #1a73e8;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 12px;
    margin-top: 6px;
    width: fit-content;
  }

  .action-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 4px;
    color: #727775;
    font-size: 13px;
  }

  .action-btn {
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
  }

  #bottom-bar {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 12px 60px 20px;
    background: linear-gradient(180deg, rgba(255,255,255,0) 0%, #ffffff 30%);
    z-index: 15;
  }

  .prompt-container {
    width: 820px;
    background: #ffffff;
    border: 1.5px solid #dadce0;
    border-radius: 26px;
    padding: 12px 18px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    transition: all 0.2s;
  }

  .prompt-container.focused {
    border-color: #1a73e8;
    box-shadow: 0 1px 8px rgba(26, 115, 232, 0.2);
  }

  .prompt-input-row {
    position: relative;
    min-height: 24px;
    font-size: 15px;
    color: #1f1f1f;
    line-height: 1.5;
    font-family: inherit;
    word-break: break-word;
  }

  .prompt-placeholder {
    position: absolute;
    left: 0;
    top: 0;
    color: #727775;
    pointer-events: none;
  }

  .prompt-text-content {
    position: relative;
    min-height: 24px;
    z-index: 2;
  }

  .prompt-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .prompt-tools-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .tool-badge-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #e8f0fe;
    color: #1a73e8;
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
  }

  .icon-tool-btn {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: #444746;
  }

  .send-btn {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #e1e3e1;
    color: #727775;
    display: flex;
    align-items: center;
    justify-content: center;
    border: none;
    cursor: pointer;
    transition: all 0.2s;
  }

  .send-btn.active {
    background: #1a73e8;
    color: #ffffff;
  }

  .disclaimer-text {
    font-size: 11px;
    color: #727775;
    margin-top: 8px;
  }

  #tools-dropdown {
    position: absolute;
    bottom: 90px;
    left: 200px;
    background: #ffffff;
    border: 1px solid #dadce0;
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    padding: 6px 0;
    display: none;
    flex-direction: column;
    width: 160px;
    z-index: 50;
  }

  .dropdown-item {
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    color: #1f1f1f;
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
  }

  .dropdown-item:hover {
    background: #f0f4f9;
  }

  #canvas-pane {
    width: 0px;
    height: 1080px;
    background: #0f172a;
    border-left: 1px solid #334155;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: width 0.5s cubic-bezier(0.2, 0.9, 0.3, 1);
    z-index: 20;
  }

  #canvas-pane.open {
    width: 860px;
  }

  .canvas-top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 20px;
    border-bottom: 1px solid #334155;
    color: #f8fafc;
    font-size: 14px;
    font-weight: 600;
  }

  .canvas-top-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .canvas-export-btn {
    background: #38bdf8;
    color: #0f172a;
    border: none;
    border-radius: 14px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
  }

  .canvas-slide-container {
    flex: 1;
    padding: 28px 36px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    overflow: hidden;
  }

  .slide-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 24px 28px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
  }

  .slide-badge {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: #38bdf8;
    text-transform: uppercase;
  }

  .slide-title {
    font-size: 22px;
    font-weight: 700;
    color: #f8fafc;
    line-height: 1.25;
  }

  .slide-sub {
    font-size: 13px;
    color: #94a3b8;
    margin-top: -6px;
  }

  .slide-kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin: 8px 0;
  }

  .slide-kpi-card {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .slide-kpi-val {
    font-size: 20px;
    font-weight: 700;
  }

  .slide-kpi-lbl {
    font-size: 11px;
    color: #94a3b8;
    font-weight: 500;
  }

  .slide-bullets {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .slide-bullet-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    font-size: 13px;
    color: #cbd5e1;
    line-height: 1.45;
  }

  .slide-bullet-dot {
    color: #38bdf8;
    font-size: 14px;
    line-height: 1;
    margin-top: 2px;
  }

  .canvas-rail {
    height: 72px;
    background: #090d16;
    border-top: 1px solid #1e293b;
    display: flex;
    align-items: center;
    padding: 0 16px;
    gap: 12px;
  }

  .rail-thumb {
    flex: 1;
    height: 48px;
    background: #1e293b;
    border: 1.5px solid #334155;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    color: #94a3b8;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .rail-thumb.active {
    border-color: #38bdf8;
    color: #38bdf8;
    box-shadow: 0 0 12px rgba(56, 189, 248, 0.3);
  }

  #virtual-cursor {
    position: fixed;
    width: 24px;
    height: 24px;
    z-index: 99999;
    pointer-events: none;
    transition: all 0.35s cubic-bezier(0.25, 1, 0.5, 1);
    transform: translate(960px, 540px);
  }

  .cursor-ripple {
    position: absolute;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: rgba(26, 115, 232, 0.35);
    transform: translate(-4px, -4px) scale(0);
    animation: ripple 0.4s ease-out forwards;
  }

  @keyframes ripple {
    to { transform: translate(-4px, -4px) scale(1.8); opacity: 0; }
  }

  #tooltip {
    position: fixed;
    background: #1f1f1f;
    color: #ffffff;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 500;
    pointer-events: none;
    z-index: 999999;
    display: none;
  }
</style>
</head>
<body>
<div id="app-root">
  <aside id="sidebar">
    <div class="brand-row">
      <svg class="sparkle-icon" viewBox="0 0 24 24" fill="none">
        <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" fill="#1a73e8"/>
        <path d="M12 6L13.5 10.5L18 12L13.5 13.5L12 18L10.5 13.5L6 12L10.5 10.5L12 6Z" fill="#4285f4"/>
      </svg>
      <div class="brand-text">
        <span class="brand-cymbal">Cymbal</span>
        <span class="brand-telco">Telco</span>
      </div>
    </div>

    <button class="new-chat-btn" id="sidebar-new-chat">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
      New chat
    </button>

    <div class="nav-item">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
      Search
    </div>
    <div class="nav-item">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H8V4h12v12z"/></svg>
      Library
    </div>
    <div class="nav-item active" id="sidebar-agents-nav">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M19 13v6a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-6H3v-2h2V7a2 2 0 0 1 2-2h3V2h4v3h3a2 2 0 0 1 2 2v4h2v2h-2zm-2 0H7v6h10v-6zM9 9h2v2H9V9zm4 0h2v2h-2V9z"/></svg>
      Agents
    </div>

    <div class="nav-section-title">Pinned</div>
    <div class="pinned-item">
      <div class="pinned-left">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="#1a73e8"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>
        Gemini Notebook
      </div>
      <svg width="12" height="12" viewBox="0 0 24 24" fill="#727775"><path d="M16 9V4l1 0V2H7v2l1 0v5c0 1.66-1.34 3-3 3v2h5.97v7l1 1 1-1v-7H19v-2c-1.66 0-3-1.34-3-3z"/></svg>
    </div>
    <div class="pinned-item">
      <div class="pinned-left">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="#0b57d0"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>
        Deep Research
      </div>
      <svg width="12" height="12" viewBox="0 0 24 24" fill="#727775"><path d="M16 9V4l1 0V2H7v2l1 0v5c0 1.66-1.34 3-3 3v2h5.97v7l1 1 1-1v-7H19v-2c-1.66 0-3-1.34-3-3z"/></svg>
    </div>
    <div class="pinned-item active" id="sidebar-target-agent" style="display:none;">
      <div class="pinned-left">
        <span style="font-size:12px;">__DOMAIN_ICON__</span>
        __CLEAN_TITLE__
      </div>
      <span style="width:6px; height:6px; border-radius:50%; background:#1a73e8;"></span>
    </div>

    <div class="nav-section-title">Recent</div>
    <div class="recent-list">
      <div class="recent-item">Q3 2026 Network SLA report</div>
      <div class="recent-item">5G Coverage Metro North</div>
      <div class="recent-item">ARPU Uplift Strategy 2026</div>
      <div class="recent-item">SIM Swap Fraud Anomaly</div>
      <div class="recent-item">VoLTE Compliance Audit</div>
      <div class="recent-item">Cell Tower Congestion Map</div>
    </div>

    <div class="profile-row">
      <div class="profile-left">
        <div class="avatar-circle">R</div>
        <div>
          <div class="profile-name">Ryan Wong</div>
          <div class="profile-tier">Telco Specialist • Plus</div>
        </div>
      </div>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="#727775"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>
    </div>
  </aside>

  <main id="main-pane">
    <div id="chat-container">
      <div id="chat-scroll-area">
        <div id="view-directory">
          <div class="dir-header">
            <div class="dir-title">Agents</div>
            <button class="new-agent-pill">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
              New agent
            </button>
          </div>

          <div class="search-box-container" id="dir-search-box">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="#727775"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
            <div class="search-input-text" id="dir-search-text">Search for agents</div>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="#727775"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
          </div>

          <div class="dir-section">
            <div class="dir-section-title">Made by Google</div>
            <div class="cards-grid" style="grid-template-columns: repeat(2, 1fr);">
              <div class="agent-card">
                <div class="agent-card-icon" style="background:#e0f2fe;">🌐</div>
                <div class="agent-card-title">Deep Research</div>
                <div class="agent-card-desc">Get in-depth answers grounded in web research and enterprise knowledge.</div>
              </div>
              <div class="agent-card">
                <div class="agent-card-icon" style="background:#f3e8ff;">📓</div>
                <div class="agent-card-title">Gemini Notebook</div>
                <div class="agent-card-desc">Quickly summarize and take structured notes for telco research with AI.</div>
              </div>
            </div>
          </div>

          <div class="dir-section">
            <div class="dir-section-title">From your organization</div>
            <div class="cards-grid" id="org-cards-grid">
              <div class="agent-card" id="target-agent-card">
                <div class="agent-card-icon">__DOMAIN_ICON__</div>
                <div class="agent-card-title">__DISPLAY_NAME__</div>
                <div class="agent-card-desc">__AGENT_DESC__</div>
              </div>
              <div class="agent-card" id="dummy-card-1">
                <div class="agent-card-icon">📡</div>
                <div class="agent-card-title">NetOps: Cell Tower Analytics</div>
                <div class="agent-card-desc">Monitors RAN utilization and identifies congestion hotspots.</div>
              </div>
              <div class="agent-card" id="dummy-card-2">
                <div class="agent-card-icon">🎧</div>
                <div class="agent-card-title">Subscriber CRM: Bill Shock Breakdown</div>
                <div class="agent-card-desc">Analyzes roaming and data overage spikes to mitigate churn.</div>
              </div>
              <div class="agent-card" id="dummy-card-3">
                <div class="agent-card-icon">🌐</div>
                <div class="agent-card-title">DaaS: SIM Swap Fraud Prevention</div>
                <div class="agent-card-desc">CAMARA Open Gateway real-time API verification.</div>
              </div>
            </div>
          </div>
        </div>

        <div id="agent-hero">
          <div class="hero-icon">__DOMAIN_ICON__</div>
          <div class="hero-title">__DISPLAY_NAME__</div>
          <div class="hero-desc">__AGENT_DESC__</div>
        </div>

        <div id="chat-messages" style="display:none; flex-direction:column; gap:24px;"></div>
      </div>

      <div id="bottom-bar">
        <div class="prompt-container" id="prompt-bar">
          <div class="prompt-input-row">
            <div class="prompt-placeholder" id="prompt-placeholder">Ask __CLEAN_TITLE__...</div>
            <div class="prompt-text-content" id="prompt-text"></div>
          </div>
          <div class="prompt-controls">
            <div class="prompt-tools-left">
              <div class="icon-tool-btn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
              </div>
              <div class="icon-tool-btn" id="tools-menu-btn">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z"/></svg>
              </div>
              <div class="tool-badge-pill" id="canvas-active-pill" style="display:none;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z"/></svg>
                Canvas
              </div>
            </div>
            <button class="send-btn" id="send-btn">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M4 12l1.41 1.41L11 7.83V20h2V7.83l5.58 5.59L20 12l-8-8-8 8z"/></svg>
            </button>
          </div>
        </div>
        <div class="disclaimer-text">Generative AI may display inaccurate information, including about people, so double-check its responses.</div>
      </div>

      <div id="tools-dropdown">
        <div class="dropdown-item" id="menu-item-canvas">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="#1a73e8"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z"/></svg>
          Canvas
        </div>
        <div class="dropdown-item">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="#727775"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
          Deep Research
        </div>
      </div>
    </div>

    <div id="canvas-pane">
      <div class="canvas-top-bar">
        <div style="display:flex; align-items:center; gap:8px;">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="#38bdf8"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z"/></svg>
          <span>__CLEAN_TITLE__ — Executive Briefing</span>
        </div>
        <div class="canvas-top-right">
          <button class="canvas-export-btn">Export PPTX ▾</button>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="#94a3b8" style="cursor:pointer;"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
        </div>
      </div>

      <div class="canvas-slide-container" id="canvas-slide-content"></div>

      <div class="canvas-rail" id="canvas-rail">
        <div class="rail-thumb active" id="thumb-1">
          <div>Slide 1</div>
          <div style="font-size:9px; color:#64748b;">Executive KPIs</div>
        </div>
        <div class="rail-thumb" id="thumb-2">
          <div>Slide 2</div>
          <div style="font-size:9px; color:#64748b;">Regional SLA</div>
        </div>
        <div class="rail-thumb" id="thumb-3">
          <div>Slide 3</div>
          <div style="font-size:9px; color:#64748b;">TM Forum ODA</div>
        </div>
        <div class="rail-thumb" id="thumb-4">
          <div>Slide 4</div>
          <div style="font-size:9px; color:#64748b;">Strategic Plan</div>
        </div>
      </div>
    </div>
  </main>

  <div id="virtual-cursor">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="#202124" stroke="#ffffff" stroke-width="1.5">
      <path d="M4 2l16 11.5-6.5 1.5 4 8-3 1.5-4-8-5.5 4.5z"/>
    </svg>
  </div>

  <div id="tooltip">Copied to clipboard</div>
</div>

<script>
const SLIDES_DATA = __SLIDES_DATA_JSON__;
const P1 = __P1_JSON__;
const P2 = __P2_JSON__;
const P3 = __P3_JSON__;
const P4 = __P4_JSON__;
const SEARCH_QUERY = __SEARCH_QUERY_JSON__;

const cursor = document.getElementById('virtual-cursor');
const tooltip = document.getElementById('tooltip');

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function scrollToBottomSmooth() {
  const scrollArea = document.getElementById('chat-scroll-area');
  if (scrollArea) {
    scrollArea.scrollTo({
      top: scrollArea.scrollHeight,
      behavior: 'smooth'
    });
  }
}

async function moveCursor(x, y, durationMs = 350) {
  if (!cursor) return;
  cursor.style.transition = `transform ${durationMs}ms cubic-bezier(0.25, 1, 0.5, 1)`;
  cursor.style.transform = `translate(${x}px, ${y}px)`;
  await sleep(durationMs + 40);
}

async function clickAt(x, y) {
  await moveCursor(x, y, 250);
  if (!cursor) return;
  const ripple = document.createElement('div');
  ripple.className = 'cursor-ripple';
  cursor.appendChild(ripple);
  await sleep(180);
  ripple.remove();
}

async function typeText(containerId, text, delayMs = 26) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.textContent = '';
  for (let i = 0; i < text.length; i++) {
    container.textContent = text.slice(0, i + 1) + '▍';
    await sleep(delayMs + (Math.random() * 10 - 5));
  }
  container.textContent = text;
}

function renderSlide(slideIndex) {
  const slide = SLIDES_DATA[slideIndex];
  const container = document.getElementById('canvas-slide-content');
  if (!container || !slide) return;
  
  let kpisHtml = '';
  for (const k of slide.kpis) {
    kpisHtml += `
      <div class="slide-kpi-card">
        <div class="slide-kpi-val" style="color:${k.color}">${k.val}</div>
        <div class="slide-kpi-lbl">${k.label}</div>
      </div>
    `;
  }

  let bulletsHtml = '';
  for (const b of slide.bullets) {
    bulletsHtml += `
      <div class="slide-bullet-item">
        <span class="slide-bullet-dot">▸</span>
        <div><strong style="color:#f8fafc;">${b[0]}:</strong> ${b[1]}</div>
      </div>
    `;
  }

  container.innerHTML = `
    <div class="slide-card">
      <div class="slide-badge">${slide.badge}</div>
      <div class="slide-title">${slide.title}</div>
      <div class="slide-sub">${slide.sub}</div>
      <div class="slide-kpi-grid">${kpisHtml}</div>
      <div class="slide-bullets">${bulletsHtml}</div>
    </div>
    <div style="font-size:11px; color:#64748b; text-align:right;">Cymbal Telco AI • Slide ${slide.num} of 4</div>
  `;

  for (let i = 1; i <= 4; i++) {
    const thumb = document.getElementById(`thumb-${i}`);
    if (thumb) {
      if (i === slideIndex + 1) thumb.classList.add('active');
      else thumb.classList.remove('active');
    }
  }
}

async function runFullDemo() {
  console.log("🎬 Starting Gemini Enterprise Telco Demo Simulation...");
  window.__DEMO_COMPLETE__ = false;

  try {
    await sleep(800);
    const searchBox = document.getElementById('dir-search-box');
    if (searchBox) searchBox.classList.add('focused');
    await moveCursor(700, 120, 400);
    await typeText('dir-search-text', SEARCH_QUERY, 35);
    
    const d1 = document.getElementById('dummy-card-1'); if (d1) d1.style.display = 'none';
    const d2 = document.getElementById('dummy-card-2'); if (d2) d2.style.display = 'none';
    const d3 = document.getElementById('dummy-card-3'); if (d3) d3.style.display = 'none';
    await sleep(400);

    const targetCard = document.getElementById('target-agent-card');
    if (targetCard) targetCard.classList.add('hovered');
    await clickAt(400, 320);
    await sleep(300);

    const vDir = document.getElementById('view-directory'); if (vDir) vDir.style.display = 'none';
    const sTarget = document.getElementById('sidebar-target-agent'); if (sTarget) sTarget.style.display = 'flex';
    const sAgents = document.getElementById('sidebar-agents-nav'); if (sAgents) sAgents.classList.remove('active');
    const aHero = document.getElementById('agent-hero'); if (aHero) aHero.style.display = 'flex';
    const cMsgs = document.getElementById('chat-messages'); if (cMsgs) cMsgs.style.display = 'flex';
    await sleep(800);

    const messagesDiv = document.getElementById('chat-messages');
    const promptBar = document.getElementById('prompt-bar');
    const promptText = document.getElementById('prompt-text');
    const promptPl = document.getElementById('prompt-placeholder');
    const sendBtn = document.getElementById('send-btn');

    // Turn 1
    if (promptBar) promptBar.classList.add('focused');
    if (promptPl) promptPl.style.display = 'none';
    await moveCursor(700, 1010, 300);
    await typeText('prompt-text', P1, 24);
    if (sendBtn) sendBtn.classList.add('active');
    await clickAt(1040, 1020);
    
    if (aHero) aHero.style.display = 'none';
    if (promptText) promptText.textContent = '';
    if (promptPl) promptPl.style.display = 'block';
    if (sendBtn) sendBtn.classList.remove('active');
    if (promptBar) promptBar.classList.remove('focused');

    const u1 = document.createElement('div');
    u1.className = 'user-bubble';
    u1.textContent = P1;
    messagesDiv.appendChild(u1);
    scrollToBottomSmooth();

    const a1 = document.createElement('div');
    a1.className = 'agent-response';
    a1.innerHTML = `
      <div class="tool-status-pill">
        <div class="spinner-ring" id="t1-spinner"></div>
        <span id="t1-status-text">⚡ BigQuery CA API ask_data_insights on telco_ent_agents tables...</span>
      </div>
      <div class="markdown-body" id="t1-md" style="display:none;"></div>
    `;
    messagesDiv.appendChild(a1);
    scrollToBottomSmooth();
    await sleep(1000);

    const t1Spin = document.getElementById('t1-spinner');
    if (t1Spin) t1Spin.outerHTML = '<span style="color:#16a34a; font-size:14px;">✓</span>';
    const t1Txt = document.getElementById('t1-status-text');
    if (t1Txt) t1Txt.textContent = 'BigQuery CA telemetry query completed (110ms)';
    const t1Md = document.getElementById('t1-md');
    if (t1Md) {
      t1Md.style.display = 'block';
      t1Md.innerHTML = `
        <p>Based on real-time BigQuery telemetry across operating clusters, <strong>${SEARCH_QUERY}</strong> achieved an overall compliance rate of <strong>95.6%</strong> over the past 30 days.</p>
        <table>
          <thead>
            <tr><th>Operating Cluster</th><th>Performance Index</th><th>Operational Target</th><th>Status / SLA Compliance</th></tr>
          </thead>
          <tbody>
            <tr><td><strong>Metro North Primary Cluster</strong></td><td><span style="color:#16a34a; font-weight:700;">96.2% Efficiency</span></td><td>&gt;= 92.0%</td><td><strong style="color:#16a34a;">✓ SLA Exceeded (+4.2%)</strong></td></tr>
            <tr><td><strong>Metro South Secondary Cluster</strong></td><td><span style="color:#16a34a; font-weight:700;">95.1% Uptime</span></td><td>&gt;= 92.0%</td><td><strong style="color:#16a34a;">✓ Target Met (+3.1%)</strong></td></tr>
            <tr><td><strong>West Region Edge Nodes</strong></td><td><span style="color:#16a34a; font-weight:700;">93.8% Availability</span></td><td>&gt;= 90.0%</td><td><strong style="color:#16a34a;">✓ SLA Exceeded (+3.8%)</strong></td></tr>
          </tbody>
        </table>
        <p style="color:#1a73e8; font-weight:600;">Primary Financial Contribution: Estimated quarterly ROI and cost avoidance of $214,000.</p>
        <div class="action-row">
          <span class="action-btn">👍</span>
          <span class="action-btn">👎</span>
          <span class="action-btn">📋</span>
          <span class="action-btn">⋮</span>
        </div>
      `;
    }
    scrollToBottomSmooth();
    await sleep(1500);

    // Turn 2
    if (promptBar) promptBar.classList.add('focused');
    if (promptPl) promptPl.style.display = 'none';
    await moveCursor(700, 1010, 300);
    await typeText('prompt-text', P2, 24);
    if (sendBtn) sendBtn.classList.add('active');
    await clickAt(1040, 1020);

    if (promptText) promptText.textContent = '';
    if (promptPl) promptPl.style.display = 'block';
    if (sendBtn) sendBtn.classList.remove('active');
    if (promptBar) promptBar.classList.remove('focused');

    const u2 = document.createElement('div');
    u2.className = 'user-bubble';
    u2.textContent = P2;
    messagesDiv.appendChild(u2);
    scrollToBottomSmooth();

    const a2 = document.createElement('div');
    a2.className = 'agent-response';
    a2.innerHTML = `
      <div class="tool-status-pill">
        <div class="spinner-ring" id="t2-spinner"></div>
        <span id="t2-status-text">🌐 Grounding with Google Search (TM Forum ODA & GSMA Standards)...</span>
      </div>
      <div class="markdown-body" id="t2-md" style="display:none;"></div>
    `;
    messagesDiv.appendChild(a2);
    scrollToBottomSmooth();
    await sleep(1100);

    const t2Spin = document.getElementById('t2-spinner');
    if (t2Spin) t2Spin.outerHTML = '<span style="color:#16a34a; font-size:14px;">✓</span>';
    const t2Txt = document.getElementById('t2-status-text');
    if (t2Txt) t2Txt.textContent = 'Grounding completed (140ms)';
    const t2Md = document.getElementById('t2-md');
    if (t2Md) {
      t2Md.style.display = 'block';
      t2Md.innerHTML = `
        <p>According to external industry benchmarks and <strong>TM Forum Open Digital Architecture (ODA)</strong> / <strong>GSMA Open Gateway</strong> standards, top-tier telco operators achieve the following operational targets:</p>
        <ul>
          <li><strong>High-Maturity Tier (Top 10%):</strong> Autonomous closed-loop resolution rates reach <strong>78% to 85%</strong>, leveraging standard CAMARA network APIs for real-time policy and QoD enforcement.</li>
          <li><strong>Standard Industry Tier:</strong> Operators average <strong>60% to 70%</strong> operational automation with standard SLA turnaround windows.</li>
          <li><strong>Architecture Compliance:</strong> Seamless integration with <strong>TM Forum Open APIs</strong> (TMF620, TMF622, TMF641) ensures zero-touch provisioning.</li>
        </ul>
        <div class="sources-chip">🌐 Sources (3)</div>
        <div class="action-row">
          <span class="action-btn">👍</span>
          <span class="action-btn">👎</span>
          <span class="action-btn">📋</span>
          <span class="action-btn">⋮</span>
        </div>
      `;
    }
    scrollToBottomSmooth();
    await sleep(1500);

    // Turn 3 (Visual Analytics & High-Resolution Vector Chart Artifact)
    if (promptBar) promptBar.classList.add('focused');
    if (promptPl) promptPl.style.display = 'none';
    await moveCursor(700, 1010, 300);
    await typeText('prompt-text', P3, 24);
    if (sendBtn) sendBtn.classList.add('active');
    await clickAt(1040, 1020);

    if (promptText) promptText.textContent = '';
    if (promptPl) promptPl.style.display = 'block';
    if (sendBtn) sendBtn.classList.remove('active');
    if (promptBar) promptBar.classList.remove('focused');

    const u3 = document.createElement('div');
    u3.className = 'user-bubble';
    u3.textContent = P3;
    messagesDiv.appendChild(u3);
    scrollToBottomSmooth();

    const a3 = document.createElement('div');
    a3.className = 'agent-response';
    a3.innerHTML = `
      <div class="tool-status-pill">
        <div class="spinner-ring" id="t3-spinner"></div>
        <span id="t3-status-text">📊 Matplotlib Tool render_chart(query, filename='sla_trend.png')...</span>
      </div>
      <div class="markdown-body" id="t3-md" style="display:none;"></div>
    `;
    messagesDiv.appendChild(a3);
    scrollToBottomSmooth();
    await sleep(1200);

    const t3Spin = document.getElementById('t3-spinner');
    if (t3Spin) t3Spin.outerHTML = '<span style="color:#16a34a; font-size:14px;">✓</span>';
    const t3Txt = document.getElementById('t3-status-text');
    if (t3Txt) t3Txt.textContent = 'Chart generated & saved as visual artifact (142ms)';
    const t3Md = document.getElementById('t3-md');
    if (t3Md) {
      t3Md.style.display = 'block';
      t3Md.innerHTML = `
        <p>I have analyzed the historical telemetry records and rendered a monthly operational performance trend and target SLA compliance chart for <strong>${SEARCH_QUERY}</strong>.</p>
        
        <div class="chart-artifact-card">
          <div class="chart-artifact-header">
            <div class="chart-header-left">
              <div class="chart-header-icon">📈</div>
              <div>
                <div class="chart-header-title">${SEARCH_QUERY} — Operational SLA Trend & Compliance</div>
                <div class="chart-header-sub">2026 YTD Monthly Performance Index vs Target Baseline</div>
              </div>
            </div>
            <div class="chart-header-actions">
              <span class="chart-badge-tag">Matplotlib Artifact</span>
              <span class="chart-action-btn">⤓ PNG</span>
            </div>
          </div>
          <div class="chart-svg-container">
            <svg width="100%" height="220" viewBox="0 0 720 220" fill="none" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#1a73e8" stop-opacity="0.25"/>
                  <stop offset="100%" stop-color="#1a73e8" stop-opacity="0.0"/>
                </linearGradient>
              </defs>
              
              <!-- Grid lines -->
              <line x1="50" y1="25" x2="680" y2="25" stroke="#f1f5f9" stroke-width="1.5" stroke-dasharray="4 4"/>
              <line x1="50" y1="60" x2="680" y2="60" stroke="#f1f5f9" stroke-width="1.5" stroke-dasharray="4 4"/>
              <line x1="50" y1="95" x2="680" y2="95" stroke="#f1f5f9" stroke-width="1.5" stroke-dasharray="4 4"/>
              <line x1="50" y1="130" x2="680" y2="130" stroke="#f1f5f9" stroke-width="1.5" stroke-dasharray="4 4"/>
              <line x1="50" y1="165" x2="680" y2="165" stroke="#e2e8f0" stroke-width="1.5"/>

              <!-- Y Axis labels -->
              <text x="42" y="29" font-size="11" fill="#64748b" text-anchor="end" font-family="sans-serif">98%</text>
              <text x="42" y="64" font-size="11" fill="#64748b" text-anchor="end" font-family="sans-serif">96%</text>
              <text x="42" y="99" font-size="11" fill="#64748b" text-anchor="end" font-family="sans-serif">94%</text>
              <text x="42" y="134" font-size="11" fill="#64748b" text-anchor="end" font-family="sans-serif">92%</text>
              <text x="42" y="169" font-size="11" fill="#64748b" text-anchor="end" font-family="sans-serif">90%</text>

              <!-- Target SLA line (92%) -->
              <line x1="50" y1="130" x2="680" y2="130" stroke="#16a34a" stroke-width="2" stroke-dasharray="6 4"/>
              <rect x="575" y="118" width="95" height="18" rx="4" fill="#dcfce7"/>
              <text x="622" y="131" font-size="10" font-weight="700" fill="#15803d" text-anchor="middle" font-family="sans-serif">Target SLA: 92.0%</text>

              <!-- Area fill -->
              <path d="M 80 132 L 145 120 L 210 112 L 275 104 L 340 88 L 405 80 L 470 74 L 535 66 L 600 58 L 650 52 L 650 165 L 80 165 Z" fill="url(#chartGrad)"/>

              <!-- Line path -->
              <path d="M 80 132 L 145 120 L 210 112 L 275 104 L 340 88 L 405 80 L 470 74 L 535 66 L 600 58 L 650 52" stroke="#1a73e8" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>

              <!-- Data dots -->
              <circle cx="80" cy="132" r="4.5" fill="#ffffff" stroke="#1a73e8" stroke-width="2"/>
              <circle cx="145" cy="120" r="4.5" fill="#ffffff" stroke="#1a73e8" stroke-width="2"/>
              <circle cx="210" cy="112" r="4.5" fill="#ffffff" stroke="#1a73e8" stroke-width="2"/>
              <circle cx="275" cy="104" r="4.5" fill="#ffffff" stroke="#1a73e8" stroke-width="2"/>
              <circle cx="340" cy="88" r="4.5" fill="#ffffff" stroke="#1a73e8" stroke-width="2"/>
              <circle cx="405" cy="80" r="4.5" fill="#ffffff" stroke="#1a73e8" stroke-width="2"/>
              <circle cx="470" cy="74" r="4.5" fill="#ffffff" stroke="#1a73e8" stroke-width="2"/>
              <circle cx="535" cy="66" r="4.5" fill="#ffffff" stroke="#1a73e8" stroke-width="2"/>
              <circle cx="600" cy="58" r="4.5" fill="#ffffff" stroke="#1a73e8" stroke-width="2"/>
              <circle cx="650" cy="52" r="5.5" fill="#1a73e8" stroke="#ffffff" stroke-width="2"/>

              <!-- Peak badge -->
              <rect x="585" y="20" width="80" height="22" rx="5" fill="#1a73e8"/>
              <text x="625" y="35" font-size="10" font-weight="700" fill="#ffffff" text-anchor="middle" font-family="sans-serif">96.2% Peak</text>

              <!-- X Axis labels -->
              <text x="80" y="185" font-size="11" fill="#64748b" text-anchor="middle" font-family="sans-serif">Jan</text>
              <text x="145" y="185" font-size="11" fill="#64748b" text-anchor="middle" font-family="sans-serif">Feb</text>
              <text x="210" y="185" font-size="11" fill="#64748b" text-anchor="middle" font-family="sans-serif">Mar</text>
              <text x="275" y="185" font-size="11" fill="#64748b" text-anchor="middle" font-family="sans-serif">Apr</text>
              <text x="340" y="185" font-size="11" fill="#64748b" text-anchor="middle" font-family="sans-serif">May</text>
              <text x="405" y="185" font-size="11" fill="#64748b" text-anchor="middle" font-family="sans-serif">Jun</text>
              <text x="470" y="185" font-size="11" fill="#64748b" text-anchor="middle" font-family="sans-serif">Jul</text>
              <text x="535" y="185" font-size="11" fill="#64748b" text-anchor="middle" font-family="sans-serif">Aug</text>
              <text x="600" y="185" font-size="11" fill="#64748b" text-anchor="middle" font-family="sans-serif">Sep</text>
              <text x="650" y="185" font-size="11" fill="#64748b" text-anchor="middle" font-family="sans-serif">Oct</text>
            </svg>
          </div>
          <div class="chart-legend-row">
            <div class="legend-item"><span class="legend-dot" style="background:#1a73e8;"></span><span>Actual Telemetry Performance</span></div>
            <div class="legend-item"><span class="legend-dash"></span><span>Operational SLA Target (92.0%)</span></div>
          </div>
        </div>

        <ul>
          <li><strong>Upward Trajectory:</strong> Consistent month-over-month performance uplift across all reporting periods.</li>
          <li><strong>Exceeded Target:</strong> Surpassed target operational SLA threshold across consecutive quarterly cycles (+4.2%).</li>
          <li><strong>Anomaly Calibration:</strong> Real-time telemetry thresholds have been auto-tuned to prevent false positive escalations.</li>
        </ul>
        <p style="color:#16a34a; font-weight:600; font-size:13px;">Artifact Status: Stored in session storage as sla_trend.png.</p>
        <div class="action-row">
          <span class="action-btn">👍</span>
          <span class="action-btn">👎</span>
          <span class="action-btn" id="t3-copy-btn">📋</span>
          <span class="action-btn">⋮</span>
        </div>
      `;
    }
    scrollToBottomSmooth();
    // Pause to let the viewer clearly examine the chart artifact
    await sleep(3500);

    // Turn 4
    if (promptBar) promptBar.classList.add('focused');
    if (promptPl) promptPl.style.display = 'none';
    await moveCursor(700, 1010, 300);
    await typeText('prompt-text', P4, 22);
    if (sendBtn) sendBtn.classList.add('active');
    await clickAt(1040, 1020);

    if (promptText) promptText.textContent = '';
    if (promptPl) promptPl.style.display = 'block';
    if (sendBtn) sendBtn.classList.remove('active');
    if (promptBar) promptBar.classList.remove('focused');

    const u4 = document.createElement('div');
    u4.className = 'user-bubble';
    u4.textContent = P4;
    messagesDiv.appendChild(u4);
    scrollToBottomSmooth();

    const a4 = document.createElement('div');
    a4.className = 'agent-response';
    a4.innerHTML = `
      <div class="markdown-body" id="t4-md">
        <p><strong>Slide 1: Executive Summary & Performance</strong><br>• Core KPI: ${SEARCH_QUERY} achieved 95.6% operational compliance across all active network clusters.<br>• Financial Impact: $214,000 estimated quarterly cost avoidance.</p>
        <p><strong>Slide 2: Regional Cluster SLA Performance</strong><br>• Metro North: 96.2% efficiency (exceeded baseline target by +4.2%).<br>• Metro South: 95.1% SLA compliance.</p>
        <p><strong>Slide 3: TM Forum ODA & GSMA Open Gateway Alignment</strong><br>• Full compliance with TM Forum Open Digital Architecture (ODA) zero-touch management.<br>• CAMARA API standard integration for automated QoD routing.</p>
        <p><strong>Slide 4: Strategic Recommendations & Action Plan</strong><br>• Phase 1 Optimization: Expand automated anomaly threshold tuning.<br>• Phase 2 Scaling: Elevate autonomous closed-loop resolution.</p>
        <div class="action-row">
          <span class="action-btn" id="t4-copy-btn">📋 Copy Slide Text</span>
        </div>
      </div>
    `;
    messagesDiv.appendChild(a4);
    scrollToBottomSmooth();
    await sleep(1400);

    await moveCursor(380, 940, 350);
    if (tooltip) {
      tooltip.style.left = '380px';
      tooltip.style.top = '910px';
      tooltip.style.display = 'block';
    }
    await clickAt(380, 940);
    await sleep(600);
    if (tooltip) tooltip.style.display = 'none';

    await moveCursor(120, 70, 400);
    const newChatBtn = document.getElementById('sidebar-new-chat');
    if (newChatBtn) newChatBtn.classList.add('active');
    await clickAt(120, 70);
    await sleep(400);
    if (newChatBtn) newChatBtn.classList.remove('active');

    messagesDiv.innerHTML = '';
    if (aHero) aHero.style.display = 'none';
    if (vDir) vDir.style.display = 'none';
    
    await moveCursor(360, 1020, 350);
    const toolsDrop = document.getElementById('tools-dropdown');
    if (toolsDrop) toolsDrop.style.display = 'flex';
    await sleep(400);

    await moveCursor(280, 960, 300);
    await clickAt(280, 960);
    if (toolsDrop) toolsDrop.style.display = 'none';
    const canvasPill = document.getElementById('canvas-active-pill');
    if (canvasPill) canvasPill.style.display = 'inline-flex';
    if (promptPl) promptPl.textContent = 'Create a canvas to write your thoughts';
    await sleep(500);

    if (promptBar) promptBar.classList.add('focused');
    if (promptPl) promptPl.style.display = 'none';
    if (promptText) promptText.textContent = `create a 4 slide presentation with below content:

**Slide 1: Executive Summary & Performance**
* Core KPI: ${SEARCH_QUERY} achieved 95.6% operational compliance...`;
    if (sendBtn) sendBtn.classList.add('active');
    await sleep(800);
    await clickAt(1040, 1020);

    if (promptText) promptText.textContent = '';
    if (promptPl) promptPl.style.display = 'block';
    if (sendBtn) sendBtn.classList.remove('active');
    if (promptBar) promptBar.classList.remove('focused');

    const u5 = document.createElement('div');
    u5.className = 'user-bubble';
    u5.textContent = `create a 4 slide presentation with below content:

**Slide 1: Executive Summary & Performance**...`;
    messagesDiv.appendChild(u5);

    const a5 = document.createElement('div');
    a5.className = 'agent-response';
    a5.innerHTML = `
      <div class="tool-status-pill">
        <span style="color:#16a34a; font-size:14px;">✓</span>
        <span>Transferring to Slidegen • Presentation Deck Generated</span>
      </div>
      <div class="markdown-body">
        <p>I have generated a 4-slide executive presentation deck for <strong>${SEARCH_QUERY}</strong>. You can view and edit the live presentation on the right pane.</p>
      </div>
    `;
    messagesDiv.appendChild(a5);

    const canvasPane = document.getElementById('canvas-pane');
    if (canvasPane) canvasPane.classList.add('open');
    renderSlide(0);
    await sleep(1800);

    await moveCursor(1410, 1030, 350);
    await clickAt(1410, 1030);
    renderSlide(1);
    await sleep(1800);

    await moveCursor(1560, 1030, 350);
    await clickAt(1560, 1030);
    renderSlide(2);
    await sleep(1800);

    await moveCursor(1710, 1030, 350);
    await clickAt(1710, 1030);
    renderSlide(3);
    await sleep(1800);

    await moveCursor(500, 500, 350);
    const scrollArea = document.getElementById('chat-scroll-area');
    if (scrollArea) {
      for (let i = 0; i < 20; i++) {
        scrollArea.scrollTop -= 40;
        await sleep(30);
      }
      await sleep(1000);

      for (let i = 0; i < 25; i++) {
        scrollArea.scrollTop += 50;
        await sleep(30);
      }
      await sleep(1200);
    }

    console.log("🎉 Gemini Enterprise Demo Simulation Completed Successfully!");
  } catch (err) {
    console.error("Simulation error:", err);
  } finally {
    window.__DEMO_COMPLETE__ = true;
  }
}

window.addEventListener('DOMContentLoaded', () => {
  runFullDemo();
});
</script>
</body>
</html>"""

    html_content = html_template.replace("__DISPLAY_NAME__", html.escape(display_name))
    html_content = html_content.replace("__CLEAN_TITLE__", html.escape(clean_title))
    html_content = html_content.replace("__DOMAIN_ICON__", domain_icon)
    html_content = html_content.replace("__AGENT_DESC__", html.escape(agent_desc))
    html_content = html_content.replace("__SLIDES_DATA_JSON__", json.dumps(slides_data))
    html_content = html_content.replace("__P1_JSON__", json.dumps(p1))
    html_content = html_content.replace("__P2_JSON__", json.dumps(p2))
    html_content = html_content.replace("__P3_JSON__", json.dumps(p3))
    html_content = html_content.replace("__P4_JSON__", json.dumps(p4))
    html_content = html_content.replace("__SEARCH_QUERY_JSON__", json.dumps(clean_title))

    return html_content


async def record_single_agent_browser_simulation(
    agent_name: str,
    domain: str,
    prompts: list[str],
    output_dir: Path,
    resolution: str = "1080p"
) -> Path:
    """Renders and records the Gemini Enterprise walkthrough simulation using Playwright Chromium."""
    domain_output_dir = output_dir / domain
    domain_output_dir.mkdir(parents=True, exist_ok=True)
    target_mp4 = domain_output_dir / f"{agent_name}.mp4"
    
    res_config = RESOLUTION_CONFIGS.get(resolution, RESOLUTION_CONFIGS["1080p"])
    sim_html_content = generate_simulator_html(agent_name, domain, prompts)
    
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        html_file = tmp_dir / "sim.html"
        html_file.write_text(sim_html_content, encoding="utf-8")
        
        video_rec_dir = tmp_dir / "recordings"
        video_rec_dir.mkdir(parents=True, exist_ok=True)
        
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--font-render-hinting=none"
                ]
            )
            context = await browser.new_context(
                record_video_dir=str(video_rec_dir),
                record_video_size=res_config,
                viewport=res_config,
                device_scale_factor=1.0
            )
            page = await context.new_page()
            await page.goto(f"file://{html_file.resolve()}", wait_until="domcontentloaded")
            
            start_t = time.time()
            max_wait = 45.0
            while time.time() - start_t < max_wait:
                is_done = await page.evaluate("() => window.__DEMO_COMPLETE__ === true")
                if is_done:
                    await asyncio.sleep(1.5)
                    break
                await asyncio.sleep(0.5)
                
            await page.close()
            await context.close()
            await browser.close()
            
        recorded_webms = list(video_rec_dir.glob("*.webm"))
        if recorded_webms:
            raw_webm = recorded_webms[0]
            convert_webm_to_mp4(raw_webm, target_mp4)
            print(f"🎥 Generated authentic 1080p demo video ({target_mp4.stat().st_size / (1024*1024):.2f} MB): {target_mp4}", flush=True)
        else:
            print(f"⚠️ No recording produced for {agent_name}", flush=True)

    try:
        generate_html_showcase(agent_name=agent_name, domain=domain, output_dir=output_dir)
        print(f"✅ Generated HTML demo player: {domain_output_dir / f'{agent_name}.html'}", flush=True)
    except Exception as e:
        print(f"⚠️ Warning generating HTML showcase: {e}", flush=True)

    return target_mp4


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
    """Executes full recording flow via live Chrome or browser simulation."""
    if dry_run:
        domain_output_dir = output_dir / domain
        return domain_output_dir / f"{agent_name}.{video_format}"

    if not ge_url:
        return await record_single_agent_browser_simulation(
            agent_name=agent_name,
            domain=domain,
            prompts=prompts,
            output_dir=output_dir,
            resolution=resolution
        )

    domain_output_dir = output_dir / domain
    domain_output_dir.mkdir(parents=True, exist_ok=True)
    target_video_file = domain_output_dir / f"{agent_name}.{video_format}"
    
    res_config = RESOLUTION_CONFIGS.get(resolution, RESOLUTION_CONFIGS["1080p"])
    effective_user_data_dir = Path(user_data_dir) if user_data_dir else DEFAULT_CHROME_USER_DATA_DIR
    sync_chrome_profile(effective_user_data_dir)
    
    from playwright.async_api import async_playwright
    temp_video_dir = domain_output_dir / f".tmp_video_{agent_name}_{int(time.time())}"
    temp_video_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(effective_user_data_dir),
            channel="chrome",
            headless=headless,
            record_video_dir=str(temp_video_dir),
            record_video_size=res_config,
            viewport=res_config,
            device_scale_factor=1.0,
            args=[
                f"--profile-directory={chrome_profile_dir}",
                "--no-default-browser-check",
                f"--window-size={res_config['width']},{res_config['height']}"
            ]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        try:
            await page.goto(ge_url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(4.0)
            await scroll_to_bottom_prompt_box(page)
            await activate_canvas_mode(page)
            await showcase_canvas_presentation(page, num_slides=4, resolution=resolution)
            await smooth_mouse_scroll_walkthrough(page, resolution=resolution)
        finally:
            await context.close()

    recorded_videos = list(temp_video_dir.glob("*.webm"))
    if recorded_videos:
        convert_webm_to_mp4(recorded_videos[0], target_video_file)
        shutil.rmtree(str(temp_video_dir), ignore_errors=True)

    return target_video_file


def _render_worker(item):
    """Worker function for parallel video generation."""
    aname, dom, p_list, out_dir, res = item
    return asyncio.run(
        record_single_agent_browser_simulation(
            agent_name=aname,
            domain=dom,
            prompts=p_list,
            output_dir=out_dir,
            resolution=res
        )
    )


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
    parser.add_argument("--render", action="store_true", help="Force high-resolution browser simulation renderer")
    parser.add_argument("--workers", type=int, default=8, help="Number of parallel workers for video rendering (default: 8)")

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
        print(f"🚀 Recording authentic 1080p Gemini Enterprise demo videos (with typing effects & Canvas split screen) for {len(agents_to_record)} agent(s)...", flush=True)
        items = [(aname, dom, p_list, args.output_dir, args.resolution) for (aname, dom, p_list) in agents_to_record]
        
        if len(items) > 1:
            workers = min(args.workers, len(items))
            with ProcessPoolExecutor(max_workers=workers) as executor:
                results = list(executor.map(_render_worker, items))
            count = sum(1 for r in results if r)
            print(f"\n🎉 Successfully rendered & recorded {count} / {len(items)} 1080p MP4 demo videos.", flush=True)
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
