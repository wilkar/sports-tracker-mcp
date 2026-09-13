import pytest

from sport_tracker_mcp.server import mcp


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
