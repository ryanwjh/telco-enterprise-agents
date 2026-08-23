"""Callbacks that inject runtime values into session state so otherwise-static YAML
`instruction:` strings (Agent Config only accepts a plain string, no dotted-path/callable) can
reference them via ADK's `{state_key}` placeholder substitution.

`set_current_date` is registered on EVERY agent in this logical agent's tree (root and every
sub-agent), not just the root. The original design registered it on the
root agent only, reasoning that a single before_agent_callback there would
run before any transfer_to_agent into a sub-agent, and all agents in one
turn share the same Session/session.state. That assumption broke once
deployed and invoked live through Gemini Enterprise: a sub-agent
(data_insights) failed with "context variable temp:current_date not found"
even though the root agent's own turns succeeded -- Gemini Enterprise's
invocation path can apparently reach a sub-agent without the root agent's
before_agent_callback having run first (root cause not fully isolated;
the fix that matters is not depending on invocation order at all). Since
this callback is idempotent and cheap (a single date.today() call), the
robust fix is for every agent to set its own copy rather than relying on
any other agent having run first. See
docs/superpowers/specs/2026-07-25-retail-merchandising-adk-agents-design.md
section 5b (local-only doc, gitignored, not on a fresh clone).

`set_bigquery_project` is registered on `data_insights.yaml` only -- it's the only agent whose
instruction references fully-qualified BigQuery table names. Reading BIGQUERY_PROJECT_ID directly
here (rather than depending on another agent having set it first) avoids repeating the exact
invocation-order bug above. Injecting the project id dynamically, instead of hardcoding it as a
literal string in the instruction, treats it the same as other deployment-specific identifiers
(service account email, Agent Engine resource name) that agents built from this template
deliberately don't commit -- see this repo's CLAUDE.md's "IAM is the real access boundary, not
tool config" note.
"""
from __future__ import annotations

import datetime
import os
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.genai import types

CURRENT_DATE_STATE_KEY = "temp:current_date"
BQ_PROJECT_STATE_KEY = "temp:bq_project_id"


def set_current_date(callback_context: CallbackContext) -> Optional[types.Content]:
  """Writes today's date into session state as an ISO-8601 string.

  Uses the `temp:` state-key prefix (google.adk.sessions.state.State.TEMP_PREFIX)
  because this value is invocation-scoped and must never be persisted or
  reused across turns/sessions -- it is recomputed on every root-agent
  invocation (i.e. every user turn).
  """
  callback_context.state[CURRENT_DATE_STATE_KEY] = datetime.date.today().isoformat()
  return None


def set_bigquery_project(callback_context: CallbackContext) -> Optional[types.Content]:
  """Writes the dev BigQuery project id into session state from BIGQUERY_PROJECT_ID."""
  project_id = (
      os.environ.get("BIGQUERY_PROJECT_ID")
      or os.environ.get("GOOGLE_CLOUD_PROJECT")
      or "your-dev-project-id"
  )
  callback_context.state[BQ_PROJECT_STATE_KEY] = project_id
  return None
