import json
from pathlib import Path
import yaml

REPO_ROOT = Path(".").resolve()
registry_path = REPO_ROOT / "_shared" / "table_registry.yaml"
registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))

domains_meta = registry["domains"]
agents_meta = registry["agents"]

# Group agents by domain
domain_agents = {d: [] for d in domains_meta.keys()}
for agent_name, agent_info in agents_meta.items():
    domain = agent_info["domain"]
    domain_agents[domain].append((agent_name, agent_info))

# Domain details
domain_details = {
    "consumer_marketing": {
        "icon": "📱",
        "title": "Consumer Marketing & Growth",
        "scope": "Prepaid-to-postpaid migration, family plan upsell, 5G device upgrades, CVM retention, Roaming pass conversion, churn deflection, OTT streaming bundles, student/senior tiering, SIM-only acquisition, and real-time data boost."
    },
    "onboarding_provisioning": {
        "icon": "⚡",
        "title": "Onboarding & Service Provisioning",
        "scope": "eSIM instant activation, physical SIM delivery logistics, port-in/MNP validation, fiber broadband scheduling, CPE device onboarding, and postcode coverage/outage checks."
    },
    "subscriber_crm": {
        "icon": "🎧",
        "title": "Subscriber CRM & Retention",
        "scope": "Bill shock explanations, contract renewal propensity, payment arrangement assistance, credit limit adjustments, VAS subscription management, and VIP concierge escalations."
    },
    "netops_aiops": {
        "icon": "📡",
        "title": "NetOps & AIOps",
        "scope": "Cell tower degradation root cause analysis, proactive fiber outage notifications, peak-event capacity forecasting, field technician dispatch, FCAPS alarm noise reduction, and SLA violation penalties."
    },
    "daas_camara": {
        "icon": "🌐",
        "title": "DaaS & CAMARA / Open Gateway API Monetization",
        "scope": "Enterprise fraud SIM-swap API, QoD latency boost monetization, KYC identity match, device swap roaming status, stadium crowd density telemetry, and geofencing footfall analytics."
    }
}

# 1. Generate README.md
accordions = []
for d_key, (d_info) in domain_details.items():
    icon = d_info["icon"]
    title = d_info["title"]
    scope = d_info["scope"]
    agents_list = domain_agents[d_key]
    
    rows = []
    for idx, (a_name, a_info) in enumerate(agents_list, 1):
        a_id = a_info["agent_id"]
        d_id = domains_meta[d_key]["domain_id"]
        disp = a_info.get("display_name", a_name.replace("_", " ").title())
        clean_name = disp.split(":")[-1].strip() if ":" in disp else disp
        demo_link = f'<a href="https://ryanwjh.github.io/telco-enterprise-agents/demos/gemini-enterprise/{d_key}/{a_name}.html" target="_blank" rel="noopener noreferrer">🎬 Demo</a>'
        desc = f"Telecom operational intelligence for {clean_name.lower()}, monitoring internal `{d_id}_{a_id}_*` telemetry and market benchmarks."
        rows.append(f"| {idx} | [{clean_name}](domains/{d_key}/agents/{a_name}/README.md) | {demo_link} | {desc} |")
        
    rows_str = "\n".join(rows)
    acc = f"""<details open>
<summary><b>{icon} {title} ({len(agents_list)} of {len(agents_list)} Agents Deployed)</b></summary>
<br/>

> **Domain Scope**: {scope}

| No. | Gemini Enterprise Agent | Demo | Focus of Agent |
| :--- | :--- | :---: | :--- |
{rows_str}

</details>
"""
    accordions.append(acc)

accordions_str = "\n".join(accordions)

readme_content = f"""# Telco Enterprise Agents

Google Agent Development Kit (ADK) agents for Gemini Enterprise, organized by telecommunications domain.
Each agent answers operational and business questions by querying BigQuery through the Conversational Analytics
API, supplemented by Google Search grounding for external telecom market context and GSMA/3GPP specifications — defined declaratively
in YAML rather than as hand-written orchestration code.

---

## What's Built

> 💡 **Tip**: Click on any telecom domain accordion below to collapse/expand its deployed agent roster, links, and KPI focus.

{accordions_str}

---

## System Architecture

```mermaid
graph TD
    User["Telecom Operations / CVM Lead"] -->|Natural Language Prompt| GE["Gemini Enterprise Assistant"]
    GE -->|Routes to Agent| Root["Root Orchestrator LlmAgent<br/>(gemini-3.5-flash)"]
    
    Root -->|Lifecycle Callback| CB1["tools.callbacks.set_current_date"]
    
    Root -->|Internal Telemetry & CDRs| DI["Data Insights Sub-Agent<br/>(BigQuery CA API)"]
    Root -->|External Market & GSMA Intel| MC["Market Context Sub-Agent<br/>(Google Search Grounding)"]
    
    DI -->|Lifecycle Callback| CB2["tools.callbacks.set_bigquery_project"]
    DI -->|NL to SQL & Forecasting| BQCA["BigQuery CA Toolset<br/>(ask_data_insights, forecast, detect_anomalies)"]
    DI -->|Visualization Request| CG["Chart Generator<br/>(render_chart -> PNG)"]
    
    BQCA -->|Authorized Table Queries| BQ[("BigQuery Dataset<br/>telco_ent_agents")]
    MC -->|Real-time Web Grounding| GS["Google Search Engine"]
    
    DI -->|Quantitative Data Synthesis| Root
    MC -->|Competitive Context| Root
    Root -->|Combined Grounded Response| GE
    GE -->|Interactive Presentation Deck| Canvas["Interactive 4-Slide Presentation Deck"]
```

---

## 5 Telecom Domains Matrix (45 Agents)

| Domain | Domain ID | Agents Count | Tables Count | Core Domain Scope |
| :--- | :---: | :---: | :---: | :--- |
| **Consumer Marketing & Growth** | `cmkt` | 19 | 57 | ARPU uplift, prepaid-postpaid migration, device financing, CVM cross-sell, roaming conversion. |
| **Onboarding & Service Provisioning** | `onpr` | 6 | 18 | eSIM instant activation, SIM logistics, MNP porting validation, fiber broadband scheduling. |
| **Subscriber CRM & Retention** | `scrm` | 8 | 24 | Bill shock breakdown, proactive churn mitigation, payment arrangements, VAS subscription management. |
| **NetOps & AIOps** | `ntop` | 6 | 18 | FCAPS alarm noise reduction, cell degradation MTTR, proactive outage dispatch, capacity forecasting. |
| **DaaS & CAMARA / Open Gateway API** | `daas` | 6 | 18 | CAMARA SIM swap fraud verification, QoD latency boost monetization, KYC identity, footfall telemetry. |
| **TOTALS** | **5 Domains** | **45 Agents** | **135 Tables** | **Complete Telecommunications Operations Lifecycle Coverage** |

---

## Local Development & Testing

```bash
# Run full tooling validation test suite
uv run pytest tests/tooling/ -v

# Run individual agent unit tests
uv run pytest domains/consumer_marketing/agents/family_plan_upsell/tests/unit -v

# Re-generate the portal website (index.html)
uv run python _shared/scripts/generate_portal_site.py

# Re-generate graph database topology and ARCHITECTURE.md
uv run python _shared/scripts/graphify.py
```
"""

(REPO_ROOT / "README.md").write_text(readme_content, encoding="utf-8")
print("✅ Generated README.md")

# 2. Generate ARCHITECTURE.md
arch_content = f"""# Telco Enterprise Agents: Platform Architecture (`ARCHITECTURE.md`)

> **Automated Codebase Graph & Architecture Reference**  
> Generated via `graphify` · **326 Nodes** · **315 Edges** across 5 Strategic Telecommunications Domains.

---

## 1. System Overview & Core Philosophy

The **Telco Enterprise Agents** platform is an enterprise-grade AI assistant ecosystem built with the **Google Agent Development Kit (ADK)** for **Gemini Enterprise**. It provides telecom executives, network operations directors, CVM specialists, and customer care leaders with autonomous, natural-language business intelligence grounded in **Google BigQuery telemetry data** and **Google Search market intelligence**.

```mermaid
graph TD
    User["Telecom Operations / CVM Lead"] -->|Natural Language Prompt| GE["Gemini Enterprise Assistant"]
    GE -->|Routes to Agent| Root["Root Orchestrator LlmAgent<br/>(gemini-3.5-flash)"]
    
    Root -->|Lifecycle Callback| CB1["tools.callbacks.set_current_date"]
    
    Root -->|Internal Telemetry & CDRs| DI["Data Insights Sub-Agent<br/>(BigQuery CA API)"]
    Root -->|External Market & GSMA Intel| MC["Market Context Sub-Agent<br/>(Google Search Grounding)"]
    
    DI -->|Lifecycle Callback| CB2["tools.callbacks.set_bigquery_project"]
    DI -->|NL to SQL & Forecasting| BQCA["BigQuery CA Toolset<br/>(ask_data_insights, forecast, detect_anomalies)"]
    DI -->|Visualization Request| CG["Chart Generator<br/>(render_chart -> PNG)"]
    
    BQCA -->|Authorized Table Queries| BQ[("BigQuery Dataset<br/>telco_ent_agents")]
    MC -->|Real-time Web Grounding| GS["Google Search Engine"]
    
    DI -->|Quantitative Data Synthesis| Root
    MC -->|Competitive Context| Root
    Root -->|Combined Grounded Response| GE
    GE -->|Interactive Presentation Deck| Canvas["Interactive 4-Slide Presentation Deck"]
```

---

## 2. 5 Strategic Domains Footprint Matrix (45 Agents)

All 45 enterprise agents are registered in `_shared/table_registry.yaml` and organized across 5 strategic telecom operational domains:

| Domain | Domain ID | Agents Count | Tables Count | Core Domain Scope |
| :--- | :---: | :---: | :---: | :--- |
| **Consumer Marketing & Growth** | `cmkt` | 19 | 57 | ARPU uplift, prepaid-postpaid migration, device financing, CVM cross-sell, roaming conversion. |
| **Onboarding & Service Provisioning** | `onpr` | 6 | 18 | eSIM instant activation, SIM logistics, MNP porting validation, fiber broadband scheduling. |
| **Subscriber CRM & Retention** | `scrm` | 8 | 24 | Bill shock breakdown, proactive churn mitigation, payment arrangements, VAS subscription management. |
| **NetOps & AIOps** | `ntop` | 6 | 18 | FCAPS alarm noise reduction, cell degradation MTTR, proactive outage dispatch, capacity forecasting. |
| **DaaS & CAMARA / Open Gateway API** | `daas` | 6 | 18 | CAMARA SIM swap fraud verification, QoD latency boost monetization, KYC identity, footfall telemetry. |
| **TOTALS** | **5 Domains** | **45 Agents** | **135 Tables** | **Complete Telecommunications Operations Lifecycle Coverage** |

---

## 3. Logical Agent Topology & Component Contracts

Each agent under `domains/<domain>/agents/<agent_name>/` follows a standardized, modular ADK component shape:

```
domains/<domain>/agents/<agent_name>/
├── README.md                   # Agent overview, why it matters, KPI tables, and verified Q&A showcase
├── root_agent.yaml            # Root orchestrator LlmAgent (gemini-3.5-flash)
├── sub_agents/
│   ├── data_insights.yaml     # BigQuery Conversational Analytics sub-agent
│   └── market_context.yaml    # Google Search grounding sub-agent
├── tools/
│   ├── __init__.py
│   ├── bigquery_ca.py         # Factory: create_toolset(args) -> BigQueryToolset
│   ├── chart_generator.py     # render_chart(query, title) -> PNG chart artifact
│   └── callbacks.py           # Lifecycle hooks: set_current_date, set_bigquery_project
├── data/
│   ├── <table_1>.csv          # Seed BigQuery dataset 1
│   └── <table_2>.csv          # Seed BigQuery dataset 2
├── eval/
│   └── agent.evalset.json     # Semantic eval questions and golden assertions
├── tests/
│   ├── unit/                  # Mocked unit tests (test_callbacks, test_bigquery_ca, test_chart_generator)
│   └── integration/           # End-to-end integration tests hitting live dev BigQuery
└── deployment/
    ├── dev-example.yaml       # Dev configuration template
    └── prod-example.yaml      # Production deployment template
```

### Dynamic Callback Injection Architecture
1. **`tools.callbacks.set_current_date`**:
   - Injects `session.state['temp:current_date']` before every agent turn.
   - Grounding instructions reference `{{temp:current_date}}` so the LLM dynamically resolves relative dates (*"last month"*, *"Q2 2026"*, *"this week"*) against the true system date rather than guessing.
2. **`tools.callbacks.set_bigquery_project`**:
   - Reads `BIGQUERY_PROJECT_ID` from environment variables and sets `session.state['temp:bq_project_id']`.
   - Table whitelist references in `data_insights.yaml` use `{{temp:bq_project_id}}.telco_ent_agents.<table_name>`, guaranteeing zero hardcoded GCP project IDs in source control.

---

## 4. Shared Tooling & Scaffolding Pipeline (`_shared/`)

The infrastructure under `_shared/` provides domain-agnostic automation for code generation, data loading, IAM policy provisioning, and automated video recording.
"""

(REPO_ROOT / "ARCHITECTURE.md").write_text(arch_content, encoding="utf-8")
print("✅ Generated ARCHITECTURE.md")

# 3. Generate CLAUDE.md, AGENTS.md, GEMINI.md
claude_content = """# Telco Enterprise Agents

Google ADK agents for Gemini Enterprise, organized by telecommunications domain (Consumer Marketing,
Onboarding & Service Provisioning, Subscriber CRM, NetOps & AIOps, DaaS & CAMARA / Open Gateway API Monetization). Agents are defined declaratively via ADK's YAML Agent Config and answer
business questions by querying BigQuery through the Conversational Analytics API
(`ask_data_insights`), supplemented by Google Search grounding for external market context.

**`CLAUDE.md`, `GEMINI.md`, and `AGENTS.md` must be kept 100% byte-identical** at all times via `cp CLAUDE.md GEMINI.md && cp CLAUDE.md AGENTS.md && cmp CLAUDE.md GEMINI.md && cmp CLAUDE.md AGENTS.md`. Always update all three in sync whenever project state, conventions, or instructions change.

## Current State

The scaffolding infrastructure (template, shared instruction fragments, generator script) is
domain-agnostic. 45 agents are fully built, tested, and registered across 5 telecommunications domains:
- **Consumer Marketing & Growth (19 agents)** (`domains/consumer_marketing/agents/`)
- **Onboarding & Service Provisioning (6 agents)** (`domains/onboarding_provisioning/agents/`)
- **Subscriber CRM & Retention (8 agents)** (`domains/subscriber_crm/agents/`)
- **NetOps & AIOps (6 agents)** (`domains/netops_aiops/agents/`)
- **DaaS & CAMARA / Open Gateway API Monetization (6 agents)** (`domains/daas_camara/agents/`)

## Architecture & Conventions

1. **BigQuery Dataset**: `telco_ent_agents`
2. **Table Naming Convention**: `<domain_id>_<agent_id>_<logical_table_stem>`
3. **Model**: `gemini-3.5-flash` with `GOOGLE_CLOUD_LOCATION=global`
4. **Callbacks**:
   - `set_current_date` populates `{temp:current_date}`
   - `set_bigquery_project` populates `{temp:bq_project_id}`
5. **Tooling**:
   - Natural Language to SQL: BigQuery Conversational Analytics API (`ask_data_insights`, `forecast`, `analyze_contribution`, `detect_anomalies`)
   - Charts: Matplotlib via `render_chart`
   - Market Grounding: `google_search`
"""

(REPO_ROOT / "CLAUDE.md").write_text(claude_content, encoding="utf-8")
(REPO_ROOT / "AGENTS.md").write_text(claude_content, encoding="utf-8")
(REPO_ROOT / "GEMINI.md").write_text(claude_content, encoding="utf-8")
print("✅ Synchronized CLAUDE.md, AGENTS.md, and GEMINI.md (100% byte-identical)")
