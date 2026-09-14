# Sports Tracker MCP Server (Unofficial)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-4.0+-brightgreen.svg)](https://github.com/jlowin/fastmcp)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type Checked: mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)

> [!IMPORTANT]
> **Unofficial Project**: This project is an independent, open-source Model Context Protocol (MCP) server. It is **not affiliated with, endorsed by, sponsored by, or associated with Sports Tracking Technologies Ltd, Amer Sports, Suunto**, or any of their affiliates or subsidiaries. All registered trademarks, product names, and company logos are the property of their respective owners.

An unofficial [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for **Sports Tracker**, enabling AI assistants (such as Claude Desktop, Cursor, and Antigravity) to query workouts, activity history, training load, VO2Max progression, recovery metrics, and social feeds.

---

## ⚡ Features

- **8 FastMCP Tools**: Complete fitness tracking integration covering workouts, social feed, user statistics, training load, VO2Max trends, and activity breakdowns.
- **Structured Pydantic Models**: Clean schemas with human-readable paces, formatted durations, and units.
- **Dual Unit Support**: Effortlessly toggle between metric (km, km/h, min/km) and imperial (miles, mph, min/mi) across queries.
- **LRU Bounded TTL Caching**: In-memory caching via `cachetools.TTLCache` (max 256 items, 60-second TTL) preventing redundant API requests and memory leaks.
- **Resilient Pagination**: Multi-day summary tools dynamically paginate backwards through workout history without premature truncation.

---

## 🛠️ Available MCP Tools

| Tool | Description | Parameters |
| :--- | :--- | :--- |
| `get_recent_workouts` | Fetch recent workouts with formatted distance, duration, pace, and heart rate. | `limit` (default: 10), `imperial` (default: false) |
| `get_social_feed` | Retrieve feed items from followed athletes or community members. | `limit` (default: 10), `imperial` (default: false) |
| `get_workout_details` | In-depth metrics for a workout: ascent/descent, HR zones, gear, cadence, energy, and Suunto extensions. | `workout_key` (required), `imperial` (default: false) |
| `get_user_stats` | Lifetime aggregate statistics and per-sport totals (distance, duration, calories, count). | `username` (optional), `imperial` (default: false) |
| `get_vo2_max_history` | Historical aerobic capacity (VO2Max) and fitness age progression extracted from workouts. | `limit` (default: 20) |
| `get_training_summary` | Aggregated volume, distance, time, and calories across all sports for the past *N* days. | `days` (default: 7), `imperial` (default: false) |
| `get_training_load_and_recovery` | Current recovery hours, training stress score (TSS), peak training effect (PTE), EPOC, and recovery status. | *None* |
| `get_recent_activities_summary` | Breakdown of sport frequency, total duration, and last performed dates over the past *N* days. | `days` (default: 14) |

---

## 💬 Example Assistant Prompts

Once integrated, your AI assistant can answer natural language queries directly:

- **Weekly Training Volume**: *"How much running and cycling have I logged over the past 14 days? Break it down by distance, time, and pace."*
- **Workout Deep Dive**: *"Give me a detailed breakdown of my latest workout, including heart rate zones, cadence, elevation gain, and Suunto metrics in imperial units."*
- **Recovery & Readiness**: *"What is my current recovery time, TSS, and EPOC from my recent activities? Am I ready for a tempo run today?"*
- **Fitness Trends**: *"Plot my aerobic capacity (VO2Max) and fitness age progression over my last 20 workouts."*
- **Interactive Dashboards**: *"Analyze my training load and render an interactive React dashboard with weekly volume charts and HR zone distribution."*

---

## ⚙️ Configuration

The server requires your Sports Tracker session key to authenticate requests.

### Environment Variables

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `STT_SESSION_KEY` | **Yes** | — | Your session token (`STTAuthorization` header). |
| `STT_BASE_URL` | No | `https://api.sports-tracker.com/apiserver/v1` | Sports Tracker API base endpoint. |

### How to get your Session Key

1. Log in to [Sports Tracker Web](https://www.sports-tracker.com) in your web browser.
2. Open your browser's Developer Tools (`F12` or `Cmd+Option+I`) and switch to the **Network** tab.
3. Refresh the page or click on any workout.
4. Inspect any request to `api.sports-tracker.com` and copy the value of the `STTAuthorization` header (or find `sessionkey` in your browser cookies/local storage).
5. Create a `.env` file in the project root:

```bash
cp .env.example .env
```

And populate:

```env
STT_SESSION_KEY=your_session_key_here
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) (recommended) or `pip`

### Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/wilkar/sports-tracker-mcp.git
cd sports-tracker-mcp
uv sync
```

### Running the Server Directly

You can start the server directly using `stdio` transport:

```bash
# Using uv:
uv run sport-tracker

# Or directly with Python:
python main.py
```

### Testing with MCP Inspector

Inspect all tools interactively in your browser using FastMCP's inspector:

```bash
uv run fastmcp dev inspector src/sport_tracker_mcp/server.py
```

Or inspect tool schemas directly from the CLI:

```bash
uv run fastmcp list src/sport_tracker_mcp/server.py
```

---

## 🔌 MCP Client Integration

### Claude Desktop

Add the server to your `claude_desktop_config.json`:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sports-tracker": {
      "command": "/path/to/sports-tracker-mcp/.venv/bin/sport-tracker",
      "env": {
      }
    }
  }
}
```

### Antigravity / Cursor

In your workspace or global MCP settings (`mcp_config.json`):

```json
{
  "mcpServers": {
    "sports-tracker": {
      "command": "/path/to/sports-tracker-mcp/.venv/bin/sport-tracker",
      "env": {

      }
    }
  }
}
```

---

## 📂 Project Structure

```text
sports-tracker-mcp/
├── src/
│   └── sport_tracker_mcp/
│       ├── client/         # Async HTTP client with LRU TTLCache & error handling
│       ├── formatting/     # Unit conversions (metric/imperial), pace, and duration utils
│       ├── models/         # Pydantic schemas for workouts, stats, load & recovery
│       ├── tools/          # 8 FastMCP tool implementations
│       ├── config.py       # Environment variable resolution & .env loader
│       └── server.py       # FastMCP server definition & CLI entrypoint
├── tests/                  # Test suite (65 tests across client, models, tools, and formatting)
├── .env.example            # Sample environment file
├── pyproject.toml          # Project metadata, dependencies, and tool configs
├── TODO.md                 # Roadmap and endpoint specs for upcoming tools
└── README.md
```

---

## 🗺️ Roadmap & Planned Tools (TODO)

The following tools are planned for future releases to expand Sports Tracker capabilities:
- [ ] **`get_routes`**: List saved and recorded GPS routes with distances, speeds, and activity types.
- [ ] **`get_route_details`**: In-depth GPS track waypoints, elevation profiles, and polyline coordinates for a specific route.
- [ ] **`export_workout_gpx`**: Download standardized GPX XML track files for activities.
- [ ] **`get_user_following`**: Retrieve followers and followed athlete profiles from Sports Tracker.

See [TODO.md](TODO.md) for full endpoint specifications.

---

## 🧪 Development & Testing

Run the test suite:

```bash
uv run pytest
```

Check types and formatting:

```bash
uv run mypy .
uv run isort --check .
uv run black --check .
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
