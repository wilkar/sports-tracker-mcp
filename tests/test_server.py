from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.utilities.mime import UI_MIME_TYPE
from mcp.types import EmbeddedResource, TextContent

from sport_tracker_mcp.server import _card, mcp
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


def test_card_returns_app_resource():
    result = _card("test_tool", "<h1>Test Card</h1>", {"status": "ok"})
    assert result.structured_content == {"status": "ok"}
    assert len(result.content) == 1

    mcp_app_res = result.content[0]
    assert isinstance(mcp_app_res, EmbeddedResource)
    assert mcp_app_res.resource.uri == "ui://sport-tracker/test_tool"
    assert mcp_app_res.resource.mime_type == UI_MIME_TYPE
    assert mcp_app_res.resource.text == "<h1>Test Card</h1>"


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
