from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.utilities.mime import UI_MIME_TYPE
from mcp.types import EmbeddedResource, TextContent

from sport_tracker_mcp import ui
from sport_tracker_mcp.server import CARD_DIR, _card, _latest_card, mcp
from tests.fixtures import MOCK_WORKOUTS_PAYLOAD


@pytest.mark.asyncio
async def test_server_metadata():
    assert mcp.name == "sport-tracker"
    assert mcp.instructions is not None
    assert "Unofficial" in mcp.instructions
    assert "Sports Tracker MCP Server" in mcp.instructions


@pytest.mark.asyncio
async def test_server_tools_registered():
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]

    expected_tools = [
        "get_recent_workouts",
        "get_social_feed",
        "get_workout_details",
        "get_user_stats",
        "get_vo2_max_history",
        "get_training_summary",
        "get_training_load_and_recovery",
        "get_recent_activities_summary",
    ]

    assert len(tools) == len(expected_tools)
    for expected in expected_tools:
        assert expected in tool_names

    # Ensure every tool has a descriptive explanation for the LLM
    for t in tools:
        assert t.description is not None
        assert len(t.description) > 10

    # Ensure visual tools have UI metadata, while get_social_feed is data-only
    visual_tools = [t for t in tools if t.name != "get_social_feed"]
    for t in visual_tools:
        assert t.meta is not None
        assert "ui" in t.meta
        assert t.meta["ui"]["resourceUri"] == f"ui://sport-tracker/{t.name}"

    social_tool = next(t for t in tools if t.name == "get_social_feed")
    assert social_tool.meta is None or "ui" not in (social_tool.meta or {})


def test_card_routes_data_to_model_and_markup_to_widget():
    """Three consumers, three channels.

    The model MUST get the data in `content`: hosts that render a widget hand
    the model the content blocks only, so data living solely in
    structured_content leaves it unable to follow up (no workout_key to fetch
    details with, no distances to compare).
    """
    result = _card("test_tool", "<h1>Test Card</h1>", {"status": "ok", "id": "abc123"})
    text = "".join(getattr(b, "text", "") for b in result.content)

    # model: the data itself, never the markup
    assert "abc123" in text
    assert "<h1>Test Card</h1>" not in text
    assert "Interactive card: file://" in text

    # typed copy for hosts that read it
    assert result.structured_content == {"status": "ok", "id": "abc123"}

    # widget: the card rides on _meta, where the shell reads it
    assert result.meta[ui.CARD_META_KEY] == "<h1>Test Card</h1>"

    # browser fallback: same markup on disk
    assert (CARD_DIR / "test_tool.html").read_text() == "<h1>Test Card</h1>"


def test_shell_is_static_and_carries_no_data():
    """The host fetches the shell BEFORE the tool runs, so it must hold no data.

    This is the bug that made cards render as a placeholder: a resource that
    tried to serve the last rendered card had nothing to serve on first call.
    """
    shell = ui.shell("get_recent_workouts")
    assert "ontoolresult" in shell  # waits for the host to push the result
    assert ui.CARD_META_KEY in shell  # reads the card out of the result's _meta
    assert "<tr" not in shell  # no rows: no data is baked in


@pytest.mark.asyncio
async def test_call_get_recent_workouts_with_sport_filter():
    with patch(
        "sport_tracker_mcp.client.SportsTrackerClient.get_workouts",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = MOCK_WORKOUTS_PAYLOAD
        res = await mcp.call_tool(
            "get_recent_workouts", {"limit": 5, "sport": "cycling"}
        )
    assert res.structured_content is not None
    assert "workouts" in res.structured_content
    workouts = res.structured_content["workouts"]
    assert len(workouts) > 0
    assert all(w["sport"] == "cycling" for w in workouts)


@pytest.mark.asyncio
async def test_call_get_recent_workouts_with_limit_25_and_all():
    with patch(
        "sport_tracker_mcp.client.SportsTrackerClient.get_workouts",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = MOCK_WORKOUTS_PAYLOAD
        # limit=25 as integer
        res_25 = await mcp.call_tool("get_recent_workouts", {"limit": 25})
        assert res_25.structured_content is not None
        assert "workouts" in res_25.structured_content

        # limit='all' as string
        res_all = await mcp.call_tool("get_recent_workouts", {"limit": "all"})
        assert res_all.structured_content is not None
        assert "workouts" in res_all.structured_content
