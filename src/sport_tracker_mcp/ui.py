"""HTML rendering for MCP tool-result cards.

Pure string rendering: no MCP types, no I/O. Each ``render_*`` takes the same
Pydantic model its tool returns and produces one self-contained document.

Layout and theme follow the card design; the palette and rule weights are the
single source of truth in ``THEME`` below.
"""

from datetime import datetime
from pathlib import Path
import re
from html import escape
from typing import Any

from .models import (
    RecentActivitiesSummary,
    TimeSeriesPoint,
    TrainingLoadAndRecovery,
    TrainingSummary,
    UserStats,
    VO2MaxHistory,
    WorkoutDetail,
    WorkoutSummary,
)
from .tools import _normalize_limit

# Light is the design's home ground: warm paper, technical-drawing ink.
THEME = {
    "paper": "#F1EFE8",
    "panel": "#FBFAF6",
    "head": "#EDEBE3",
    "fill": "#E8E5DC",
    "rule": "#CFCBC0",
    "hair": "#E3E0D6",
    "hair2": "#EFEDE5",
    "ink": "#1A1F2B",
    "ink2": "#5A6070",
    "ink3": "#8A8F9C",
    "accent4": "#C3D0F4",
    "accent3": "#9FB4EC",
    "accent2": "#6C8CE4",
    "accent": "#3F6BE0",
    "warn": "#C4632A",
    # Hard offset, no blur. Dark needs a heavier one to read at all.
    "shadow": "rgba(26,31,43,.06)",
}

# Dark keeps the same roles, not an inversion: the ground takes the ink's hue
# family, the ink takes the paper's warmth, and the accent ramp runs dim->bright
# so ordered series still read in order.
DARK = {
    "paper": "#14161B",
    "panel": "#1B1E25",
    "head": "#23262E",
    "fill": "#2A2E37",
    "rule": "#3A3F4A",
    "hair": "#2E323B",
    "hair2": "#24272F",
    "ink": "#E8E6DF",
    "ink2": "#A8AEBC",
    "ink3": "#7A8090",
    "accent4": "#2E4478",
    "accent3": "#3F5C9E",
    "accent2": "#5478C9",
    "accent": "#6E95F0",
    "warn": "#E08A52",
    "shadow": "rgba(0,0,0,.45)",
}

# Ordered series walk the accent ramp and end on warn. Referenced as CSS vars so
# a theme swap recolours bars and zone rows without re-rendering.
RAMP = [f"var(--{k})" for k in ("accent4", "accent3", "accent2", "accent", "warn")]


def _vars(palette: dict[str, str]) -> str:
    return ";".join(f"--{k}:{v}" for k, v in palette.items())


_CSS = """
:root{%(light)s;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){%(dark)s;color-scheme:dark}}
:root[data-theme="dark"]{%(dark)s;color-scheme:dark}

*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
 font-family:'Space Grotesk',system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased;
 background-image:linear-gradient(var(--hair) 1px,transparent 1px),linear-gradient(90deg,var(--hair) 1px,transparent 1px);
 background-size:32px 32px}
.wrap{max-width:1280px;margin:0 auto;padding:24px 16px 48px;display:flex;flex-direction:column;gap:20px}
.m{font-family:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace;font-variant-numeric:tabular-nums}
.lbl{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:10px;letter-spacing:.08em;
 text-transform:uppercase;color:var(--ink3)}
.card{background:var(--panel);border:1px solid var(--rule);box-shadow:3px 3px 0 var(--shadow)}
.hd{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:9px 14px;
 border-bottom:1px solid var(--rule);background:var(--head)}
.hd .i{font-size:11px;font-weight:600;color:var(--accent)}
.hd .n{font-size:13px;font-weight:600}
.hd .a{font-size:11px;color:var(--ink3)}
.hd .r{margin-left:auto;font-size:11px;color:var(--ink3)}
.pad{padding:16px 14px}
.bd{border-bottom:1px solid var(--hair)}
.cells{display:grid;gap:1px;background:var(--hair);border-bottom:1px solid var(--hair)}
.cell{background:var(--panel);padding:12px}
.cell .k{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:10px;color:var(--ink3)}
.cell .v{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:19px;font-weight:600;
 font-variant-numeric:tabular-nums}
.big{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:42px;font-weight:600;
 line-height:1.05;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.track{background:var(--fill)}
.track>span{display:block;height:100%%}
.zone{display:grid;grid-template-columns:52px 1fr 66px;align-items:center;gap:10px}
.zone+.zone{margin-top:8px}
.sport{display:grid;grid-template-columns:1fr 92px 76px;align-items:center;gap:10px;padding:8px 14px}
.sport .nm{font-size:13px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rows{width:100%%;border-collapse:collapse}
.rows th{text-align:left;font-weight:400;padding:8px 14px;border-bottom:1px solid var(--hair);
 font-family:'JetBrains Mono',ui-monospace,monospace;font-size:10px;letter-spacing:.08em;
 text-transform:uppercase;color:var(--ink3);white-space:nowrap}
.rows td{padding:9px 14px;border-bottom:1px solid var(--hair2);font-family:'JetBrains Mono',ui-monospace,monospace;
 font-size:12px;font-variant-numeric:tabular-nums}
.rows td.s{font-family:'Space Grotesk',system-ui,sans-serif;font-size:13px;font-weight:500}
.r{text-align:right}
.dim{color:var(--ink2)}
.tight,.tight .cell{padding:9px 10px}
.v17 .v,.v17{font-size:17px}
.scroll{overflow-x:auto}
.seg{display:flex;border:1px solid var(--ink)}
.seg button{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:11px;padding:5px 10px;
 border:0;cursor:pointer;background:transparent;color:var(--ink)}
.seg button+button{border-left:1px solid var(--ink)}
.seg button[aria-pressed=true]{background:var(--ink);color:var(--paper)}
.chip{display:inline-block;padding:2px 6px;border:1px solid var(--accent);color:var(--accent);
 font-family:'JetBrains Mono',ui-monospace,monospace;font-size:10px}
.workout-row{transition:background .15s ease}
.workout-row:hover{background:var(--hair) !important}
.ts-pane{animation:fadeIn .2s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(2px)}to{opacity:1;transform:translateY(0)}}
.split{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.split>div{padding:16px 14px;border-bottom:1px solid var(--hair)}
.split>div+div{border-left:1px solid var(--hair)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (max-width:560px){.split>div+div{border-left:0}}
""" % {"light": _vars(THEME), "dark": _vars(DARK)}

_JS = """
(function(){
 var d=document,K='stt-theme';

 // "auto" follows the host (MCP Apps pushes a theme) or the OS; light/dark pin it.
 function applyTheme(choice){
  var root=d.documentElement;
  if(choice==='auto'){ root.removeAttribute('data-theme'); }
  else { root.setAttribute('data-theme',choice); }
  d.querySelectorAll('[data-theme-set]').forEach(function(b){
   b.setAttribute('aria-pressed',String(b.dataset.themeSet===choice));});
  try{ localStorage.setItem(K,choice); }catch(e){}
 }
 // A theme the host stamped on <html> before this ran beats the "auto" default.
 var saved=null; try{ saved=localStorage.getItem(K); }catch(e){}
 applyTheme(saved || d.documentElement.getAttribute('data-theme') || 'auto');
 d.addEventListener('click',function(e){
  var b=e.target.closest('[data-theme-set]'); if(!b) return;
  applyTheme(b.dataset.themeSet);
 });

 function applyWorkoutFilters(card){
  var limBtn=card.querySelector('[data-limit][aria-pressed="true"]');
  var lim=limBtn?limBtn.dataset.limit:'10';
  var maxN=(lim==='all')?Infinity:parseInt(lim,10);

  var sportBtn=card.querySelector('[data-sport-filter][aria-pressed="true"]');
  var s=sportBtn?sportBtn.dataset.sportFilter:'all';

  var count=0;
  card.querySelectorAll('.workout-row').forEach(function(r){
   var rSport=(r.dataset.sport||'').toLowerCase();
   var sportMatch=(s==='all'||rSport===s);
   if(sportMatch && count < maxN){
    r.style.display='';
    count++;
   } else {
    r.style.display='none';
   }
  });
 }

 d.querySelectorAll('.card').forEach(function(card){
  card.addEventListener('click',function(e){
   var b=e.target.closest('[data-limit],[data-sport-filter]');if(!b)return;
   var attr=b.dataset.limit!==undefined?'data-limit':'data-sport-filter';
   card.querySelectorAll('['+attr+']').forEach(function(x){x.setAttribute('aria-pressed',String(x===b));});
   applyWorkoutFilters(card);
  });
 });


 d.querySelectorAll('.ts-tab').forEach(function(b){
  b.addEventListener('click',function(){
   var t=b.dataset.tab;
   var card=b.closest('.card')||d;
   card.querySelectorAll('.ts-tab').forEach(function(btn){
    btn.setAttribute('aria-pressed',String(btn===b));});
   card.querySelectorAll('.ts-pane').forEach(function(p){
    p.style.display=(p.dataset.pane===t)?'block':'none';});
  });
 });
})();
"""


def _pressed(val: bool) -> str:
    return "true" if val else "false"


def _e(value: Any) -> str:
    return escape("" if value is None else str(value), quote=True)


def _pct(value: float, peak: float) -> str:
    if peak <= 0:
        return "0%"
    return f"{max(0.0, min(100.0, value / peak * 100)):.1f}%"


# --- shell ------------------------------------------------------------------


def _doc(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(title)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">{body}</div>
<script>{_JS}
</script>
</body>
</html>"""


def _sport_selector(sports: list[str], selected: str | None = None) -> str:
    if not sports or len(sports) <= 1:
        return ""
    cur = (selected or "all").lower()
    buttons = [
        f'<button type="button" data-sport-filter="all" aria-pressed="{_pressed(cur == "all")}">all</button>'
    ]
    for s in sports:
        s_low = s.lower()
        buttons.append(
            f'<button type="button" data-sport-filter="{_e(s_low)}" aria-pressed="{_pressed(cur == s_low)}">{_e(s)}</button>'
        )
    return (
        f'<div style="display:flex;align-items:center;gap:6px">'
        f'<span class="lbl">sport</span><div class="seg">{"".join(buttons)}</div></div>'
    )


def _limit_selector(limit: int | str = 10) -> str:
    norm = _normalize_limit(limit)
    cur = "all" if norm == 0 or norm >= 50 else str(norm)
    buttons = [
        f'<button type="button" data-limit="{n}" aria-pressed="{_pressed(cur == str(n))}">{n}</button>'
        for n in (5, 10, 25, "all")
    ]
    return (
        f'<div style="display:flex;align-items:center;gap:6px">'
        f'<span class="lbl">show</span><div class="seg">{"".join(buttons)}</div></div>'
    )


def _theme_toggle() -> str:
    """Theme control. Lives in `_head`, so every card gets one for free."""
    return (
        '<div style="display:flex;align-items:center;gap:6px">'
        '<span class="lbl">theme</span><div class="seg">'
        '<button type="button" data-theme-set="light" aria-pressed="false">light</button>'
        '<button type="button" data-theme-set="dark" aria-pressed="false">dark</button>'
        '<button type="button" data-theme-set="auto" aria-pressed="true">auto</button>'
        "</div></div>"
    )


def _head(
    index: str,
    tool: str,
    args: str = "",
    returns: str = "",
    extra: str = "",
) -> str:
    bits = [
        f'<span class="m i">{_e(index)}</span>',
        f'<span class="m n">{_e(tool)}</span>',
    ]
    if args:
        bits.append(f'<span class="m a">{_e(args)}</span>')
    if returns:
        bits.append(f'<span class="m r">&rarr; {_e(returns)}</span>')
    controls = f"{extra} {_theme_toggle()}" if extra else _theme_toggle()
    bits.append(
        f'<div style="margin-left:auto;display:flex;flex-wrap:wrap;'
        f'align-items:center;gap:12px">{controls}</div>'
    )
    return f'<div class="hd">{"".join(bits)}</div>'


def _cells(items: list[tuple[str, str]], cols: int, cls: str = "") -> str:
    c = f" {cls}" if cls else ""
    inner = "".join(
        f'<div class="cell"><div class="k">{_e(k)}</div><div class="v">{v}</div></div>'
        for k, v in items
    )
    return f'<div class="cells{c}" style="grid-template-columns:repeat({cols},1fr)">{inner}</div>'


def _bar(width: str, color: str, height: str = "6px") -> str:
    return (
        f'<div class="track" style="flex:1;min-width:20px;height:{height}">'
        f'<span style="width:{width};background:{color}"></span></div>'
    )


def _sport_rows(rows: list[tuple[str, int, float, str, str]]) -> str:
    """rows: (sport, count, bar_fraction_of_peak, distance_str, trailing)."""
    peak = max((r[2] for r in rows), default=0.0)
    out = []
    for sport, count, value, dist_str, trailing in rows:
        out.append(
            f'<div class="sport"><div style="display:flex;align-items:center;gap:8px;min-width:0">'
            f'<span class="nm">{_e(sport)}</span>'
            f'<span class="m" style="font-size:11px;color:var(--ink3);flex:none">&times;{count}</span>'
            f'{_bar(_pct(value, peak), "var(--accent)", "5px")}</div>'
            f'<div class="m r" style="font-size:12px">{_e(dist_str)}</div>'
            f'<div class="m r dim" style="font-size:12px">{_e(trailing)}</div>'
            f"</div>"
        )
    return f'<div style="padding:6px 0">{"".join(out)}</div>'


def _when(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%m-%d %H:%M")
    except ValueError:
        return iso[:16]


# --- 01 ---------------------------------------------------------------------


def render_recent_workouts(
    items: list[WorkoutSummary],
    *,
    limit: int | str = 10,
    imperial: bool = False,
    sport: str | None = None,
) -> str:
    peak = max((w.distance_km for w in items), default=0.0)
    norm_limit = _normalize_limit(limit)
    initial_show = norm_limit if norm_limit > 0 else len(items)
    rows = []
    for i, w in enumerate(items):
        hr = f"{w.avg_hr or '—'}/{w.max_hr or '—'}"
        disp = "" if i < initial_show else ";display:none"
        rows.append(
            f'<tr class="workout-row" data-sport="{_e(w.sport)}" '
            f'style="box-shadow:inset 3px 0 0 {RAMP[i % len(RAMP)]}{disp}">'
            f'<td class="s"><span style="font-weight:600">{_e(w.sport)}</span></td>'
            f'<td class="dim">{_e(_when(w.start_time))}</td>'
            f'<td><div style="display:flex;align-items:center;gap:10px">'
            f'{_bar(_pct(w.distance_km, peak), "var(--accent)")}'
            f'<span class="r" style="width:82px;flex:none">{_e(w.distance_formatted)}</span>'
            f"</div></td>"
            f"<td>{_e(w.duration_formatted)}</td>"
            f"<td>{_e(w.avg_pace_formatted)}</td>"
            f'<td class="dim">{_e(w.avg_speed_formatted)}</td>'
            f'<td class="dim">{_e(hr)}</td>'
            f'<td class="r">{_e(w.calories_kcal or "—")}</td></tr>'
        )
    if not rows:
        sport_msg = f" for '{sport}'" if sport else ""
        rows = [
            f'<tr><td colspan="8" style="color:var(--ink3)">no workouts in range{_e(sport_msg)}</td></tr>'
        ]

    unique_sports = list(dict.fromkeys(w.sport for w in items if w.sport))
    sport_sel = _sport_selector(unique_sports, selected=sport)
    lim_sel = _limit_selector(limit)
    controls = [c for c in [sport_sel, lim_sel] if c]
    extra = " ".join(controls)

    args_list = [f"limit={limit}"]
    if sport:
        args_list.append(f'sport="{sport}"')
    args_str = ", ".join(args_list)

    body = (
        '<div class="card">'
        + _head(
            "01",
            "get_recent_workouts",
            args_str,
            "list[WorkoutSummary]",
            extra=extra,
        )
        + '<div class="scroll"><table class="rows" style="min-width:760px"><thead><tr>'
        "<th>sport</th><th>start_time</th><th>distance</th><th>duration</th>"
        '<th>pace</th><th>avg_speed</th><th>hr avg/max</th><th class="r">kcal</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>' + "</div>"
    )
    return _doc("Recent workouts", body)


# --- 02 ---------------------------------------------------------------------


def _render_series_svg(
    pts: list[TimeSeriesPoint],
    label: str,
    color: str = "var(--accent)",
) -> str:
    if not pts:
        return f'<div class="m" style="padding:14px;color:var(--ink3)">no time series data</div>'
    vals = [p.value for p in pts]
    secs = [p.seconds for p in pts]
    min_v, max_v = min(vals), max(vals)
    span = max_v - min_v if max_v != min_v else 1.0
    y_min = max(0.0, min_v - span * 0.08)
    y_max = max_v + span * 0.08
    y_range = y_max - y_min
    max_s = max(secs) if max(secs) > 0 else 1

    width, height = 740, 140
    pad_l, pad_r, pad_t, pad_b = 42, 14, 12, 22
    pw = width - pad_l - pad_r
    ph = height - pad_t - pad_b

    coords = [
        (
            round(pad_l + (p.seconds / max_s) * pw, 1),
            round(pad_t + ph - ((p.value - y_min) / y_range) * ph, 1),
        )
        for p in pts
    ]
    line_d = " ".join(
        [f"M {coords[0][0]} {coords[0][1]}"] + [f"L {x} {y}" for x, y in coords[1:]]
    )
    area_d = f"{line_d} L {coords[-1][0]} {pad_t + ph} L {coords[0][0]} {pad_t + ph} Z"
    mid_v = (min_v + max_v) / 2
    mid_y = pad_t + ph / 2
    gid = f"g-{abs(hash(label)) % 100000}"

    dur_m0 = f"{int(max_s/120)}:{int((max_s/2)%60):02d}"
    dur_m1 = f"{int(max_s/60)}:{int(max_s%60):02d}"

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'style="display:block;overflow:visible" role="img" aria-label="{_e(label)} chart">'
        f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.32"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0.02"/>'
        f"</linearGradient></defs>"
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l + pw}" y2="{pad_t}" style="stroke:var(--hair)" stroke-dasharray="3 3"/>'
        f'<line x1="{pad_l}" y1="{mid_y}" x2="{pad_l + pw}" y2="{mid_y}" style="stroke:var(--hair)" stroke-dasharray="3 3"/>'
        f'<line x1="{pad_l}" y1="{pad_t + ph}" x2="{pad_l + pw}" y2="{pad_t + ph}" style="stroke:var(--rule)"/>'
        f'<path d="{area_d}" fill="url(#{gid})"/>'
        f'<path d="{line_d}" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<text x="{pad_l - 6}" y="{pad_t + 4}" text-anchor="end" class="m" font-size="10" style="fill:var(--ink3)">{max_v:.0f}</text>'
        f'<text x="{pad_l - 6}" y="{mid_y + 3}" text-anchor="end" class="m" font-size="10" style="fill:var(--ink3)">{mid_v:.0f}</text>'
        f'<text x="{pad_l - 6}" y="{pad_t + ph}" text-anchor="end" class="m" font-size="10" style="fill:var(--ink3)">{min_v:.0f}</text>'
        f'<text x="{pad_l}" y="{height - 6}" class="m" font-size="10" style="fill:var(--ink3)">0:00</text>'
        f'<text x="{pad_l + pw / 2}" y="{height - 6}" text-anchor="middle" class="m" font-size="10" style="fill:var(--ink3)">{dur_m0}</text>'
        f'<text x="{pad_l + pw}" y="{height - 6}" text-anchor="end" class="m" font-size="10" style="fill:var(--ink3)">{dur_m1}</text>'
        f"</svg>"
    )


def render_workout_details(detail: WorkoutDetail, *, imperial: bool = False) -> str:
    hero = (
        f'<div class="pad bd" style="display:flex;flex-wrap:wrap;align-items:flex-end;gap:18px">'
        f'<div style="flex:1 1 220px;min-width:0">'
        f'<div style="font-size:22px;font-weight:600;letter-spacing:-.01em">'
        f"{_e(detail.description or detail.sport)}</div>"
        f'<div class="m dim" style="font-size:12px;margin-top:4px">'
        f"{_e(detail.sport)} &middot; {_e(detail.start_time)}</div></div>"
        f'<div style="display:flex;flex-wrap:wrap;gap:26px">'
        f'<div><div class="lbl">distance</div><div class="m" style="font-size:24px;font-weight:600">{_e(detail.distance_formatted)}</div></div>'
        f'<div><div class="lbl">duration</div><div class="m" style="font-size:24px;font-weight:600">'
        f"{_e(detail.duration_formatted)}</div></div>"
        f'<div><div class="lbl">avg_pace</div><div class="m" style="font-size:24px;font-weight:600">{_e(detail.avg_pace_formatted)}</div></div>'
        f"</div></div>"
    )

    # Time series section
    time_series_html = ""
    if detail.time_series:
        charts = []
        tab_buttons = []
        stream_meta = {
            "heart_rate": ("Heart Rate", "bpm", "var(--warn)"),
            "altitude": (
                "Altitude",
                "ft" if imperial else "m",
                "var(--accent)",
            ),
            "speed": ("Speed", "mph" if imperial else "km/h", "var(--accent2)"),
        }
        first_key = next(
            (
                k
                for k in ["heart_rate", "altitude", "speed"]
                if detail.time_series.get(k)
            ),
            None,
        )
        if not first_key and detail.time_series:
            first_key = next(iter(detail.time_series))

        for key in ["heart_rate", "altitude", "speed"]:
            pts = detail.time_series.get(key)
            if not pts:
                continue
            title, unit, color = stream_meta.get(
                key, (key.replace("_", " ").title(), "", "var(--accent)")
            )
            is_active = key == first_key
            tab_buttons.append(
                f'<button type="button" class="ts-tab" data-tab="{key}" aria-pressed="{_pressed(is_active)}">{_e(title)}</button>'
            )
            chart_svg = _render_series_svg(pts, title, color)
            disp = "block" if is_active else "none"
            vals = [p.value for p in pts]
            charts.append(
                f'<div class="ts-pane" data-pane="{key}" style="display:{disp}">'
                f'<div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:8px">'
                f'<span class="lbl">{_e(title)} time series</span>'
                f'<span class="m dim" style="font-size:11px">'
                f"min: <b>{min(vals):.0f}</b> &middot; avg: <b>{sum(vals)/len(vals):.0f}</b> &middot; max: <b>{max(vals):.0f} {unit}</b>"
                f"</span></div>"
                f"{chart_svg}</div>"
            )

        if charts:
            tabs_header = (
                f'<div style="display:flex;align-items:center;justify-content:space-between;padding:9px 14px;'
                f'border-bottom:1px solid var(--hair);background:var(--head)">'
                f'<div class="lbl">time series data</div>'
                f'<div class="seg">{"".join(tab_buttons)}</div></div>'
            )
            time_series_html = (
                f'<div class="bd" style="background:var(--panel)">'
                f"{tabs_header}"
                f'<div style="padding:14px">{"".join(charts)}</div></div>'
            )

    panels = []
    if detail.heart_rate_zones:
        secs = {k: _zone_secs(v) for k, v in detail.heart_rate_zones.items()}
        peak = max(secs.values(), default=0.0)
        zones = "".join(
            f'<div class="zone"><span class="m dim" style="font-size:11px">{_e(k)}</span>'
            f'{_bar(_pct(secs[k], peak), RAMP[i % len(RAMP)], "14px")}'
            f'<span class="m r" style="font-size:12px">'
            f"{_e(detail.heart_rate_zones[k])}</span></div>"
            for i, k in enumerate(sorted(detail.heart_rate_zones))
        )
        panels.append(
            f'<div><div class="lbl" style="margin-bottom:12px">heart_rate_zones</div>{zones}</div>'
        )

    ext = [
        (
            "training_stress_score",
            _e(
                "—"
                if detail.training_stress_score is None
                else detail.training_stress_score
            ),
        ),
        (
            "peak_training_effect",
            _e(
                "—"
                if detail.peak_training_effect is None
                else detail.peak_training_effect
            ),
        ),
        ("peak_epoc", _e("—" if detail.peak_epoc is None else detail.peak_epoc)),
        (
            "recovery_time_hours",
            _e(
                "—"
                if detail.recovery_time_hours is None
                else detail.recovery_time_hours
            ),
        ),
    ]
    panels.append(
        f'<div><div class="lbl" style="margin-bottom:12px">suunto extensions</div>'
        f'{_cells(ext, 2, cls="tight v17")}</div>'
    )

    elev = [
        ("ascent_meters", f"{detail.ascent_meters:,.0f}"),
        ("descent_meters", f"{detail.descent_meters:,.0f}"),
        ("max_speed", _e(detail.max_speed_formatted)),
        ("gear", _e(detail.gear or "—")),
    ]
    panels.append(
        f'<div><div class="lbl" style="margin-bottom:12px">elevation &amp; speed</div>'
        f'{_cells(elev, 2, cls="tight v17")}</div>'
    )

    body = (
        '<div class="card" id="workout-details-card">'
        + _head(
            "02",
            "get_workout_details",
            _e(detail.sport),
            "WorkoutDetail",
        )
        + hero
        + time_series_html
        + f'<div class="split">{"".join(panels)}</div></div>'
    )
    return _doc("Workout details", body)


def _zone_secs(value: str) -> float:
    try:
        h, m, s = (int(p) for p in value.split(":"))
        return h * 3600 + m * 60 + s
    except (ValueError, AttributeError):
        return 0.0


# --- 03 ---------------------------------------------------------------------

_RECOVERY_SCALE = 48.0


def render_training_load_and_recovery(load: TrainingLoadAndRecovery) -> str:
    circ = 2 * 3.14159265 * 50
    dash = circ * min(load.cumulative_recovery_hours / _RECOVERY_SCALE, 1.0)
    gauge = (
        f'<svg viewBox="0 0 120 120" width="118" height="118" style="flex:none" role="img" '
        f'aria-label="Cumulative recovery {load.cumulative_recovery_hours:g} hours">'
        f'<circle cx="60" cy="60" r="50" fill="none" style="stroke:var(--fill)" stroke-width="12"></circle>'
        f'<circle cx="60" cy="60" r="50" fill="none" style="stroke:var(--accent)" stroke-width="12" '
        f'stroke-dasharray="{dash:.0f} {circ:.0f}" transform="rotate(-90 60 60)"></circle>'
        f'<text x="60" y="56" text-anchor="middle" font-family="JetBrains Mono, monospace" '
        f'font-size="26" font-weight="600" style="fill:var(--ink)">'
        f"{load.cumulative_recovery_hours:g}</text>"
        f'<text x="60" y="74" text-anchor="middle" font-family="JetBrains Mono, monospace" '
        f'font-size="10" letter-spacing="1" style="fill:var(--ink3)">HOURS</text></svg>'
    )
    chip = (
        f'<span class="chip" style="margin-left:auto">'
        f"{_e(load.recovery_status.replace('_', ' '))}</span>"
    )
    head_banner = (
        f'<div class="pad bd" style="display:flex;align-items:center;gap:18px;background:var(--panel)">'
        f"{gauge}<div>"
        f'<div class="lbl">recovery time</div>'
        f'<div class="big">{load.latest_workout_recovery_hours:g}<span class="m dim" style="font-size:16px;font-weight:400">'
        f" hrs (last workout)</span></div>"
        f'<div class="m dim" style="font-size:12px;margin-top:6px">'
        f"Cumulative recovery at <b>{load.cumulative_recovery_hours:g}</b> hrs "
        f"across recent efforts.</div></div>{chip}</div>"
    )
    cells = _cells(
        [
            (
                "training_stress_score",
                (
                    "—"
                    if load.training_stress_score is None
                    else f"{load.training_stress_score:g}"
                ),
            ),
            (
                "peak_training_effect",
                (
                    "—"
                    if load.peak_training_effect is None
                    else f"{load.peak_training_effect:g}"
                ),
            ),
            (
                "peak_epoc",
                "—" if load.peak_epoc is None else f"{load.peak_epoc:g}",
            ),
            ("latest_sport", _e(load.latest_sport or "—")),
        ],
        4,
    )
    body = (
        '<div class="card">'
        + _head(
            "03",
            "get_training_load_and_recovery",
            "",
            "TrainingLoadAndRecovery",
        )
        + head_banner
        + cells
        + "</div>"
    )
    return _doc("Training load & recovery", body)


# --- 04 ---------------------------------------------------------------------


def render_training_summary(summary: TrainingSummary, *, imperial: bool = False) -> str:
    hero = (
        f'<div class="pad bd" style="display:flex;flex-wrap:wrap;align-items:flex-end;gap:18px">'
        f'<div><div class="lbl">total_workouts</div><div class="big">{summary.workouts_count}</div></div>'
        f'<div style="margin-left:auto;display:flex;flex-wrap:wrap;gap:24px">'
        f'<div><div class="lbl">distance</div><div class="m" style="font-size:24px;font-weight:600">{_e(summary.total_distance_formatted)}</div></div>'
        f'<div><div class="lbl">duration</div><div class="m" style="font-size:24px;font-weight:600">'
        f"{_e(summary.total_duration_formatted)}</div></div>"
        f'<div><div class="lbl">energy</div><div class="m" style="font-size:24px;font-weight:600">'
        f"{summary.total_calories_kcal:,} kcal</div></div>"
        f"</div></div>"
    )
    rows = [
        (
            b.sport,
            b.workouts_count,
            b.distance_km if b.distance_km > 0 else float(b.workouts_count),
            b.distance_formatted,
            f"{b.calories_kcal:,} kcal",
        )
        for b in summary.sports
    ]
    sport_block = _sport_rows(rows) if rows else ""
    body = (
        '<div class="card">'
        + _head(
            "04",
            "get_training_summary",
            f"days={summary.days}",
            "TrainingSummary",
        )
        + hero
        + sport_block
        + "</div>"
    )
    return _doc("Training summary", body)


# --- 05 ---------------------------------------------------------------------


def render_vo2_max_history(history: VO2MaxHistory) -> str:
    series = [r.vo2_max for r in reversed(history.records) if r.vo2_max]
    chart = ""
    if series:
        lo, hi = min(series), max(series)
        span = hi - lo if hi != lo else 1.0
        w = 1200
        h = 140
        pad_x = 24
        pad_y = 16
        pts = []
        for i, val in enumerate(series):
            x = (
                pad_x + i * (w - 2 * pad_x) / (len(series) - 1)
                if len(series) > 1
                else w / 2
            )
            y = h - pad_y - (val - lo) / span * (h - 2 * pad_y)
            pts.append((x, y))
        polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        dots = "".join(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" style="fill:var(--ink);stroke:var(--paper)" stroke-width="2"/>'
            for x, y in pts
        )
        chart = (
            f'<div style="padding:14px;border-bottom:1px solid var(--hair)">'
            f'<div class="lbl" style="margin-bottom:8px">trend ({len(series)} points)</div>'
            f'<svg viewBox="0 0 {w} {h}" style="width:100%%;height:auto;display:block" role="img" '
            f'aria-label="VO2Max trendline from {lo:g} to {hi:g}">'
            f'<polyline points="{polyline}" fill="none" style="stroke:var(--accent)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
            f"{dots}</svg></div>"
        )
    rows = (
        "".join(
            f'<tr><td class="m">{_e(_when(r.date))}</td><td class="s">{_e(r.sport)}</td>'
            f'<td class="r m" style="font-weight:600;color:var(--accent)">{r.vo2_max}</td>'
            f'<td class="r m dim">{_e(r.max_hr or "—")}</td></tr>'
            for r in history.records[:10]
        )
        or f'<tr><td colspan="4" style="color:var(--ink3)">no VO2Max records</td></tr>'
    )
    body = (
        '<div class="card">'
        + _head("05", "get_vo2_max_history", "", "VO2MaxHistory")
        + _cells(
            [
                (
                    "latest_vo2_max",
                    _e(
                        "—"
                        if history.latest_vo2_max is None
                        else history.latest_vo2_max
                    ),
                ),
                (
                    "average_vo2_max",
                    _e(
                        "—"
                        if history.average_vo2_max is None
                        else history.average_vo2_max
                    ),
                ),
                (
                    "fitness_age",
                    _e(
                        "—"
                        if history.latest_fitness_age is None
                        else history.latest_fitness_age
                    ),
                ),
            ],
            3,
        )
        + chart
        + '<table class="rows"><thead><tr><th>date</th><th>sport</th>'
        '<th class="r">vo2</th><th class="r">hr</th></tr></thead>'
        f"<tbody>{rows}</tbody></table></div>"
    )
    return _doc("VO2Max history", body)


# --- 06 ---------------------------------------------------------------------


def render_user_stats(stats: UserStats, *, imperial: bool = False) -> str:
    rows = [
        (
            s.sport,
            s.workouts_count,
            s.distance_km if s.distance_km > 0 else float(s.workouts_count),
            s.distance_formatted,
            f"{s.duration_hours or 0:g}h",
        )
        for s in stats.sports[:8]
    ]
    body = (
        '<div class="card">'
        + _head("06", "get_user_stats", "username=None", "UserStats")
        + f'<div class="pad bd"><div class="lbl">total_distance</div>'
        f'<div class="big">{_e(stats.total_distance_formatted)}</div></div>'
        + _cells(
            [
                ("workouts", f"{stats.total_workouts:,}"),
                ("hours", f"{stats.total_duration_hours:,.1f}"),
                ("kcal", f"{stats.total_calories_kcal:,}"),
                ("days", f"{stats.total_days:,}"),
            ],
            4,
        )
        + (_sport_rows(rows) if rows else "")
        + "</div>"
    )
    return _doc("Lifetime stats", body)


# --- 07 ---------------------------------------------------------------------


def render_recent_activities_summary(summary: RecentActivitiesSummary) -> str:
    rows = (
        "".join(
            f'<tr><td class="s">{_e(a.sport)}</td><td class="r">{a.count}</td>'
            f'<td class="r">{_e(a.total_duration_formatted)}</td>'
            f'<td class="r dim">{_e(a.last_performed)}</td></tr>'
            for a in summary.activities
        )
        or f'<tr><td colspan="4" style="color:var(--ink3)">no sessions in range</td></tr>'
    )
    body = (
        '<div class="card">'
        + _head(
            "07",
            "get_recent_activities_summary",
            f"days={summary.days}",
            "RecentActivitiesSummary",
        )
        + f'<div class="pad bd" style="display:flex;align-items:baseline;gap:12px">'
        f'<div class="big">{summary.total_sessions}</div>'
        f'<div class="m dim" style="font-size:11px">'
        f"total_sessions across {len(summary.activities)} sports<br>"
        f"in the past {summary.days} days</div></div>"
        + '<table class="rows"><thead><tr><th>sport</th><th class="r">count</th>'
        '<th class="r">duration</th><th class="r">last</th></tr></thead>'
        f"<tbody>{rows}</tbody></table></div>"
    )
    return _doc("Recent activities", body)


# --- MCP Apps shell ---------------------------------------------------------

# The host fetches this resource BEFORE the tool runs, so it cannot contain the
# card: at fetch time there is no data yet. It is a static shell that waits for
# the host to push the tool result over the AppBridge, then injects the markup
# the server rendered into it. That keeps every renderer above in Python.
CARD_META_KEY = "sport-tracker/card"

def _load_ext_apps() -> str:
    """The vendored ext-apps client, rewritten to publish a global.

    The bundle ends in `export{...,OO as App}`. Inside an inline module script
    those exports are unreachable — nothing can import an inline module — so the
    trailing export becomes an assignment the next script block can read.
    """
    src = (Path(__file__).parent / "vendor" / "ext-apps-app-2.0.0.js").read_text(
        encoding="utf-8"
    )
    match = re.search(r"export\{(?P<names>[^}]*)\};?\s*$", src)
    if match is None:  # pragma: no cover - vendored file is pinned
        raise RuntimeError("vendored ext-apps bundle has no trailing export")
    pairs = []
    for entry in match.group("names").split(","):
        local, _, exported = entry.partition(" as ")
        pairs.append(f"{(exported or local).strip()}:{local.strip()}")
    return src[: match.start()] + "window.__extApps={" + ",".join(pairs) + "};"


_VENDORED_APP = _load_ext_apps()

_SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<style>%(css)s
#stt-wait{padding:16px;font:12px 'JetBrains Mono',ui-monospace,monospace;color:%(ink3)s;white-space:pre-wrap}
</style>
</head>
<body>
<div class="wrap" id="stt-root"><div id="stt-wait">loading %(title)s&hellip;</div></div>
<script type="module">
// ext-apps client, vendored: an import from a CDN is at the mercy of the
// widget's CSP, and when it is blocked the card silently never leaves
// "loading…". Inlining removes the network from the path entirely.
%(app_js)s
//# sourceURL=ext-apps-app.js
</script>
<script type="module">
const root = document.getElementById("stt-root");
const wait = document.getElementById("stt-wait");
const say = (m) => { if (wait) wait.textContent = m; };
window.addEventListener("error", (e) => say("card error: " + (e.message || e.type)));
function paint(result){
  const markup = result && result._meta && result._meta["%(meta_key)s"];
  if (!markup) { say("tool result arrived without a card in _meta"); return; }
  const doc = new DOMParser().parseFromString(markup, "text/html");
  const wrap = doc.querySelector(".wrap");
  root.innerHTML = wrap ? wrap.innerHTML : doc.body.innerHTML;
  for (const old of root.querySelectorAll("script")) {
    const s = document.createElement("script");
    s.textContent = old.textContent;
    old.replaceWith(s);
  }
}
try {
  const Ctor = window.__extApps && window.__extApps.App;
  if (!Ctor) { say("ext-apps client did not load"); }
  else {
    const app = new Ctor({ name: "sport-tracker", version: "1.0.0" });
    app.ontoolresult = paint;
    // Follow the host's theme while the card is on "auto". A pinned light/dark
    // choice sets data-theme on <html>, which this must not override.
    const followHost = (t) => {
      if (!t) return;
      let pinned = null;
      try { pinned = localStorage.getItem("stt-theme"); } catch (e) {}
      if (pinned && pinned !== "auto") return;
      document.documentElement.setAttribute("data-theme", t === "dark" ? "dark" : "light");
    };
    app.onhostcontextchanged = (ctx) => followHost(ctx && ctx.theme);
    await app.connect();
    followHost((app.getHostContext() || {}).theme);
    say("connected — waiting for tool result…");
    setTimeout(() => {
      if (wait && wait.isConnected) say("connected, but no tool result after 10s");
    }, 10000);
  }
} catch (e) {
  say("card bridge failed: " + (e && e.message ? e.message : String(e)));
}
</script>
</body>
</html>"""


def shell(title: str) -> str:
    """Static app shell for one tool's card; data arrives over the AppBridge."""
    return _SHELL % {
        "title": _e(title),
        "css": _CSS,
        "ink3": "var(--ink3)",
        "app_js": _VENDORED_APP,
        "meta_key": CARD_META_KEY,
    }
