"""Factory for this logical agent's BigQuery Conversational Analytics tool.

See docs/superpowers/specs/2026-07-25-retail-merchandising-adk-agents-design.md
(local-only doc, gitignored, not on a fresh clone) sections 5a and 6 for why this is a Python
factory instead of a YAML tool
config: BigQueryToolset takes a BigQueryCredentialsConfig object as a
constructor argument, which plain YAML cannot express.
"""
from __future__ import annotations

import os

import google.auth
from google.adk.integrations.bigquery import BigQueryCredentialsConfig
from google.adk.integrations.bigquery import BigQueryToolset
from google.adk.integrations.bigquery.config import BigQueryToolConfig
from google.adk.integrations.bigquery.config import WriteMode
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_configs import ToolArgsConfig


def _resolve_credentials_config() -> BigQueryCredentialsConfig:
  """Resolves BigQuery credentials for the current environment.

  Locally (adk run, tests/integration) this resolves to Application Default
  Credentials via `gcloud auth application-default login`. When deployed to
  Agent Engine, `google.auth.default()` instead resolves to the service
  account attached to that deployment. Same code path either way — this is
  intentional, see the design spec's Global Constraints on credential
  resolution.

  Scope must be `cloud-platform`, not the narrower `bigquery` scope: the
  `ask_data_insights` tool calls the Conversational Analytics API
  (`geminidataanalytics.googleapis.com`'s `:chat` endpoint), which requires
  `https://www.googleapis.com/auth/cloud-platform` (confirmed against Google's
  own API reference — discovered 2026-07-26 when a deployed agent failed
  every `ask_data_insights` call with no BigQuery/GDA audit log trail at all,
  meaning the request was rejected for insufficient token scope before it
  ever reached either service's authorization layer). This was invisible in
  local testing because `google.auth.default(scopes=...)` only re-scopes
  service account credentials — the developer's own user ADC used in
  `adk run`/`tests/integration` ignores this parameter entirely, so the bug
  only surfaces once a real service account is attached at deploy time.
  """
  credentials, _ = google.auth.default(
      scopes=["https://www.googleapis.com/auth/cloud-platform"]
  )
  return BigQueryCredentialsConfig(credentials=credentials)


def create_toolset(args: ToolArgsConfig) -> BaseTool:
  """Builds this logical agent's BigQueryToolset from its YAML tool args."""
  config = args.model_dump()
  tool_config = BigQueryToolConfig(
      write_mode=WriteMode(config.get("write_mode", "blocked")),
      application_name=config.get("application_name"),
      job_labels=config.get("job_labels"),
      compute_project_id=os.environ.get("BIGQUERY_PROJECT_ID"),
  )
  return BigQueryToolset(
      tool_filter=config.get("tool_filter"),
      credentials_config=_resolve_credentials_config(),
      bigquery_tool_config=tool_config,
  )
