#!/usr/bin/env python3
"""
generate_telco_demo_videos.py — High-Resolution Gemini Enterprise Walkthrough Video Generator

Generates crystal-clear, authentic 1080p 25fps Gemini Enterprise UI walkthrough demo videos (~5:45 duration)
matching the exact design system, colors, typography, layout, and visual flow of the
Gemini Enterprise interface:
  1. Google Gemini Sidebar: Logo, navigation items (New chat, Search, Library, Agents, and recent chats).
  2. Agent Directory Search: Animated typing of the agent name in the search bar.
  3. "From your organization" Card: Exact card matching Image 2 with agent icon, title, and description.
  4. Interactive Multi-Turn Chat:
     - Turn 1 (Data Insights): BigQuery Conversational Analytics SLA table & financial ROI.
     - Turn 2 (Market Grounding): Google Search grounding with TM Forum ODA & GSMA benchmarks.
     - Turn 3 (Visual Analytics): Matplotlib visual tool & sample_chart.png artifact.
     - Turn 4 (Gemini Enterprise Canvas): 4-slide strategy presentation deck.
     - Outro: Multi-turn summary & Vertex AI Agent Engine session persistence.

Usage:
    .venv/bin/python _shared/scripts/generate_telco_demo_videos.py --name family_plan_upsell
    .venv/bin/python _shared/scripts/generate_telco_demo_videos.py --all
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import yaml
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

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
    """Renders the left navigation sidebar from the reference layout."""
    draw.rectangle([(0, 0), (280, 1080)], fill=(248, 249, 250))
    draw.line([(280, 0), (280, 1080)], fill=(227, 227, 227), width=1)

    # Top Brand: Spark + Cymbal Telco
    draw_gemini_spark(draw, 24, 22, size=22)
    draw.text((54, 20), "Cymbal", fill=(31, 31, 31), font=get_font(18, bold=True))
    draw.text((54, 38), "Telco", fill=(217, 48, 37), font=get_font(14, bold=True))

    # Collapse icon
    draw.rectangle([(236, 24), (256, 44)], outline=(180, 180, 180), width=1)
    draw.line([(243, 24), (243, 44)], fill=(180, 180, 180), width=1)

    # "New chat" button
    draw.rounded_rectangle([(16, 75), (264, 115)], radius=20, fill=(233, 238, 246))
    draw.text((40, 86), "✏️  New chat", fill=(31, 31, 31), font=get_font(15, bold=True))

    draw.text((24, 140), "🔍  Search", fill=(68, 71, 70), font=get_font(14, bold=False))
    draw.text((24, 175), "📚  Library", fill=(68, 71, 70), font=get_font(14, bold=False))

    # Agents button
    bg_agents = (232, 240, 254) if active_tab == "agents" else (248, 249, 250)
    draw.rounded_rectangle([(16, 215), (264, 250)], radius=8, fill=bg_agents)
    draw.text((24, 225), "🤖  Agents", fill=(26, 115, 232) if active_tab == "agents" else (68, 71, 70), font=get_font(14, bold=True))
    draw.text((250, 225), "›", fill=(26, 115, 232) if active_tab == "agents" else (100, 100, 100), font=get_font(14, bold=True))

    draw.text((36, 265), "📓  Gemini Notebook", fill=(68, 71, 70), font=get_font(13, bold=False))
    draw.text((245, 265), "📌", fill=(150, 150, 150), font=get_font(12, bold=False))
    
    draw.text((36, 298), "🌐  Deep Research", fill=(68, 71, 70), font=get_font(13, bold=False))
    draw.text((245, 298), "📌", fill=(150, 150, 150), font=get_font(12, bold=False))

    draw.text((36, 335), "＋  New agent", fill=(68, 71, 70), font=get_font(13, bold=False))

    # Recent Section
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

    # Footer
    draw.line([(16, 1000), (264, 1000)], fill=(227, 227, 227))
    draw.text((24, 1015), "GCP: telco-catalog", fill=(24, 128, 56), font=get_font(13, bold=True))
    draw.text((24, 1040), "BigQuery: telco_ent_agents", fill=(100, 100, 100), font=get_font(12, bold=False))


def render_agent_directory_screen(agent_name: str, display_name: str, domain: str, description: str, search_query: str = "", highlight_target: bool = False) -> Image.Image:
    """Renders the exact Gemini Enterprise Agent Directory matching Image 2 reference."""
    img = Image.new("RGB", (1920, 1080), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    render_sidebar(draw, display_name, domain, active_tab="agents")

    # Main Area: x=280..1920
    # Top Bar: "Agents" title + "+ New agent" button
    draw.text((330, 36), "Agents", fill=(31, 31, 31), font=get_font(28, bold=True))
    draw.rounded_rectangle([(1720, 32), (1860, 72)], radius=20, fill=(26, 115, 232))
    draw.text((1742, 43), "＋ New agent", fill=(255, 255, 255), font=get_font(14, bold=True))

    # Search Bar: x=330..1860, y=95..145
    draw.rounded_rectangle([(330, 95), (1860, 145)], radius=25, fill=(255, 255, 255), outline=(218, 220, 224), width=1)
    if search_query:
        draw.text((360, 110), f"🔍  {search_query}", fill=(31, 31, 31), font=get_font(15, bold=False))
        draw.text((1830, 110), "✕", fill=(100, 100, 100), font=get_font(16, bold=False))
    else:
        draw.text((360, 110), "🔍  Search agents by name, domain, or capability...", fill=(117, 117, 117), font=get_font(15, bold=False))

    # Section 1: "Made by Google"
    draw.text((330, 175), "Made by Google", fill=(68, 71, 70), font=get_font(14, bold=True))
    
    # Card 1: Deep Research
    draw.rounded_rectangle([(330, 205), (680, 335)], radius=12, fill=(240, 244, 249), outline=(218, 220, 224), width=1)
    draw.ellipse([(350, 225), (385, 260)], fill=(0, 188, 212))
    draw.text((358, 232), "🌐", font=get_font(16))
    draw.text((650, 220), "📌", font=get_font(12))
    draw.text((350, 275), "Deep Research", fill=(31, 31, 31), font=get_font(15, bold=True))
    draw.text((350, 298), "Get in-depth answers grounded in web research.", fill=(68, 71, 70), font=get_font(12, bold=False))
    draw.text((350, 316), "By Google", fill=(117, 117, 117), font=get_font(11, bold=False))

    # Card 2: Gemini Notebook
    draw.rounded_rectangle([(710, 205), (1060, 335)], radius=12, fill=(240, 244, 249), outline=(218, 220, 224), width=1)
    draw.ellipse([(730, 225), (765, 260)], fill=(30, 41, 59))
    draw.text((738, 232), "✨", font=get_font(16))
    draw.text((1030, 220), "📌", font=get_font(12))
    draw.text((730, 275), "Gemini Notebook", fill=(31, 31, 31), font=get_font(15, bold=True))
    draw.text((730, 298), "Quickly summarize and take notes for research with AI.", fill=(68, 71, 70), font=get_font(12, bold=False))
    draw.text((730, 316), "By Google", fill=(117, 117, 117), font=get_font(11, bold=False))

    # Section 2: "From your organization"
    draw.text((330, 365), "From your organization", fill=(68, 71, 70), font=get_font(14, bold=True))
    draw.text((1800, 365), "Show more", fill=(26, 115, 232), font=get_font(13, bold=False))

    # 4 Organization Cards
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
        
        # Icon box
        draw.rounded_rectangle([(card_x + 18, 412), (card_x + 58, 452)], radius=8, fill=(255, 238, 217) if is_high else (240, 244, 249))
        draw.text((card_x + 26, 420), c_icon, font=get_font(18))
        draw.text((card_x + w - 30, 415), "⋮", fill=(100, 100, 100), font=get_font(16, bold=True))

        # Title
        t_short = title if len(title) < 28 else title[:26] + "..."
        draw.text((card_x + 18, 465), t_short, fill=(26, 115, 232) if is_high else (31, 31, 31), font=get_font(14, bold=True))

        # Description wrapped
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

    # Section 3: "Your agents"
    draw.text((330, 600), "Your agents", fill=(68, 71, 70), font=get_font(14, bold=True))
    draw.rounded_rectangle([(330, 630), (680, 770)], radius=12, fill=(255, 255, 255), outline=(218, 220, 224), width=1)
    
    # Avatar 'M'
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

    # Top Header Bar (x=280..1920, y=0..65)
    draw.rectangle([(280, 0), (1920, 65)], fill=(255, 255, 255))
    draw.line([(280, 65), (1920, 65)], fill=(227, 227, 227), width=1)

    # Active Agent Pill
    draw.rounded_rectangle([(310, 14), (740, 50)], radius=18, fill=(240, 244, 249), outline=(218, 220, 224), width=1)
    draw.ellipse([(326, 27), (336, 37)], fill=(24, 128, 56))  # Green active dot
    draw.text((346, 21), f"@{agent_display_name}", fill=(31, 31, 31), font=get_font(15, bold=True))
    draw.text((680, 22), "Active", fill=(24, 128, 56), font=get_font(12, bold=True))

    # Model Pill
    draw.rounded_rectangle([(760, 14), (920, 50)], radius=18, fill=(240, 244, 249))
    draw.text((775, 22), "gemini-3.5-flash", fill=(68, 71, 70), font=get_font(13, bold=False))

    # Domain Title
    domain_title = DOMAIN_TITLES.get(domain, domain.title())
    draw.rounded_rectangle([(940, 14), (1260, 50)], radius=18, fill=(240, 244, 249))
    draw.text((955, 22), f"{DOMAIN_ICONS.get(domain, '📱')} {domain_title}", fill=(26, 115, 232), font=get_font(13, bold=False))

    # Right side controls
    draw.text((1720, 22), "Canvas Mode ⚡  |  Export  |  Docs", fill=(100, 100, 100), font=get_font(13, bold=False))

    # Bottom Prompt Input Box
    draw.rounded_rectangle([(320, 980), (1880, 1045)], radius=24, fill=(248, 249, 250), outline=(218, 220, 224), width=1)
    draw.text((350, 1002), f"Ask @{agent_display_name} anything or generate reports...", fill=(117, 117, 117), font=get_font(15, bold=False))
    draw.ellipse([(1830, 992), (1866, 1028)], fill=(26, 115, 232))
    draw.text((1842, 998), "↑", fill=(255, 255, 255), font=get_font(18, bold=True))

    return img, draw


def generate_rich_telco_video(agent_name: str, domain: str, output_path: Path) -> bool:
    """Generates an authentic, crystal-clear 1080p Gemini Enterprise demo video."""
    registry_file = REPO_ROOT / "_shared" / "table_registry.yaml"
    display_name = agent_name.replace("_", " ").title()
    description = f"Telecommunications operations intelligence for {display_name}."
    roi_metric = "ARPU Growth & Cost Avoidance"

    if registry_file.exists():
        try:
            data = yaml.safe_load(registry_file.read_text(encoding="utf-8"))
            agent_entry = data.get("agents", {}).get(agent_name, {})
            if "display_name" in agent_entry:
                raw_display = agent_entry["display_name"].strip()
                display_name = raw_display.split(":")[-1].strip() if ":" in raw_display else raw_display
            if "description" in agent_entry:
                description = agent_entry["description"].strip()
            if "roi_metric" in agent_entry:
                roi_metric = agent_entry["roi_metric"].strip()
        except Exception:
            pass

    clean_name = display_name
    chart_path = REPO_ROOT / "domains" / domain / "agents" / agent_name / "sample_chart.png"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # -------------------------------------------------------------
        # STEP 1: Agent Directory Screen (Image 2) — Empty Search (0:00 - 0:03 = 3s)
        # -------------------------------------------------------------
        img_dir1 = render_agent_directory_screen(agent_name, clean_name, domain, description, search_query="")
        img_dir1.save(tmp_path / "f01_dir1.png")

        # -------------------------------------------------------------
        # STEP 2: Agent Directory Screen — Typing in Search Bar (0:03 - 0:07 = 4s)
        # -------------------------------------------------------------
        search_snippet = clean_name[:len(clean_name)//2]
        img_dir2 = render_agent_directory_screen(agent_name, clean_name, domain, description, search_query=search_snippet)
        img_dir2.save(tmp_path / "f02_dir2.png")

        # -------------------------------------------------------------
        # STEP 3: Agent Directory Screen — Matching Card Selected (0:07 - 0:15 = 8s)
        # -------------------------------------------------------------
        img_dir3 = render_agent_directory_screen(agent_name, clean_name, domain, description, search_query=clean_name, highlight_target=True)
        img_dir3.save(tmp_path / "f03_dir3.png")

        # -------------------------------------------------------------
        # STEP 4: Turn 1 (Data Insights & BigQuery KPI Analysis) (0:15 - 1:15 = 60s)
        # -------------------------------------------------------------
        img_t1, d1 = render_chat_base(clean_name, domain)
        
        # User message
        d1.rounded_rectangle([(1100, 95), (1860, 155)], radius=18, fill=(233, 238, 246))
        d1.text((1125, 115), f"What are our primary operational metrics for {clean_name.lower()} in 2026 YTD?", fill=(31, 31, 31), font=get_font(15, bold=True))

        # Agent Spark + Response
        draw_gemini_spark(d1, 320, 180, size=24)
        
        # Tool badge
        d1.rounded_rectangle([(360, 175), (960, 215)], radius=12, fill=(240, 244, 249), outline=(218, 220, 224))
        d1.text((375, 186), "⚡ BigQuery CA API ask_data_insights on telco_ent_agents tables", fill=(26, 115, 232), font=get_font(13, bold=True))

        # Response card
        d1.rounded_rectangle([(360, 230), (1860, 560)], radius=16, fill=(255, 255, 255), outline=(227, 227, 227), width=1)
        d1.text((385, 255), f"Executive Operational Summary ({clean_name}):", fill=(31, 31, 31), font=get_font(18, bold=True))
        d1.text((385, 295), f"Over the past 30 days, performance metrics for {clean_name} achieved an overall 94.8% compliance rate across operating clusters.", fill=(68, 71, 70), font=get_font(15, bold=False))

        # Table
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

        d1.text((385, 495), f"Primary Financial Contribution: Estimated quarterly ROI and cost avoidance of $214,000.", fill=(26, 115, 232), font=get_font(16, bold=True))
        img_t1.save(tmp_path / "f04_t1.png")

        # -------------------------------------------------------------
        # STEP 5: Turn 2 (Google Search Market Grounding) (1:15 - 2:30 = 75s)
        # -------------------------------------------------------------
        img_t2, d2 = render_chat_base(clean_name, domain)
        
        # User message
        d2.rounded_rectangle([(1020, 95), (1860, 155)], radius=18, fill=(233, 238, 246))
        d2.text((1045, 115), f"What are current telecom industry benchmarks and GSMA/ODA standards for {clean_name.lower()}?", fill=(31, 31, 31), font=get_font(15, bold=True))

        draw_gemini_spark(d2, 320, 180, size=24)

        # Tool badge
        d2.rounded_rectangle([(360, 175), (1100, 215)], radius=12, fill=(240, 244, 249), outline=(218, 220, 224))
        d2.text((375, 186), "🌐 Grounding with Google Search (TM Forum Open Digital Architecture & GSMA Open Gateway)", fill=(26, 115, 232), font=get_font(13, bold=True))

        # Response card
        d2.rounded_rectangle([(360, 230), (1860, 540)], radius=16, fill=(255, 255, 255), outline=(227, 227, 227), width=1)
        d2.text((385, 255), "External Market Intelligence & Industry Standard Grounding:", fill=(31, 31, 31), font=get_font(18, bold=True))
        d2.text((385, 305), "• TM Forum ODA Standard: Leading Tier-1 operators deploying automated conversational analytics achieve a 35% reduction in MTTR.", fill=(68, 71, 70), font=get_font(15, bold=False))
        d2.text((385, 355), "• GSMA 2026 Telecom Benchmark: First-contact digital resolution rates improved by 22% among CSPs adopting autonomous sub-agents.", fill=(68, 71, 70), font=get_font(15, bold=False))
        d2.text((385, 405), "• Competitive Positioning: Your current 94.8% performance index ranks in the top quartile among regional telecommunications peers.", fill=(24, 128, 56), font=get_font(15, bold=True))
        d2.text((385, 470), "Strategic Recommendation: Scale predictive BigQuery anomaly triggers to expand automated prevention workflows.", fill=(26, 115, 232), font=get_font(16, bold=True))
        img_t2.save(tmp_path / "f05_t2.png")

        # -------------------------------------------------------------
        # STEP 6: Turn 3 (Visual Analytics & Real Matplotlib Chart Artifact) (2:30 - 3:45 = 75s)
        # -------------------------------------------------------------
        img_t3, d3 = render_chat_base(clean_name, domain)
        
        # User message
        d3.rounded_rectangle([(1050, 95), (1860, 155)], radius=18, fill=(233, 238, 246))
        d3.text((1075, 115), f"Render a chart comparing monthly performance metrics for {clean_name.lower()} vs annual targets.", fill=(31, 31, 31), font=get_font(15, bold=True))

        draw_gemini_spark(d3, 320, 180, size=24)

        # Tool badge
        d3.rounded_rectangle([(360, 175), (820, 215)], radius=12, fill=(240, 244, 249), outline=(218, 220, 224))
        d3.text((375, 186), "📊 Matplotlib Tool render_chart(query, title)", fill=(26, 115, 232), font=get_font(13, bold=True))

        # Response card with chart
        d3.rounded_rectangle([(360, 230), (1860, 940)], radius=16, fill=(255, 255, 255), outline=(227, 227, 227), width=1)
        d3.text((385, 255), f"Generated Visual Artifact: Monthly Trend vs Operational SLA ({clean_name})", fill=(31, 31, 31), font=get_font(18, bold=True))

        # Paste real chart artifact
        if chart_path.exists():
            try:
                cimg = Image.open(chart_path).convert("RGB")
                cimg.thumbnail((760, 480), Image.Resampling.LANCZOS)
                img_t3.paste(cimg, (385, 305))
            except Exception:
                d3.text((385, 350), f"[Chart loaded: {chart_path.name}]", fill=(100, 100, 100), font=get_font(15, bold=False))

        # Visual insights card on right
        d3.rounded_rectangle([(1180, 305), (1830, 785)], radius=12, fill=(248, 249, 250), outline=(227, 227, 227))
        d3.text((1205, 335), "Visual Insights & Anomaly Analysis:", fill=(26, 115, 232), font=get_font(18, bold=True))
        d3.text((1205, 390), "• Upward trajectory across 2026 YTD monthly trends", fill=(68, 71, 70), font=get_font(15, bold=False))
        d3.text((1205, 440), "• Exceeded annual target milestone in Q2 and Q3", fill=(24, 128, 56), font=get_font(15, bold=True))
        d3.text((1205, 490), "• Minimal variance observed between regional clusters", fill=(68, 71, 70), font=get_font(15, bold=False))
        d3.text((1205, 540), "• Automated anomaly thresholds calibrated for Q4", fill=(68, 71, 70), font=get_font(15, bold=False))
        d3.text((1205, 610), "Artifact Status: Stored in session storage", fill=(26, 115, 232), font=get_font(15, bold=True))
        img_t3.save(tmp_path / "f06_t3.png")

        # -------------------------------------------------------------
        # STEP 7: Turn 4 (Canvas Mode 4-Slide Presentation Deck) (3:45 - 5:15 = 90s)
        # -------------------------------------------------------------
        img_t4, d4 = render_chat_base(clean_name, domain)
        
        # User message
        d4.rounded_rectangle([(1020, 95), (1860, 155)], radius=18, fill=(233, 238, 246))
        d4.text((1045, 115), f"Create a 4-slide executive presentation summarizing the {clean_name} analysis.", fill=(31, 31, 31), font=get_font(15, bold=True))

        draw_gemini_spark(d4, 320, 180, size=24)

        # Canvas mode header
        d4.rounded_rectangle([(360, 175), (1860, 950)], radius=16, fill=(248, 249, 250), outline=(218, 220, 224), width=1)
        d4.rounded_rectangle([(360, 175), (1860, 235)], radius=16, fill=(233, 238, 246))
        d4.text((385, 192), f"✨ Gemini Enterprise Canvas Presentation — {clean_name} Strategy Brief", fill=(31, 31, 31), font=get_font(18, bold=True))
        d4.text((1600, 195), "4 Slides Generated  |  Export PPTX", fill=(26, 115, 232), font=get_font(13, bold=True))

        # 4 Slide Cards Grid
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

        # -------------------------------------------------------------
        # STEP 8: Conversation Review / Outro (5:15 - 5:45 = 30s)
        # -------------------------------------------------------------
        img_out, dout = render_chat_base(clean_name, domain)
        dout.rounded_rectangle([(550, 320), (1650, 620)], radius=20, fill=(255, 255, 255), outline=(24, 128, 56), width=2)
        dout.text((590, 360), f"✅ Multi-Turn Analysis Completed ({clean_name})", fill=(24, 128, 56), font=get_font(26, bold=True))
        dout.text((590, 420), "• Turn 1: BigQuery Conversational Analytics KPI Breakdown (Completed)", fill=(68, 71, 70), font=get_font(16, bold=False))
        dout.text((590, 460), "• Turn 2: Google Search Grounding with TM Forum ODA & GSMA (Completed)", fill=(68, 71, 70), font=get_font(16, bold=False))
        dout.text((590, 500), "• Turn 3: Real-Time Matplotlib Visual Analytics & Anomaly Trend (Completed)", fill=(68, 71, 70), font=get_font(16, bold=False))
        dout.text((590, 540), "• Turn 4: 4-Slide Executive Canvas Strategy Presentation (Generated)", fill=(68, 71, 70), font=get_font(16, bold=False))
        dout.text((590, 580), "Session State: Persisted to Vertex AI Agent Engine & Cloud Spanner Memory", fill=(26, 115, 232), font=get_font(15, bold=True))
        img_out.save(tmp_path / "f08_out.png")

        # High-resolution, visually lossless FFmpeg encoding (CRF 18, 1080p @ 25fps, natural ~46s pacing):
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
        return True


def _worker(item):
    agent_name, info = item
    domain = info.get("domain", "consumer_marketing")
    target_mp4 = REPO_ROOT / "demos" / "gemini-enterprise" / domain / f"{agent_name}.mp4"
    return generate_rich_telco_video(agent_name, domain, target_mp4)


def main():
    parser = argparse.ArgumentParser(description="Generate authentic 1080p MP4 demo videos for Telco Enterprise Agents")
    parser.add_argument("--name", type=str, help="Agent name (e.g. family_plan_upsell)")
    parser.add_argument("--all", action="store_true", help="Generate demo videos for all 45 agents")
    args = parser.parse_args()

    registry_file = REPO_ROOT / "_shared" / "table_registry.yaml"
    data = yaml.safe_load(registry_file.read_text(encoding="utf-8"))
    agents = data.get("agents", {})

    if args.all:
        print(f"🚀 Generating crystal-clear 1080p demo videos (seamless ~46s duration, CRF 18) across 8 parallel workers for all {len(agents)} agents...", flush=True)
        items = list(agents.items())
        with ProcessPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(_worker, items))
        count = sum(1 for r in results if r)
        print(f"\n🎉 Successfully generated {count} / {len(agents)} high-resolution 1080p MP4 demo videos.", flush=True)
        return

    if not args.name:
        print("Error: Specify --name <agent_name> or --all", file=sys.stderr)
        sys.exit(1)

    domain = agents.get(args.name, {}).get("domain", "consumer_marketing")
    target_mp4 = REPO_ROOT / "demos" / "gemini-enterprise" / domain / f"{args.name}.mp4"
    generate_rich_telco_video(args.name, domain, target_mp4)


if __name__ == "__main__":
    main()
