# Telco Enterprise Agents

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
