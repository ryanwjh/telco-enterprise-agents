"""Unit tests for the chart-rendering tool. All BigQuery/matplotlib-adjacent I/O is mocked or
uses matplotlib's non-interactive Agg backend -- no network access, no real credentials, no
display required.
"""
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from tools.chart_generator import CHART_ARTIFACT_FILENAME
from tools.chart_generator import render_chart


def _mock_client_with_rows(rows):
    mock_client = MagicMock()
    mock_client.query.return_value.result.return_value = rows
    return mock_client


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_query", ["DELETE FROM table", "DROP TABLE table", "UPDATE table SET x=1"])
async def test_render_chart_rejects_non_select_queries(bad_query):
    mock_tool_context = MagicMock()
    mock_tool_context.save_artifact = AsyncMock()

    result = await render_chart(bad_query, "Some Chart", mock_tool_context)

    assert result["status"] == "error"
    mock_tool_context.save_artifact.assert_not_called()


@pytest.mark.asyncio
@patch("tools.chart_generator._resolve_bigquery_client")
async def test_render_chart_returns_a_clear_error_instead_of_raising_on_bad_sql(
    mock_resolve_client,
):
    # A malformed/invalid query (e.g. the LLM guessing a wrong column name) must come back as a
    # structured error the LLM can react to and retry from, not an uncaught exception that
    # crashes the whole agent turn -- confirmed via a real deployed-agent smoke test (Assortment
    # Planning) where the LLM guessed a nonexistent column and BigQuery's exception propagated
    # uncaught. Every future agent scaffolded from this template inherits this fix automatically.
    mock_client = MagicMock()
    mock_client.query.return_value.result.side_effect = Exception("Name x not found inside t2")
    mock_resolve_client.return_value = mock_client
    mock_tool_context = MagicMock()
    mock_tool_context.save_artifact = AsyncMock()

    result = await render_chart("SELECT bad_col FROM t", "Title", mock_tool_context)

    assert result["status"] == "error"
    assert "Name x not found inside t2" in result["message"]
    mock_tool_context.save_artifact.assert_not_called()


@pytest.mark.asyncio
@patch("tools.chart_generator._resolve_bigquery_client")
async def test_render_chart_returns_error_on_empty_result(mock_resolve_client):
    mock_resolve_client.return_value = _mock_client_with_rows([])
    mock_tool_context = MagicMock()
    mock_tool_context.save_artifact = AsyncMock()

    result = await render_chart("SELECT a, b FROM t", "Some Chart", mock_tool_context)

    assert result["status"] == "error"
    mock_tool_context.save_artifact.assert_not_called()


@pytest.mark.asyncio
@patch("tools.chart_generator._resolve_bigquery_client")
async def test_render_chart_saves_a_png_artifact_on_success(mock_resolve_client):
    rows = [("Down Parka", 935), ("Rain Jacket", 1050)]
    mock_resolve_client.return_value = _mock_client_with_rows(rows)
    mock_tool_context = MagicMock()
    mock_tool_context.save_artifact = AsyncMock(return_value=1)

    result = await render_chart(
        "SELECT product_name, units_sold FROM t", "Units Sold", mock_tool_context
    )

    assert result == {
        "status": "success",
        "artifact_filename": CHART_ARTIFACT_FILENAME,
        "artifact_version": 1,
        "message": f"Chart created and saved as an artifact named '{CHART_ARTIFACT_FILENAME}'.",
    }
    mock_tool_context.save_artifact.assert_awaited_once()
    _, kwargs = mock_tool_context.save_artifact.call_args
    assert kwargs["filename"] == CHART_ARTIFACT_FILENAME
    assert kwargs["artifact"].inline_data.mime_type == "image/png"
    assert len(kwargs["artifact"].inline_data.data) > 0


@pytest.mark.asyncio
async def test_render_chart_accepts_with_queries():
    # A "WITH ... SELECT" CTE query must not be rejected by the SELECT-only guard.
    mock_tool_context = MagicMock()
    mock_tool_context.save_artifact = AsyncMock()
    with patch("tools.chart_generator._resolve_bigquery_client") as mock_resolve_client:
        mock_resolve_client.return_value = _mock_client_with_rows([("a", 1)])
        result = await render_chart(
            "WITH t AS (SELECT 1) SELECT * FROM t", "Title", mock_tool_context
        )

    assert result["status"] == "success"
