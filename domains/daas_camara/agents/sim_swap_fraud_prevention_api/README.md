# DaaS & CAMARA: SIM Swap Fraud Prevention API

Part of the **Telco Enterprise Agents** platform for Gemini Enterprise.

---

## 1. Why This Agent Matters

### Business Problem
Exposes CAMARA-compliant SIM Swap verification APIs to financial institutions to prevent unauthorized OTP interception.

### Target Personas
Open Gateway Product Director, Banking Security Partnerships Lead, API Monetization Architect

### Key Metrics Tracked
| Metric | Benchmark / Target | Business Impact |
| :--- | :--- | :--- |
| **CAMARA SIM Swap Query Latency** | `< 150 ms` | Sub-200ms API response time integrated into high-speed banking auth flows. |
| **Account Takeover (ATO) Interception** | `>= 99.8%` | Zero-day fraud prevention for unauthorized bank transfers following SIM swap. |
| **Banking Partner API Availability** | `99.999% SLA` | Carrier-grade high availability for mission-critical financial verification. |

---

## 2. What It Answers & Sub-Agent Routing

### Sub-Agent Architecture
- **`data_insights`**: Queries internal BigQuery tables using the BigQuery Conversational Analytics API (`ask_data_insights`, `forecast`, `analyze_contribution`, `detect_anomalies`) and generates visual data charts via `render_chart`.
- **`market_context`**: Leverages Google Search grounding for external telecom industry benchmarks, GSMA/3GPP standards, TM Forum ODA specifications, and competitive intelligence.
- **`root_agent`**: Orchestrates routing between internal analytics and external market intelligence.

---

## 3. Sample Q&A Showcase

### Example 1: Internal Analytics (Data Insights)
*Question:* "What are our primary operational metrics and performance targets for sim swap fraud prevention api across operating regions in 2026 YTD?"
*Response:*
> Over the past 30 days, performance metrics for **SIM Swap Fraud Prevention API** achieved an overall **94.8% compliance rate** across all operating clusters, exceeding the 92.0% operational benchmark.
> 
> - **Metro North:** 96.2% efficiency index
> - **Metro South:** 95.1% operational uptime
> - **West Region:** 93.8% target achievement
> 
> Primary Business Value: **API Monetization ($1.1M annual B2B banking revenue)**.

### Example 2: Market Grounding (Market Context)
*Question:* "What are the latest telecom industry standards, GSMA guidelines, and market benchmarks for sim swap fraud prevention api?"
*Response:*
> According to recent TM Forum Open Digital Architecture (ODA) and GSMA 2026 industry intelligence, tier-1 operators deploying automated conversational AI and AIOps analytics achieve a **35% reduction in MTTR** and a **22% improvement in customer satisfaction (CSAT)**.

### Example 3: Chart Visualization (`sample_chart.png`)
*Question:* "Render a chart comparing monthly performance metrics for sim swap fraud prevention api vs annual targets."
*Generated Visual Artifact:*
![Sample Chart](sample_chart.png)

---

## 4. Operational Value & Deployment
- **Deployment Class**: ReasoningEngine / Vertex AI Agent Engine
- **Runtime**: `gemini-3.5-flash`
- **Location**: `us-central1`
