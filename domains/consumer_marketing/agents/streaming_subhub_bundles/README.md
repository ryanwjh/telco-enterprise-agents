# Consumer Marketing: Streaming SubHub Bundles

Part of the **Telco Enterprise Agents** platform for Gemini Enterprise.

---

## 1. Why This Agent Matters

### Business Problem
Correlates OTT streaming data to recommend unified billing content bundles.

### Target Personas
Content Partnerships Director, Entertainment Bundle Specialist, BSS Commerce Manager

### Key Metrics Tracked
| Metric | Benchmark / Target | Business Impact |
| :--- | :--- | :--- |
| **OTT SubHub Adoption Rate** | `>= 21.0%` | Subscribers consolidating 2+ external streaming subscriptions into telco billing. |
| **Multi-Subscription Churn Resilience** | `0.45% churn` | Significantly lower monthly churn for subscribers with unified entertainment packs. |
| **Carrier Billing Commission Revenue** | `+$85K/mo` | Incremental commission revenue earned from OTT digital marketplace partners. |

---

## 2. What It Answers & Sub-Agent Routing

### Sub-Agent Architecture
- **`data_insights`**: Queries internal BigQuery tables using the BigQuery Conversational Analytics API (`ask_data_insights`, `forecast`, `analyze_contribution`, `detect_anomalies`) and generates visual data charts via `render_chart`.
- **`market_context`**: Leverages Google Search grounding for external telecom industry benchmarks, GSMA/3GPP standards, TM Forum ODA specifications, and competitive intelligence.
- **`root_agent`**: Orchestrates routing between internal analytics and external market intelligence.

---

## 3. Sample Q&A Showcase

### Example 1: Internal Analytics (Data Insights)
*Question:* "What are our primary operational metrics and performance targets for streaming subhub bundles across operating regions in 2026 YTD?"
*Response:*
> Over the past 30 days, performance metrics for **Streaming SubHub Bundles** achieved an overall **94.8% compliance rate** across all operating clusters, exceeding the 92.0% operational benchmark.
> 
> - **Metro North:** 96.2% efficiency index
> - **Metro South:** 95.1% operational uptime
> - **West Region:** 93.8% target achievement
> 
> Primary Business Value: **Stickiness & ARPU (+$8.50/mo bundle ARPU)**.

### Example 2: Market Grounding (Market Context)
*Question:* "What are the latest telecom industry standards, GSMA guidelines, and market benchmarks for streaming subhub bundles?"
*Response:*
> According to recent TM Forum Open Digital Architecture (ODA) and GSMA 2026 industry intelligence, tier-1 operators deploying automated conversational AI and AIOps analytics achieve a **35% reduction in MTTR** and a **22% improvement in customer satisfaction (CSAT)**.

### Example 3: Chart Visualization (`sample_chart.png`)
*Question:* "Render a chart comparing monthly performance metrics for streaming subhub bundles vs annual targets."
*Generated Visual Artifact:*
![Sample Chart](sample_chart.png)

---

## 4. Operational Value & Deployment
- **Deployment Class**: ReasoningEngine / Vertex AI Agent Engine
- **Runtime**: `gemini-3.5-flash`
- **Location**: `us-central1`
