import tempfile
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.apps import AppConfig
from fastmcp.tools import ToolResult
from fastmcp.utilities.mime import UI_MIME_TYPE
from mcp.types import TextContent

# Absolute, not relative: `fastmcp list/dev <file>` loads this module by path,
# outside its package, where a relative import has no parent to resolve against.
from sport_tracker_mcp import tools, ui

mcp = FastMCP(
    name="sport-tracker",
    instructions=(
        "Unofficial Sports Tracker MCP Server providing comprehensive fitness tracking, "
        "workout analysis, VO2Max trends, training load, and recovery metrics."
    ),
)


# Last card rendered per tool, for tests and debugging. The widget gets its
# copy from the tool result's _meta, not from here.
# ponytail: process-global, last-write-wins; fine for one stdio client per process.
_latest_card: dict[str, str] = {}


CARD_DIR = Path(tempfile.gettempdir()) / "sport-tracker-cards"


def _card(tool: str, markup: str, data: Any) -> ToolResult:
    """Structured data for the model; the rendered card for the widget.

    Three consumers, three channels:

    * `structured_content` — the model reasons over this.
    * `_meta["sport-tracker/card"]` — the MCP Apps widget. The host fetches the
      ui:// shell BEFORE the tool runs, so the card cannot live in the resource;
      it rides on the tool result and the shell injects it on arrival.
    * a file on disk — for hosts with no widget support at all, linked from the
      one line of text the model sees.

    The markup never goes in `content`: a host without MCP Apps flattens that
    into the model's context, costing ~8x the structured payload to render
    nothing.
    """
    _latest_card[tool] = markup
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    path = CARD_DIR / f"{tool}.html"
    path.write_text(markup, encoding="utf-8")
    return ToolResult(
        content=[TextContent(type="text", text=f"Interactive card: file://{path}")],
        structured_content=data,
        meta={ui.CARD_META_KEY: markup},
    )


async def get_recent_workouts(
    limit: int | str = 10, imperial: bool = False, sport: str | None = None
) -> ToolResult:
    """Get recent workouts with formatted distance, duration, pace, and HR.

    Args:
        limit: Number of recent workouts to retrieve (default: 10, accepts integers or 'all').
        imperial: If True, return units in imperial (miles, ft) instead of metric.
        sport: Optional sport name to filter by (e.g. 'running', 'cycling', 'walking', 'gym').
    """
    items = await tools.get_recent_workouts(limit=limit, imperial=imperial, sport=sport)
    return _card(
        "get_recent_workouts",
        ui.render_recent_workouts(items, limit=limit, imperial=imperial, sport=sport),
        {"workouts": [i.model_dump() for i in items]},
    )


async def get_workout_details(workout_key: str, imperial: bool = False) -> ToolResult:
    """Get detailed workout metrics including ascent, descent, HR zones, gear, and Suunto extensions."""
    detail = await tools.get_workout_details(workout_key=workout_key, imperial=imperial)
    return _card(
        "get_workout_details",
        ui.render_workout_details(detail, imperial=imperial),
        detail.model_dump(),
    )


async def get_training_load_and_recovery() -> ToolResult:
    """Get current training load, recovery hours, TSS, PTE, EPOC, and recovery status from the latest workout."""
    load = await tools.get_training_load_and_recovery()
    return _card(
        "get_training_load_and_recovery",
        ui.render_training_load_and_recovery(load),
        load.model_dump(),
    )


async def get_training_summary(days: int = 7, imperial: bool = False) -> ToolResult:
    """Get aggregated training volume, distance, time, and calories across sports for the past N days."""
    summary = await tools.get_training_summary(days=days, imperial=imperial)
    return _card(
        "get_training_summary",
        ui.render_training_summary(summary, imperial=imperial),
        summary.model_dump(),
    )


async def get_vo2_max_history(limit: int = 20) -> ToolResult:
    """Get VO2Max and fitness age history extracted from recent workouts."""
    history = await tools.get_vo2_max_history(limit=limit)
    return _card(
        "get_vo2_max_history", ui.render_vo2_max_history(history), history.model_dump()
    )


async def get_user_stats(
    username: str | None = None, imperial: bool = False
) -> ToolResult:
    """Get lifetime totals and per-sport breakdown stats for the logged-in user or specified username."""
    stats = await tools.get_user_stats(username=username, imperial=imperial)
    return _card(
        "get_user_stats",
        ui.render_user_stats(stats, imperial=imperial),
        stats.model_dump(),
    )


async def get_recent_activities_summary(days: int = 14) -> ToolResult:
    """Get a breakdown of activity frequency, total time spent, and last performed dates over the past N days.

    Args:
        days: Number of past days to aggregate activity summary for (default: 14).
    """
    summary = await tools.get_recent_activities_summary(days=days)
    return _card(
        "get_recent_activities_summary",
        ui.render_recent_activities_summary(summary),
        summary.model_dump(),
    )


async def get_social_feed(limit: int = 10, imperial: bool = False) -> ToolResult:
    """Get social feed items from followed athletes or community (data-only).

    Args:
        limit: Maximum number of feed items to retrieve (default: 10).
        imperial: If True, format units in imperial.
    """
    items = await tools.get_social_feed(limit=limit, imperial=imperial)
    return ToolResult(
        content=[
            TextContent(
                type="text",
                text=f"Retrieved {len(items)} social feed items.",
            )
        ],
        structured_content={"items": [i.model_dump() for i in items]},
    )


UI_TOOLS = (
    get_recent_workouts,
    get_workout_details,
    get_user_stats,
    get_vo2_max_history,
    get_training_summary,
    get_training_load_and_recovery,
    get_recent_activities_summary,
)

for _tool in UI_TOOLS:
    _name = _tool.__name__
    _uri = f"ui://sport-tracker/{_name}"
    # Only FastMCP's own _meta["ui"] key. Adding the namespaced
    # `io.modelcontextprotocol/ui` alongside it stopped Claude Desktop from
    # fetching the resource at all — that id belongs to protocol 2026-07-28,
    # which this handshake (2025-11-25) does not negotiate.
    mcp.tool(_tool, name=_name, app=AppConfig(resource_uri=_uri))
    # One concrete resource per tool, not a `{tool}` template: templates are
    # served from resources/templates/list, which Claude Desktop does not call —
    # it lists resources/list and reads the URI declared in the tool's meta.
    # A static shell, never the card itself: the host fetches this ~2ms BEFORE
    # it calls the tool, so at fetch time there is no data. The shell waits for
    # the tool result on the AppBridge and injects the markup from its _meta.
    mcp.resource(_uri, name=f"{_name} card", mime_type=UI_MIME_TYPE)(
        (lambda n: lambda: ui.shell(n))(_name)
    )

# Data-only tool (no UI card)
mcp.tool(get_social_feed, name="get_social_feed")


def main() -> None:
    """Run the Sports Tracker FastMCP server using stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
