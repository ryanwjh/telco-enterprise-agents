# NetOps & AIOps: Automated Gemini PIR Generator

Part of the **Telco Enterprise Agents** platform for Gemini Enterprise.

---

## 1. Why This Agent Matters

### Business Problem
Drafts comprehensive Post Incident Reviews (PIR) by synthesizing incident chronology, telemetry spikes, and remediation logs.

### Target Personas
Service Reliability Engineering (SRE) Lead, Network Quality VP, Incident Commander

### Key Metrics Tracked
| Metric | Benchmark / Target | Business Impact |
| :--- | :--- | :--- |
| **PIR Draft Generation Lead Time** | `< 5 minutes` | Time to compile full multi-source incident timeline following service restoration. |
| **Chronology & Telemetry Accuracy** | `>= 98.0%` | Precise alignment of alarm timestamps, engineer chat logs, and remediation commands. |
| **Post-Mortem Action Item Completion** | `>= 92.0%` | Tracking and verification of preventive architecture recommendations. |

---

## 2. What It Answers & Sub-Agent Routing

### Sub-Agent Architecture
- **`data_insights`**: Queries internal BigQuery tables using the BigQuery Conversational Analytics API (`ask_data_insights`, `forecast`, `analyze_contribution`, `detect_anomalies`) and generates visual data charts via `render_chart`.
- **`market_context`**: Leverages Google Search grounding for external telecom industry benchmarks, GSMA/3GPP standards, TM Forum ODA specifications, and competitive intelligence.
- **`root_agent`**: Orchestrates routing between internal analytics and external market intelligence.

---

## 3. Sample Q&A Showcase

### Example 1: Internal Analytics (Data Insights)
*Question:* "What are our primary operational metrics and performance targets for automated gemini pir generator across operating regions in 2026 YTD?"
*Response:*
> Over the past 30 days, performance metrics for **Automated Gemini PIR Generator** achieved an overall **94.8% compliance rate** across all operating clusters, exceeding the 92.0% operational benchmark.
> 
> - **Metro North:** 96.2% efficiency index
> - **Metro South:** 95.1% operational uptime
> - **West Region:** 93.8% target achievement
> 
> Primary Business Value: **Engineering Efficiency (85% reduction in manual PIR drafting time)**.

### Example 2: Market Grounding (Market Context)
*Question:* "What are the latest telecom industry standards, GSMA guidelines, and market benchmarks for automated gemini pir generator?"
*Response:*
> According to recent TM Forum Open Digital Architecture (ODA) and GSMA 2026 industry intelligence, tier-1 operators deploying automated conversational AI and AIOps analytics achieve a **35% reduction in MTTR** and a **22% improvement in customer satisfaction (CSAT)**.

### Example 3: Chart Visualization (`sample_chart.png`)
*Question:* "Render a chart comparing monthly performance metrics for automated gemini pir generator vs annual targets."
*Generated Visual Artifact:*
![Sample Chart](sample_chart.png)

---

## 4. Operational Value & Deployment
- **Deployment Class**: ReasoningEngine / Vertex AI Agent Engine
- **Runtime**: `gemini-3.5-flash`
- **Location**: `us-central1`
