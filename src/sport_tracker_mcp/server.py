from fastmcp import FastMCP

from sport_tracker_mcp.tools import (
    get_recent_activities_summary,
    get_recent_workouts,
    get_social_feed,
    get_training_load_and_recovery,
    get_training_summary,
    get_user_stats,
    get_vo2_max_history,
    get_workout_details,
)

mcp = FastMCP(
    name="sport-tracker",
    instructions="Unofficial Sports Tracker MCP Server providing comprehensive fitness tracking, workout analysis, VO2Max trends, training load, and recovery metrics.",
)

# Register all MCP tools
mcp.add_tool(get_recent_workouts)
mcp.add_tool(get_social_feed)
mcp.add_tool(get_workout_details)
mcp.add_tool(get_user_stats)
mcp.add_tool(get_vo2_max_history)
mcp.add_tool(get_training_summary)
mcp.add_tool(get_training_load_and_recovery)
mcp.add_tool(get_recent_activities_summary)


def main() -> None:
    """Run the Sports Tracker FastMCP server using stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
