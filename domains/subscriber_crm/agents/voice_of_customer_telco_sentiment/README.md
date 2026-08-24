# Subscriber CRM: Voice of Customer Telco Sentiment

Part of the **Telco Enterprise Agents** platform for Gemini Enterprise.

---

## 1. Why This Agent Matters

### Business Problem
Performs real-time NLP sentiment analysis across care transcripts, NPS surveys, and social channels to surface systemic friction.

### Target Personas
Voice of Customer Lead, Chief Customer Officer, Quality Assurance Manager

### Key Metrics Tracked
| Metric | Benchmark / Target | Business Impact |
| :--- | :--- | :--- |
| **Care Transcript Sentiment Classification** | `>= 94.2%` | Real-time identification of customer frustration, billing confusion, and churn intent. |
| **Systemic Issue Root-Cause Discovery** | `< 4 hours` | Lead time from emerging billing/network glitch to executive escalation notification. |
| **Negative Sentiment Intervention Save Rate** | `>= 31.0%` | Proactive outreach to dissatisfied callers converting into positive retention. |

---

## 2. What It Answers & Sub-Agent Routing

### Sub-Agent Architecture
- **`data_insights`**: Queries internal BigQuery tables using the BigQuery Conversational Analytics API (`ask_data_insights`, `forecast`, `analyze_contribution`, `detect_anomalies`) and generates visual data charts via `render_chart`.
- **`market_context`**: Leverages Google Search grounding for external telecom industry benchmarks, GSMA/3GPP standards, TM Forum ODA specifications, and competitive intelligence.
- **`root_agent`**: Orchestrates routing between internal analytics and external market intelligence.

---

## 3. Sample Q&A Showcase

### Example 1: Internal Analytics (Data Insights)
*Question:* "What are our primary operational metrics and performance targets for voice of customer telco sentiment across operating regions in 2026 YTD?"
*Response:*
> Over the past 30 days, performance metrics for **Voice of Customer Telco Sentiment** achieved an overall **94.8% compliance rate** across all operating clusters, exceeding the 92.0% operational benchmark.
> 
> - **Metro North:** 96.2% efficiency index
> - **Metro South:** 95.1% operational uptime
> - **West Region:** 93.8% target achievement
> 
> Primary Business Value: **Root-Cause Sentiment Intelligence (-28% recurring customer friction points)**.

### Example 2: Market Grounding (Market Context)
*Question:* "What are the latest telecom industry standards, GSMA guidelines, and market benchmarks for voice of customer telco sentiment?"
*Response:*
> According to recent TM Forum Open Digital Architecture (ODA) and GSMA 2026 industry intelligence, tier-1 operators deploying automated conversational AI and AIOps analytics achieve a **35% reduction in MTTR** and a **22% improvement in customer satisfaction (CSAT)**.

### Example 3: Chart Visualization (`sample_chart.png`)
*Question:* "Render a chart comparing monthly performance metrics for voice of customer telco sentiment vs annual targets."
*Generated Visual Artifact:*
![Sample Chart](sample_chart.png)

---

## 4. Operational Value & Deployment
- **Deployment Class**: ReasoningEngine / Vertex AI Agent Engine
- **Runtime**: `gemini-3.5-flash`
- **Location**: `us-central1`
