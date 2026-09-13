# Sports Tracker MCP Server — Roadmap & Planned Tools (TODO)

The following tools and capabilities are planned for upcoming releases of the server:

## 🗺️ Planned MCP Tools

### 1. Routes & Navigation
- **`get_routes`**
  - *Endpoint*: `GET /routes`
  - *Description*: Retrieve a list of saved and recorded GPS routes with activity type, total distance, and average speed.
- **`get_route_details`**
  - *Endpoint*: `GET /routes/{route_id}`
  - *Description*: Fetch detailed GPS track waypoints, segment polylines, start/end coordinates, and 3D elevation profiles (`x`, `y`, `z`).

### 2. Workout Export
- **`export_workout_gpx`**
  - *Endpoint*: `GET /workout/exportGpx/{workout_key}?token={session_key}`
  - *Description*: Export and download full GPX XML track files including GPS timestamps, trackpoints, and heart rate extensions.

### 3. Community & Following
- **`get_user_following`**
  - *Endpoint*: `GET /user/follow`
  - *Description*: List followed athletes, followers, and social connection statuses.
