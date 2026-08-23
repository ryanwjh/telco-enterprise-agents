"""End-to-end integration test: runs this logical agent's root agent against a real
(dev-project) BigQuery dataset via the Conversational Analytics API.

Requires:
  - BIGQUERY_PROJECT_ID env var pointing at a dev GCP project
  - The dev dataset seeded via _shared/scripts/load_agent_data.py (see data/README.md)
  - Application Default Credentials for an account with BigQuery access to that project

Skipped automatically if BIGQUERY_PROJECT_ID is not set (e.g. in CI without GCP access).

Note: this uses `google.adk.agents.config_agent_utils.from_config`, which ADK's own source
marks deprecated in favor of a future reflection-based loader that did not exist at the time
this template was written. It is what ADK's own `adk run`/`adk web` CLI calls internally as of
google-adk>=2.5.0. Revisit this import if a newer google-adk drops it.
"""
import os
from pathlib import Path

import pytest
from google.adk.agents.config_agent_utils import from_config
from google.adk.runners import InMemoryRunner
from google.genai import types

AGENT_DIR = Path(__file__).resolve().parents[2]

requires_bigquery = pytest.mark.skipif(
    not os.environ.get("BIGQUERY_PROJECT_ID"),
    reason="BIGQUERY_PROJECT_ID not set; skipping live BigQuery integration test",
)


@requires_bigquery
async def test_root_agent_answers_a_basic_question():
    agent = from_config(str(AGENT_DIR / "root_agent.yaml"))
    runner = InMemoryRunner(agent=agent, app_name="prepaid_to_postpaid")
    session = await runner.session_service.create_session(
        app_name="prepaid_to_postpaid", user_id="test_user"
    )

    events = [
        event
        async for event in runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=types.Content(
                role="user", parts=[types.Part(text="What can you help me with?")]
            ),
        )
    ]

    final_texts = [
        part.text
        for event in events
        if event.content
        for part in event.content.parts
        if part.text
    ]
    assert any(final_texts), "expected at least one text response from the agent"

    # A response existing at all is the real proof the current-date callback worked: the shared
    # grounding-rules instruction references the strict (non-optional) `{temp:current_date}`
    # form, which raises KeyError during instruction rendering if the before_agent_callback never
    # ran or never set the key -- that would have failed this whole test with an exception, not
    # just an empty response. (Confirmed empirically against a real deployment: querying
    # get_session() after the run does *not* show `temp:current_date` in this google-adk
    # version -- its newer node-based execution engine doesn't appear to commit a content-less
    # before_agent_callback state delta to the durably-fetchable session, even though the value
    # is correctly visible live, within the same turn, to every agent's own instruction
    # rendering. That's an ADK persistence-plumbing detail, not a sign the feature is broken --
    # don't try to assert on get_session() state here.)
    assert not any("{temp:current_date}" in text for text in final_texts), (
        "found a literal, unsubstituted {temp:current_date} placeholder in the agent's response"
    )
