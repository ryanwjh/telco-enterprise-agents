# Subscriber CRM: Proactive Retention Save Offers

Part of the **Telco Enterprise Agents** platform for Gemini Enterprise.

---

## 1. Why This Agent Matters

### Business Problem
Generates personalized, margin-aware discount and upgrade incentives during active cancellation requests.

### Target Personas
Retention Operations Director, CVM Value Optimization Lead, Loyalty Program Head

### Key Metrics Tracked
| Metric | Benchmark / Target | Business Impact |
| :--- | :--- | :--- |
| **Cancellation Save Rate** | `>= 38.5%` | High-value subscribers choosing personalized retention offer over contract cancellation. |
| **Offer Margin Protection** | `>= 42% margin` | Algorithmically constrained discount depth preserving account contribution margin. |
| **6-Month Post-Save Churn Rate** | `< 3.8%` | Sustained customer retention following acceptance of personalized save proposal. |

---

## 2. What It Answers & Sub-Agent Routing

### Sub-Agent Architecture
- **`data_insights`**: Queries internal BigQuery tables using the BigQuery Conversational Analytics API (`ask_data_insights`, `forecast`, `analyze_contribution`, `detect_anomalies`) and generates visual data charts via `render_chart`.
- **`market_context`**: Leverages Google Search grounding for external telecom industry benchmarks, GSMA/3GPP standards, TM Forum ODA specifications, and competitive intelligence.
- **`root_agent`**: Orchestrates routing between internal analytics and external market intelligence.

---

## 3. Sample Q&A Showcase

### Example 1: Internal Analytics (Data Insights)
*Question:* "What are our primary operational metrics and performance targets for proactive retention save offers across operating regions in 2026 YTD?"
*Response:*
> Over the past 30 days, performance metrics for **Proactive Retention Save Offers** achieved an overall **94.8% compliance rate** across all operating clusters, exceeding the 92.0% operational benchmark.
> 
> - **Metro North:** 96.2% efficiency index
> - **Metro South:** 95.1% operational uptime
> - **West Region:** 93.8% target achievement
> 
> Primary Business Value: **Save Rate Improvement (+32% retention save rate)**.

### Example 2: Market Grounding (Market Context)
*Question:* "What are the latest telecom industry standards, GSMA guidelines, and market benchmarks for proactive retention save offers?"
*Response:*
> According to recent TM Forum Open Digital Architecture (ODA) and GSMA 2026 industry intelligence, tier-1 operators deploying automated conversational AI and AIOps analytics achieve a **35% reduction in MTTR** and a **22% improvement in customer satisfaction (CSAT)**.

### Example 3: Chart Visualization (`sample_chart.png`)
*Question:* "Render a chart comparing monthly performance metrics for proactive retention save offers vs annual targets."
*Generated Visual Artifact:*
![Sample Chart](sample_chart.png)

---

## 4. Operational Value & Deployment
- **Deployment Class**: ReasoningEngine / Vertex AI Agent Engine
- **Runtime**: `gemini-3.5-flash`
- **Location**: `us-central1`
