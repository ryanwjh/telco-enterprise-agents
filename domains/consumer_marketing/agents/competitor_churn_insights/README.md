# Consumer Marketing: Competitor Churn Insights

Part of the **Telco Enterprise Agents** platform for Gemini Enterprise.

---

## 1. Why This Agent Matters

### Business Problem
Addressing core telecommunications operational challenges in competitor churn insights through automated quantitative analytics, predictive AI, and real-time grounding.

### Target Personas
Head of Telecom Operations, Consumer Marketing Director, Principal Network Engineer, CVM Strategy Lead

### Key Metrics Tracked
| Metric | Benchmark / Target | Business Impact |
| :--- | :--- | :--- |
| **Operational Efficiency** | `Target >= 92.0%` | Primary performance compliance rate across regional networks. |
| **Incident & Churn Reduction** | `Target < 1.5%` | Reduction in operational defects, service fallout, and customer churn. |
| **Financial ROI Uplift** | `+$180K/mo target` | Net recurring revenue contribution and operational cost savings. |

---

## 2. What It Answers & Sub-Agent Routing

### Sub-Agent Architecture
- **`data_insights`**: Queries internal BigQuery tables (`cmkt_cpci_*`) using the BigQuery Conversational Analytics API (`ask_data_insights`, `forecast`, `analyze_contribution`, `detect_anomalies`) and generates visual data charts via `render_chart`.
- **`market_context`**: Leverages Google Search grounding for external telecom industry benchmarks, GSMA/3GPP standards, and competitive intelligence.
- **`root_agent`**: Orchestrates routing between internal analytics and external market intelligence.

---

## 3. Sample Q&A Showcase

### Example 1: Internal Analytics (Data Insights)
*Question:* "What are our primary operational metrics and performance targets for competitor churn insights across operating regions in 2026 YTD?"
*Response:*
> Over the past 30 days, performance metrics for **Competitor Churn Insights** achieved an overall **94.8% compliance rate** across all operating clusters, exceeding the 92.0% operational benchmark.
> 
> - **Metro North:** 96.2% efficiency index
> - **Metro South:** 95.1% operational uptime
> - **West Region:** 93.8% target achievement
> 
> Total estimated operational savings delivered approximately **$214,000** in quarterly cost avoidance.

### Example 2: Market Grounding (Market Context)
*Question:* "What are the latest telecom industry standards, GSMA guidelines, and market benchmarks for competitor churn insights?"
*Response:*
> According to recent TM Forum Open Digital Architecture (ODA) and GSMA 2026 industry intelligence, tier-1 operators deploying automated conversational AI and AIOps analytics achieve a **35% reduction in MTTR** and a **22% improvement in customer satisfaction (CSAT)**.

### Example 3: Chart Visualization (`sample_chart.png`)
*Question:* "Render a chart comparing monthly performance metrics for competitor churn insights vs annual targets."
*Generated Visual Artifact:*
![Sample Chart](sample_chart.png)

---

## 4. Authorized BigQuery Tables

- `cmkt_cpci_port_out_mnp_requests` — Seeded via `data/port_out_mnp_requests.csv`
- `cmkt_cpci_competitor_campaign_intel` — Seeded via `data/competitor_campaign_intel.csv`
- `cmkt_cpci_churn_driver_correlations` — Seeded via `data/churn_driver_correlations.csv`

---

## 5. Example Questions

1. "What are our primary operational metrics and performance targets for competitor churn insights across operating regions in 2026 YTD?"
2. "What are the latest telecom industry standards, GSMA guidelines, and market benchmarks for competitor churn insights?"
3. "Render a chart comparing monthly performance metrics for competitor churn insights vs annual targets."
4. "Break down competitor churn insights volume by operating cluster and customer segment for 2026 YTD."
5. "What are the projected quarterly financial impacts and ROI of optimizing competitor churn insights?"

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
uv run --frozen pytest domains/consumer_marketing/agents/competitor_churn_insights/tests/unit -v

# Run interactively with ADK CLI
adk run domains/consumer_marketing/agents/competitor_churn_insights
```
