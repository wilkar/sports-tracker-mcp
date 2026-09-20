# Sports Tracker MCP Server (Unofficial)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-4.0+-brightgreen.svg)](https://github.com/jlowin/fastmcp)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type Checked: mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)

Ask your AI assistant about your training: workouts, VO2Max trends, training load, recovery, and lifetime stats — answered with interactive cards.

> [!IMPORTANT]
> **Unofficial Project**: This project is an independent, open-source Model Context Protocol (MCP) server. It is **not affiliated with, endorsed by, sponsored by, or associated with Sports Tracking Technologies Ltd, Amer Sports, Suunto**, or any of their affiliates or subsidiaries. All registered trademarks, product names, and company logos are the property of their respective owners.

> [!NOTE]
> **Runs locally, always.** The server talks to Sports Tracker with a session key taken from your own browser. That key is tied to your account and never leaves your machine — so there is no hosted version of this server, and there cannot be one.

---

## 🚀 Quick start

### 1. Get your session key

Log in to [Sports Tracker Web](https://www.sports-tracker.com), open DevTools (`F12` / `Cmd+Option+I`) → **Network**, refresh the page, click any request to `api.sports-tracker.com`, and copy the value of the **`STTAuthorization`** request header.

<!-- Screenshot goes here: Network tab with the STTAuthorization header highlighted. -->

> [!WARNING]
> Treat this key like a password — it grants full access to your Sports Tracker account. Never paste it into an issue, a gist, or a shared config. It also **expires**: when tools start failing with an authentication error, repeat this step to get a fresh one.

### 2. Add the server

**Claude Code** — one command:

```bash
claude mcp add sports-tracker -e STT_SESSION_KEY=your_session_key_here \
  -- uvx --from git+https://github.com/wilkar/sports-tracker-mcp sport-tracker-mcp
```

**Claude Desktop** — add to `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`, Windows: `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "sports-tracker": {
      "command": "uvx",
      "args": ["--from", "/path/to/the/repo", "sport-tracker-mcp"],
      "env": {
        "STT_SESSION_KEY": "your_session_key_here"
      }
    }
  }
}
```

**Cursor / Antigravity** — add the same JSON block to your MCP settings (`mcp_config.json`).

Nothing to clone and no virtualenv to manage: [uv](https://github.com/astral-sh/uv) fetches and runs the server on demand. If your client reports `uvx: command not found`, use the absolute path from `which uvx` (e.g. `/opt/homebrew/bin/uvx`).

### 3. Ask it something

> *"How far did I run in the last 7 days?"*

That's it. If you get an answer, you're done.

---

## 🛠️ Available MCP Tools

| Tool | UI Card | Description | Parameters |
| :--- | :---: | :--- | :--- |
| `get_recent_workouts` | ✅ | Fetch recent workouts with interactive sport and limit filters, clickable workout rows, and metrics. | `limit` (default: 10, supports 5, 10, 25, 'all'), `imperial` (default: false), `sport` (optional) |
| `get_workout_details` | ✅ | In-depth workout analysis with interactive time series charts (HR, altitude, speed), HR zones, ascent/descent, and Suunto extensions. | `workout_key` (required), `imperial` (default: false) |
| `get_training_load_and_recovery` | ✅ | Recovery gauge, cumulative recovery hours, TSS, PTE, and EPOC metrics. | *None* |
| `get_training_summary` | ✅ | Aggregated volume, distance, time, and calories across sports for the past *N* days. | `days` (default: 7), `imperial` (default: false) |
| `get_vo2_max_history` | ✅ | Aerobic capacity (VO2Max) trendline and fitness age progression extracted from workouts. | `limit` (default: 20) |
| `get_user_stats` | ✅ | Lifetime aggregate statistics and per-sport totals (distance, duration, calories, count). | `username` (optional), `imperial` (default: false) |
| `get_recent_activities_summary` | ✅ | Breakdown of sport frequency, total duration, and last performed dates over the past *N* days with interval selector. | `days` (default: 14) |
| `get_social_feed` | ❌ (data-only) | Retrieve feed items from followed athletes or community members. | `limit` (default: 10), `imperial` (default: false) |

Cards render as interactive HTML in hosts that support MCP Apps (`io.modelcontextprotocol/ui`); every tool also returns plain structured data, so clients without UI support lose nothing.

### More things to ask

- *"How much running and cycling have I logged over the past 14 days? Break it down by distance, time, and pace."*
- *"Give me a detailed breakdown of my latest workout, including heart rate zones, elevation gain, and Suunto metrics in imperial units."*
- *"What is my current recovery time, TSS, and EPOC? Am I ready for a tempo run today?"*
- *"Plot my VO2Max and fitness age progression over my last 20 workouts."*

---

## ⚙️ Configuration reference

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `STT_SESSION_KEY` | **Yes** | — | Your session token (the `STTAuthorization` header). |
| `STT_BASE_URL` | No | `https://api.sports-tracker.com/apiserver/v1` | Sports Tracker API base endpoint. |

Pass both through your MCP client's `env` block (as in [Quick start](#2-add-the-server)); the server reads them from the process environment at startup.

> [!NOTE]
> **On `STT_BASE_URL`**: your session token is sent as a header to whatever host this names. Leave it at the default unless you are deliberately pointing at a trusted local debugging proxy.

---

## 🧑‍💻 Development

```bash
git clone https://github.com/wilkar/sports-tracker-mcp.git
cd sports-tracker-mcp
uv sync
```

Run the server from the clone:

```bash
STT_SESSION_KEY="your_key" uv run sport-tracker-mcp
# or keep it in a local .env (cp .env.example .env):
uv run --env-file .env sport-tracker-mcp
```

Point an MCP client at your working copy by swapping the `--from` target for an absolute path:

```bash
claude mcp add sports-tracker-dev -e STT_SESSION_KEY=your_key \
  -- uvx --from /absolute/path/to/sports-tracker-mcp sport-tracker-mcp
```

Tests, types and formatting:

```bash
uv run pytest
uv run mypy .
uv run isort --check .
uv run black --check .
```

Inspect the tool schemas:

```bash
uv run fastmcp list src/sport_tracker_mcp/server.py
uv run fastmcp dev inspector src/sport_tracker_mcp/server.py
```

### Project structure

```text
src/sport_tracker_mcp/
├── client.py       # Async HTTP client with TTL cache & error handling
├── config.py       # Environment variable resolution
├── constants.py    # Activity ID mappings
├── formatting.py   # Unit conversions (metric/imperial), pace, duration
├── models.py       # Pydantic schemas for workouts, stats, load & recovery
├── server.py       # FastMCP server, tool registration & UI cards
├── tools.py        # Tool implementations
└── ui.py           # HTML rendering for tool-result cards
```

---

## 🗺️ Roadmap

- [ ] **`get_routes`**: List saved and recorded GPS routes with distances, speeds, and activity types.
- [ ] **`get_route_details`**: GPS track waypoints, elevation profiles, and polyline coordinates for a route.
- [ ] **`export_workout_gpx`**: Download standardized GPX XML track files for activities.
- [ ] **`get_user_following`**: Retrieve followers and followed athlete profiles.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
