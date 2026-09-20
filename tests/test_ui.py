import pytest

from sport_tracker_mcp import ui
from sport_tracker_mcp.models import (
    RecentActivitiesSummary,
    TrainingLoadAndRecovery,
    TrainingSummary,
    UserStats,
    VO2MaxHistory,
    WorkoutDetail,
    WorkoutSummary,
)
from tests.fixtures import (
    MOCK_USER_STATS_PAYLOAD,
    MOCK_WORKOUT_DETAILS_PAYLOAD,
    MOCK_WORKOUTS_PAYLOAD,
)


def _summaries() -> list[WorkoutSummary]:
    items = [WorkoutSummary.from_api(w) for w in MOCK_WORKOUTS_PAYLOAD]
    return [i for i in items if i is not None]


def test_every_renderer_produces_a_document():
    """Each card is a complete, self-contained HTML document."""
    detail = WorkoutDetail.from_api(MOCK_WORKOUT_DETAILS_PAYLOAD)
    assert detail is not None
    pages = [
        ui.render_recent_workouts(_summaries()),
        ui.render_workout_details(detail),
        ui.render_training_load_and_recovery(
            TrainingLoadAndRecovery.from_workout(MOCK_WORKOUTS_PAYLOAD[0])
        ),
        ui.render_training_summary(
            TrainingSummary.from_workouts(MOCK_WORKOUTS_PAYLOAD)
        ),
        ui.render_vo2_max_history(VO2MaxHistory.from_workouts(MOCK_WORKOUTS_PAYLOAD)),
        ui.render_user_stats(UserStats.from_api(MOCK_USER_STATS_PAYLOAD)),
        ui.render_recent_activities_summary(
            RecentActivitiesSummary.from_workouts(MOCK_WORKOUTS_PAYLOAD)
        ),
    ]
    for html in pages:
        assert html.startswith("<!doctype html>")
        assert html.rstrip().endswith("</html>")
        assert ui.THEME["accent"] in html


def test_empty_payloads_render_without_crashing():
    """No workouts / no records is a normal state, not an error."""
    assert "no workouts in range" in ui.render_recent_workouts([])
    assert "no sessions in range" in ui.render_recent_activities_summary(
        RecentActivitiesSummary.from_workouts([])
    )
    assert "no VO2Max records" in ui.render_vo2_max_history(
        VO2MaxHistory.from_workouts([])
    )
    ui.render_training_load_and_recovery(TrainingLoadAndRecovery.from_workout(None))


def test_workout_details_renders_time_series():
    """Workout detail card renders time series SVG charts and metric tabs."""
    detail = WorkoutDetail.from_api(MOCK_WORKOUT_DETAILS_PAYLOAD)
    assert detail is not None
    assert "heart_rate" in detail.time_series
    assert "altitude" in detail.time_series
    assert "speed" in detail.time_series

    html = ui.render_workout_details(detail)
    assert "time series data" in html
    assert '<svg viewBox="0 0 740 140"' in html
    assert 'data-tab="heart_rate"' in html
    assert 'data-tab="altitude"' in html
    assert 'data-tab="speed"' in html
    assert "min:" in html and "max:" in html


def test_recent_workouts_has_limit_selector():
    """Recent workouts includes interactive limit selector."""
    html = ui.render_recent_workouts(_summaries(), limit=10)
    assert 'data-limit="5"' in html
    assert 'data-limit="10"' in html
    assert 'data-limit="25"' in html
    assert 'data-limit="all"' in html
    assert 'class="workout-row"' in html
    assert f'data-sport="{_summaries()[0].sport}"' in html


def test_recent_workouts_has_sport_filter():
    """Recent workouts card includes interactive sport selector when multiple sports are present."""
    html = ui.render_recent_workouts(_summaries(), limit=10, sport="gym")
    assert 'sport="gym"' in html
    assert 'data-sport-filter="all"' in html
    assert 'data-sport-filter="gym"' in html
    assert 'data-sport-filter="walking"' in html

    empty_html = ui.render_recent_workouts([], limit=10, sport="surfing")
    assert "no workouts in range for &#x27;surfing&#x27;" in empty_html


def test_no_keys_are_exposed_in_visible_ui():
    """Ensure workout keys and internal IDs are never exposed as visible text in the UI."""
    detail = WorkoutDetail.from_api(MOCK_WORKOUT_DETAILS_PAYLOAD)
    assert detail is not None
    key = detail.workout_key

    # 1. Recent workouts card: no "key:" label, no copy key button, no key in tooltip
    workouts_html = ui.render_recent_workouts(_summaries())
    workouts_body = workouts_html.split("<script>")[0]
    assert "copy key" not in workouts_body
    assert "key:" not in workouts_body
    assert f"({key})" not in workouts_body

    # 2. Workout details card: header does not expose workout_key="xxx"
    details_html = ui.render_workout_details(detail)
    details_body = details_html.split("<script>")[0]
    assert f'workout_key="{key}"' not in details_body
    assert "workout_key" not in details_body

    # 3. Training load & recovery: no "workout_key" cell
    load_html = ui.render_training_load_and_recovery(
        TrainingLoadAndRecovery.from_workout(MOCK_WORKOUTS_PAYLOAD[0])
    )
    load_body = load_html.split("<script>")[0]
    assert "workout_key" not in load_body


def test_recent_activities_summary_rendering():
    """Activities summary renders the days and session count."""
    summary = RecentActivitiesSummary.from_workouts(MOCK_WORKOUTS_PAYLOAD, days=14)
    html = ui.render_recent_activities_summary(summary)
    assert "days=14" in html
    assert str(summary.total_sessions) in html


def test_values_are_escaped():
    """Sport names and descriptions come from the API — never trust them raw."""
    raw = dict(MOCK_WORKOUTS_PAYLOAD[0])
    raw["description"] = '<script>alert("xss")</script>'
    detail = WorkoutDetail.from_api(raw)
    assert detail is not None
    html = ui.render_workout_details(detail)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_recent_workouts_renders_model_formatted_strings():
    """Cards render the model's pre-formatted distance, speed, and pace."""
    summaries = _summaries()
    html = ui.render_recent_workouts(summaries)
    assert summaries[0].distance_formatted in html
    assert summaries[0].avg_speed_formatted in html
    assert summaries[0].avg_pace_formatted in html


def test_bar_widths_are_clamped():
    assert ui._pct(50, 100) == "50.0%"
    assert ui._pct(200, 100) == "100.0%"
    assert ui._pct(5, 0) == "0%"


def test_recent_workouts_limit_selector_states():
    # Test limit=25
    html_25 = ui.render_recent_workouts(_summaries(), limit=25)
    assert 'data-limit="25" aria-pressed="true"' in html_25
    assert 'data-limit="10" aria-pressed="false"' in html_25

    # Test limit="all"
    html_all = ui.render_recent_workouts(_summaries(), limit="all")
    assert 'data-limit="all" aria-pressed="true"' in html_all
    assert 'data-limit="10" aria-pressed="false"' in html_all

    # Test limit=10
    html_10 = ui.render_recent_workouts(_summaries(), limit=10)
    assert 'data-limit="10" aria-pressed="true"' in html_10
    assert 'data-limit="25" aria-pressed="false"' in html_10

    # Test limit=5
    html_5 = ui.render_recent_workouts(_summaries(), limit=5)
    assert 'data-limit="5" aria-pressed="true"' in html_5
    assert 'data-limit="10" aria-pressed="false"' in html_5


def test_both_themes_are_defined_as_tokens():
    """Every colour is a token, defined for light and dark in the same shape.

    A colour whose only definition sits inside a media/[data-theme] block never
    applies in the un-stamped state, which renders one theme's text on the
    other theme's ground.
    """
    css = ui._CSS
    for key in ui.THEME:
        assert f"--{key}:" in css, f"{key} missing from :root"
        assert ui.THEME[key] in css, f"light {key} missing"
        assert ui.DARK[key] in css, f"dark {key} missing"
    # All three states: bare :root, OS preference, explicit toggle.
    assert ":root{" in css
    assert '@media (prefers-color-scheme:dark){:root:not([data-theme="light"])' in css
    assert ':root[data-theme="dark"]' in css


def test_no_hardcoded_palette_colours_in_markup():
    """Cards reference tokens, never raw hex, or the toggle cannot recolour them."""
    detail = WorkoutDetail.from_api(MOCK_WORKOUT_DETAILS_PAYLOAD)
    assert detail is not None
    cards = [
        ui.render_recent_workouts(_summaries()),
        ui.render_workout_details(detail),
        ui.render_training_load_and_recovery(
            TrainingLoadAndRecovery.from_workout(MOCK_WORKOUTS_PAYLOAD[0])
        ),
        ui.render_user_stats(UserStats.from_api(MOCK_USER_STATS_PAYLOAD)),
    ]
    for card in cards:
        body = card.split("</style>")[1]
        for key, value in ui.THEME.items():
            assert value not in body, f"raw {key} ({value}) in markup; use var(--{key})"


def test_every_card_offers_the_theme_toggle():
    detail = WorkoutDetail.from_api(MOCK_WORKOUT_DETAILS_PAYLOAD)
    assert detail is not None
    cards = [
        ui.render_recent_workouts(_summaries()),
        ui.render_workout_details(detail),
        ui.render_training_summary(TrainingSummary.from_workouts(MOCK_WORKOUTS_PAYLOAD)),
        ui.render_vo2_max_history(VO2MaxHistory.from_workouts(MOCK_WORKOUTS_PAYLOAD)),
        ui.render_user_stats(UserStats.from_api(MOCK_USER_STATS_PAYLOAD)),
        ui.render_recent_activities_summary(
            RecentActivitiesSummary.from_workouts(MOCK_WORKOUTS_PAYLOAD)
        ),
        ui.render_training_load_and_recovery(
            TrainingLoadAndRecovery.from_workout(MOCK_WORKOUTS_PAYLOAD[0])
        ),
    ]
    for card in cards:
        for choice in ("light", "dark", "auto"):
            assert f'data-theme-set="{choice}"' in card
