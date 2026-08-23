"""Tool that renders a chart from a BigQuery query result and saves it as an ADK artifact.

ADK's built-in `ask_data_insights` tool can never produce a chart -- ADK itself sends a hardcoded
system instruction to the Conversational Analytics API forbidding charts, with no config override
(see docs/superpowers/specs/2026-07-25-retail-merchandising-adk-agents-design.md section 5d,
local-only doc, gitignored). This tool works around that by querying BigQuery directly and
rendering the chart itself via matplotlib, then saving it through ADK's documented artifact API
(`ToolContext.save_artifact`). Confirmed 2026-07-26 via a real deployed-agent smoke test
(Assortment Planning): the artifact mechanism fires correctly and the resulting image renders in
the real Gemini Enterprise chat UI -- this was genuinely unconfirmed going in, given contradictory
public reports about whether Gemini Enterprise displays ADK artifacts at all.
"""
from __future__ import annotations

import io
import os

import google.auth
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from google.adk.tools.tool_context import ToolContext
from google.cloud import bigquery
from google.genai import types

CHART_ARTIFACT_FILENAME = "chart.png"


def _resolve_bigquery_client() -> bigquery.Client:
  """Resolves a BigQuery client the same way tools/bigquery_ca.py does: ADC locally, the
  attached service account when deployed, scoped for BigQuery data access.
  """
  credentials, _ = google.auth.default(
      scopes=["https://www.googleapis.com/auth/bigquery"]
  )
  project_id = os.environ.get("BIGQUERY_PROJECT_ID")
  return bigquery.Client(project=project_id, credentials=credentials)


async def render_chart(
    sql_query: str, chart_title: str, tool_context: ToolContext
) -> dict:
  """Runs a read-only SQL query against this agent's authorized BigQuery tables and renders
  the result as a bar chart, saved as an image artifact.

  Args:
    sql_query: A SELECT/WITH-only BigQuery Standard SQL query against this agent's authorized
      tables. Must return exactly two columns: a label column first, a numeric value column
      second.
    chart_title: A short, human-readable chart title.
  """
  normalized = sql_query.strip().upper()
  if not (normalized.startswith("SELECT") or normalized.startswith("WITH")):
    return {
        "status": "error",
        "message": "Only SELECT/WITH queries are allowed for chart generation.",
    }

  client = _resolve_bigquery_client()
  try:
    rows = list(client.query(sql_query).result())
  except Exception as exc:  # BigQuery raises many distinct exception types for bad SQL.
    return {
        "status": "error",
        "message": f"Query failed: {exc}. Check column/table names and try again.",
    }
  if not rows:
    return {"status": "error", "message": "Query returned no rows to chart."}

  labels = [str(row[0]) for row in rows]
  values = [row[1] for row in rows]

  fig, ax = plt.subplots()
  ax.bar(labels, values)
  ax.set_title(chart_title)
  fig.autofmt_xdate(rotation=45)

  buf = io.BytesIO()
  fig.savefig(buf, format="png", bbox_inches="tight")
  plt.close(fig)
  buf.seek(0)

  version = await tool_context.save_artifact(
      filename=CHART_ARTIFACT_FILENAME,
      artifact=types.Part.from_bytes(data=buf.read(), mime_type="image/png"),
  )
  return {
      "status": "success",
      "artifact_filename": CHART_ARTIFACT_FILENAME,
      "artifact_version": version,
      "message": f"Chart created and saved as an artifact named '{CHART_ARTIFACT_FILENAME}'.",
  }
