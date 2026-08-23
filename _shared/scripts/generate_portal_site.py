#!/usr/bin/env python3
"""
generate_portal_site.py — Telco Enterprise Agents Portal Generator

Programmatically reads _shared/table_registry.yaml and all agent READMEs across 9 domains
to generate a self-contained, lightning-fast, interactive single-page portal (index.html)
for GitHub Pages with live search, domain filtering, KPI tags, prompt previews, architecture modal,
and embedded 1080p video modal players with dual light/dark themes.

Usage:
    uv run python _shared/scripts/generate_portal_site.py
"""

import html
import json
from pathlib import Path
import re
import sys
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from _shared.scripts.prompt_parser import parse_agent_prompts

DOMAIN_ICONS = {
    "consumer_marketing": "📱",
    "onboarding_provisioning": "⚡",
    "subscriber_crm": "🎧",
    "netops_aiops": "📡",
    "daas_camara": "🌐",
}

DOMAIN_DISPLAY_NAMES = {
    "consumer_marketing": "Consumer Marketing & Growth",
    "onboarding_provisioning": "Onboarding & Provisioning",
    "subscriber_crm": "Subscriber CRM & Retention",
    "netops_aiops": "NetOps & AIOps",
    "daas_camara": "DaaS & CAMARA / Open Gateway",
}

DOMAIN_ORDER = [
    "consumer_marketing",
    "onboarding_provisioning",
    "subscriber_crm",
    "netops_aiops",
    "daas_camara",
]


def extract_agent_metadata(agent_name: str, domain: str, reg_agent: dict, repo_root: Path) -> dict:
    """Extracts rich metadata, KPIs, and prompts for an agent from its README.md."""
    readme_path = repo_root / "domains" / domain / "agents" / agent_name / "README.md"
    
    display_name = reg_agent.get("display_name", agent_name.replace("_", " ").title())
    location = reg_agent.get("location", "us-central1")
    tables = reg_agent.get("tables", [])
    
    description = f"Autonomous enterprise reasoning agent for {display_name} in telecommunications operations."
    kpis = []
    prompts = []
    
    if readme_path.exists():
        content = readme_path.read_text(encoding="utf-8")
        
        # 1. Extract Description from Business Problem or Why This Agent Matters
        bp_match = re.search(r"###\s+Business Problem\s*\n+(.*?)(?=\n\s*###|\n\s*##|\n\s*---|\Z)", content, re.DOTALL)
        if bp_match:
            text = bp_match.group(1).strip()
            lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
            if lines:
                cleaned = " ".join(lines)
                cleaned = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", cleaned).replace("**", "").replace("*", "").strip()
                if len(cleaned) > 20:
                    description = cleaned
        elif "Why This Agent Matters" in content:
            why_match = re.search(r"##\s+(?:1\.\s+)?Why This Agent Matters\s*\n+(.*?)(?=\n\s*###|\n\s*##|\n\s*---|\Z)", content, re.DOTALL)
            if why_match:
                text = why_match.group(1).strip()
                lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
                if lines:
                    cleaned = " ".join(lines)
                    cleaned = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", cleaned).replace("**", "").replace("*", "").strip()
                    if len(cleaned) > 20:
                        description = cleaned
        else:
            # Fallback to paragraph before first section
            ans_match = re.search(r"^(Answers questions about.*?)(?=\n\s*\n|\n\s*#|\Z)", content, re.DOTALL | re.MULTILINE)
            if ans_match:
                cleaned = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", ans_match.group(1).strip()).replace("**", "").replace("*", "").strip()
                if len(cleaned) > 20:
                    description = cleaned
                    
        # 2. Extract KPIs from KPI table
        kpi_table_match = re.search(r"\|\s*Metric\s*\|\s*Definition\s*\|\s*Target\s*\|.*?\n((?:\|.*?\n)+)", content, re.IGNORECASE)
        if kpi_table_match:
            rows = kpi_table_match.group(1).strip().split("\n")
            for row in rows:
                cols = [c.strip() for c in row.split("|")[1:-1]]
                if len(cols) >= 3 and cols[0] and not cols[0].startswith("---") and cols[0] != ":---":
                    metric_name = cols[0].replace("**", "").strip()
                    target = cols[2].replace("**", "").strip()
                    if metric_name and target:
                        kpis.append(f"{metric_name}: {target}")
                    elif metric_name:
                        kpis.append(metric_name)
                    if len(kpis) >= 4:
                        break
                        
        # 3. Extract Prompts
        try:
            prompts = parse_agent_prompts(readme_path)
        except Exception:
            prompts = [
                f"What are our key performance metrics for {display_name} across telecom operating markets in 2026 YTD?",
                f"What are current telecommunications industry benchmarks and best practices for {display_name}?",
                f"Show me a visual chart comparing our {display_name} performance vs annual target."
            ]
    else:
        prompts = [
            f"What are our key performance metrics for {display_name} across telecom operating markets in 2026 YTD?",
            f"What are current telecommunications industry benchmarks and best practices for {display_name}?",
            f"Show me a visual chart comparing our {display_name} performance vs annual target."
        ]
        
    demo_html_rel = f"demos/gemini-enterprise/{domain}/{agent_name}.html"
    demo_mp4_rel = f"demos/gemini-enterprise/{domain}/{agent_name}.mp4"
    readme_rel = f"domains/{domain}/{agents_dir_rel(domain, agent_name)}"
    
    return {
        "id": reg_agent.get("agent_id", ""),
        "name": agent_name,
        "display_name": display_name,
        "domain": domain,
        "domain_display": DOMAIN_DISPLAY_NAMES.get(domain, domain.title()),
        "icon": DOMAIN_ICONS.get(domain, "🤖"),
        "location": location,
        "description": description,
        "kpis": kpis[:4],
        "prompts": prompts[:3],
        "tables": tables,
        "demo_html": demo_html_rel,
        "demo_mp4": demo_mp4_rel,
        "readme": readme_rel,
    }


def agents_dir_rel(domain: str, agent_name: str) -> str:
    return f"agents/{agent_name}/README.md"


def build_portal_html(agents_data: list[dict], domains_data: dict) -> str:
    """Generates the complete index.html file."""
    
    total_agents = len(agents_data)
    total_domains = len(DOMAIN_ORDER)
    total_tables = sum(len(a.get("tables", [])) for a in agents_data)
    
    # Pre-count agents per domain
    domain_counts = {}
    for a in agents_data:
        d = a["domain"]
        domain_counts[d] = domain_counts.get(d, 0) + 1
        
    agents_json = json.dumps(agents_data, indent=2)
    
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gemini Enterprise Agents for Telco — 100 Multi-Agent Catalog</title>
  <meta name="description" content="Explore 100 specialized Gemini Enterprise Agents for telecommunications enterprise operations, built on Google ADK, Gemini Enterprise, and BigQuery Conversational Analytics.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  
  <script>
    // Synchronous theme initialization to prevent Flash of Unstyled Content (FOUC)
    (function() {{
      const savedTheme = localStorage.getItem('telco_agents_theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      document.documentElement.setAttribute('data-theme', savedTheme);
    }})();
  </script>

  <style>
    :root, [data-theme="dark"] {{
      --bg-primary: #0f172a;
      --bg-secondary: #1e293b;
      --bg-card: #1e293b;
      --bg-card-hover: #243248;
      --bg-surface: #0f172a;
      --bg-input: #0f172a;
      --border-color: #334155;
      --border-faint: rgba(255, 255, 255, 0.14);
      --border-subtle: #1e293b;
      --border-focus: #38bdf8;
      --text-primary: #f8fafc;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --accent-blue: #38bdf8;
      --accent-blue-hover: #0284c7;
      --accent-indigo: #818cf8;
      --accent-emerald: #34d399;
      --accent-amber: #fbbf24;
      --badge-bg: rgba(56, 189, 248, 0.12);
      --badge-border: rgba(56, 189, 248, 0.28);
      --badge-text: #38bdf8;
      --kpi-bg: rgba(52, 211, 153, 0.1);
      --kpi-border: rgba(52, 211, 153, 0.25);
      --kpi-text: #34d399;
      --region-bg: rgba(129, 140, 248, 0.12);
      --region-border: rgba(129, 140, 248, 0.28);
      --region-text: #a5b4fc;
      --shadow-card: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.4);
      --shadow-modal: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
      --modal-overlay: rgba(15, 23, 42, 0.85);
    }}

    [data-theme="light"] {{
      --bg-primary: #f8fafc;
      --bg-secondary: #ffffff;
      --bg-card: #ffffff;
      --bg-card-hover: #f8fafc;
      --bg-surface: #f1f5f9;
      --bg-input: #ffffff;
      --border-color: #cbd5e1;
      --border-faint: #cbd5e1;
      --border-subtle: #e2e8f0;
      --border-focus: #0284c7;
      --text-primary: #0f172a;
      --text-secondary: #475569;
      --text-muted: #64748b;
      --accent-blue: #0284c7;
      --accent-blue-hover: #0369a1;
      --accent-indigo: #6366f1;
      --accent-emerald: #059669;
      --accent-amber: #d97706;
      --badge-bg: #e0f2fe;
      --badge-border: #bae6fd;
      --badge-text: #0284c7;
      --kpi-bg: #d1fae5;
      --kpi-border: #a7f3d0;
      --kpi-text: #065f46;
      --region-bg: #e0e7ff;
      --region-border: #c7d2fe;
      --region-text: #4338ca;
      --shadow-card: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
      --shadow-modal: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
      --modal-overlay: rgba(15, 23, 42, 0.6);
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-primary);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      line-height: 1.5;
      transition: background-color 0.2s ease, color 0.2s ease;
    }}

    /* Global Header */
    .site-header {{
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 40;
      backdrop-filter: blur(8px);
    }}

    .header-inner {{
      max-width: 1360px;
      margin: 0 auto;
      padding: 14px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }}

    .brand-logo {{
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
      color: var(--text-primary);
    }}

    .brand-icon {{
      font-size: 1.6rem;
      line-height: 1;
    }}

    .brand-text {{
      display: flex;
      flex-direction: column;
    }}

    .brand-title {{
      font-family: 'Google Sans', sans-serif;
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: var(--text-primary);
    }}

    .brand-subtitle {{
      font-size: 0.75rem;
      color: var(--text-secondary);
      font-weight: 500;
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .btn-header {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      border: 1px solid var(--border-color);
      background: var(--bg-card);
      color: var(--text-primary);
      transition: all 0.15s ease;
    }}

    .btn-header:hover {{
      background: var(--bg-surface);
      border-color: var(--border-focus);
      color: var(--accent-blue);
    }}

    .btn-primary-header {{
      background: var(--accent-blue);
      color: #0f172a !important;
      border-color: var(--accent-blue);
      font-weight: 700;
    }}

    .btn-primary-header:hover {{
      background: var(--accent-blue-hover);
      border-color: var(--accent-blue-hover);
      color: #ffffff !important;
    }}

    /* Hero Section */
    .hero {{
      padding: 48px 24px 32px;
      max-width: 1360px;
      margin: 0 auto;
      width: 100%;
      text-align: center;
    }}

    .hero-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 0.8rem;
      font-weight: 600;
      background: var(--badge-bg);
      border: 1px solid var(--badge-border);
      color: var(--accent-blue);
      margin-bottom: 16px;
    }}

    .hero-title {{
      font-family: 'Google Sans', sans-serif;
      font-size: 2.5rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      margin-bottom: 12px;
      color: var(--text-primary);
    }}

    .hero-title span {{
      background: linear-gradient(135deg, var(--accent-blue), var(--accent-indigo));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}

    .hero-desc {{
      max-width: 820px;
      margin: 0 auto 28px;
      font-size: 1.05rem;
      color: var(--text-secondary);
      line-height: 1.6;
    }}

    /* Stat Counters */
    .stat-row {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      max-width: 1080px;
      margin: 0 auto;
    }}

    .stat-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-faint);
      border-radius: 12px;
      padding: 12px 10px;
      text-align: center;
      transition: transform 0.15s ease, border-color 0.15s ease;
    }}

    .stat-card:hover {{
      transform: translateY(-2px);
      border-color: var(--border-focus);
    }}

    .stat-number {{
      font-family: 'Google Sans', sans-serif;
      font-size: 1.4rem;
      font-weight: 700;
      color: var(--text-primary);
      margin-bottom: 2px;
    }}

    .stat-label {{
      font-size: 0.68rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      line-height: 1.35;
      color: var(--text-muted);
    }}

    /* Main Container */
    .main-container {{
      max-width: 1360px;
      margin: 0 auto;
      padding: 24px;
      width: 100%;
      flex: 1;
    }}

    /* Search & Filter Toolbar */
    .toolbar {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-faint);
      border-radius: 14px;
      padding: 18px;
      margin-bottom: 28px;
      box-shadow: var(--shadow-card);
    }}

    .search-row {{
      display: flex;
      gap: 12px;
      margin-bottom: 16px;
      position: relative;
    }}

    .search-input-wrapper {{
      position: relative;
      flex: 1;
    }}

    .search-icon {{
      position: absolute;
      left: 14px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      font-size: 1rem;
      pointer-events: none;
    }}

    .search-input {{
      width: 100%;
      background: var(--bg-input);
      border: 1px solid var(--border-faint);
      border-radius: 10px;
      padding: 12px 14px 12px 42px;
      font-size: 0.95rem;
      color: var(--text-primary);
      font-family: inherit;
      outline: none;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }}

    .search-input:focus {{
      border-color: var(--border-focus);
      box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2);
    }}

    .search-clear {{
      position: absolute;
      right: 12px;
      top: 50%;
      transform: translateY(-50%);
      background: none;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      font-size: 1rem;
      padding: 4px;
      display: none;
    }}

    .search-clear:hover {{
      color: var(--text-primary);
    }}

    /* Domain Tabs */
    .domain-pills {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .domain-btn {{
      background: var(--bg-surface);
      border: 1px solid var(--border-faint);
      color: var(--text-secondary);
      padding: 8px 14px;
      border-radius: 9999px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }}

    .domain-btn:hover {{
      color: var(--text-primary);
      border-color: var(--border-focus);
    }}

    .domain-btn.active {{
      background: var(--accent-blue);
      color: #0f172a;
      border-color: var(--accent-blue);
      font-weight: 700;
    }}

    .domain-count {{
      font-size: 0.72rem;
      padding: 2px 6px;
      border-radius: 9999px;
      background: rgba(0, 0, 0, 0.15);
      font-family: 'JetBrains Mono', monospace;
    }}

    .domain-btn.active .domain-count {{
      background: rgba(15, 23, 42, 0.25);
      color: #0f172a;
    }}

    /* Results Header */
    .results-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      padding: 0 4px;
    }}

    .results-count {{
      font-size: 0.9rem;
      font-weight: 600;
      color: var(--text-secondary);
    }}

    .results-count strong {{
      color: var(--text-primary);
    }}

    /* Agent Grid */
    .agent-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(390px, 1fr));
      gap: 20px;
    }}

    .agent-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-faint);
      border-radius: 14px;
      padding: 22px;
      display: flex;
      flex-direction: column;
      box-shadow: var(--shadow-card);
      transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
      position: relative;
    }}

    .agent-card:hover {{
      transform: translateY(-3px);
      border-color: var(--border-focus);
      box-shadow: 0 14px 30px -8px rgba(0, 0, 0, 0.35);
    }}

    .card-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
      gap: 8px;
    }}

    .card-badges {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }}

    .badge-domain {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: 3px 8px;
      border-radius: 6px;
      background: var(--badge-bg);
      border: 1px solid var(--badge-border);
      color: var(--badge-text);
    }}

    .badge-region {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 0.7rem;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      background: var(--region-bg);
      border: 1px solid var(--region-border);
      color: var(--region-text);
      font-family: 'JetBrains Mono', monospace;
    }}

    .card-title {{
      font-family: 'Google Sans', sans-serif;
      font-size: 1.2rem;
      font-weight: 700;
      color: var(--text-primary);
      margin-bottom: 8px;
      line-height: 1.35;
    }}

    .card-desc {{
      font-size: 0.88rem;
      color: var(--text-secondary);
      line-height: 1.5;
      margin-bottom: 16px;
      flex: 1;
      display: -webkit-box;
      -webkit-line-clamp: 4;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}

    /* KPI Tags */
    .kpi-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 16px;
    }}

    .kpi-pill {{
      font-size: 0.72rem;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 6px;
      background: var(--kpi-bg);
      border: 1px solid var(--kpi-border);
      color: var(--kpi-text);
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }}

    /* Prompts Collapsible */
    .prompts-container {{
      border-top: 1px solid var(--border-color);
      padding-top: 12px;
      margin-bottom: 16px;
    }}

    .prompts-toggle {{
      background: none;
      border: none;
      color: var(--text-secondary);
      font-size: 0.78rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      cursor: pointer;
      padding: 2px 0;
    }}

    .prompts-toggle:hover {{
      color: var(--accent-blue);
    }}

    .prompts-list {{
      margin-top: 8px;
      display: none;
      flex-direction: column;
      gap: 6px;
    }}

    .prompts-list.open {{
      display: flex;
    }}

    .prompt-item {{
      font-size: 0.78rem;
      color: var(--text-secondary);
      background: var(--bg-surface);
      padding: 6px 10px;
      border-radius: 6px;
      border-left: 3px solid var(--accent-indigo);
      line-height: 1.4;
      font-style: italic;
    }}

    /* Card Actions */
    .card-actions {{
      display: flex;
      gap: 8px;
      align-items: center;
      margin-top: auto;
      padding-top: 14px;
      border-top: 1px solid var(--border-color);
    }}

    .btn-watch {{
      flex: 1;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      background: var(--accent-blue);
      color: #0f172a;
      padding: 9px 14px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 700;
      border: none;
      cursor: pointer;
      transition: all 0.15s ease;
    }}

    .btn-watch:hover {{
      background: var(--accent-blue-hover);
      color: #ffffff;
      transform: translateY(-1px);
    }}

    .btn-showcase {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      background: var(--bg-surface);
      color: var(--text-primary);
      padding: 9px 12px;
      border-radius: 8px;
      font-size: 0.82rem;
      font-weight: 600;
      text-decoration: none;
      border: 1px solid var(--border-color);
      transition: all 0.15s ease;
    }}

    .btn-showcase:hover {{
      border-color: var(--border-focus);
      color: var(--accent-blue);
    }}

    .btn-doc {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: none;
      color: var(--text-muted);
      padding: 8px;
      border-radius: 8px;
      font-size: 1rem;
      text-decoration: none;
      border: 1px solid transparent;
      transition: all 0.15s ease;
    }}

    .btn-doc:hover {{
      color: var(--text-primary);
      border-color: var(--border-color);
      background: var(--bg-surface);
    }}

    /* No Results State */
    .no-results {{
      grid-column: 1 / -1;
      text-align: center;
      padding: 60px 20px;
      background: var(--bg-card);
      border: 1px dashed var(--border-color);
      border-radius: 14px;
      display: none;
    }}

    .no-results-icon {{
      font-size: 3rem;
      margin-bottom: 12px;
    }}

    .no-results-title {{
      font-size: 1.2rem;
      font-weight: 700;
      margin-bottom: 6px;
      color: var(--text-primary);
    }}

    .no-results-desc {{
      color: var(--text-secondary);
      font-size: 0.9rem;
      margin-bottom: 16px;
    }}

    /* Modals */
    .modal-backdrop {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: var(--modal-overlay);
      backdrop-filter: blur(6px);
      z-index: 100;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
      opacity: 0;
      transition: opacity 0.2s ease;
    }}

    .modal-backdrop.open {{
      display: flex;
      opacity: 1;
    }}

    .modal-dialog {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      width: 100%;
      max-width: 960px;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: var(--shadow-modal);
      position: relative;
      display: flex;
      flex-direction: column;
    }}

    .modal-header {{
      padding: 20px 24px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .modal-title-wrap {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .modal-title {{
      font-family: 'Google Sans', sans-serif;
      font-size: 1.3rem;
      font-weight: 700;
      color: var(--text-primary);
    }}

    .modal-close {{
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      color: var(--text-secondary);
      border-radius: 8px;
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 1.2rem;
      transition: all 0.15s ease;
    }}

    .modal-close:hover {{
      color: var(--text-primary);
      border-color: var(--border-focus);
    }}

    .modal-body {{
      padding: 24px;
      flex: 1;
    }}

    .video-container {{
      position: relative;
      width: 100%;
      background: #000;
      border-radius: 12px;
      overflow: hidden;
      margin-bottom: 20px;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
    }}

    .video-container video {{
      width: 100%;
      display: block;
      max-height: 520px;
    }}

    .modal-meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 20px;
    }}

    .modal-meta-item {{
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}

    .modal-meta-label {{
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }}

    .modal-meta-value {{
      font-size: 0.88rem;
      font-weight: 600;
      color: var(--text-primary);
    }}

    .modal-turns {{
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 16px;
      margin-bottom: 20px;
    }}

    .modal-turns h3 {{
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--accent-indigo);
      margin-bottom: 10px;
    }}

    .modal-turns-list {{
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}

    .modal-turns-list li {{
      font-size: 0.84rem;
      color: var(--text-secondary);
      line-height: 1.45;
    }}

    .modal-turns-list strong {{
      color: var(--text-primary);
    }}

    .modal-footer {{
      padding: 16px 24px;
      border-top: 1px solid var(--border-color);
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }}

    /* Architecture Blueprint Visual Component */
    .arch-flow-container {{
      display: flex;
      flex-direction: column;
      gap: 14px;
      margin-bottom: 20px;
    }}

    .arch-layer-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-faint);
      border-radius: 12px;
      padding: 16px 18px;
    }}

    .arch-layer-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      flex-wrap: wrap;
      gap: 8px;
    }}

    .arch-layer-title {{
      font-family: 'Google Sans', sans-serif;
      font-size: 1rem;
      font-weight: 700;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .arch-layer-pill {{
      font-size: 0.72rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 9999px;
      background: var(--badge-bg);
      border: 1px solid var(--badge-border);
      color: var(--accent-blue);
      font-family: 'JetBrains Mono', monospace;
    }}

    .arch-layer-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 10px;
    }}

    .arch-item {{
      background: var(--bg-card);
      border: 1px solid var(--border-faint);
      border-radius: 8px;
      padding: 10px 12px;
      font-size: 0.8rem;
      color: var(--text-secondary);
      line-height: 1.45;
    }}

    .arch-item strong {{
      display: block;
      color: var(--text-primary);
      margin-bottom: 3px;
      font-size: 0.84rem;
    }}

    .arch-subagents-row {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }}

    @media (max-width: 640px) {{
      .arch-subagents-row {{
        grid-template-columns: 1fr;
      }}
    }}

    .arch-arrow {{
      text-align: center;
      color: var(--accent-blue);
      font-size: 1.1rem;
      line-height: 1;
      margin: -6px 0;
      opacity: 0.85;
    }}

    /* Footer */
    .site-footer {{
      background: var(--bg-secondary);
      border-top: 1px solid var(--border-color);
      padding: 32px 24px;
      margin-top: 48px;
      text-align: center;
    }}

    .footer-inner {{
      max-width: 1360px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
    }}

    .footer-text {{
      font-size: 0.85rem;
      color: var(--text-muted);
    }}

    .footer-links {{
      display: flex;
      gap: 18px;
      flex-wrap: wrap;
    }}

    .footer-link {{
      color: var(--text-secondary);
      text-decoration: none;
      font-size: 0.85rem;
      font-weight: 500;
      transition: color 0.15s ease;
    }}

    .footer-link:hover {{
      color: var(--accent-blue);
      text-decoration: underline;
    }}

    /* Responsive adjustments */
    @media (max-width: 768px) {{
      .hero-title {{
        font-size: 1.85rem;
      }}
      .agent-grid {{
        grid-template-columns: 1fr;
      }}
      .stat-row {{
        grid-template-columns: repeat(2, 1fr);
      }}
      .header-inner {{
        flex-direction: column;
        align-items: flex-start;
      }}
      .header-actions {{
        width: 100%;
        justify-content: space-between;
      }}
    }}
  </style>
</head>
<body>

  <!-- Global Header -->
  <header class="site-header">
    <div class="header-inner">
      <a href="index.html" class="brand-logo">
        <span class="brand-icon">📡</span>
        <div class="brand-text">
          <span class="brand-title">Gemini Enterprise Agents for Telco</span>
          <span class="brand-subtitle">Google ADK & Gemini Enterprise Multi-Agent Swarm</span>
        </div>
      </a>
      <div class="header-actions">
        <button id="archBtn" class="btn-header" aria-label="View Architecture Blueprint">
          <span>📐</span> Architecture Blueprint
        </button>
        <button id="themeToggleBtn" class="btn-header" aria-label="Toggle Light/Dark Theme">
          <span id="themeIcon">☀️</span> <span id="themeText">Light</span>
        </button>
        <a href="https://github.com/ryanwjh/telco-enterprise-agents" target="_blank" rel="noopener noreferrer" class="btn-header btn-primary-header">
          <span>⭐</span> GitHub Repository
        </a>
      </div>
    </div>
  </header>

  <!-- Hero Section -->
  <section class="hero">
    <div class="hero-pill">
      <span>🚀</span> 45 Enterprise Agents Fully Deployed (5 Telco Domains)
    </div>
    <h1 class="hero-title">
      Gemini Enterprise Agents for <span>Telco</span>
    </h1>
    <p class="hero-desc">
      A declarative, multi-agent platform powered by Google Agent Development Kit (ADK), Gemini Enterprise, and BigQuery Conversational Analytics. Real-time quantitative querying against 135+ enterprise telecommunications datasets, grounded with external Google Search market intelligence.
    </p>

    <!-- Platform Stats -->
    <div class="stat-row">
      <div class="stat-card">
        <div class="stat-number">45</div>
        <div class="stat-label">Telco Enterprise Agents</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">9</div>
        <div class="stat-label">Telco Domains</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">135+</div>
        <div class="stat-label">BigQuery Tables</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">2</div>
        <div class="stat-label">GCP Hosting Regions</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">100%</div>
        <div class="stat-label">Agents Demos Ready</div>
      </div>
    </div>
  </section>

  <!-- Main Content Area -->
  <main class="main-container">
    
    <!-- Toolbar: Search & Domain Filters -->
    <section class="toolbar">
      <div class="search-row">
        <div class="search-input-wrapper">
          <span class="search-icon">🔍</span>
          <input type="text" id="searchInput" class="search-input" placeholder="Search 45 agents by name, KPI (e.g. ARPU, Churn %, MTTR, SLA), business question, or BigQuery table..." autocomplete="off">
          <button id="searchClear" class="search-clear" aria-label="Clear search">✕</button>
        </div>
      </div>

      <!-- Domain Pills -->
      <div class="domain-pills" id="domainPills">
        <button class="domain-btn active" data-domain="all">
          <span>🌐</span> All Domains <span class="domain-count">{total_agents}</span>
        </button>
        {"".join([f'''<button class="domain-btn" data-domain="{d}">
          <span>{DOMAIN_ICONS[d]}</span> {DOMAIN_DISPLAY_NAMES[d]} <span class="domain-count">{domain_counts.get(d, 0)}</span>
        </button>''' for d in DOMAIN_ORDER])}
      </div>
    </section>

    <!-- Results Header -->
    <div class="results-bar">
      <div class="results-count" id="resultsCount">
        Showing <strong>{total_agents}</strong> of {total_agents} enterprise agents
      </div>
    </div>

    <!-- Agent Grid -->
    <div class="agent-grid" id="agentGrid">
      <!-- Injected via JavaScript -->
    </div>

    <!-- No Results Fallback -->
    <div class="no-results" id="noResults">
      <div class="no-results-icon">🔎</div>
      <div class="no-results-title">No Matching Enterprise Agents Found</div>
      <p class="no-results-desc">Try refining your search keyword or switching domain filter tabs.</p>
      <button class="btn-header" onclick="resetFilters()">Reset All Filters</button>
    </div>

  </main>

  <!-- Video Player Modal -->
  <div class="modal-backdrop" id="videoModal">
    <div class="modal-dialog">
      <div class="modal-header">
        <div class="modal-title-wrap">
          <div style="display:flex; gap:8px; align-items:center; margin-bottom:4px;">
            <span id="modalDomainBadge" class="badge-domain">Domain</span>
            <span id="modalRegionBadge" class="badge-region">us-central1</span>
          </div>
          <h2 id="modalAgentTitle" class="modal-title">Agent Title</h2>
        </div>
        <button class="modal-close" id="modalCloseBtn" aria-label="Close modal">✕</button>
      </div>
      <div class="modal-body">
        <div class="video-container">
          <video id="modalVideo" src="" controls playsinline preload="auto">
            Your browser does not support HTML5 video.
          </video>
        </div>

        <div class="modal-meta-grid">
          <div class="modal-meta-item">
            <span class="modal-meta-label">Resolution</span>
            <span class="modal-meta-value">1080p Full HD (1920×1080)</span>
          </div>
          <div class="modal-meta-item">
            <span class="modal-meta-label">Model Reasoning</span>
            <span class="modal-meta-value">Gemini 3.5 Flash (Global)</span>
          </div>
          <div class="modal-meta-item">
            <span class="modal-meta-label">Platform UI</span>
            <span class="modal-meta-value">Gemini Enterprise</span>
          </div>
          <div class="modal-meta-item">
            <span class="modal-meta-label">Data Execution</span>
            <span class="modal-meta-value">BigQuery Conversational Analytics</span>
          </div>
        </div>

        <div class="modal-turns">
          <h3>🎬 Demonstration Workflow Sequence</h3>
          <ul class="modal-turns-list" id="modalTurnsList">
            <li><strong>Turn 1 (Data Insights):</strong> BigQuery Conversational Analytics natural language to SQL quantitative execution.</li>
            <li><strong>Turn 2 (Market Grounding):</strong> Live Google Search grounding against external industry benchmarks and regulatory statistics.</li>
            <li><strong>Turn 3 (Visual Analytics):</strong> Python Matplotlib visual chart generation with KPI callouts.</li>
            <li><strong>Turn 4 (Canvas Presentation):</strong> Executive 4-slide slide deck generated in Gemini Enterprise Canvas.</li>
          </ul>
        </div>
      </div>
      <div class="modal-footer">
        <a id="modalDownloadBtn" href="#" download class="btn-header">
          <span>⬇️</span> Download MP4
        </a>
        <a id="modalShowcaseBtn" href="#" target="_blank" class="btn-header btn-primary-header">
          <span>🚀</span> Open Full Showcase Player
        </a>
      </div>
    </div>
  </div>

  <!-- Architecture Blueprint Modal -->
  <div class="modal-backdrop" id="archModal">
    <div class="modal-dialog" style="max-width: 1020px;">
      <div class="modal-header">
        <div class="modal-title-wrap">
          <h2 class="modal-title">📐 Telecommunications Enterprise Multi-Agent Architecture</h2>
          <span style="font-size:0.8rem; color:var(--text-secondary);">Enterprise 4-Tier Google ADK & Gemini Enterprise Topology</span>
        </div>
        <button class="modal-close" id="archCloseBtn" aria-label="Close architecture modal">✕</button>
      </div>
      <div class="modal-body">

        <div class="arch-flow-container">
          <!-- Tier 1 -->
          <div class="arch-layer-card">
            <div class="arch-layer-header">
              <div class="arch-layer-title">
                <span>💬</span> Tier 1: Client & Presentation Layer
              </div>
              <span class="arch-layer-pill">Gemini Enterprise</span>
            </div>
            <div class="arch-layer-grid">
              <div class="arch-item">
                <strong>Discovery Engine Assistant</strong>
                100 Registered Enterprise Agents searchable via natural language chat
              </div>
              <div class="arch-item">
                <strong>Real-Time SSE Streaming</strong>
                Live multi-turn token streaming & dynamic markdown formatting
              </div>
              <div class="arch-item">
                <strong>Gemini Canvas Presentations</strong>
                Automated 4-slide executive decks generated directly from queries
              </div>
            </div>
          </div>

          <div class="arch-arrow">▼</div>

          <!-- Tier 2 -->
          <div class="arch-layer-card">
            <div class="arch-layer-header">
              <div class="arch-layer-title">
                <span>🧠</span> Tier 2: Orchestration & Multi-Agent Reasoning
              </div>
              <span class="arch-layer-pill">Gemini Enterprise Agent Platform</span>
            </div>
            <div class="arch-layer-grid">
              <div class="arch-item">
                <strong>Declarative ADK Framework</strong>
                Zero-boilerplate root orchestrators (`root_agent.yaml`)
              </div>
              <div class="arch-item">
                <strong>Multi-Region Hosting</strong>
                `us-central1` & `us-east4` hosting containers with auto-scaling
              </div>
              <div class="arch-item">
                <strong>Global Model Inference</strong>
                `gemini-3.5-flash` with low latency via global inference endpoint
              </div>
              <div class="arch-item">
                <strong>Lifecycle Callbacks</strong>
                IAM token scoping, date injection & dataset context binding
              </div>
            </div>
          </div>

          <div class="arch-arrow">▼</div>

          <!-- Tier 3: Parallel Sub-Agents -->
          <div class="arch-subagents-row">
            <div class="arch-layer-card" style="border-top: 3px solid var(--accent-emerald);">
              <div class="arch-layer-header">
                <div class="arch-layer-title" style="font-size:0.95rem;">
                  <span>📊</span> Sub-Agent 3A: BigQuery Data Insights
                </div>
                <span class="arch-layer-pill" style="color:var(--accent-emerald); background:var(--kpi-bg); border-color:var(--kpi-border);">Conversational Analytics</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:8px;">
                <div class="arch-item">
                  <strong>Natural Language to SQL Engine</strong>
                  Conversational Analytics API executes parameterized SQL directly
                </div>
                <div class="arch-item">
                  <strong>Built-in ML Models</strong>
                  BigQuery forecasting, anomaly detection & contribution analysis
                </div>
                <div class="arch-item">
                  <strong>Matplotlib Chart Generator</strong>
                  Serverless visual chart rendering (`render_chart`)
                </div>
              </div>
            </div>

            <div class="arch-layer-card" style="border-top: 3px solid var(--accent-blue);">
              <div class="arch-layer-header">
                <div class="arch-layer-title" style="font-size:0.95rem;">
                  <span>🌐</span> Sub-Agent 3B: Market Context & Grounding
                </div>
                <span class="arch-layer-pill">Google Search Grounding</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:8px;">
                <div class="arch-item">
                  <strong>Real-Time Web Grounding</strong>
                  Live Google Search verification for fresh industry trends
                </div>
                <div class="arch-item">
                  <strong>External Benchmarks</strong>
                  GSMA, 3GPP, TM Forum, FCC compliance & Telecom industry benchmarks
                </div>
                <div class="arch-item">
                  <strong>Competitor Intelligence</strong>
                  Live market pricing, promotional tracking & consumer sentiment
                </div>
              </div>
            </div>
          </div>

          <div class="arch-arrow">▼</div>

          <!-- Tier 4 -->
          <div class="arch-layer-card" style="border-top: 3px solid var(--accent-indigo);">
            <div class="arch-layer-header">
              <div class="arch-layer-title">
                <span>🗄️</span> Tier 4: Enterprise Telco Data Lakehouse
              </div>
              <span class="arch-layer-pill" style="color:var(--region-text); background:var(--region-bg); border-color:var(--region-border);">Google Cloud BigQuery</span>
            </div>
            <div class="arch-layer-grid">
              <div class="arch-item">
                <strong>Enterprise Dataset</strong>
                `retail_ent_agents` multi-tenant telco schema
              </div>
              <div class="arch-item">
                <strong>300+ Partitioned Tables</strong>
                Structured namespace: `&lt;domain_id&gt;_&lt;agent_id&gt;_&lt;table_name&gt;`
              </div>
              <div class="arch-item">
                <strong>IAM Table Allowlisting</strong>
                Strict per-agent service account dataset authorization
              </div>
            </div>
          </div>
        </div>

        <div class="modal-turns">
          <h3>🚀 Key Architectural Pillars</h3>
          <ul class="modal-turns-list">
            <li><strong>Declarative ADK Architecture:</strong> Zero-code orchestrator models bind BigQuery tools and Google Search tools with strict domain separation.</li>
            <li><strong>Global Low-Latency Inference:</strong> `gemini-3.5-flash` global routing delivers ~30% faster time-to-first-token than regional clusters.</li>
            <li><strong>Dual Sub-Agent Pattern:</strong> Quantitative BigQuery queries and qualitative market grounding execute in specialized sub-agent contexts for hallucination-free answers.</li>
          </ul>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-header btn-primary-header" id="archOkBtn">Close Blueprint</button>
      </div>
    </div>
  </div>

  <!-- Site Footer -->
  <footer class="site-footer">
    <div class="footer-inner">
      <div class="brand-logo" style="justify-content: center;">
        <span class="brand-icon">📡</span>
        <span class="brand-title">Gemini Enterprise Agents for Telco</span>
      </div>
      <p class="footer-text">
        100 Enterprise Agents across 9 Strategic Telco Domains. Powered by Google ADK, Gemini Enterprise, and BigQuery.
      </p>
      <div class="footer-links">
        <a href="https://github.com/ryanwjh/telco-enterprise-agents" target="_blank" rel="noopener noreferrer" class="footer-link">GitHub Repository</a>
        <a href="https://github.com/ryanwjh/telco-enterprise-agents/blob/master/README.md" target="_blank" rel="noopener noreferrer" class="footer-link">Project Documentation</a>
        <a href="https://github.com/ryanwjh/telco-enterprise-agents/blob/master/ARCHITECTURE.md" target="_blank" rel="noopener noreferrer" class="footer-link">Architecture Reference</a>
      </div>
    </div>
  </footer>

  <!-- Embedded JSON Data & Client Application Script -->
  <script>
    const AGENTS_DATA = {agents_json};

    let activeDomain = 'all';
    let searchQuery = '';

    // Elements
    const searchInput = document.getElementById('searchInput');
    const searchClear = document.getElementById('searchClear');
    const domainPills = document.getElementById('domainPills');
    const agentGrid = document.getElementById('agentGrid');
    const noResults = document.getElementById('noResults');
    const resultsCount = document.getElementById('resultsCount');
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const themeIcon = document.getElementById('themeIcon');
    const themeText = document.getElementById('themeText');

    // Video Modal Elements
    const videoModal = document.getElementById('videoModal');
    const modalVideo = document.getElementById('modalVideo');
    const modalAgentTitle = document.getElementById('modalAgentTitle');
    const modalDomainBadge = document.getElementById('modalDomainBadge');
    const modalRegionBadge = document.getElementById('modalRegionBadge');
    const modalTurnsList = document.getElementById('modalTurnsList');
    const modalDownloadBtn = document.getElementById('modalDownloadBtn');
    const modalShowcaseBtn = document.getElementById('modalShowcaseBtn');
    const modalCloseBtn = document.getElementById('modalCloseBtn');

    // Architecture Modal Elements
    const archModal = document.getElementById('archModal');
    const archBtn = document.getElementById('archBtn');
    const archCloseBtn = document.getElementById('archCloseBtn');
    const archOkBtn = document.getElementById('archOkBtn');

    // Theme Management
    function initTheme() {{
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      updateThemeUI(current);
    }}

    function updateThemeUI(theme) {{
      if (theme === 'light') {{
        themeIcon.textContent = '🌙';
        themeText.textContent = 'Dark';
      }} else {{
        themeIcon.textContent = '☀️';
        themeText.textContent = 'Light';
      }}
    }}

    themeToggleBtn.addEventListener('click', () => {{
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('telco_agents_theme', next);
      updateThemeUI(next);
    }});

    // Render Cards
    function renderAgents() {{
      const query = searchQuery.toLowerCase().trim();
      
      const filtered = AGENTS_DATA.filter(agent => {{
        const matchesDomain = activeDomain === 'all' || agent.domain === activeDomain;
        if (!matchesDomain) return false;

        if (!query) return true;

        const textPool = [
          agent.display_name,
          agent.name,
          agent.domain_display,
          agent.description,
          agent.location,
          ...(agent.kpis || []),
          ...(agent.prompts || []),
          ...(agent.tables || [])
        ].join(' ').toLowerCase();

        return textPool.includes(query);
      }});

      resultsCount.innerHTML = `Showing <strong>${{filtered.length}}</strong> of ${{AGENTS_DATA.length}} enterprise agents`;

      if (filtered.length === 0) {{
        agentGrid.innerHTML = '';
        noResults.style.display = 'block';
        return;
      }}

      noResults.style.display = 'none';

      agentGrid.innerHTML = filtered.map(agent => {{
        const kpiPills = (agent.kpis || []).map(kpi => 
          `<span class="kpi-pill">🎯 ${{htmlEscape(kpi)}}</span>`
        ).join('');

        const promptItems = (agent.prompts || []).map((prompt, idx) => 
          `<div class="prompt-item">"${{htmlEscape(prompt)}}"</div>`
        ).join('');

        return `
          <div class="agent-card" data-agent-id="${{agent.id}}">
            <div class="card-top">
              <div class="card-badges">
                <span class="badge-domain">${{agent.icon}} ${{htmlEscape(agent.domain_display)}}</span>
                <span class="badge-region">${{agent.location}}</span>
              </div>
            </div>
            <h3 class="card-title">${{htmlEscape(agent.display_name)}}</h3>
            <p class="card-desc">${{htmlEscape(agent.description)}}</p>

            ${{kpiPills ? `<div class="kpi-row">${{kpiPills}}</div>` : ''}}

            ${{promptItems ? `
              <div class="prompts-container">
                <button class="prompts-toggle" onclick="togglePrompts(this)">
                  <span>💬 Sample Business Questions (${{agent.prompts.length}})</span>
                  <span class="toggle-icon">▼</span>
                </button>
                <div class="prompts-list">
                  ${{promptItems}}
                </div>
              </div>
            ` : ''}}

            <div class="card-actions">
              <button class="btn-watch" onclick="openVideoModal('${{agent.name}}')">
                <span>🎬</span> Watch Demo
              </button>
              <a href="${{agent.demo_html}}" target="_blank" rel="noopener noreferrer" class="btn-showcase" title="Open Dedicated Showcase Player">
                <span>📄</span> Showcase
              </a>
              <a href="${{agent.readme}}" target="_blank" rel="noopener noreferrer" class="btn-doc" title="View Technical README">
                <span>📖</span>
              </a>
            </div>
          </div>
        `;
      }}).join('');
    }}

    function togglePrompts(btn) {{
      const list = btn.nextElementSibling;
      const icon = btn.querySelector('.toggle-icon');
      if (list.classList.contains('open')) {{
        list.classList.remove('open');
        icon.textContent = '▼';
      }} else {{
        list.classList.add('open');
        icon.textContent = '▲';
      }}
    }}

    function htmlEscape(str) {{
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }}

    // Search input handler
    searchInput.addEventListener('input', (e) => {{
      searchQuery = e.target.value;
      searchClear.style.display = searchQuery ? 'block' : 'none';
      renderAgents();
    }});

    searchClear.addEventListener('click', () => {{
      searchInput.value = '';
      searchQuery = '';
      searchClear.style.display = 'none';
      renderAgents();
      searchInput.focus();
    }});

    // Domain Filter Handler
    domainPills.addEventListener('click', (e) => {{
      const btn = e.target.closest('.domain-btn');
      if (!btn) return;

      document.querySelectorAll('.domain-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      activeDomain = btn.dataset.domain;
      renderAgents();
    }});

    function resetFilters() {{
      searchInput.value = '';
      searchQuery = '';
      searchClear.style.display = 'none';
      activeDomain = 'all';
      document.querySelectorAll('.domain-btn').forEach(b => {{
        b.classList.toggle('active', b.dataset.domain === 'all');
      }});
      renderAgents();
    }}

    // Video Modal Handlers
    function openVideoModal(agentName) {{
      const agent = AGENTS_DATA.find(a => a.name === agentName);
      if (!agent) return;

      modalAgentTitle.textContent = agent.display_name;
      modalDomainBadge.innerHTML = `${{agent.icon}} ${{agent.domain_display}}`;
      modalRegionBadge.textContent = agent.location;
      modalVideo.src = `${{agent.demo_mp4}}#t=10`;
      modalDownloadBtn.href = agent.demo_mp4;
      modalShowcaseBtn.href = agent.demo_html;

      if (agent.prompts && agent.prompts.length >= 3) {{
        modalTurnsList.innerHTML = `
          <li><strong>Turn 1 (Data Insights):</strong> "${{htmlEscape(agent.prompts[0])}}"</li>
          <li><strong>Turn 2 (Market Grounding):</strong> "${{htmlEscape(agent.prompts[1])}}"</li>
          <li><strong>Turn 3 (Visual Analytics):</strong> "${{htmlEscape(agent.prompts[2])}}"</li>
          <li><strong>Turn 4 (Canvas Presentation):</strong> Executive 4-slide slide deck generated in Gemini Enterprise Canvas.</li>
        `;
      }}

      videoModal.classList.add('open');
      document.body.style.overflow = 'hidden';
      modalVideo.play().catch(() => {{}});
    }}

    function closeVideoModal() {{
      videoModal.classList.remove('open');
      document.body.style.overflow = '';
      modalVideo.pause();
      modalVideo.src = '';
    }}

    modalCloseBtn.addEventListener('click', closeVideoModal);
    videoModal.addEventListener('click', (e) => {{
      if (e.target === videoModal) closeVideoModal();
    }});

    // Architecture Modal Handlers
    function openArchModal() {{
      archModal.classList.add('open');
      document.body.style.overflow = 'hidden';
    }}

    function closeArchModal() {{
      archModal.classList.remove('open');
      document.body.style.overflow = '';
    }}

    archBtn.addEventListener('click', openArchModal);
    archCloseBtn.addEventListener('click', closeArchModal);
    archOkBtn.addEventListener('click', closeArchModal);
    archModal.addEventListener('click', (e) => {{
      if (e.target === archModal) closeArchModal();
    }});

    // ESC key listener for modals
    document.addEventListener('keydown', (e) => {{
      if (e.key === 'Escape') {{
        if (videoModal.classList.contains('open')) closeVideoModal();
        if (archModal.classList.contains('open')) closeArchModal();
      }}
    }});

    // Initial Load
    initTheme();
    renderAgents();
  </script>
</body>
</html>
"""


def main():
    print("=" * 70)
    print("🚀 GENERATING TELCO ENTERPRISE AGENTS PORTAL (index.html)")
    print("=" * 70)
    
    registry_file = REPO_ROOT / "_shared" / "table_registry.yaml"
    if not registry_file.exists():
        print(f"❌ Error: {registry_file} not found!")
        sys.exit(1)
        
    registry = yaml.safe_load(registry_file.read_text(encoding="utf-8"))
    reg_agents = registry.get("agents", {})
    reg_domains = registry.get("domains", {})
    
    print(f"📋 Found {len(reg_agents)} registered agents across {len(reg_domains)} domains in table_registry.yaml.")
    
    agents_data = []
    for agent_name, agent_info in reg_agents.items():
        domain = agent_info.get("domain", "")
        if not domain:
            print(f"⚠️ Warning: Agent '{agent_name}' missing domain field in registry.")
            continue
        meta = extract_agent_metadata(agent_name, domain, agent_info, REPO_ROOT)
        agents_data.append(meta)
        
    # Sort agents by domain order, then display name
    domain_rank = {d: i for i, d in enumerate(DOMAIN_ORDER)}
    agents_data.sort(key=lambda a: (domain_rank.get(a["domain"], 99), a["display_name"]))
    
    print(f"✨ Compiled metadata for {len(agents_data)} agents.")
    
    portal_html = build_portal_html(agents_data, reg_domains)
    
    output_file = REPO_ROOT / "index.html"
    output_file.write_text(portal_html, encoding="utf-8")
    
    file_size_kb = output_file.stat().st_size / 1024
    print(f"✅ Successfully generated {output_file} ({file_size_kb:.1f} KB).")
    print("=" * 70)


if __name__ == "__main__":
    main()
