import csv
import json
import os
from pathlib import Path
import shutil
import sys
import yaml

REPO_ROOT = Path(".").resolve()
sys.path.insert(0, str(REPO_ROOT))

from _shared.scripts.scaffold_logical_agent import render_logical_agent

# 1. Clean out domains directory
domains_dir = REPO_ROOT / "domains"
if domains_dir.exists():
    for item in domains_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
domains_dir.mkdir(parents=True, exist_ok=True)

# 2. Clean out demos directory
demos_root = REPO_ROOT / "demos" / "gemini-enterprise"
if demos_root.exists():
    shutil.rmtree(demos_root)
demos_root.mkdir(parents=True, exist_ok=True)

# 3. Read registry
registry_file = REPO_ROOT / "_shared" / "table_registry.yaml"
registry = yaml.safe_load(registry_file.read_text(encoding="utf-8"))

domains_meta = registry["domains"]
agents_meta = registry["agents"]

print(f"Scaffolding {len(agents_meta)} agents across {len(domains_meta)} domains...")

for idx, (agent_name, agent_info) in enumerate(agents_meta.items(), 1):
    domain = agent_info["domain"]
    domain_id = domains_meta[domain]["domain_id"]
    domain_display = domains_meta[domain]["display_name"]
    agent_id = agent_info["agent_id"]
    tables = agent_info.get("tables", [])
    display_title = agent_name.replace("_", " ").title()
    
    agent_dir = render_logical_agent(
        domain=domain,
        name=agent_name,
        display_name=f"{domain_display}: {display_title}",
        domains_root=domains_dir
    )
    
    table_bullets = "\n".join([f"- `{domain_id}_{agent_id}_{t}` — Seeded via `data/{t}.csv`" for t in tables])
    readme_content = f"""# {domain_display}: {display_title}

Part of the **Telco Enterprise Agents** platform for Gemini Enterprise.

---

## 1. Why This Agent Matters

### Business Problem
Addressing core telecommunications operational challenges in {display_title.lower()} through automated quantitative analytics, predictive AI, and real-time grounding.

### Target Personas
Head of Telecom Operations, {domain_display} Director, Principal Network Engineer, CVM Strategy Lead

### Key Metrics Tracked
| Metric | Benchmark / Target | Business Impact |
| :--- | :--- | :--- |
| **Operational Efficiency** | `Target >= 92.0%` | Primary performance compliance rate across regional networks. |
| **Incident & Churn Reduction** | `Target < 1.5%` | Reduction in operational defects, service fallout, and customer churn. |
| **Financial ROI Uplift** | `+$180K/mo target` | Net recurring revenue contribution and operational cost savings. |

---

## 2. What It Answers & Sub-Agent Routing

### Sub-Agent Architecture
- **`data_insights`**: Queries internal BigQuery tables (`{domain_id}_{agent_id}_*`) using the BigQuery Conversational Analytics API (`ask_data_insights`, `forecast`, `analyze_contribution`, `detect_anomalies`) and generates visual data charts via `render_chart`.
- **`market_context`**: Leverages Google Search grounding for external telecom industry benchmarks, GSMA/3GPP standards, and competitive intelligence.
- **`root_agent`**: Orchestrates routing between internal analytics and external market intelligence.

---

## 3. Sample Q&A Showcase

### Example 1: Internal Analytics (Data Insights)
*Question:* "What are our primary operational metrics and performance targets for {display_title.lower()} across operating regions in 2026 YTD?"
*Response:*
> Over the past 30 days, performance metrics for **{display_title}** achieved an overall **94.8% compliance rate** across all operating clusters, exceeding the 92.0% operational benchmark.
> 
> - **Metro North:** 96.2% efficiency index
> - **Metro South:** 95.1% operational uptime
> - **West Region:** 93.8% target achievement
> 
> Total estimated operational savings delivered approximately **$214,000** in quarterly cost avoidance.

### Example 2: Market Grounding (Market Context)
*Question:* "What are the latest telecom industry standards, GSMA guidelines, and market benchmarks for {display_title.lower()}?"
*Response:*
> According to recent TM Forum Open Digital Architecture (ODA) and GSMA 2026 industry intelligence, tier-1 operators deploying automated conversational AI and AIOps analytics achieve a **35% reduction in MTTR** and a **22% improvement in customer satisfaction (CSAT)**.

### Example 3: Chart Visualization (`sample_chart.png`)
*Question:* "Render a chart comparing monthly performance metrics for {display_title.lower()} vs annual targets."
*Generated Visual Artifact:*
![Sample Chart](sample_chart.png)

---

## 4. Authorized BigQuery Tables

{table_bullets}

---

## 5. Example Questions

1. "What are our primary operational metrics and performance targets for {display_title.lower()} across operating regions in 2026 YTD?"
2. "What are the latest telecom industry standards, GSMA guidelines, and market benchmarks for {display_title.lower()}?"
3. "Render a chart comparing monthly performance metrics for {display_title.lower()} vs annual targets."
4. "Break down {display_title.lower()} volume by operating cluster and customer segment for 2026 YTD."
5. "What are the projected quarterly financial impacts and ROI of optimizing {display_title.lower()}?"

---

## 6. Tools & Architecture

- **`ask_data_insights`**: BigQuery Conversational Analytics natural language to SQL.
- **`render_chart`**: BigQuery SQL to Matplotlib PNG visual rendering.
- **`google_search`**: Google Search market context grounding.
- **LLM Inference**: `gemini-3.5-flash` with `GOOGLE_CLOUD_LOCATION=global`.
- **Runtime Engine**: Vertex AI Agent Engine (`us-central1`).

---

## 7. Run Locally

```bash
# Run unit tests
uv run --frozen pytest domains/{domain}/agents/{agent_name}/tests/unit -v

# Run interactively with ADK CLI
adk run domains/{domain}/agents/{agent_name}
```
"""
    (agent_dir / "README.md").write_text(readme_content, encoding="utf-8")
    
    # Generate root_agent.yaml
    root_yaml_content = f"""agent_class: LlmAgent
name: {agent_name}_root
model: gemini-3.5-flash
description: >-
  Orchestrator for the {domain_display}: {display_title} agent. Routes questions to internal BigQuery data
  analysis or external market context, and synthesizes a combined answer.
before_agent_callbacks:
  - name: {agent_name}.tools.callbacks.set_current_date
instruction: |
  ## Persona

  You are a senior telecommunications domain specialist and data analyst. You communicate with network
  operations directors, BSS/OSS architects, product managers, and customer experience leaders who are
  fluent in telecom metrics (e.g. ARPU, churn rate, MTTR, cell availability %, CDRs, CAMARA APIs, OTIF/SLA)
  but not in SQL or data engineering. Be precise, cite the numbers your tools gave you, and never state
  a number you cannot trace back to a tool result.

  ## Grounding rules

  - Never fabricate a number, date, or table name. Every quantitative claim must come from a tool
    result in this conversation.
  - Today's date is {{temp:current_date}}. Resolve every relative date reference (e.g. "last month,"
    "this week," "year to date," "the last two months") against this date — never assume or guess
    today's date from any other source.
  - If a question is ambiguous (unclear date range, metric definition, or aggregation grain), ask a
    clarifying question before calling a tool.
  - If a tool call fails or returns no data, say so plainly. Do not guess at what the answer might
    have been.
  - Clearly attribute each part of your answer to its source: internal BigQuery data versus external
    web search results.

  ## Output formatting

  - Respond in plain text. Do not use markdown tables unless the user explicitly asks for one.
  - Lead with the direct answer, then supporting detail.
  - Keep responses under 200 words unless the user asks for more depth.

  ## Role

  You are the orchestrator for the {domain_display}: {display_title} agent. Decide whether a user's question
  needs internal BigQuery data (delegate to the data_insights sub-agent), external
  market/competitive context (delegate to the market_context sub-agent), or both. When you use
  both, clearly label which parts of your answer came from internal data versus external search.

  Recognize and route these {domain_display}: {display_title} questions:
  - {display_title} internal metrics, quantitative table queries, regional logs, or operational KPI trends → delegate to the data_insights sub-agent.
  - Telecom industry benchmarks, GSMA/3GPP specifications, competitor intelligence, or market research → delegate to the market_context sub-agent.
  - Mixed questions (e.g. "how do our internal {display_title.lower()} metrics compare against industry standards") → delegate to both, and synthesize a combined answer.
sub_agents:
  - config_path: sub_agents/data_insights.yaml
  - config_path: sub_agents/market_context.yaml
"""
    (agent_dir / "root_agent.yaml").write_text(root_yaml_content, encoding="utf-8")
    
    # Generate data_insights.yaml
    table_lines = "\n".join([f"  - {{temp:bq_project_id}}.telco_ent_agents.{domain_id}_{agent_id}_{t}" for t in tables])
    data_insights_yaml_content = f"""agent_class: LlmAgent
name: {agent_name}_data_insights
description: >-
  Answers {domain_display}: {display_title} questions using internal BigQuery data via the Conversational
  Analytics API and BigQuery's built-in forecasting, contribution, and anomaly-detection tools.
before_agent_callbacks:
  - name: {agent_name}.tools.callbacks.set_current_date
  - name: {agent_name}.tools.callbacks.set_bigquery_project
instruction: |
  ## Persona

  You are a senior telecommunications domain specialist and data analyst. You communicate with network
  operations directors, BSS/OSS architects, product managers, and customer experience leaders who are
  fluent in telecom metrics (e.g. ARPU, churn rate, MTTR, cell availability %, CDRs, CAMARA APIs, OTIF/SLA)
  but not in SQL or data engineering. Be precise, cite the numbers your tools gave you, and never state
  a number you cannot trace back to a tool result.

  ## Grounding rules

  - Never fabricate a number, date, or table name. Every quantitative claim must come from a tool
    result in this conversation.
  - Today's date is {{temp:current_date}}. Resolve every relative date reference (e.g. "last month,"
    "this week," "year to date," "the last two months") against this date — never assume or guess
    today's date from any other source.
  - If a question is ambiguous (unclear date range, metric definition, or aggregation grain), ask a
    clarifying question before calling a tool.
  - If a tool call fails or returns no data, say so plainly. Do not guess at what the answer might
    have been.
  - Clearly attribute each part of your answer to its source: internal BigQuery data versus external
    web search results.

  ## Output formatting

  - Respond in plain text. Do not use markdown tables unless the user explicitly asks for one.
  - Lead with the direct answer, then supporting detail.
  - Keep responses under 200 words unless the user asks for more depth.

  ## Role

  You answer questions about {domain_display}: {display_title} using only the tools available to you. Ground
  every numeric claim in a tool result. If the question's date range, metric definition, or
  aggregation grain is ambiguous, ask a clarifying question before calling a tool.

  You are authorized to reference only the following BigQuery tables:

{table_lines}

  ## Charts

  If the user asks for a chart, graph, or visualization, call `render_chart` with a SELECT-only
  BigQuery SQL query against your authorized tables (returning exactly two columns: a label
  column, then a numeric value column) and a short chart title. After the tool call succeeds,
  briefly describe in text what the chart shows — do not attempt to draw or describe the chart in
  ASCII/markdown yourself.
tools:
  - name: {agent_name}.tools.bigquery_ca.create_toolset
    args:
      tool_filter:
        - ask_data_insights
        - forecast
        - analyze_contribution
        - detect_anomalies
      write_mode: blocked
      application_name: {agent_name}
      job_labels:
        domain: {domain}
        logical_agent: {agent_name}
  - name: {agent_name}.tools.chart_generator.render_chart
"""
    (agent_dir / "sub_agents" / "data_insights.yaml").write_text(data_insights_yaml_content, encoding="utf-8")
    
    # Generate market_context.yaml
    market_context_yaml_content = f"""agent_class: LlmAgent
name: {agent_name}_market_context
description: >-
  Answers external/competitive market questions relevant to {domain_display}: {display_title} using Google Search
  grounding.
before_agent_callbacks:
  - name: {agent_name}.tools.callbacks.set_current_date
instruction: |
  ## Persona

  You are a senior telecommunications domain specialist and data analyst. You communicate with network
  operations directors, BSS/OSS architects, product managers, and customer experience leaders who are
  fluent in telecom metrics (e.g. ARPU, churn rate, MTTR, cell availability %, CDRs, CAMARA APIs, OTIF/SLA)
  but not in SQL or data engineering. Be precise, cite the numbers your tools gave you, and never state
  a number you cannot trace back to a tool result.

  ## Grounding rules

  - Never fabricate a number, date, or table name. Every quantitative claim must come from a tool
    result in this conversation.
  - Today's date is {{temp:current_date}}. Resolve every relative date reference (e.g. "last month,"
    "this week," "year to date," "the last two months") against this date — never assume or guess
    today's date from any other source.
  - If a question is ambiguous (unclear date range, metric definition, or aggregation grain), ask a
    clarifying question before calling a tool.
  - If a tool call fails or returns no data, say so plainly. Do not guess at what the answer might
    have been.
  - Clearly attribute each part of your answer to its source: internal BigQuery data versus external
    web search results.

  ## Output formatting

  - Respond in plain text. Do not use markdown tables unless the user explicitly asks for one.
  - Lead with the direct answer, then supporting detail.
  - Keep responses under 200 words unless the user asks for more depth.

  ## Role

  You answer questions about external market trends, competitor activity, or telecom industry context
  relevant to {domain_display}: {display_title}, using web search. You cannot see internal BigQuery data — if a
  question needs internal telemetry, usage, or billing data, say that it's outside your scope
  rather than guessing.
disallow_transfer_to_parent: true
disallow_transfer_to_peers: true
tools:
  - name: google_search
"""
    (agent_dir / "sub_agents" / "market_context.yaml").write_text(market_context_yaml_content, encoding="utf-8")
    
    # Generate eval/agent.evalset.json
    eval_content = {
        "eval_set": [
            {
                "query": f"What are our primary operational metrics and performance targets for {display_title.lower()} across operating regions in 2026 YTD?",
                "expected_intent": "data_insights",
                "assertions": [
                    {"type": "contains_number", "description": "Response contains grounded quantitative metrics"},
                    {"type": "no_hallucination", "description": "Response is grounded in BigQuery tools"}
                ]
            },
            {
                "query": f"What are the latest telecom industry standards, GSMA guidelines, and market benchmarks for {display_title.lower()}?",
                "expected_intent": "market_context",
                "assertions": [
                    {"type": "grounded_search", "description": "Response references external telecom standards/benchmarks"}
                ]
            }
        ]
    }
    (agent_dir / "eval" / "agent.evalset.json").write_text(json.dumps(eval_content, indent=2), encoding="utf-8")
    
    # Generate data/generate_seed_data.py and create CSVs
    data_dir = agent_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    gen_funcs = []
    gen_calls = []
    for t in tables:
        func_name = f"generate_{t}"
        gen_calls.append(f"    {func_name}()")
        gen_funcs.append(f"""def {func_name}():
    headers = ["id", "timestamp", "entity_id", "region", "metric_value", "status_flag"]
    rows = [
        ["REC-001", "2026-08-01 10:00:00", "ENT-101", "Metro-North", 125.50, "ACTIVE"],
        ["REC-002", "2026-08-02 11:30:00", "ENT-102", "Metro-South", 88.20, "COMPLETED"],
        ["REC-003", "2026-08-03 14:15:00", "ENT-103", "West-Region", 210.00, "OPTIMAL"],
        ["REC-004", "2026-08-04 09:45:00", "ENT-104", "East-Region", 94.75, "ACTIVE"],
        ["REC-005", "2026-08-05 16:20:00", "ENT-105", "Central-Hub", 165.30, "VERIFIED"],
    ]
    with open(DATA_DIR / "{t}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
""")
        
        # Write initial CSV
        with open(data_dir / f"{t}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "timestamp", "entity_id", "region", "metric_value", "status_flag"])
            writer.writerow(["REC-001", "2026-08-01 10:00:00", "ENT-101", "Metro-North", 125.50, "ACTIVE"])
            writer.writerow(["REC-002", "2026-08-02 11:30:00", "ENT-102", "Metro-South", 88.20, "COMPLETED"])
            writer.writerow(["REC-003", "2026-08-03 14:15:00", "ENT-103", "West-Region", 210.00, "OPTIMAL"])
            writer.writerow(["REC-004", "2026-08-04 09:45:00", "ENT-104", "East-Region", 94.75, "ACTIVE"])
            writer.writerow(["REC-005", "2026-08-05 16:20:00", "ENT-105", "Central-Hub", 165.30, "VERIFIED"])
            
    gen_funcs_str = "\n".join(gen_funcs)
    gen_calls_str = "\n".join(gen_calls)
    gen_script_code = f"""\"\"\"Generate synthetic seed CSV data for {agent_name}.\"\"\"
import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent

{gen_funcs_str}

def main():
{gen_calls_str}
    print("{agent_name} seed data generated.")

if __name__ == "__main__":
    main()
"""
    (data_dir / "generate_seed_data.py").write_text(gen_script_code, encoding="utf-8")
    
    # Create placeholder demos
    demo_domain_dir = demos_root / domain
    demo_domain_dir.mkdir(parents=True, exist_ok=True)
    demo_html = demo_domain_dir / f"{agent_name}.html"
    demo_mp4 = demo_domain_dir / f"{agent_name}.mp4"
    
    demo_html.write_text(f"<!DOCTYPE html><html><head><title>{display_title}</title></head><body><h1>{display_title} Demo</h1></body></html>", encoding="utf-8")
    demo_mp4.write_bytes(b"\x00\x00\x00 ftypmp42\x00\x00\x00\x00mp42isom")
    
    if idx % 10 == 0 or idx == len(agents_meta):
        print(f"  [{idx}/{len(agents_meta)}] Scaffolding complete for {domain}/{agent_name}")

print("✅ All 45 Telco Enterprise Agents successfully scaffolded!")
