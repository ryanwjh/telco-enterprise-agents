# Consumer Marketing: Retail Store Placement

Part of the **Telco Enterprise Agents** platform for Gemini Enterprise.

---

## 1. Why This Agent Matters

### Business Problem
Analyzes geospatial telemetry and foot traffic to optimize retail store and kiosk locations.

### Target Personas
Retail Operations VP, Geospatial Network Planner, Channel Strategy Director

### Key Metrics Tracked
| Metric | Benchmark / Target | Business Impact |
| :--- | :--- | :--- |
| **Store Footfall Conversion** | `>= 24.0%` | Walk-in traffic converting into new postpaid subscriptions or device upgrades. |
| **Capex Site Efficiency** | `+32% ROI` | Net revenue contribution per square foot across company-owned retail stores. |
| **Underperforming Site Rationalization** | `< 60 days` | Identification and relocation cycle time for low-yield retail kiosks. |

---

## 2. What It Answers & Sub-Agent Routing

### Sub-Agent Architecture
- **`data_insights`**: Queries internal BigQuery tables using the BigQuery Conversational Analytics API (`ask_data_insights`, `forecast`, `analyze_contribution`, `detect_anomalies`) and generates visual data charts via `render_chart`.
- **`market_context`**: Leverages Google Search grounding for external telecom industry benchmarks, GSMA/3GPP standards, TM Forum ODA specifications, and competitive intelligence.
- **`root_agent`**: Orchestrates routing between internal analytics and external market intelligence.

---

## 3. Sample Q&A Showcase

### Example 1: Internal Analytics (Data Insights)
*Question:* "What are our primary operational metrics and performance targets for retail store placement across operating regions in 2026 YTD?"
*Response:*
> Over the past 30 days, performance metrics for **Retail Store Placement** achieved an overall **94.8% compliance rate** across all operating clusters, exceeding the 92.0% operational benchmark.
> 
> - **Metro North:** 96.2% efficiency index
> - **Metro South:** 95.1% operational uptime
> - **West Region:** 93.8% target achievement
> 
> Primary Business Value: **Capex/Opex Optimization ($1.2M annual savings)**.

### Example 2: Market Grounding (Market Context)
*Question:* "What are the latest telecom industry standards, GSMA guidelines, and market benchmarks for retail store placement?"
*Response:*
> According to recent TM Forum Open Digital Architecture (ODA) and GSMA 2026 industry intelligence, tier-1 operators deploying automated conversational AI and AIOps analytics achieve a **35% reduction in MTTR** and a **22% improvement in customer satisfaction (CSAT)**.

### Example 3: Chart Visualization (`sample_chart.png`)
*Question:* "Render a chart comparing monthly performance metrics for retail store placement vs annual targets."
*Generated Visual Artifact:*
![Sample Chart](sample_chart.png)

---

## 4. Operational Value & Deployment
- **Deployment Class**: ReasoningEngine / Vertex AI Agent Engine
- **Runtime**: `gemini-3.5-flash`
- **Location**: `us-central1`
