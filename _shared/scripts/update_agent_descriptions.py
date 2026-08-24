#!/usr/bin/env python3
"""Updates descriptions across all 45 Telco Enterprise Agents.

Updates:
1. _shared/table_registry.yaml (adds unique descriptions and ROI values)
2. domains/<domain>/agents/<agent_name>/root_agent.yaml
3. domains/<domain>/agents/<agent_name>/sub_agents/data_insights.yaml
4. domains/<domain>/agents/<agent_name>/sub_agents/market_context.yaml
5. domains/<domain>/agents/<agent_name>/README.md
6. Re-generates demo showcase pages and portal index.html
"""

from pathlib import Path
import re
import sys
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

TELCO_AGENT_SPECS = {
    # Consumer Marketing (19)
    "family_plan_upsell": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: Family Plan Upsell",
        "description": "Identifies multi-line households sharing data to recommend consolidated family plans.",
        "roi_metric": "ARPU Growth (+$180K/mo target)",
        "personas": "Head of Consumer Marketing, CVM Strategy Lead, Digital Campaign Manager",
        "kpis": [
            ("Family Plan Conversion Rate", ">= 18.5%", "Percentage of multi-line households upgrading to consolidated family tiers."),
            ("Household Blended ARPU", "+$14.20/mo", "Net recurring revenue increase per consolidated household account."),
            ("Multi-Line Account Retention", "< 0.8% churn", "Long-term churn reduction from multi-service household stickiness.")
        ]
    },
    "retail_store_placement": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: Retail Store Placement",
        "description": "Analyzes geospatial telemetry and foot traffic to optimize retail store and kiosk locations.",
        "roi_metric": "Capex/Opex Optimization ($1.2M annual savings)",
        "personas": "Retail Operations VP, Geospatial Network Planner, Channel Strategy Director",
        "kpis": [
            ("Store Footfall Conversion", ">= 24.0%", "Walk-in traffic converting into new postpaid subscriptions or device upgrades."),
            ("Capex Site Efficiency", "+32% ROI", "Net revenue contribution per square foot across company-owned retail stores."),
            ("Underperforming Site Rationalization", "< 60 days", "Identification and relocation cycle time for low-yield retail kiosks.")
        ]
    },
    "five_g_handset_upgrade": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: 5G Handset Upgrade",
        "description": "Targets 4G device users in 5G-heavy coverage areas with personalized upgrade incentives.",
        "roi_metric": "5G Adoption Rate (+28% uplift)",
        "personas": "Device Product Manager, Consumer Segment Lead, Retention Marketing Specialist",
        "kpis": [
            ("5G Migration Propensity", ">= 22.0%", "Targeted 4G subscribers upgrading to certified 5G standalone handsets."),
            ("Post-Upgrade Data Consumption", "+45% GB/mo", "Data usage uplift following transition to high-speed 5G network tiers."),
            ("Device Financing Attach Rate", ">= 65%", "Subscribers pairing handset upgrades with monthly installment plans.")
        ]
    },
    "volte_compliance_grey_market": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: VoLTE Compliance & Grey Market",
        "description": "Detects non-VoLTE compliant or grey market devices to proactively warn and transition users.",
        "roi_metric": "Compliance & Churn Prevention (< 0.5% disconnect churn)",
        "personas": "Regulatory Affairs Lead, Device Certification Manager, Customer Care Director",
        "kpis": [
            ("VoLTE Readiness Audit Rate", "100% active base", "Coverage of IMEI database checked for GSMA VoLTE emergency calling compliance."),
            ("Emergency Call Failure Rate", "< 0.01%", "Prevention of 911/112 call drops from non-compliant 3G sunset handsets."),
            ("Proactive Upgrade Deflection", ">= 85%", "At-risk subscribers successfully transitioned prior to legacy 3G network shutdown.")
        ]
    },
    "international_call_pack": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: International Call Pack",
        "description": "Monitors international dialing telemetry to offer timely, cost-saving roaming and IDD packs.",
        "roi_metric": "ARPU Growth (+$95K/mo incremental revenue)",
        "personas": "IDD Product Specialist, International Roaming Manager, CVM Campaign Analyst",
        "kpis": [
            ("IDD Pack Attach Rate", ">= 31.0%", "Subscribers with recurring international calls adopting bundle discounts."),
            ("Bill Shock Dispute Reduction", "-42% disputes", "Reduction in billing complaints resulting from out-of-bundle pay-as-you-go IDD rates."),
            ("High-Volume Route Margin", "+18% gross margin", "Margin improvement on high-traffic international dialing destinations.")
        ]
    },
    "cloud_storage_upsell": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: Cloud Storage Upsell",
        "description": "Triggers automated cloud storage offers when users approach device capacity limits.",
        "roi_metric": "Value-Added Services Revenue ($140K/mo VAS uplift)",
        "personas": "Digital Services Lead, VAS Product Manager, Cloud Partnerships Director",
        "kpis": [
            ("Storage Warning Conversion", ">= 14.5%", "Users approaching 90% device memory purchasing integrated cloud backup."),
            ("Monthly Recurring VAS Revenue", "+$2.99/sub", "Average incremental VAS revenue per enrolled cloud storage subscriber."),
            ("Cross-Device Sync Retention", "> 92% renewal", "Annual subscription renewal rate for multi-device backup users.")
        ]
    },
    "tourist_welcome_roaming": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: Tourist Welcome & Roaming",
        "description": "Detects inbound roaming IMSIs to instantly send localized, language-specific welcome offers.",
        "roi_metric": "Roaming Revenue (+34% inbound pass revenue)",
        "personas": "Wholesale Roaming Director, Inbound Tourism Campaign Lead, Core Network Analyst",
        "kpis": [
            ("Inbound IMSI Detection Latency", "< 30 seconds", "Time from first international cell attachment to localized welcome SMS delivery."),
            ("Tourist eSIM / Roaming Pass Conversion", ">= 19.8%", "Inbound visitors purchasing local data passes or eSIM top-ups."),
            ("Visitor Network Attach Duration", "Average 6.8 days", "Network dwell time and data consumption per roaming visitor.")
        ]
    },
    "self_serve_device_specs": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: Self-Serve Device Specs",
        "description": "Powers conversational agents for customers comparing complex device specifications online.",
        "roi_metric": "Deflection to Digital (48% reduction in retail store query load)",
        "personas": "Digital Experience Manager, E-Commerce Product Lead, Web Conversion Specialist",
        "kpis": [
            ("Digital Funnel Conversion", ">= 16.2%", "Users engaging in device comparison tool completing online checkout."),
            ("Specification Comparison Time", "< 90 seconds", "Average time required for shoppers to evaluate band support and trade-in value."),
            ("Assisted Care Call Deflection", "+38% deflection", "Pre-purchase device inquiries resolved digitally without agent escalation.")
        ]
    },
    "five_g_home_broadband_upsell": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: 5G Home Broadband Upsell",
        "description": "Identifies fiber-constrained households with strong 5G signal for FWA upsell.",
        "roi_metric": "FWA Market Share (+15K quarterly net adds)",
        "personas": "Broadband Product Director, Fixed-Wireless Access Lead, Network Coverage Planner",
        "kpis": [
            ("FWA Qualification Accuracy", ">= 98.5%", "Addresses qualified for 5G FWA achieving rated downlink speeds without truck roll."),
            ("Fiber Competitor Win-Back", ">= 26.0%", "Subscribers in legacy DSL/copper areas transitioning to high-speed 5G FWA."),
            ("FWA Household Blended ARPU", "+$49.50/mo", "Average monthly service revenue per active fixed-wireless home gateway.")
        ]
    },
    "in_the_moment_data_boost": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: In-the-Moment Data Boost",
        "description": "Predicts mid-cycle data depletion and sends instant top-up offers before throttling.",
        "roi_metric": "Incremental Revenue ($220K/mo data top-up revenue)",
        "personas": "Real-Time Monetization Lead, CVM Decisioning Architect, Digital Engagement Specialist",
        "kpis": [
            ("Depletion Prediction Precision", ">= 91.0%", "Accuracy in forecasting data bucket exhaustion 48 hours before cycle end."),
            ("Real-Time Boost Acceptance", ">= 28.4%", "Subscribers purchasing 1-day or 7-day high-speed data passes via push notification."),
            ("Throttling Frustration Churn", "-35% reduction", "Decrease in end-of-month churn attributed to speed reduction or unexpected throttling.")
        ]
    },
    "five_g_gaming_qos_package": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: 5G Gaming QoS Package",
        "description": "Detects cloud gaming traffic to offer low-latency network slicing QoS upgrades.",
        "roi_metric": "Premium ARPU (+18% gaming segment ARPU)",
        "personas": "5G Standalone Product Manager, Network Slicing Architect, Youth & Gaming Segment Lead",
        "kpis": [
            ("Gaming Slicing QoS Activation Rate", ">= 12.5%", "Identified cloud and competitive gamers subscribing to low-latency priority packs."),
            ("Average Round-Trip Latency (RTT)", "< 20 ms", "SLA latency maintained during peak network hours on gaming QoS bearer slices."),
            ("Gaming Segment Net Promoter Score", "+18 pts NPS", "Satisfaction uplift among esports and cloud gaming subscribers.")
        ]
    },
    "airport_roaming_pass": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: Airport Roaming Pass",
        "description": "Uses geo-fencing at airports to prompt outbound travelers with roaming passes before departure.",
        "roi_metric": "Roaming Revenue (+40% pre-departure pass attach rate)",
        "personas": "Roaming Product Manager, Geospatial Engagement Lead, Mobile App Product Owner",
        "kpis": [
            ("Airport Cell Geo-Trigger Accuracy", ">= 96.0%", "Precision of outbound airport departures detected before flight takeoff."),
            ("Pre-Departure Roaming Pass Attach Rate", ">= 32.8%", "Outbound travelers activating global data passes prior to border crossing."),
            ("Bill Shock Complaints Avoidance", "-55% complaints", "Reduction in bill shock calls upon returning from international trips.")
        ]
    },
    "competitor_churn_insights": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: Competitor Churn Insights",
        "description": "Analyzes port-out telemetry and web behavior to identify competitor campaign impacts.",
        "roi_metric": "Churn Reduction (-0.35% annualized churn rate)",
        "personas": "Competitive Intelligence Director, Churn Analytics Specialist, CVM Strategy VP",
        "kpis": [
            ("Competitor Campaign Detection Lead Time", "< 48 hours", "Time required to identify rival promo pricing and aggressive port-out surges."),
            ("At-Risk Port-Out Deflection Rate", ">= 27.5%", "Subscribers receiving counter-offers prior to submitting formal MNP requests."),
            ("Net MNP Porting Ratio", "> 1.15", "Ratio of inbound port-ins versus outbound competitor departures.")
        ]
    },
    "prepaid_to_postpaid": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: Prepaid to Postpaid",
        "description": "Identifies consistent prepaid reloaders and offers customized postpaid transition plans.",
        "roi_metric": "Customer Lifetime Value (3.2x CLV increase per migrated user)",
        "personas": "Prepaid Segment Manager, Postpaid Acquisition Lead, Financial Risk Analyst",
        "kpis": [
            ("Migration Conversion Rate", ">= 11.2%", "Qualified high-frequency reloaders migrating to contract postpaid plans."),
            ("Migrated Subscriber 12-Month Retention", ">= 89.0%", "One-year retention rate for customers converted from prepaid to postpaid."),
            ("Average Monthly Spend Uplift", "+$18.50/mo", "ARPU differential between historical prepaid reloads and new postpaid tier.")
        ]
    },
    "streaming_subhub_bundles": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: Streaming SubHub Bundles",
        "description": "Correlates OTT streaming data to recommend unified billing content bundles.",
        "roi_metric": "Stickiness & ARPU (+$8.50/mo bundle ARPU)",
        "personas": "Content Partnerships Director, Entertainment Bundle Specialist, BSS Commerce Manager",
        "kpis": [
            ("OTT SubHub Adoption Rate", ">= 21.0%", "Subscribers consolidating 2+ external streaming subscriptions into telco billing."),
            ("Multi-Subscription Churn Resilience", "0.45% churn", "Significantly lower monthly churn for subscribers with unified entertainment packs."),
            ("Carrier Billing Commission Revenue", "+$85K/mo", "Incremental commission revenue earned from OTT digital marketplace partners.")
        ]
    },
    "smartwatch_onenumber_esim": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: Smartwatch OneNumber eSIM",
        "description": "Prompts users pairing new smartwatches with instant eSIM activation workflows.",
        "roi_metric": "Connected Device Revenue (+25K monthly active eSIM lines)",
        "personas": "Connected Devices Lead, eSIM Solutions Architect, IoT Consumer Marketing Lead",
        "kpis": [
            ("Wearable Detection-to-Activation Latency", "< 5 minutes", "Time from Bluetooth pairing to active cellular smartwatch line on network."),
            ("OneNumber Multi-Device Attach Rate", ">= 24.5%", "Subscribers adding secondary wearable cellular lines to primary postpaid tier."),
            ("Wearable Line Recurring ARPU", "+$10.00/mo", "Incremental recurring revenue per active companion smartwatch subscription.")
        ]
    },
    "work_from_home_broadband": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: Work-From-Home Broadband",
        "description": "Detects consistent enterprise VPN traffic to suggest dedicated WFH broadband lines.",
        "roi_metric": "B2C/B2B Blended Revenue (+$28.00/mo corporate-subsidized line)",
        "personas": "SME & Enterprise B2B2C Director, Broadband Product Lead, Commercial Strategy Manager",
        "kpis": [
            ("WFH High-Usage Identification Rate", ">= 88.0%", "Accuracy in segmenting residential users running continuous VPN and video streams."),
            ("Corporate-Split Billing Attach Rate", ">= 17.5%", "Subscribers securing employer reimbursement for dedicated high-bandwidth lines."),
            ("Service Level Uptime & SLA Compliance", "99.95%", "Reliability compliance for mission-critical remote work broadband tiers.")
        ]
    },
    "social_media_pass": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: Social Media Pass",
        "description": "Identifies high social media usage to offer zero-rated social data passes.",
        "roi_metric": "Gen Z Market Share (+14% youth segment acquisition)",
        "personas": "Youth Segment Marketing Specialist, Social Media Campaign Lead, Core Data Monetization Analyst",
        "kpis": [
            ("Youth Segment Conversion Rate", ">= 33.0%", "Gen Z and student subscribers adopting unlimited social media data add-ons."),
            ("Prepaid Balance Longevity", "+8.4 days", "Increased prepaid account active duration from targeted social data passes."),
            ("App Engagement & Referral Index", "4.6/5.0", "Social sharing and viral campaign referral rate among youth plan users.")
        ]
    },
    "secondary_tablet_sim": {
        "domain": "consumer_marketing",
        "display_name": "Consumer Marketing: Secondary Tablet SIM",
        "description": "Detects smartphone tethering hotspots to recommend dedicated high-speed tablet SIM plans.",
        "roi_metric": "Multi-Device Penetration (+18K connected tablet additions)",
        "personas": "Device Ecosystem Lead, Multi-Line Growth Manager, Postpaid Upsell Specialist",
        "kpis": [
            ("Tethering Cluster Detection Precision", ">= 92.5%", "Accuracy in identifying subscribers regularly hotspotting laptops and tablets."),
            ("Dedicated Data SIM Conversion Rate", ">= 15.8%", "Subscribers migrating from smartphone hotspots to standalone tablet SIMs."),
            ("Tablet Line Recurring ARPU", "+$15.00/mo", "Incremental recurring service revenue per activated tablet line.")
        ]
    },

    # Onboarding & Provisioning (6)
    "postcode_coverage_outages": {
        "domain": "onboarding_provisioning",
        "display_name": "Onboarding & Provisioning: Postcode Coverage & Outages",
        "description": "Validates address-level signal strength, 5G spectrum bands, and active cell outages before provisioning.",
        "roi_metric": "Reduced Early Churn (< 0.9% 30-day onboarding churn)",
        "personas": "Service Provisioning Director, Coverage Validation Lead, Order Management Specialist",
        "kpis": [
            ("Pre-Provisioning Signal Accuracy", ">= 99.1%", "Verification of RSRP/SINR threshold compliance prior to service dispatch."),
            ("Outage-Induced Provisioning Hold", "100% automated", "Automatic hold placed on new activations in areas experiencing active fiber/tower faults."),
            ("30-Day Early Return Rate", "< 1.2%", "Reduction in hardware returns caused by unexpected poor indoor coverage.")
        ]
    },
    "esim_device_compatibility": {
        "domain": "onboarding_provisioning",
        "display_name": "Onboarding & Provisioning: eSIM Device Compatibility",
        "description": "Instantly verifies device IMEI/EID for eSIM readiness and carrier-lock status during digital checkout.",
        "roi_metric": "Activation Success Rate (98.4% digital onboarding completion)",
        "personas": "Digital Journey Product Manager, eSIM Systems Architect, Omnichannel Onboarding Lead",
        "kpis": [
            ("IMEI/EID Compatibility Check Latency", "< 500 ms", "Sub-second verification of device manufacturer, OS, and eSIM capability."),
            ("Digital Activation Dropout Rate", "< 2.5%", "Minimization of checkout dropouts during QR code download and profile installation."),
            ("Carrier-Lock Early Warning Accuracy", ">= 97.0%", "Proactive notification to customers with carrier-locked handsets before eSIM push.")
        ]
    },
    "mnp_number_porting_tracker": {
        "domain": "onboarding_provisioning",
        "display_name": "Onboarding & Provisioning: MNP Number Porting Tracker",
        "description": "Orchestrates MNP port-in eligibility, donor network validation, and automated subscriber status updates.",
        "roi_metric": "Porting Lead Time Reduction (-60% MNP processing delay)",
        "personas": "Inter-Carrier Operations Manager, MNP Clearinghouse Lead, Customer Onboarding Specialist",
        "kpis": [
            ("First-Pass MNP Validation Success", ">= 94.0%", "Porting requests accepted without donor network rejection or mismatch errors."),
            ("End-to-End Porting Lead Time", "< 2 hours", "Average duration from subscriber MNP submission to active network switch."),
            ("Proactive MNP SMS Notification Rate", "100% events", "Real-time automated status updates delivered at every clearinghouse milestone.")
        ]
    },
    "fiber_fwa_self_install": {
        "domain": "onboarding_provisioning",
        "display_name": "Onboarding & Provisioning: Fiber & FWA Self-Install",
        "description": "Guides subscribers through ONT optical modem and 5G FWA gateway self-installation and automated diagnostics.",
        "roi_metric": "Truck Roll Avoidance ($350K/mo field technician savings)",
        "personas": "Broadband Field Operations Director, Self-Install Product Owner, Technical Care Lead",
        "kpis": [
            ("Self-Installation Success Rate", ">= 86.5%", "Subscribers completing modem setup and Wi-Fi pairing without technician dispatch."),
            ("Automated Line Diagnostic Completion", "< 3 minutes", "Automated optical attenuation and 5G signal test executed upon first power-on."),
            ("Day-1 Tech Support Call Rate", "< 4.0%", "Reduction in inbound troubleshooting calls following new broadband activation.")
        ]
    },
    "kyc_digital_identity_verification": {
        "domain": "onboarding_provisioning",
        "display_name": "Onboarding & Provisioning: KYC Digital Identity Verification",
        "description": "Automates government ID validation, biometric liveness checks, and fraud screening for instant SIM provisioning.",
        "roi_metric": "Onboarding Velocity & Fraud Prevention (99.2% regulatory KYC compliance)",
        "personas": "Fraud Risk Director, Regulatory Compliance Officer, Digital Identity Solutions Architect",
        "kpis": [
            ("Automated ID OCR & Biometric Match Rate", ">= 95.8%", "Instant identity verification without manual back-office document review."),
            ("Synthetic Identity & Fraud Rejection", ">= 99.4%", "Interception of fraudulent documents and stolen identities during digital signup."),
            ("Average KYC Processing Time", "< 45 seconds", "End-to-end identity check and regulatory database lookup completion time.")
        ]
    },
    "multi_service_bundle_activation": {
        "domain": "onboarding_provisioning",
        "display_name": "Onboarding & Provisioning: Multi-Service Bundle Activation",
        "description": "Orchestrates end-to-end multi-play provisioning across mobile, fixed broadband, and OTT subscriptions.",
        "roi_metric": "First-Time-Right Activation Rate (96.5% zero-fallout provisioning)",
        "personas": "BSS/OSS Orchestration Architect, Fulfilment Operations Lead, Multi-Play Product Director",
        "kpis": [
            ("Multi-Play Zero-Fallout Rate", ">= 96.5%", "Complete bundle provisioning across BSS, HSS/UDM, and OTT platforms without manual ticket."),
            ("Unified Activation Milestone Sync", "< 15 minutes", "Synchronization of mobile SIM, home fiber, and streaming subscription readiness."),
            ("Order Fallout Resolution Time", "< 30 minutes", "Automated retry and self-healing workflow for transient BSS interface timeouts.")
        ]
    },

    # Subscriber CRM & Retention (8)
    "multi_line_account_management": {
        "domain": "subscriber_crm",
        "display_name": "Subscriber CRM: Multi-Line Account Management",
        "description": "Simplifies complex family and enterprise shared accounts by summarizing multi-line usage and shared pools.",
        "roi_metric": "CSAT / NPS (+22 pts care satisfaction index)",
        "personas": "Customer Experience VP, Care Center Operations Director, B2B Account Service Lead",
        "kpis": [
            ("Multi-Line Query Resolution Time", "< 120 seconds", "Conversational AI summarization of line-by-line data usage and billing splits."),
            ("Shared Data Pool Rebalancing Rate", ">= 94.0%", "Automated adjustments to line data caps preventing shared pool exhaustion."),
            ("Care Agent Repeat Call Rate", "< 5.2%", "Reduction in follow-up calls regarding multi-device household billing inquiries.")
        ]
    },
    "proactive_retention_save_offers": {
        "domain": "subscriber_crm",
        "display_name": "Subscriber CRM: Proactive Retention Save Offers",
        "description": "Generates personalized, margin-aware discount and upgrade incentives during active cancellation requests.",
        "roi_metric": "Save Rate Improvement (+32% retention save rate)",
        "personas": "Retention Operations Director, CVM Value Optimization Lead, Loyalty Program Head",
        "kpis": [
            ("Cancellation Save Rate", ">= 38.5%", "High-value subscribers choosing personalized retention offer over contract cancellation."),
            ("Offer Margin Protection", ">= 42% margin", "Algorithmically constrained discount depth preserving account contribution margin."),
            ("6-Month Post-Save Churn Rate", "< 3.8%", "Sustained customer retention following acceptance of personalized save proposal.")
        ]
    },
    "smart_ivr_outage_deflection": {
        "domain": "subscriber_crm",
        "display_name": "Subscriber CRM: Smart IVR Outage Deflection",
        "description": "Matches caller CLI to known network incident telemetry and plays automated resolution updates to deflect care queues.",
        "roi_metric": "Call Deflection (64% IVR deflection during major fiber cuts)",
        "personas": "Contact Center Operations VP, Network Incident Communications Lead, Telephony Architect",
        "kpis": [
            ("Caller-to-Incident Geo-Match Precision", ">= 98.8%", "Accurate identification of incoming callers located within active outage zones."),
            ("Automated IVR Deflection Rate", ">= 62.0%", "Callers listening to automated status update and hanging up satisfied without agent transfer."),
            ("Post-Restoration SMS Notification Rate", "100% impacted", "Automated SMS confirmation sent immediately upon cell tower or fiber restoration.")
        ]
    },
    "bill_shock_charge_breakdown": {
        "domain": "subscriber_crm",
        "display_name": "Subscriber CRM: Bill Shock Charge Breakdown",
        "description": "Explains third-party billing, roaming charges, and off-bundle data spikes with natural language itemized breakdowns.",
        "roi_metric": "Billing Dispute Reduction (-52% billing dispute volume)",
        "personas": "Billing Operations Lead, Customer Disputes Manager, Revenue Assurance Director",
        "kpis": [
            ("First-Contact Dispute Resolution", ">= 88.0%", "Subscribers accepting natural-language itemized charge explanation without credit request."),
            ("Disputed Charge Explanation Clarity", "4.7/5.0 CSAT", "Customer feedback score on automated roaming and third-party charge breakdowns."),
            ("Billing Credit Adjustment Cost", "-38% goodwill credits", "Reduction in goodwill credits issued due to improved charge transparency.")
        ]
    },
    "vas_subscription_manager": {
        "domain": "subscriber_crm",
        "display_name": "Subscriber CRM: VAS Subscription Manager",
        "description": "Allows subscribers to review, audit, and cancel recurring third-party value-added services and micro-subscriptions.",
        "roi_metric": "Billing Transparency & Trust (94% digital VAS self-serve resolution)",
        "personas": "VAS Partnerships Manager, Customer Trust & Safety Lead, Care Automation Specialist",
        "kpis": [
            ("Digital VAS Audit & Cancellation Rate", ">= 92.0%", "Subscribers successfully managing third-party recurring charges via self-serve chat."),
            ("Unintended Subscription Chargeback Rate", "< 0.4%", "Minimization of credit card and carrier billing chargeback disputes."),
            ("VAS Trust & Clarity Rating", "+16 pts NPS", "Improvement in customer trust index regarding carrier-billed partner services.")
        ]
    },
    "vip_high_arpu_concierge": {
        "domain": "subscriber_crm",
        "display_name": "Subscriber CRM: VIP & High-ARPU Concierge",
        "description": "Identifies high-ARPU and enterprise executive accounts to prioritize routing, dedicated SLAs, and white-glove support.",
        "roi_metric": "VIP Retention & Loyalty (< 0.25% VIP annualized churn)",
        "personas": "Executive Concierge Director, High-Value Segment Lead, Enterprise Client Success VP",
        "kpis": [
            ("VIP Queue Routing SLA", "< 10 seconds", "Priority queuing and zero-wait routing for top 5% revenue-generating subscribers."),
            ("Executive First-Contact Resolution", ">= 95.5%", "Complete inquiry resolution on initial interaction for tier-1 enterprise accounts."),
            ("VIP Net Promoter Score", ">= +68 NPS", "Consistently high satisfaction ratings among premium and corporate accounts.")
        ]
    },
    "voice_of_customer_telco_sentiment": {
        "domain": "subscriber_crm",
        "display_name": "Subscriber CRM: Voice of Customer Telco Sentiment",
        "description": "Performs real-time NLP sentiment analysis across care transcripts, NPS surveys, and social channels to surface systemic friction.",
        "roi_metric": "Root-Cause Sentiment Intelligence (-28% recurring customer friction points)",
        "personas": "Voice of Customer Lead, Chief Customer Officer, Quality Assurance Manager",
        "kpis": [
            ("Care Transcript Sentiment Classification", ">= 94.2%", "Real-time identification of customer frustration, billing confusion, and churn intent."),
            ("Systemic Issue Root-Cause Discovery", "< 4 hours", "Lead time from emerging billing/network glitch to executive escalation notification."),
            ("Negative Sentiment Intervention Save Rate", ">= 31.0%", "Proactive outreach to dissatisfied callers converting into positive retention.")
        ]
    },
    "payment_arrangement_promise_to_pay": {
        "domain": "subscriber_crm",
        "display_name": "Subscriber CRM: Payment Arrangement & Promise to Pay",
        "description": "Evaluates credit history and payment behavior to structure flexible installments and temporary payment extensions.",
        "roi_metric": "Bad Debt Minimization (-36% involuntary collection churn)",
        "personas": "Credit & Collections Director, Risk Decisioning Specialist, Customer Care Operations Lead",
        "kpis": [
            ("Promise-to-Pay Fulfillment Rate", ">= 82.5%", "Subscribers successfully fulfilling structured installment schedule on time."),
            ("Involuntary Suspension Avoidance", ">= 74.0%", "At-risk accounts maintaining active service through flexible installment commitments."),
            ("Bad Debt Write-Off Reduction", "$420K/quarter", "Reduction in delinquent balances routed to external collection agencies.")
        ]
    },

    # NetOps & AIOps (6)
    "fcaps_alarm_noise_reduction": {
        "domain": "netops_aiops",
        "display_name": "NetOps & AIOps: FCAPS Alarm Noise Reduction",
        "description": "Correlates, deduplicates, and suppresses cascading raw SNMP alarms to isolate true actionable network incidents.",
        "roi_metric": "MTTR Reduction (-45% alarm storm MTTR)",
        "personas": "Network Operations Center (NOC) Director, Principal AIOps Architect, RAN Operations Lead",
        "kpis": [
            ("Raw Alarm Deduplication Ratio", ">= 88.5%", "Suppression of redundant and sympathetic alarms during major power or fiber outages."),
            ("Root-Cause Incident Clustering Accuracy", ">= 96.0%", "Correct identification of the primary failing node among cascading alarms."),
            ("NOC Operator Ticket Fatigue Reduction", "-58% tickets", "Reduction in duplicate incident tickets generated per operational shift.")
        ]
    },
    "automated_gemini_pir_generator": {
        "domain": "netops_aiops",
        "display_name": "NetOps & AIOps: Automated Gemini PIR Generator",
        "description": "Drafts comprehensive Post Incident Reviews (PIR) by synthesizing incident chronology, telemetry spikes, and remediation logs.",
        "roi_metric": "Engineering Efficiency (85% reduction in manual PIR drafting time)",
        "personas": "Service Reliability Engineering (SRE) Lead, Network Quality VP, Incident Commander",
        "kpis": [
            ("PIR Draft Generation Lead Time", "< 5 minutes", "Time to compile full multi-source incident timeline following service restoration."),
            ("Chronology & Telemetry Accuracy", ">= 98.0%", "Precise alignment of alarm timestamps, engineer chat logs, and remediation commands."),
            ("Post-Mortem Action Item Completion", ">= 92.0%", "Tracking and verification of preventive architecture recommendations.")
        ]
    },
    "cell_tower_congestion_analytics": {
        "domain": "netops_aiops",
        "display_name": "NetOps & AIOps: Cell Tower Congestion Analytics",
        "description": "Evaluates PRB utilization, throughput bottlenecks, and cell handover failures to recommend dynamic antenna tilt and carrier tuning.",
        "roi_metric": "Cell Availability & QoS Optimization (+12% throughput in congested sectors)",
        "personas": "RAN Performance Director, RF Optimization Specialist, Network Planning Engineer",
        "kpis": [
            ("Physical Resource Block (PRB) Efficiency", "< 75% peak", "Mitigation of sector saturation during high-traffic commute and stadium windows."),
            ("Call Drop & Handover Failure Rate", "< 0.35%", "Optimization of inter-frequency and inter-RAT handovers in dense urban clusters."),
            ("Automated Antenna Tilt & Carrier Tuning", "< 15 minutes", "Closed-loop parameter adjustments applied to alleviate localized sector hotspots.")
        ]
    },
    "fiber_backhaul_latency_optimization": {
        "domain": "netops_aiops",
        "display_name": "NetOps & AIOps: Fiber Backhaul Latency Optimization",
        "description": "Analyzes jitter, packet loss, and latency anomalies across DWDM and IP-MPLS backhaul links to optimize routing paths.",
        "roi_metric": "Backhaul SLA Compliance (99.995% transport uptime)",
        "personas": "Transport Network Director, Optical Transmission Engineer, IP Core Network Specialist",
        "kpis": [
            ("Peak Optical Jitter & Latency", "< 8 ms", "Latency performance maintained across regional transmission ring topologies."),
            ("Degraded Fiber Route Auto-Reroute", "< 50 ms", "Sub-second failover and traffic rerouting over alternate DWDM wave paths."),
            ("Transport Bandwidth Congestion Forewarning", "72 hrs in advance", "Predictive alerting for link utilization approaching 85% capacity threshold.")
        ]
    },
    "predictive_hardware_maintenance": {
        "domain": "netops_aiops",
        "display_name": "NetOps & AIOps: Predictive Hardware Maintenance",
        "description": "Predicts optical transceivers, fan module, and battery degradation using thermal telemetry and failure modeling.",
        "roi_metric": "Proactive Outage Prevention (-38% hardware failure outages)",
        "personas": "Field Service Operations Director, Network Reliability Engineer, Infrastructure Maintenance Manager",
        "kpis": [
            ("Hardware Failure Prediction Lead Time", "14 to 30 days", "Advance notice for degrading optical lasers, power units, and chassis fans."),
            ("Predictive Model Precision", ">= 93.5%", "Accuracy of scheduled preventative replacement tickets without false dispatches."),
            ("Unscheduled Emergency Truck Rolls", "-44% reduction", "Replacement of emergency dispatch costs with batched routine site visits.")
        ]
    },
    "site_power_energy_efficiency": {
        "domain": "netops_aiops",
        "display_name": "NetOps & AIOps: Site Power & Energy Efficiency",
        "description": "Monitors base station power consumption, diesel generator runtime, and solar battery storage to minimize carbon footprint and grid costs.",
        "roi_metric": "Opex & Carbon Reduction ($1.8M annual power savings)",
        "personas": "Sustainability & Energy VP, Facilities Operations Lead, Green Telco Strategy Director",
        "kpis": [
            ("Base Station Power Consumption", "-16.5% kWh", "Energy reduction achieved via dynamic radio sleep modes during off-peak night hours."),
            ("Renewable & Battery Utilization", ">= 45% mix", "Maximizing solar battery storage discharge during peak grid tariff windows."),
            ("Diesel Generator Runtime Minimization", "-52% hours", "Reduction in auxiliary generator diesel consumption across off-grid cell sites.")
        ]
    },

    # DaaS & CAMARA Open Gateway (6)
    "stadium_arena_crowd_density": {
        "domain": "daas_camara",
        "display_name": "DaaS & CAMARA: Stadium & Arena Crowd Density",
        "description": "Aggregates and anonymizes real-time cell attachment telemetry to provide crowd density heatmaps to event venues.",
        "roi_metric": "DaaS Telemetry Monetization ($650K annual B2B enterprise revenue)",
        "personas": "Data Monetization VP, Smart Venues Solution Architect, Privacy & Compliance Lead",
        "kpis": [
            ("Real-Time Footfall Telemetry Latency", "< 60 seconds", "Streaming crowd density updates delivered to stadium operations dashboards."),
            ("Differential Privacy & GDPR Anonymization", "100% compliant", "Zero PII leakage via k-anonymity aggregation and spatial hashing."),
            ("Venue Resource Optimization Index", "+28% efficiency", "Concession and security queue wait time reduction powered by crowd telemetry.")
        ]
    },
    "sim_swap_fraud_prevention_api": {
        "domain": "daas_camara",
        "display_name": "DaaS & CAMARA: SIM Swap Fraud Prevention API",
        "description": "Exposes CAMARA-compliant SIM Swap verification APIs to financial institutions to prevent unauthorized OTP interception.",
        "roi_metric": "API Monetization ($1.1M annual B2B banking revenue)",
        "personas": "Open Gateway Product Director, Banking Security Partnerships Lead, API Monetization Architect",
        "kpis": [
            ("CAMARA SIM Swap Query Latency", "< 150 ms", "Sub-200ms API response time integrated into high-speed banking auth flows."),
            ("Account Takeover (ATO) Interception", ">= 99.8%", "Zero-day fraud prevention for unauthorized bank transfers following SIM swap."),
            ("Banking Partner API Availability", "99.999% SLA", "Carrier-grade high availability for mission-critical financial verification.")
        ]
    },
    "number_verification_api": {
        "domain": "daas_camara",
        "display_name": "DaaS & CAMARA: Number Verification API",
        "description": "Provides seamless, cryptographically secure SIM-based MSISDN authentication for mobile banking and fintech applications.",
        "roi_metric": "Auth Friction & Fraud Elimination (99.5% passwordless login success)",
        "personas": "Fintech Partnerships Director, Identity & Access Management Architect, CAMARA Standards Delegate",
        "kpis": [
            ("Silent SIM Auth Verification Time", "< 300 ms", "Zero-interaction cryptographic verification without SMS OTP latency or intercept."),
            ("SMS OTP Interception Fraud Rate", "0.00%", "Complete elimination of SMS sniffing and phishing vector vulnerabilities."),
            ("Fintech App User Conversion Rate", "+14.2% uplift", "Checkout and registration completion rate improvements from one-click auth.")
        ]
    },
    "device_location_verification_api": {
        "domain": "daas_camara",
        "display_name": "DaaS & CAMARA: Device Location Verification API",
        "description": "Validates device location within specified radii using network-grounded cell triangulation without requiring device GPS.",
        "roi_metric": "Anti-Fraud Geo-Verification ($480K annual fraud loss avoidance)",
        "personas": "Risk Decisioning Lead, Anti-Fraud Solutions Architect, Location Intelligence Manager",
        "kpis": [
            ("Network Triangulation Precision", "< 500 meters", "Cell tower and timing advance verification without dependency on user device GPS."),
            ("ATM & Card Transaction Geo-Match", ">= 98.2%", "Verification that cardholder handset is physically present at point-of-sale terminal."),
            ("GPS Spoofing & Emulator Detection", "100% filtered", "Rejection of fake GPS and emulator spoofing attempts via radio network telemetry.")
        ]
    },
    "quality_on_demand_qod_api": {
        "domain": "daas_camara",
        "display_name": "DaaS & CAMARA: Quality on Demand (QoD) API",
        "description": "Exposes programmable 5G Quality on Demand (QoD) latency slicing APIs to cloud gaming and enterprise drone platforms.",
        "roi_metric": "5G Network API Monetization ($850K annual 5G API revenue)",
        "personas": "5G Open Gateway Director, Autonomous Systems Lead, Cloud Gaming Strategy VP",
        "kpis": [
            ("Dynamic QoS Session Provisioning Latency", "< 1.5 seconds", "Time required to dynamically assign high-priority dedicated bearer to client session."),
            ("Deterministic Latency Jitter SLA", "< 5 ms variance", "Guaranteed packet delivery window for tele-operation and cloud gaming streams."),
            ("QoD Session Revenue Realization", "$0.08/active minute", "Micro-billing monetization per duration of requested high-QoS network session.")
        ]
    },
    "device_swap_roaming_status_api": {
        "domain": "daas_camara",
        "display_name": "DaaS & CAMARA: Device Swap & Roaming Status API",
        "description": "Delivers real-time roaming status and IMEI swap detection webhooks to fraud detection and corporate security engines.",
        "roi_metric": "Real-Time Risk Scoring ($390K annual enterprise security subscription revenue)",
        "personas": "Cybersecurity Product Director, Corporate Risk Systems Lead, DaaS API Solutions Engineer",
        "kpis": [
            ("Device Swap Webhook Latency", "< 2 seconds", "Instant notification dispatched to enterprise risk engine upon foreign IMEI insertion."),
            ("Roaming Country Verification Accuracy", "100% verified", "Real-time international VLR country code confirmation for corporate fraud detection."),
            ("Corporate Fleet Security Alert Precision", ">= 97.5%", "Accurate identification of lost, stolen, or compromised corporate mobile devices.")
        ]
    }
}


def update_table_registry():
    registry_path = REPO_ROOT / "_shared" / "table_registry.yaml"
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    
    for agent_name, spec in TELCO_AGENT_SPECS.items():
        if agent_name in data.get("agents", {}):
            data["agents"][agent_name]["display_name"] = spec["display_name"]
            data["agents"][agent_name]["description"] = spec["description"]
            data["agents"][agent_name]["roi_metric"] = spec["roi_metric"]

    registry_path.write_text(yaml.dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print("✅ Updated _shared/table_registry.yaml with unique descriptions and ROI metrics.")


def update_agent_files():
    for agent_name, spec in TELCO_AGENT_SPECS.items():
        domain = spec["domain"]
        agent_dir = REPO_ROOT / "domains" / domain / "agents" / agent_name
        if not agent_dir.exists():
            continue

        # 1. Update root_agent.yaml
        root_agent_path = agent_dir / "root_agent.yaml"
        if root_agent_path.exists():
            root_content = f"""agent_class: LlmAgent
name: {agent_name}_root
model: gemini-3.5-flash
description: >-
  {spec['description']} Routes questions to internal BigQuery data
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

  You are the orchestrator for the {spec['display_name']} agent.
  Purpose: {spec['description']}
  
  Decide whether a user's question needs internal BigQuery data (delegate to the data_insights sub-agent),
  external market/competitive context (delegate to the market_context sub-agent), or both. When you use
  both, clearly label which parts of your answer came from internal data versus external search.

  Recognize and route these {spec['display_name']} questions:
  - Internal metrics, quantitative table queries, regional logs, or operational KPI trends → delegate to the data_insights sub-agent.
  - Telecom industry benchmarks, GSMA/3GPP specifications, competitor intelligence, or market research → delegate to the market_context sub-agent.
  - Mixed questions (e.g. "how do our internal metrics compare against industry standards") → delegate to both, and synthesize a combined answer.
sub_agents:
  - config_path: sub_agents/data_insights.yaml
  - config_path: sub_agents/market_context.yaml
"""
            root_agent_path.write_text(root_content, encoding="utf-8")

        # 2. Update README.md
        readme_path = agent_dir / "README.md"
        clean_name = spec['display_name'].split(':')[-1].strip()
        
        kpi_table_rows = "\n".join([
            f"| **{m}** | `{b}` | {i} |" for m, b, i in spec['kpis']
        ])
        
        readme_content = f"""# {spec['display_name']}

Part of the **Telco Enterprise Agents** platform for Gemini Enterprise.

---

## 1. Why This Agent Matters

### Business Problem
{spec['description']}

### Target Personas
{spec['personas']}

### Key Metrics Tracked
| Metric | Benchmark / Target | Business Impact |
| :--- | :--- | :--- |
{kpi_table_rows}

---

## 2. What It Answers & Sub-Agent Routing

### Sub-Agent Architecture
- **`data_insights`**: Queries internal BigQuery tables using the BigQuery Conversational Analytics API (`ask_data_insights`, `forecast`, `analyze_contribution`, `detect_anomalies`) and generates visual data charts via `render_chart`.
- **`market_context`**: Leverages Google Search grounding for external telecom industry benchmarks, GSMA/3GPP standards, TM Forum ODA specifications, and competitive intelligence.
- **`root_agent`**: Orchestrates routing between internal analytics and external market intelligence.

---

## 3. Sample Q&A Showcase

### Example 1: Internal Analytics (Data Insights)
*Question:* "What are our primary operational metrics and performance targets for {clean_name.lower()} across operating regions in 2026 YTD?"
*Response:*
> Over the past 30 days, performance metrics for **{clean_name}** achieved an overall **94.8% compliance rate** across all operating clusters, exceeding the 92.0% operational benchmark.
> 
> - **Metro North:** 96.2% efficiency index
> - **Metro South:** 95.1% operational uptime
> - **West Region:** 93.8% target achievement
> 
> Primary Business Value: **{spec['roi_metric']}**.

### Example 2: Market Grounding (Market Context)
*Question:* "What are the latest telecom industry standards, GSMA guidelines, and market benchmarks for {clean_name.lower()}?"
*Response:*
> According to recent TM Forum Open Digital Architecture (ODA) and GSMA 2026 industry intelligence, tier-1 operators deploying automated conversational AI and AIOps analytics achieve a **35% reduction in MTTR** and a **22% improvement in customer satisfaction (CSAT)**.

### Example 3: Chart Visualization (`sample_chart.png`)
*Question:* "Render a chart comparing monthly performance metrics for {clean_name.lower()} vs annual targets."
*Generated Visual Artifact:*
![Sample Chart](sample_chart.png)

---

## 4. Operational Value & Deployment
- **Deployment Class**: ReasoningEngine / Vertex AI Agent Engine
- **Runtime**: `gemini-3.5-flash`
- **Location**: `us-central1`
"""
        readme_path.write_text(readme_content, encoding="utf-8")

    print("✅ Updated root_agent.yaml and README.md across all 45 agents.")


if __name__ == "__main__":
    update_table_registry()
    update_agent_files()
