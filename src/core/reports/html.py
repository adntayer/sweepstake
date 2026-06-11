"""Generate rich mobile-first HTML reports directly from gold-layer CSV data.

Produces:
  - Per-participant boleiros/<name>.html (X-ray analysis)
  - Per-match jogos/<phase>/<match>.html (prediction analysis)
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime

import pandas as pd
import pytz

from src.core.config import ChampionshipConfig
from src.core.printing import print_colored
from src.core.reports.new_views import (
    build_all_team_pages,
    build_group_standings_page,
    build_round_matrix_page,
    build_round_predictions_page,
    build_similarity_matrix_page,
)


def _norm(path: str) -> str:
    """Normalize a path to the current OS format."""
    return os.path.normpath(path)


# ------------------------------------------------------------------
# Shared CSS block (theme-driven) — now loaded from external styles/base.css
# ------------------------------------------------------------------

_CSS_BASE = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, sans-serif;
    background: var(--bg);
    color: var(--text);
    font-size: 16px;
    line-height: 1.5;
    -webkit-text-size-adjust: 100%;
}

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }

select:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

/* Hero banner */
.hero {
    background: var(--bg);
    padding: 1.5rem 1rem;
    text-align: center;
    color: var(--text);
    border-bottom: 1px solid var(--card-border);
}
.hero h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
.hero .subtitle { font-size: 0.9rem; opacity: 0.85; }
.hero .timestamp { font-size: 0.75rem; opacity: 0.65; margin-top: 0.5rem; }

/* Back navigation */
.back-nav {
    position: sticky;
    top: 0;
    z-index: 10;
    background: var(--card-bg);
    border-bottom: 1px solid var(--card-border);
    padding: 0.75rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.back-nav a {
    color: var(--accent);
    font-size: 1rem;
    font-weight: 600;
    min-height: 44px;
    display: flex;
    align-items: center;
}

/* Cards */
.card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 1rem;
    margin: 0.75rem;
}
.card-title {
    font-size: 0.85rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
}

/* Stat cards row */
.stat-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
    padding: 0.75rem;
}
.stat-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 10px;
    padding: 0.75rem;
    text-align: center;
}
.stat-card .value {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--accent);
}
.stat-card .label {
    font-size: 0.7rem;
    color: var(--text-muted);
    text-transform: uppercase;
    margin-top: 0.25rem;
}

/* Score display */
.score-card {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 1rem;
    padding: 1.5rem 1rem;
    font-size: 1.75rem;
    font-weight: 700;
}
.score-card .team { flex: 1; text-align: center; font-size: 1rem; }
.score-card .score {
    color: var(--accent);
    font-size: 2rem;
    white-space: nowrap;
}
.score-card .vs { color: var(--text-muted); font-size: 0.9rem; }

/* Badge */
.badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-success { background: var(--success); color: #fff; }
.badge-warning { background: var(--warning); color: var(--text-inverse); }
.badge-danger { background: var(--danger); color: #fff; }

/* CSS bar charts */
.bar-chart { padding: 0.5rem 0; }
.bar-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.4rem;
    font-size: 0.85rem;
}
.bar-label { width: 100px; color: var(--text-muted); text-align: right; font-size: 0.7rem; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar-track {
    flex: 1;
    height: 20px;
    background: var(--card-border);
    border-radius: 4px;
    overflow: hidden;
}
.bar-fill {
    height: 100%;
    background: var(--primary);
    border-radius: 4px;
    transition: width 0.3s;
}
.bar-pct { min-width: 40px; text-align: right; color: var(--text-muted); }
.bar-row { cursor: pointer; }
.bar-players { display: none; width: 100%; padding: 0.3rem 0 0 100px; font-size: 0.75rem; color: var(--text-muted); }
.bar-row.expanded .bar-players { display: flex; flex-direction: column; gap: 0.15rem; }
.bar-player { padding: 0.1rem 0; }
.bar-player::before { content: "\2022 "; }

/* Player prediction rows */
.pred-row {
    display: flex;
    align-items: center;
    padding: 0.75rem;
    border-bottom: 1px solid var(--card-border);
    gap: 0.75rem;
}
.pred-row:last-child { border-bottom: none; }
.pred-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--primary);
    color: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.85rem;
    flex-shrink: 0;
}
.pred-info { flex: 1; min-width: 0; }
.pred-name { font-weight: 600; font-size: 0.9rem; }
.pred-date { font-weight: 400; font-size: 0.75rem; color: var(--text-muted); display: inline-block; }
.pred-detail { font-size: 0.8rem; color: var(--text-muted); }
.pred-points {
    font-weight: 700;
    font-size: 1rem;
    flex-shrink: 0;
    min-width: 50px;
    text-align: right;
}

/* Ranking table */
.rank-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
}
.rank-table th {
    background: var(--card-border);
    color: var(--text-muted);
    padding: 0.5rem 0.75rem;
    text-align: left;
    font-size: 0.75rem;
    text-transform: uppercase;
    position: sticky;
    top: 0;
    z-index: 2;
}
.rank-table td {
    padding: 0.6rem 0.75rem;
    border-bottom: 1px solid var(--card-border);
}
.rank-table tr:nth-child(even) { background: var(--zebra-stripe); }
.rank-table .rank-1 td { background: var(--accent-highlight); }
.rank-table .rank-2 td { background: var(--silver-highlight); }
.rank-table .rank-3 td { background: var(--bronze-highlight); }

/* Section spacing */
.section { margin: 1rem 0; }
.section-title {
    font-size: 1rem;
    font-weight: 700;
    padding: 0 0.75rem;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Accordion / details */
details {
    margin: 0.5rem 0.75rem;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 8px;
    overflow: hidden;
}
summary {
    padding: 1rem;
    cursor: pointer;
    font-weight: 600;
    min-height: 44px;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    user-select: none;
}
summary:hover { background: var(--hover-overlay); }
details[open] summary { border-bottom: 1px solid var(--card-border); }
details .content { padding: 0.75rem 1rem; }

/* Striker badge */
.striker-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--card-bg);
    border: 1px solid var(--accent);
    border-radius: 8px;
    padding: 0.5rem 1rem;
    margin: 0.75rem;
    font-size: 0.9rem;
}
.striker-badge .icon { font-size: 1.2rem; }

/* Score pill */
.score-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.3rem 0.8rem;
    border-radius: 999px;
    font-weight: 800;
    font-size: 1.1rem;
    white-space: nowrap;
}

/* Utility */
.text-center { text-align: center; }
.text-muted { color: var(--text-muted); }
.mt-0 { margin-top: 0; }
.mb-1 { margin-bottom: 0.5rem; }
.grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem; }
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; }
.stat-card-sm { padding: 0.5rem; }
.stat-card-sm .value { font-size: 1.1rem; }
.stat-card-sm .label { font-size: 0.6rem; }
.card-link {
    display: block;
    margin: 0 0.75rem;
    text-align: center;
    font-weight: 600;
}
.card-link.accent { border-color: var(--accent); }
.arena-select {
    width: 100%;
    padding: 0.5rem;
    background: var(--card-bg);
    color: var(--text);
    border: 1px solid var(--card-border);
    border-radius: 6px;
    font-size: 0.9rem;
}
.arena-select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.arena-label { font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.25rem; }
.compare-date { color: var(--text-muted); margin-bottom: 0.15rem; }
.compare-row { margin-bottom: 0.4rem; font-size: 0.8rem; }
.compare-label-p1 { min-width: 30px; color: var(--accent); font-size: 0.75rem; }
.compare-label-p2 { min-width: 30px; color: var(--text-muted); font-size: 0.75rem; }
.compare-bar-track { height: 12px; }
.compare-bar-fill-accent { background: var(--accent); }
.compare-bar-fill-voce { background: var(--voce); }
.compare-bar-fill-bolao { background: var(--bolao); }
.compare-val { min-width: 25px; text-align: right; font-size: 0.75rem; }
.compare-diff { text-align: right; font-size: 0.7rem; font-weight: 700; }

/* Heatmap */
.heat-container { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.heat-row { display: flex; gap: 0; margin-bottom: 2px; }
.heat-label { width: 80px; min-width: 80px; font-size: 0.7rem; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 4px; line-height: 28px; text-align: right; }
.heat-cells { display: flex; gap: 2px; }
.heat-cell { width: 28px; min-width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 0.6rem; font-weight: 600; color: var(--text); border-radius: 3px; flex-shrink: 0; }
.heat-cell-header { width: 28px; min-width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 0.55rem; font-weight: 600; color: var(--text-muted); flex-shrink: 0; border-radius: 3px; }
.heat-total-label { width: 80px; min-width: 80px; font-size: 0.65rem; color: var(--text-muted); white-space: nowrap; padding-right: 4px; line-height: 28px; text-align: right; border-top: 1px solid var(--card-border); }
/* Larger cells for match-page heatmap */
.heat-cell-lg { width: 34px; min-width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 600; color: var(--text); border-radius: 4px; flex-shrink: 0; }
.heatmap-match { display:flex; flex-direction:column; gap:6px; }
.heatmap-top { display:flex; align-items:center; justify-content:center; gap:6px; font-weight:600; font-size:0.9rem; padding:6px 0 2px 0; }
.heatmap-top img { width:28px; height:28px; }
.heatmap-body { display:flex; gap:10px; }
.heatmap-away { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:4px; font-weight:600; font-size:0.8rem; min-width:56px; text-align:center; }
.heatmap-away img { width:28px; height:28px; }
.heatmap-grid { flex:1; min-width:0; }
.heat-cell-lg { cursor: pointer; }
.heat-legend { font-size: 0.65rem; color: var(--text-muted); text-align: center; padding: 0.25rem 0; }
.heat-popup {
    display: none; position: fixed; z-index: 999;
    background: var(--card-bg); border: 1px solid var(--card-border);
    border-radius: 8px; padding: 0.6rem 0.8rem;
    font-size: 0.75rem; color: var(--text);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    max-width: 200px;
}
.heat-popup.show { display: block; }

/* Bottom navigation bar */
.bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 100;
    background: var(--card-bg);
    border-top: 1px solid var(--card-border);
    display: flex;
    justify-content: space-around;
    align-items: center;
    padding: 0.25rem 0;
    padding-bottom: max(0.25rem, env(safe-area-inset-bottom));
    box-shadow: 0 -2px 10px var(--shadow-color);
}
.bottom-nav a {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.1rem;
    padding: 0.3rem 0.5rem;
    font-size: 0.65rem;
    color: var(--text-muted);
    text-decoration: none;
    min-height: 44px;
    justify-content: center;
    border-radius: 8px;
    transition: background 0.2s;
    -webkit-tap-highlight-color: transparent;
}
.bottom-nav a:active { background: var(--hover-overlay); }
.bottom-nav a .nav-icon { font-size: 1.2rem; line-height: 1; }
.bottom-nav a.active { color: var(--accent); }
body { padding-bottom: 70px; }

/* Zebra cards */
.zebra-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 1rem;
    margin: 0.75rem;
}
.zebra-card.upset { border-color: var(--danger); border-width: 2px; }
.zebra-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}
.zebra-badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
}
.zebra-badge.upset { background: var(--danger); color: #fff; }
.zebra-badge.favorite { background: var(--success); color: #fff; }
.zebra-matchup { font-size: 1rem; font-weight: 700; margin-bottom: 0.25rem; }
.zebra-detail { font-size: 0.8rem; color: var(--text-muted); line-height: 1.6; }
.zebra-players { margin-top: 0.5rem; font-size: 0.8rem; }
.zebra-players .tag {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    margin: 0.1rem;
    background: var(--accent-highlight);
    border-radius: 999px;
    font-size: 0.7rem;
    color: var(--accent);
}

/* Momentum / streak styles */
.streak-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.6rem 0.75rem;
    border-bottom: 1px solid var(--card-border);
    font-size: 0.85rem;
}
.streak-row:last-child { border-bottom: none; }
.streak-name { flex: 1; font-weight: 600; }
.streak-bar-mini {
    height: 6px;
    border-radius: 3px;
    flex: 0 0 80px;
    background: var(--card-border);
    overflow: hidden;
}
.streak-bar-mini .fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.3s;
}
.streak-bar-mini .fill.hot { background: var(--success); }
.streak-bar-mini .fill.cold { background: var(--danger); }
.streak-val { min-width: 30px; text-align: right; font-size: 0.75rem; font-weight: 700; }

/* Profile badge */
.profile-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.8rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
    border: 1px solid var(--accent);
    background: var(--accent-highlight);
}

/* Trend indicators */
.trend-up { color: var(--success); }
.trend-down { color: var(--danger); }
.trend-flat { color: var(--text-muted); }

/* Hot streak indicator */
.hot-streak {
    display: inline-block;
    font-size: 0.9rem;
    animation: pulse-fire 1.5s ease-in-out infinite;
}
@keyframes pulse-fire {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.2); }
}

/* Mini stat columns */
.mini-stat { text-align: center; padding: 0.3rem; }
.mini-stat .val { font-size: 1.2rem; font-weight: 700; color: var(--accent); }
.mini-stat .lbl { font-size: 0.6rem; color: var(--text-muted); text-transform: uppercase; }

/* Team logos */
.team-logo { width: 28px; height: 28px; object-fit: contain; vertical-align: middle; border-radius: 4px; }
.team-logo-sm { width: 24px; height: 24px; object-fit: contain; vertical-align: middle; border-radius: 3px; }
.team-logo-lg { width: 48px; height: 48px; object-fit: contain; vertical-align: middle; border-radius: 6px; }

/* Responsive */
@media (max-width: 359px) {
    .hero h1 { font-size: 1.25rem; }
    .hero .subtitle { font-size: 0.8rem; }
    .bottom-nav a { font-size: 0.55rem; }
    .bottom-nav a .nav-icon { font-size: 1rem; }
}
@media (min-width: 768px) {
    body { max-width: 800px; margin: 0 auto; }
    .stat-row { grid-template-columns: repeat(3, 1fr); }
}
"""


def _bottom_nav_html(active: str = "", prefix: str = "") -> str:
    """Build the fixed bottom navigation bar. 'active' should match a href."""
    items = [
        ("index.html", "\U0001f3e0", "In\u00edcio"),
        ("arena.html", "\u2694\ufe0f", "Arena"),
        ("zebras.html", "\U0001f993", "Zebras"),
        ("palpites.html", "\U0001f4cb", "Palpites"),
        ("bolao_xray.html", "\U0001f50d", "Raio-X"),
    ]
    links = ""
    for href, icon, label in items:
        cls = ' class="active"' if active == href else ""
        links += f'<a href="{prefix}{href}"{cls}><span class="nav-icon">{icon}</span>{label}</a>\n'
    return f'<nav class="bottom-nav">{links}</nav>'


def _page_frame(config: ChampionshipConfig, title: str, body: str, back_link: str = "", active_nav: str = "") -> str:
    """Wrap body content in the standard HTML page frame."""
    back_html = ""
    nav_prefix = ""
    if back_link:
        back_html = f'<div class="back-nav"><a href="{back_link}">\u2190 Voltar</a></div>'
        idx = back_link.rfind("index.html")
        if idx >= 0:
            nav_prefix = back_link[:idx]

    tz = pytz.timezone(config.timezone)
    now_str = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
    {config.theme.to_css_vars()}
    {_CSS_BASE}
    </style>
</head>
<body>
{back_html}
{body}
<div style="text-align:center;padding:2rem 1rem 5rem;color:var(--text-muted);font-size:0.75rem;">
    atualizado às {now_str}
</div>
{_bottom_nav_html(active_nav, nav_prefix)}
</body>
</html>"""


def _save(filepath: str, content: str) -> None:
    """Write an HTML file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def _initials(name: str) -> str:
    """Get initials from a name (max 2 chars)."""
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


def _avatar_html(name: str) -> str:
    """Generate an avatar circle with initials."""
    return f'<div class="pred-avatar">{_initials(name)}</div>'


def _max_points_per_game(config: ChampionshipConfig) -> int:
    """Return the maximum possible points for a single game."""
    if not config.scoring_rules:
        return 12
    return max(r.points for r in config.scoring_rules)


from src.core.logo_fetcher import _team_logo_tag


# ------------------------------------------------------------------
# Per-player page
# ------------------------------------------------------------------

def _build_boleiro(config: ChampionshipConfig, boleiro: str) -> str:
    """Build a per-player HTML report."""
    if os.path.exists(config.gold_valid_path()):
        df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
        if df_valid.empty:
            df_valid = pd.read_csv(config.gold_all_path(), sep=",")
    else:
        df_valid = pd.read_csv(config.gold_all_path(), sep=",")
    df_striker = pd.read_csv(config.playoff_strikers_path(), sep=",")
    max_pts = _max_points_per_game(config)

    df_bol = df_valid.loc[df_valid["who"] == boleiro].copy()

    # --- Load playoff predictions for this player ---
    playoff_parts = []
    for pr in (config.playoff_rounds or []):
        phase_valid_path = config.gold_playoff_valid_path(pr.key)
        if os.path.exists(phase_valid_path):
            df_phase = pd.read_csv(phase_valid_path, sep=",")
            df_phase_player = df_phase[df_phase["who"] == boleiro]
            if not df_phase_player.empty:
                playoff_parts.append(df_phase_player)

    if playoff_parts:
        df_playoff = pd.concat(playoff_parts, ignore_index=True)
        df_bol = pd.concat([df_bol, df_playoff], ignore_index=True)

    df_bol = df_bol.sort_values(["date", "hour"], ascending=True)
    df_bol["pontos_acumulados"] = df_bol["pontos"].cumsum()

    # Load bonus points (playoff team picks) — not included in df_bol/pontos
    bonus_total = 0
    bonus_by_phase: dict[str, int] = {}
    bonus_csv = _norm(os.path.join(config._au_first_round(), "playoffs_scored.csv"))
    if os.path.exists(bonus_csv):
        df_bonus_all = pd.read_csv(bonus_csv, sep=",")
        df_bonus_player = df_bonus_all[df_bonus_all["boleiro"] == boleiro]
        if not df_bonus_player.empty:
            bonus_total = int(df_bonus_player["points"].sum())
            for _, row in df_bonus_player.iterrows():
                ph = str(row["phase"])
                bonus_by_phase[ph] = bonus_by_phase.get(ph, 0) + int(row["points"])

    total_pts = int(df_bol["pontos"].sum())
    avg_per_game = round(df_bol["pontos"].mean(), 1) if len(df_bol) > 0 else 0
    num_games = len(df_bol)
    num_days = df_bol["date"].nunique()
    avg_per_day = round(total_pts / num_days, 1) if num_days > 0 else 0

    # Striker
    striker_name = ""
    df_st = df_striker.loc[df_striker["boleiro"] == boleiro]
    if not df_st.empty:
        striker_name = str(df_st.iloc[0]["striker"])

    # Points by date with max possible context
    df_by_date = df_bol.groupby("date", as_index=False)["pontos"].sum()
    df_by_date["date_dt"] = pd.to_datetime(df_by_date["date"])
    df_by_date["date_str"] = df_by_date["date_dt"].dt.strftime("%d/%m")

    # Calculate max possible per day for this player
    df_games_count = df_bol.groupby("date").size().reset_index(name="num_games")
    df_games_count["max_possible"] = df_games_count["num_games"] * max_pts
    df_by_date = df_by_date.merge(df_games_count[["date", "max_possible"]], on="date")

    timeline_bars = ""
    if not df_by_date.empty:
        max_date_pts = df_by_date["pontos"].max()
        if max_date_pts > 0:
            for _, row in df_by_date.iterrows():
                pts = int(row["pontos"])
                max_p = int(row["max_possible"])
                pct_of_max = round(pts / max_p * 100) if max_p > 0 else 0
                pct_bar = pct_of_max
                timeline_bars += (
                    f'<div class="bar-row">'
                    f'<span class="bar-label">{row["date_str"]}</span>'
                    f'<div class="bar-track"><div class="bar-fill" style="width:{pct_bar}%"></div></div>'
                    f'<span class="bar-pct">{pts}/{max_p} ({pct_of_max}%)</span>'
                    f'</div>\n'
                )

    # Player pts/day vs bolão avg/day (raw, not moving average)
    df_all_by_date = df_valid.groupby("date", as_index=False).agg({"pontos": ["sum", "count"]})
    df_all_by_date.columns = ["date", "total_pts", "num_players"]
    df_all_by_date["bolao_avg"] = (df_all_by_date["total_pts"] / df_all_by_date["num_players"]).round(1)
    df_all_by_date["date_str"] = pd.to_datetime(df_all_by_date["date"]).dt.strftime("%d/%m")

    df_player_by_date = df_bol.groupby("date", as_index=False)["pontos"].sum()
    df_player_by_date.columns = ["date", "player_pts"]

    df_compare = df_all_by_date[["date", "date_str", "bolao_avg"]].merge(
        df_player_by_date[["date", "player_pts"]], on="date", how="left"
    )
    df_compare["player_pts"] = df_compare["player_pts"].fillna(0)
    df_compare = df_compare.sort_values("date")

    compare_bars = ""
    if not df_compare.empty:
        max_val = max(df_compare["player_pts"].max(), df_compare["bolao_avg"].max())
        if max_val > 0:
            for _, row in df_compare.iterrows():
                p_pts = row["player_pts"]
                b_avg = row["bolao_avg"]
                p_pct = round(p_pts / max_val * 100)
                b_pct = round(b_avg / max_val * 100)
                diff = p_pts - b_avg
                diff_color = "var(--voce)" if diff >= 0 else "var(--bolao)"
                diff_icon = "\u25b2" if diff >= 0 else "\u25bc"
                compare_bars += (
                    f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;font-size:0.8rem;">'
                    f'<span style="min-width:40px;color:var(--text-muted)">{row["date_str"]}</span>'
                    f'<div style="flex:1;">'
                    f'<div style="display:flex;align-items:center;gap:0.25rem;">'
                    f'<span style="min-width:40px;color:var(--voce)">Voce</span>'
                    f'<div class="bar-track" style="height:14px;"><div class="bar-fill" style="width:{p_pct}%;background:var(--voce)"></div></div>'
                    f'<span style="min-width:30px;text-align:right">{p_pts}</span>'
                    f'</div>'
                    f'<div style="display:flex;align-items:center;gap:0.25rem;">'
                    f'<span style="min-width:40px;color:var(--bolao)">Bolao</span>'
                    f'<div class="bar-track" style="height:14px;"><div class="bar-fill" style="width:{b_pct}%;background:var(--bolao)"></div></div>'
                    f'<span style="min-width:30px;text-align:right">{b_avg}</span>'
                    f'</div>'
                    f'</div>'
                    f'<span style="color:{diff_color};min-width:40px;text-align:right;font-weight:700">{diff_icon}{abs(diff):.1f}</span>'
                    f'</div>\n'
                )

    boleiro_dir = _norm(os.path.join(config.reports_dir, "html", "boleiros"))

    # --- Detect pending matches (past but no result) for this player ---
    n_pending = 0
    pending_rows = ""
    all_path = config.gold_all_path()
    if os.path.exists(all_path):
        df_all = pd.read_csv(all_path, sep=",")
        df_player_all = df_all[df_all["who"] == boleiro].copy()
        if not df_player_all.empty:
            tz = pytz.timezone(config.timezone)
            today_dt = datetime.now(tz).date()
            df_player_all["date_dt"] = pd.to_datetime(df_player_all["date"], errors="coerce")
            df_pending = df_player_all[
                (df_player_all.get("valido", 0) == 0)
                & (df_player_all["date_dt"].dt.date < today_dt)
            ].drop_duplicates(subset=["match"])
            n_pending = len(df_pending)
            if n_pending:
                rev_map = {v: k for k, v in config.team_name_mapping.items()}
                for _, row in df_pending.sort_values(["date", "hour"], ascending=False).iterrows():
                    date_str = pd.to_datetime(row["date"]).strftime("%d/%m") + (f" {row['hour']}" if pd.notna(row.get("hour")) and str(row.get("hour", "")).strip() else "")
                    home_en = rev_map.get(row["home_team"], row["home_team"])
                    away_en = rev_map.get(row["away_team"], row["away_team"])
                    home_logo = _team_logo_tag(home_en, config, cls="team-logo-sm", start=boleiro_dir)
                    away_logo = _team_logo_tag(away_en, config, cls="team-logo-sm", start=boleiro_dir)
                    match_slug = str(row.get("match", ""))
                    hour_p = str(row.get("hour", ""))
                    phase_v = str(row.get("phase", "")) if row.get("phase") else config.group_phase_label
                    game_href = f"../jogos/{phase_v}/{row['date'].strip()}_{hour_p}_{match_slug}.html"
                    pending_rows += (
                        f'<div class="pred-row">'
                        f'<div class="pred-info">'
                        f'<div class="pred-name"><a href="{game_href}" style="color:var(--text);text-decoration:none;">{home_logo}{row["home_team"]} vs {away_logo}{row["away_team"]}</a> <span class="pred-date">{date_str}</span></div>'
                        f'<div class="pred-detail">Previsto: {row["resultado_bol_placar"]} | \u23f3 Aguardando resultado | <a href="{game_href}" style="color:var(--accent);">ver jogo</a></div>'
                        f'</div>'
                        f'<div class="score-pill" style="color:var(--warning);background:rgba(245,158,11,0.1);border:1px solid var(--warning)">+0 \u23f3</div>'
                        f'</div>\n'
                    )

    # Match history rows (newest first)
    playoff_emoji_map = {"segunda_fase": "\U0001f3c6", "oitavas": "\U0001f3c1", "quartas": "\U0001f525", "semi": "\U0001f3af", "terceiro_lugar": "\U0001f949", "final": "\U0001f3c6"}
    df_hist = df_bol.sort_values(["date", "hour"], ascending=False)

    def _format_real_placar(row: pd.Series) -> str:
        """Format the real scoreline, handling NaN gracefully."""
        rrp = row.get("resultado_real_placar", "")
        if pd.isna(rrp) or str(rrp).strip().lower() in ("nan", "", "none"):
            return f'{row["home_team"]} vs {row["away_team"]}'
        return f'{row["home_team"]} {rrp} {row["away_team"]}'

    # Pre-compute per-match ranking for all players (group + playoff)
    match_ranks: dict[str, dict[str, int]] = {}
    def _add_match_ranks(df: pd.DataFrame) -> None:
        if "match" not in df.columns:
            return
        for match_slug, grp in df[df["match"].notna()].groupby("match"):
            if not match_slug:
                continue
            ranked = grp.sort_values("pontos", ascending=False)
            rank_map: dict[str, int] = {}
            current_rank = 1
            prev_pts = None
            for i, (_, r) in enumerate(ranked.iterrows()):
                p = int(r["pontos"])
                if prev_pts is not None and p < prev_pts:
                    current_rank = i + 1
                rank_map[str(r["who"])] = current_rank
                prev_pts = p
            match_ranks[str(match_slug)] = rank_map
    _add_match_ranks(df_valid)
    for pr in (config.playoff_rounds or []):
        path = config.gold_playoff_valid_path(pr.key)
        if os.path.exists(path):
            _add_match_ranks(pd.read_csv(path, sep=","))

    def _build_history_rows(rows_df: pd.DataFrame) -> str:
        rev_map = {v: k for k, v in config.team_name_mapping.items()}
        out = ""
        for _, row in rows_df.iterrows():
            pts = int(row["pontos"])
            hour_str = str(row.get("hour", ""))
            date_str = pd.to_datetime(row["date"]).strftime("%d/%m") + (f" {hour_str}" if hour_str else "")
            criterio_emoji = config.scoring_emoji(row.get("criterio", ""))
            css_var, css_bg, css_border = config.scoring_css_var(row.get("criterio", ""))
            if css_var:
                pts_color = css_var
                pts_bg = css_bg
                pts_border = css_border
            else:
                hex_color = config.scoring_color(row.get("criterio", ""))
                if hex_color:
                    pts_color = hex_color
                    pts_bg = hex_color + "1a"
                    pts_border = hex_color + "40"
                else:
                    pts_color = "var(--text-muted)"
                    pts_bg = "transparent"
                    pts_border = "var(--card-border)"
            # Phase indicator for playoff matches
            phase_label = ""
            phase_val = row.get("phase", "")
            if phase_val and phase_val in playoff_emoji_map:
                phase_label = f"{playoff_emoji_map[phase_val]} {phase_val} | "
            home_en = rev_map.get(row["home_team"], row["home_team"])
            away_en = rev_map.get(row["away_team"], row["away_team"])
            home_logo = _team_logo_tag(home_en, config, cls="team-logo-sm", start=boleiro_dir)
            away_logo = _team_logo_tag(away_en, config, cls="team-logo-sm", start=boleiro_dir)
            # Game link
            match_slug = str(row.get("match", ""))
            phase_v = str(phase_val) if phase_val else config.group_phase_label
            game_href = f"../jogos/{phase_v}/{row['date']}_{hour_str}_{match_slug}.html"
            # Player rank for this match
            rank_str = ""
            if match_slug in match_ranks:
                player_rank = match_ranks[match_slug].get(boleiro)
                if player_rank is not None:
                    rank_str = f"{player_rank}\u00ba lugar | "
            out += (
                f'<div class="pred-row">'
                f'<div class="pred-info">'
                f'<div class="pred-name"><a href="{game_href}" style="color:var(--text);text-decoration:none;">{_format_real_placar(row)}</a> <span class="pred-date">{phase_label}{date_str}</span></div>'
            f'<div class="pred-detail">{home_logo} {row["resultado_bol_placar"]} {away_logo} | {criterio_emoji} {row["criterio"]} | {rank_str}<a href="{game_href}" style="color:var(--accent);">ver jogo</a></div>'
                f'</div>'
                f'<div class="score-pill" style="color:{pts_color};background:{pts_bg};border:1px solid {pts_border}">+{pts} {criterio_emoji}</div>'
                f'</div>\n'
            )
        return out

    tz = pytz.timezone(config.timezone)
    today = datetime.now(tz).date()
    df_by_date_dt = df_hist["date"].apply(lambda d: pd.to_datetime(d).date())
    df_hist_past = df_hist[df_by_date_dt < today]
    df_hist_future = df_hist[df_by_date_dt >= today].sort_values(["date", "hour"], ascending=True)

    # Exclude pending matches from past (they'll be shown in pending section)
    pending_slug_set = set()
    if n_pending:
        all_path_p = config.gold_all_path()
        if os.path.exists(all_path_p):
            df_all_p = pd.read_csv(all_path_p, sep=",")
            df_pending_p = df_all_p[
                (df_all_p["who"] == boleiro)
                & (df_all_p.get("valido", 0) == 0)
            ]
            pending_slug_set = set(df_pending_p["match"].unique())
        if pending_slug_set:
            df_hist_past = df_hist_past[~df_hist_past["match"].isin(pending_slug_set)]

    n_past = len(df_hist_past)
    n_future = len(df_hist_future)

    history_rows_past = _build_history_rows(df_hist_past) if n_past else ""
    history_rows_future = _build_history_rows(df_hist_future) if n_future else '<div style="color:var(--text-muted);font-size:0.85rem;padding:0.3rem 0;">Nenhum jogo futuro.</div>'

    # Build stat rows: add pending stat if any
    pending_stat_html = ""
    if n_pending > 0:
        pending_stat_html = f'<div class="stat-card"><div class="value" style="color:var(--warning);font-size:1.2rem;">\u23f3 {n_pending}</div><div class="label">Aguardando</div></div>'

    grand_total = total_pts + bonus_total
    body = f"""
<div class="hero">
    <h1>\U0001f464 {boleiro}</h1>
    <div class="subtitle">{config.report_title}</div>
</div>

<div class="stat-row" style="grid-template-columns:repeat(2,1fr);">
    <div class="stat-card">
        <div class="value" style="color:var(--voce)">{total_pts}</div>
        <div class="label">Total Jogos</div>
    </div>
    <div class="stat-card">
        <div class="value" style="color:var(--accent)">{grand_total}</div>
        <div class="label">Total c/ B\u00f4nus</div>
    </div>
</div>
<div class="stat-row" style="grid-template-columns:repeat(2,1fr);margin-top:0;">
    <div class="stat-card">
        <div class="value" style="color:var(--voce)">{avg_per_game}</div>
        <div class="label">Media/Jogo ({num_games})</div>
    </div>
    <div class="stat-card">
        <div class="value" style="color:var(--voce)">{round(total_pts / (num_games * max_pts) * 100, 1) if num_games > 0 else 0}%</div>
        <div class="label">Aproveitamento</div>
    </div>
    {pending_stat_html}
</div>
"""

    # --- Scoring distribution per criteria (bar chart) ---
    rule_order = config.scoring_rule_names()
    rule_map = config.scoring_dict()
    n_preds = len(df_bol)
    criteria_counts = df_bol["criterio"].value_counts()
    largest_cnt = max((int(criteria_counts.get(t, 0)) for t in rule_order), default=1)
    dist_rows = ""
    for t in rule_order:
        cnt = int(criteria_counts.get(t, 0))
        pts_per = rule_map.get(t, 0)
        pct = round(cnt / n_preds * 100, 1) if n_preds else 0
        bar_w = max(cnt / largest_cnt * 100, 1)
        name_part = t.split("-", 1)[1] if "-" in t else t
        label = f"{name_part} (+{pts_per}p)" if pts_per > 0 else name_part
        color = config.scoring_color(t)
        emoji = config.scoring_emoji(t)
        dist_rows += f"""
        <tr>
            <td style="padding:0.3rem 0.5rem;"><span style="color:{color};font-weight:700;">{emoji}</span> {label}</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;font-weight:600;">{cnt}</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;color:var(--text-muted);">{pct}%</td>
            <td style="padding:0.3rem 0.5rem;width:30%;"><div class="bar-track"><div class="bar-fill" style="width:{bar_w:.0f}%;background:{color};height:10px;"></div></div></td>
        </tr>"""
    body += f"""
<div class="section">
    <div class="section-title">\U0001f3af Distribui\u00e7\u00e3o de Acertos ({n_preds})</div>
    <div class="card">
        <table style="width:100%;border-collapse:collapse;">
            {dist_rows}
        </table>
    </div>
</div>
"""

    # ------------------------------------------------------------------
    # Bonus teams for knockout phases — at top, colored by result, scored
    # ------------------------------------------------------------------
    bonus_html = ""
    bonus_path = config.bronze_bonus_path(boleiro)
    if os.path.exists(bonus_path):
        df_bonus = pd.read_csv(bonus_path, sep=",")
        if not df_bonus.empty and os.path.exists(config.games_file):
            df_games = pd.read_csv(config.games_file, sep=",")
            df_games["round"] = df_games["round"].astype(str).str.strip()
            playoff_keys = [pr.key for pr in (config.playoff_rounds or [])]

            # Determine today's date in the configured timezone
            tz = pytz.timezone(config.timezone)
            today = datetime.now(tz).date()

            # For each phase: find latest match date and compute winners
            phase_latest_date = {}  # phase -> latest date
            advancing = {}           # phase -> list of teams that advanced
            for pk in playoff_keys:
                phase_matches = df_games[df_games["round"] == pk]
                winners = []
                dates = []
                for _, row in phase_matches.iterrows():
                    raw_date = str(row.get("date", ""))
                    date_part = raw_date[:10] if " " in raw_date else raw_date
                    try:
                        d = pd.to_datetime(date_part).date()
                        dates.append(d)
                    except (ValueError, TypeError):
                        pass
                    hg = float(row["home_goals"]) if pd.notna(row.get("home_goals")) else None
                    ag = float(row["away_goals"]) if pd.notna(row.get("away_goals")) else None
                    if hg is not None and ag is not None:
                        if hg > ag:
                            winners.append(str(row["home_team"]))
                        elif ag > hg:
                            winners.append(str(row["away_team"]))
                        else:
                            hp = row.get("home_pen", "")
                            ap = row.get("away_pen", "")
                            try:
                                hp_v = float(hp) if pd.notna(hp) and str(hp).strip() else None
                                ap_v = float(ap) if pd.notna(ap) and str(ap).strip() else None
                            except (ValueError, TypeError):
                                hp_v = ap_v = None
                            if hp_v is not None and ap_v is not None:
                                if hp_v > ap_v:
                                    winners.append(str(row["home_team"]))
                                elif ap_v > hp_v:
                                    winners.append(str(row["away_team"]))
                            elif hp_v is not None:
                                winners.append(str(row["home_team"]))
                            elif ap_v is not None:
                                winners.append(str(row["away_team"]))
                advancing[pk] = winners
                phase_latest_date[pk] = max(dates) if dates else None

            phase_order = [pr.key for pr in (config.playoff_rounds or [])]
            phase_label_map = {pr.key: pr.name for pr in (config.playoff_rounds or [])}
            phase_emoji_map = {
                "segunda_fase": "\U0001f3c6",
                "oitavas": "\U0001f3c1",
                "quartas": "\U0001f525",
                "semi": "\U0001f3af",
                "terceiro_lugar": "\U0001f949",
                "final": "\U0001f3c6",
            }
            playoff_scoring = getattr(config, "playoff_scoring", {})

            df_bonus["phase_order"] = df_bonus["phase"].map(
                {k: i for i, k in enumerate(phase_order)}
            ).fillna(99)
            df_bonus = df_bonus.sort_values(["phase_order", "team"])

            total_bonus_pts = 0
            phase_blocks = ""
            champion_team = ""
            # Exclude 'campeao' from the general phase blocks loop to handle it separately
            for phase_key, group in df_bonus[df_bonus["phase"] != "campeao"].groupby("phase", sort=False):
                label = phase_label_map.get(phase_key, phase_key)
                emoji = phase_emoji_map.get(phase_key, "\u26bd")
                pts_per_correct = playoff_scoring.get(phase_key, 0)
                advancing_teams = advancing.get(phase_key, [])

                # Determine if this phase is checkable (all matches already played)
                latest = phase_latest_date.get(phase_key)
                checkable = latest is not None and today >= latest

                phase_pts = 0
                teams_list = ""
                for _, row in group.iterrows():
                    team = row["team"]
                    # Always compute points from games.csv regardless of checkable
                    passed = team in advancing_teams
                    if passed:
                        phase_pts += pts_per_correct

                    if not checkable:
                        # Not yet time — yellow
                        bg = "rgba(234,179,8,0.15)"
                        border = "var(--warning)"
                        color = "var(--warning)"
                    else:
                        bg = "rgba(34,197,94,0.15)" if passed else "rgba(239,68,68,0.15)"
                        border = "var(--success)" if passed else "var(--danger)"
                        color = "var(--success)" if passed else "var(--danger)"
                    teams_list += (
                        f'<span style="display:inline-block;padding:0.2rem 0.6rem;margin:0.15rem;'
                        f'background:{bg};border:1px solid {border};border-radius:999px;'
                        f'font-size:0.75rem;color:{color};">{team}</span>'
                    )

                total_bonus_pts += phase_pts
                if checkable:
                    pts_label = f'<span style="color:var(--accent);font-weight:700;">+{phase_pts}</span>'
                else:
                    pts_label = f'<span style="color:var(--warning);font-weight:700;">\u23f3 +{phase_pts}</span>'
                phase_blocks += (
                    f'<div style="margin-bottom:0.5rem;">'
                    f'<div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);margin-bottom:0.3rem;">'
                    f'{emoji} {label} {pts_label}</div>'
                    f'<div>{teams_list}</div>'
                    f'</div>\n'
                )

            # Champion block is separate and should be shown if available, regardless of other phases
            champion_row = df_bonus[df_bonus["phase"] == "campeao"]
            champion_team = champion_row.iloc[0]["team"] if not champion_row.empty else ""
            champion_block = (
                f'<div style="margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid var(--card-border);">'
                f'<div style="font-size:0.8rem;font-weight:600;color:var(--accent);margin-bottom:0.3rem;">'
                f'\U0001f3c6 Campe\u00e3o</div>'
                f'<div>{champion_team}</div>'
                f'</div>\n'
            ) if champion_team else ""

            legend = ""
            total_label = ""
            if phase_blocks:
                total_label = f'<span style="color:var(--accent);margin-left:0.5rem;font-weight:700;">+{total_bonus_pts}</span>'
                legend = (
                    '<div style="font-size:0.7rem;color:var(--text-muted);margin-bottom:0.5rem;'
                    'display:flex;gap:0.75rem;flex-wrap:wrap;">'
                    '<span>\U0001f7e1 fase n\u00e3o iniciada</span>'
                    '<span style="color:var(--success);">\u25cf time avan\u00e7ou</span>'
                    '<span style="color:var(--danger);">\u25cf time eliminado</span>'
                    '</div>'
                )

            bonus_html = ""
            if phase_blocks or champion_block:
                bonus_html = (
                    f'<details class="section" open>'
                    f'<summary style="font-size:1rem;font-weight:700;padding:0 0.75rem;margin-bottom:0.5rem;display:flex;align-items:center;gap:0.5rem;cursor:pointer;min-height:44px;">'
                    f'\U0001f3c6 Times Bonus {total_label}</summary>'
                    f'<div class="card">{legend}{phase_blocks}{champion_block}</div>'
                    f'</details>\n'
                )

            # Ensure champion_team is available for the top badges later in the function
            # Since champion_team is defined in this loop, we need to make sure it's accessible
            # The variable champion_team is already in the current scope.

    # --- Build top-of-page: striker + champion + bonus + timeline + compare ---
    top_badges = ""
    if striker_name:
        top_badges += f'<div class="striker-badge"><span class="icon">\U0001f3af</span> Artilheiro: <strong>{striker_name}</strong></div>\n'
    if champion_team:
        top_badges += f'<div class="striker-badge"><span class="icon">\U0001f3c6</span> Campe\u00e3o: <strong>{champion_team}</strong></div>\n'
    body += top_badges

    if bonus_html:
        body += bonus_html

    # ------------------------------------------------------------------
    # Phase points table
    # ------------------------------------------------------------------
    phase_emoji_map = {
        "1afase": "\U0001f4ca",
        "segunda_fase": "\U0001f3c6",
        "oitavas": "\U0001f3c1",
        "quartas": "\U0001f525",
        "semi": "\U0001f3af",
        "terceiro_lugar": "\U0001f949",
        "final": "\U0001f3c6",
    }

    # Group stage: use round_by_round.csv which has per-round breakdown
    group_match_pts = 0
    rr_path = _norm(os.path.join(config._au_first_round(), "round_by_round.csv"))
    if os.path.exists(rr_path):
        df_rr = pd.read_csv(rr_path, sep=",")
        df_rr_player = df_rr[df_rr["boleiro"] == boleiro]
        if not df_rr_player.empty:
            group_match_pts = int(df_rr_player["points"].sum())
    else:
        # No round_by_round — check if this player has any gold group data
        group_path = config.gold_group_boleiro_path(boleiro)
        if os.path.exists(group_path):
            df_grp = pd.read_csv(group_path, sep=",")
            df_grp_player = df_grp[df_grp["who"] == boleiro] if "who" in df_grp.columns else df_grp
            if not df_grp_player.empty and "pontos" in df_grp_player.columns:
                group_match_pts = int(df_grp_player["pontos"].sum())

    phase_rows = ""
    phase_total_pts = 0
    # 1st phase (group stage)
    if group_match_pts > 0 or (total_pts > 0 and group_match_pts >= 0):
        phase_rows += (
            f'<tr><td>\U0001f4ca 1\u00aa Fase</td>'
            f'<td style="text-align:right;">+{group_match_pts}</td>'
            f'<td style="text-align:right;">-</td>'
            f'<td style="text-align:right;font-weight:600;color:var(--accent);">+{group_match_pts}</td></tr>\n'
        )
        phase_total_pts += group_match_pts

    # Playoff phases
    for pr in config.playoff_rounds or []:
        phase_key = pr.key
        phase_name = pr.name

        phase_valid_path = config.gold_playoff_valid_path(phase_key)
        phase_pts = 0
        if os.path.exists(phase_valid_path):
            df_pp = pd.read_csv(phase_valid_path, sep=",")
            df_pp_player = df_pp[df_pp["who"] == boleiro]
            if not df_pp_player.empty:
                phase_pts = int(df_pp_player["pontos"].sum())

        bns = bonus_by_phase.get(phase_key, 0)
        tot = phase_pts + bns
        if tot > 0 or phase_pts > 0 or bns > 0:
            phase_total_pts += tot
            emoji = phase_emoji_map.get(phase_key, "\u26bd")
            bonus_str = f'+{bns}' if bns else '-'
            phase_rows += (
                f'<tr><td>{emoji} {phase_name}</td>'
                f'<td style="text-align:right;">+{phase_pts}</td>'
                f'<td style="text-align:right;">{bonus_str}</td>'
                f'<td style="text-align:right;font-weight:600;color:var(--accent);">+{tot}</td></tr>\n'
            )

    if phase_rows:
        body += (
            f'<div class="section">'
            f'<div class="section-title">\U0001f4ca Pontos por Fase</div>'
            f'<div class="card" style="overflow-x:auto;">'
            f'<table style="width:100%;border-collapse:collapse;font-size:0.85rem;">'
            f'<thead><tr style="color:var(--text-muted);border-bottom:1px solid var(--card-border);">'
            f'<th style="text-align:left;padding:0.4rem;">Fase</th>'
            f'<th style="text-align:right;padding:0.4rem;">Jogos</th>'
            f'<th style="text-align:right;padding:0.4rem;">B\u00f4nus</th>'
            f'<th style="text-align:right;padding:0.4rem;">Total</th>'
            f'</tr></thead><tbody>'
            f'{phase_rows}'
            f'<tr style="border-top:2px solid var(--accent);font-weight:700;">'
            f'<td style="padding:0.4rem;">Total</td>'
            f'<td style="text-align:right;">+{total_pts}</td>'
            f'<td style="text-align:right;">+{bonus_total}</td>'
            f'<td style="text-align:right;color:var(--accent);">+{grand_total}</td></tr>'
            f'</tbody></table>'
            f'<div style="font-size:0.7rem;color:var(--text-muted);margin-top:0.5rem;">'
            f'Jogos = pontos dos palpites \u00b7 B\u00f4nus = pontos dos times escolhidos por fase'
            f'</div></div></div>\n'
        )

    if timeline_bars:
        body += f'<div class="card"><div class="card-title">Pontos por dia</div><div class="bar-chart">{timeline_bars}</div></div>\n'

    if compare_bars:
        body += f'<div class="card"><div class="card-title">Pontos por Dia — Voce vs Bolao</div><div style="padding:0.5rem 0;">{compare_bars}</div></div>\n'

    # ------------------------------------------------------------------
    # Radar chart data (5 axes: Points, Precision, Boldness, Zebras, Regularity)
    # ------------------------------------------------------------------
    gold_dir = config._au_first_round()
    max_possible_total = len(df_bol) * max_pts
    pts_pct = min(100, round(total_pts / max_possible_total * 100)) if max_possible_total else 0
    prec_pct = min(100, round(avg_per_game / max_pts * 100)) if max_pts else 0

    bold_path = _norm(os.path.join(gold_dir, "boldness_index.csv"))
    boldness_norm = 50
    boldness_score_val = 0.0
    if os.path.exists(bold_path):
        df_bold_tmp = pd.read_csv(bold_path, sep=",")
        df_bp = df_bold_tmp[df_bold_tmp["boleiro"] == boleiro]
        if not df_bp.empty:
            boldness_score_val = float(df_bp.iloc[0]["boldness_score"])
            boldness_norm = max(0, min(100, round(50 + boldness_score_val * 25)))

    upset_path = _norm(os.path.join(gold_dir, "upset_tracker.csv"))
    zebra_pct = 0
    if os.path.exists(upset_path):
        df_upset = pd.read_csv(upset_path, sep=",")
        upset_matches = df_upset[df_upset.get("is_upset", 0) == 1]
        total_upsets = len(upset_matches)
        player_upsets = 0
        for _, r in upset_matches.iterrows():
            pc = str(r.get("players_correct", ""))
            if boleiro in [p.strip() for p in pc.split("|")]:
                player_upsets += 1
        zebra_pct = round(player_upsets / total_upsets * 100) if total_upsets else 0

    cons_path = _norm(os.path.join(gold_dir, "consistency.csv"))
    reg_pct = 50
    if os.path.exists(cons_path):
        df_cons_tmp = pd.read_csv(cons_path, sep=",")
        df_cp = df_cons_tmp[df_cons_tmp["boleiro"] == boleiro]
        if not df_cp.empty and "running_avg_5" in df_cp.columns:
            avg_run = df_cp["running_avg_5"].mean()
            reg_pct = min(100, round(avg_run / max_pts * 100)) if max_pts else 50

    radar_data_json = json.dumps([
        {"label": "Pontua\u00e7\u00e3o", "value": pts_pct},
        {"label": "Precis\u00e3o", "value": prec_pct},
        {"label": "Ousadia", "value": boldness_norm},
        {"label": "Zebras", "value": zebra_pct},
        {"label": "Regularidade", "value": reg_pct},
    ])

    radar_css = """
.radar-wrap { position: relative; width: 220px; height: 220px; margin: 0 auto; }
.radar-wrap canvas { width: 100%; height: 100%; }
.radar-legend { display: flex; flex-wrap: wrap; gap: 0.25rem 0.75rem; margin-top: 0.5rem; font-size: 0.7rem; color: var(--text-muted); justify-content: center; }
.radar-legend span::before { content: '\\25CF'; margin-right: 0.25rem; }
"""

    radar_js = f"""
<script>
(function() {{
    var data = {radar_data_json};
    var canvas = document.getElementById('radar-canvas');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var W = canvas.width = canvas.offsetWidth || 220;
    var H = canvas.height = canvas.offsetHeight || 220;
    var cx = W / 2, cy = H / 2;
    var R = Math.min(W, H) / 2 - 35;
    var n = data.length;

    function getPt(i, r) {{
        var a = Math.PI / 2 - i * 2 * Math.PI / n;
        return {{ x: cx + r * Math.cos(a), y: cy - r * Math.sin(a) }};
    }}

    // Grid
    for (var lv = 1; lv <= 4; lv++) {{
        ctx.beginPath();
        for (var i = 0; i <= n; i++) {{
            var p = getPt(i % n, R * lv / 4);
            i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
        }}
        ctx.strokeStyle = 'rgba(128,128,128,0.15)';
        ctx.stroke();
    }}

    // Axes
    for (var i = 0; i < n; i++) {{
        var p = getPt(i, R);
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(p.x, p.y);
        ctx.strokeStyle = 'rgba(128,128,128,0.2)';
        ctx.stroke();
    }}

    // Data polygon
    ctx.beginPath();
    for (var i = 0; i <= n; i++) {{
        var r = R * data[i % n].value / 100;
        var p = getPt(i % n, r);
        i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
    }}
    ctx.fillStyle = 'rgba(99,102,241,0.15)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(99,102,241,0.7)';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Data points
    for (var i = 0; i < n; i++) {{
        var r = R * data[i].value / 100;
        var p = getPt(i, r);
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, 2 * Math.PI);
        ctx.fillStyle = '#6366f1';
        ctx.fill();
    }}

    // Labels
    ctx.fillStyle = 'var(--text)';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    for (var i = 0; i < n; i++) {{
        var p = getPt(i, R + 18);
        ctx.fillText(data[i].label, p.x, p.y + 4);
    }}
}})();
</script>
"""

    body += f"""
<style>{radar_css}</style>
<div class="section">
    <div class="section-title">\U0001f4ca Radar do Jogador</div>
    <div class="card" style="text-align:center;">
        <div class="radar-wrap"><canvas id="radar-canvas"></canvas></div>
        <div class="radar-legend">
            <span>Pontua\u00e7\u00e3o: {pts_pct}%</span>
            <span>Precis\u00e3o: {prec_pct}%</span>
            <span>Ousadia: {boldness_norm}%</span>
            <span>Zebras: {zebra_pct}%</span>
            <span>Regularidade: {reg_pct}%</span>
        </div>
        <div style="font-size:0.7rem;color:var(--text-muted);text-align:left;margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid var(--card-border);">
            <strong style="font-size:0.75rem;">Legenda:</strong><br>
            \u2022 <strong>Pontua\u00e7\u00e3o</strong>: % de pontos em rela\u00e7\u00e3o ao m\u00e1ximo poss\u00edvel<br>
            \u2022 <strong>Precis\u00e3o</strong>: m\u00e9dia de pontos por jogo / pontos m\u00e1ximos por jogo<br>
            \u2022 <strong>Ousadia</strong>: qu\u00e3o diferente suas apostas s\u00e3o da m\u00e9dia do bol\u00e3o<br>
            \u2022 <strong>Zebras</strong>: % das surpresas que voc\u00ea acertou<br>
            \u2022 <strong>Regularidade</strong>: consist\u00eancia dos seus palpites ao longo do tempo<br>
            <span style="display:block;margin-top:0.3rem;">(\u00cdndices de 0% a 100%)</span>
        </div>
    </div>
</div>
{radar_js}
"""

    # ------------------------------------------------------------------
    # Perfil do Jogador (advanced stats + badges from gold layer)
    # ------------------------------------------------------------------
    profile_html = ""
    _ph = lambda msg: f'<div style="color:var(--text-muted);font-size:0.85rem;padding:0.3rem 0;">\u23f3 {msg}</div>\n'

    # --- Compute badges for this player ---
    badges: list[str] = []

    # 1. Current streak badge (already have streak_len, streak_type from above)
    streak_html_inner = ""
    if os.path.exists(cons_path):
        df_cons2 = pd.read_csv(cons_path, sep=",")
        df_cp2 = df_cons2[df_cons2["boleiro"] == boleiro].sort_values("date")
        streak_len2 = 0
        streak_type2 = ""
        if not df_cp2.empty:
            for _, r in reversed(list(df_cp2.iterrows())):
                st = r.get("streak_type", "")
                if st == "hit":
                    if streak_type2 == "" or streak_type2 == "hit":
                        streak_type2 = "hit"
                        streak_len2 += 1
                    else:
                        break
                elif st == "miss":
                    if streak_type2 == "" or streak_type2 == "miss":
                        streak_type2 = "miss"
                        streak_len2 += 1
                    else:
                        break
                else:
                    break
        if streak_type2 == "hit" and streak_len2 >= 3:
            badges.append(f'<span class="profile-badge" style="border-color:var(--success);background:rgba(34,197,94,0.15);">\U0001f525 Embrazado ({streak_len2})</span>')
            streak_html_inner = f'<div style="margin-top:0.25rem;"><span class="profile-badge" style="border-color:var(--success);background:rgba(34,197,94,0.15);">\U0001f525 Sequ\u00eancia: {streak_len2} acertos</span></div>\n'
        elif streak_type2 == "miss":
            streak_html_inner = f'<div style="margin-top:0.25rem;"><span class="profile-badge" style="border-color:var(--danger);background:rgba(239,68,68,0.15);">\U0001f4a9 Sequ\u00eancia: {streak_len2} erros</span></div>\n'
    if not streak_html_inner:
        streak_html_inner = _ph("Sequ\u00eancia atual dispon\u00edvel ap\u00f3s os primeiros jogos.")

    # 2. Zebra hunter badge
    if os.path.exists(upset_path):
        df_upset2 = pd.read_csv(upset_path, sep=",")
        upset_only = df_upset2[df_upset2.get("is_upset", 0) == 1]
        zebra_counts: dict[str, int] = {}
        for _, r in upset_only.iterrows():
            pc = str(r.get("players_correct", ""))
            for p in [x.strip() for x in pc.split("|") if x.strip()]:
                zebra_counts[p] = zebra_counts.get(p, 0) + 1
        sorted_zebras = sorted(zebra_counts.items(), key=lambda x: -x[1])
        if len(sorted_zebras) >= 3 and boleiro in [z[0] for z in sorted_zebras[:3]]:
            badges.append(f'<span class="profile-badge" style="border-color:var(--danger);background:rgba(239,68,68,0.15);">\U0001f993 Ca\u00e7ador de Zebras</span>')

    # 3. Boldness badge
    if os.path.exists(bold_path):
        df_bold2 = pd.read_csv(bold_path, sep=",")
        df_bp2 = df_bold2[df_bold2["boleiro"] == boleiro]
        if not df_bp2.empty:
            bs = float(df_bp2.iloc[0]["boldness_score"])
            if bs > 0.3:
                badges.append(f'<span class="profile-badge" style="border-color:var(--warning);background:rgba(245,158,11,0.15);">\U0001f4a5 Ousado</span>')
            elif bs < -0.3:
                badges.append(f'<span class="profile-badge" style="border-color:var(--bolao);background:rgba(59,130,246,0.15);">\U0001F9CA Conservador</span>')

    # 4. Leader badge
    rank_path = _norm(os.path.join(gold_dir, "ranking_history.csv"))
    if os.path.exists(rank_path):
        df_rank = pd.read_csv(rank_path, sep=",")
        df_rank = df_rank.sort_values("date")
        latest_date = df_rank["date"].iloc[-1] if not df_rank.empty else None
        if latest_date:
            df_latest = df_rank[df_rank["date"] == latest_date]
            top = df_latest.loc[df_latest["rank"].idxmin()] if not df_latest.empty else None
            if top is not None and top["boleiro"] == boleiro:
                badges.append(f'<span class="profile-badge" style="border-color:var(--accent);background:rgba(255,215,0,0.15);">\U0001f40d L\u00edder</span>')

    # 5. Team expert badge
    ta_path = _norm(os.path.join(gold_dir, "team_accuracy.csv"))
    if os.path.exists(ta_path):
        df_ta = pd.read_csv(ta_path, sep=",")
        df_ta["team"] = df_ta["team"].str.strip()
        best_team = ""
        best_pct = 0
        for team in df_ta["team"].unique():
            df_tt = df_ta[df_ta["team"] == team]
            if df_tt.empty:
                continue
            agg = df_tt.groupby("boleiro").agg(
                total_bets=("total_bets", "sum"),
                correct_winner=("correct_winner", "sum"),
            ).reset_index()
            agg["acc"] = agg["correct_winner"] / agg["total_bets"] * 100
            top_acc = agg.loc[agg["acc"].idxmax()] if not agg.empty else None
            if top_acc is not None and top_acc["boleiro"] == boleiro and top_acc["total_bets"] >= 3 and top_acc["acc"] > 50:
                if top_acc["acc"] > best_pct:
                    best_pct = top_acc["acc"]
                    best_team = team
        if best_team:
            badges.append(f'<span class="profile-badge" style="border-color:var(--success);background:rgba(34,197,94,0.15);">\U0001f3af Especialista em {best_team[:12]}</span>')

    badges_html = f'<div style="display:flex;flex-wrap:wrap;gap:0.4rem;margin-bottom:0.75rem;">{" ".join(badges)}</div>' if badges else ""

    # --- Profile type from boldness_index ---
    boldness_html = ""
    if os.path.exists(bold_path):
        df_bold3 = pd.read_csv(bold_path, sep=",")
        df_bp3 = df_bold3[df_bold3["boleiro"] == boleiro]
        if not df_bp3.empty:
            bs2 = float(df_bp3.iloc[0]["boldness_score"])
            if bs2 > 0.3:
                pt = "\U0001f680 Ousado"
                pdsc = "Voc\u00ea aposta em placares acima da m\u00e9dia do bol\u00e3o"
            elif bs2 < -0.3:
                pt = "\U0001F9CA Conservador"
                pdsc = "Voc\u00ea aposta em placares abaixo da m\u00e9dia do bol\u00e3o"
            else:
                pt = "\u2696\ufe0f Equilibrado"
                pdsc = "Voc\u00ea aposta na m\u00e9dia do bol\u00e3o"
            boldness_html = f'<div style="margin-bottom:0.5rem;"><span class="profile-badge">{pt}</span> <span style="font-size:0.8rem;color:var(--text-muted);">({pdsc})</span></div>\n'
    if not boldness_html:
        boldness_html = _ph("Perfil de ousadia dispon\u00edvel ap\u00f3s os primeiros jogos.")

    # --- Best and worst teams (goal_error_by_team) ---
    error_path = _norm(os.path.join(gold_dir, "goal_error_by_team.csv"))
    best_team_html = ""
    worst_team_html = ""
    bias_html = ""
    if os.path.exists(error_path):
        df_err = pd.read_csv(error_path, sep=",")
        df_err_p_all = df_err[df_err["boleiro"] == boleiro].copy()
        if not df_err_p_all.empty:
            df_err_p = df_err_p_all[df_err_p_all["role"] == "total"].copy()
            if df_err_p.empty:
                df_err_p = df_err_p_all.copy()
            df_err_p_sorted = df_err_p.sort_values("mae")
            best_teams = df_err_p_sorted.head(3)
            worst_teams = df_err_p_sorted.tail(3)

            best_team_html = "<div style='margin-top:0.5rem;'>"
            best_team_html += '<div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);margin-bottom:0.3rem;">\U0001f3c6 Times que voce mais acerta</div>'
            for _, r in best_teams.iterrows():
                best_team_html += f'<div style="font-size:0.85rem;padding:0.15rem 0;"><strong>{r["team"]}</strong> ({r["role"]}) \u2014 erro medio de {r["mae"]:.1f} gols</div>\n'
            best_team_html += "</div>"

            worst_team_html = "<div style='margin-top:0.5rem;'>"
            worst_team_html += '<div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);margin-bottom:0.3rem;">\U0001f4a9 Times que voce mais erra</div>'
            for _, r in worst_teams.iterrows():
                worst_team_html += f'<div style="font-size:0.85rem;padding:0.15rem 0;"><strong>{r["team"]}</strong> ({r["role"]}) \u2014 erro medio de {r["mae"]:.1f} gols</div>\n'
            worst_team_html += "</div>"

            bias_teams = df_err_p[df_err_p["goal_bias"].abs() >= 0.5].sort_values("goal_bias")
            if not bias_teams.empty:
                bias_html = "<div style='margin-top:0.5rem;'>"
                bias_html += '<div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);margin-bottom:0.3rem;">\U0001f4ca Vies de palpites</div>'
                for _, r in bias_teams.head(4).iterrows():
                    direction = "superestima" if r["goal_bias"] > 0 else "subestima"
                    bias_html += f'<div style="font-size:0.85rem;padding:0.15rem 0;">Voce <strong>{direction}</strong> o {r["team"]} em {abs(r["goal_bias"]):.1f} gols</div>\n'
                bias_html += "</div>"
    if not best_team_html:
        best_team_html = _ph("Times que voc\u00ea mais acerta dispon\u00edvel ap\u00f3s os primeiros jogos.")
    if not worst_team_html:
        worst_team_html = _ph("Times que voc\u00ea mais erra dispon\u00edvel ap\u00f3s os primeiros jogos.")
    if not bias_html:
        bias_html = _ph("Vi\u00e9s de palpites dispon\u00edvel ap\u00f3s os primeiros jogos.")

    # --- Combine profile ---
    profile_parts = badges_html + boldness_html + streak_html_inner + best_team_html + worst_team_html + bias_html
    profile_html = f'<div class="section"><div class="section-title">\U0001f9d0 Perfil do Jogador</div><div class="card">{profile_parts}</div></div>\n'

    body += profile_html

    encerrados_total = n_past + n_pending
    body += f"""
<details class="section">
    <summary style="font-size:1rem;font-weight:700;padding:0 0.75rem;margin-bottom:0.5rem;display:flex;align-items:center;gap:0.5rem;cursor:pointer;min-height:44px;">
    \U0001f4cb Jogos Encerrados ({encerrados_total})</summary>
"""
    if n_pending:
        body += f"""    <div class="card" style="margin-bottom:0.5rem;">
        <div style="font-size:0.8rem;font-weight:600;color:var(--warning);margin-bottom:0.3rem;">\u23f3 Aguardando Resultado ({n_pending})</div>
        {pending_rows}</div>
"""
    if history_rows_past:
        body += f"""    <div class="card">
        <div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);margin-bottom:0.3rem;">\u2705 Com Resultado ({n_past})</div>
        {history_rows_past}</div>
"""
    if not encerrados_total:
        body += """    <div class="card"><div style="color:var(--text-muted);font-size:0.85rem;padding:0.3rem 0;">Nenhum jogo encerrado.</div></div>"""

    body += f"""
</details>
<details class="section" open>
    <summary style="font-size:1rem;font-weight:700;padding:0 0.75rem;margin-bottom:0.5rem;display:flex;align-items:center;gap:0.5rem;cursor:pointer;min-height:44px;">
    \U0001f4cb Jogos Futuros ({n_future})</summary>
    <div class="card">{history_rows_future}</div>
</details>
"""
    return _page_frame(config, f"{boleiro} - {config.report_title}", body, back_link="../index.html")


# ------------------------------------------------------------------
# Per-match page
# ------------------------------------------------------------------

def _build_match(config: ChampionshipConfig, match: str, phase: str, df_match: pd.DataFrame) -> str:
    """Build a per-match HTML report."""
    df_match = df_match.copy()
    df_match = df_match.sort_values(["pontos", "who"], ascending=False)

    home = str(df_match.iloc[0]["home_team"])
    away = str(df_match.iloc[0]["away_team"])
    date_str = str(df_match.iloc[0]["date"])
    hour_str = str(df_match.iloc[0].get("hour", ""))

    rev_map = {v: k for k, v in config.team_name_mapping.items()}
    home_en = rev_map.get(home, home)
    away_en = rev_map.get(away, away)
    match_dir = _norm(os.path.join(config.reports_dir, "html", "jogos", phase))
    home_logo = _team_logo_tag(home_en, config, cls="team-logo-sm", start=match_dir)
    away_logo = _team_logo_tag(away_en, config, cls="team-logo-sm", start=match_dir)

    # Check if result exists
    has_result = df_match["resultado_real_placar"].notna().any() and df_match["resultado_real_placar"].iloc[0] != "nan"

    real_placar = ""
    if has_result:
        real_placar = str(df_match.iloc[0]["resultado_real_placar"])

    # Pre-game: team vote distribution
    df_pre_time = df_match["resultado_bol_time"].value_counts().reset_index()
    df_pre_time.columns = ["vencedor", "#"]
    total_t = int(df_pre_time["#"].sum())
    team_bars = ""
    for _, row in df_pre_time.iterrows():
        pct = round(row["#"] / total_t * 100)
        count = int(row["#"])
        team_bars += (
            f'<div class="bar-row">'
            f'<span class="bar-label">{row["vencedor"]}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>'
            f'<span class="bar-pct">{pct}% ({count}/{total_t})</span>'
            f'</div>\n'
        )

    # Pre-game: score heatmap
    max_h = int(df_match["home_goals_bol"].max())
    max_a = int(df_match["away_goals_bol"].max())
    max_h = max(max_h, 4)
    max_a = max(max_a, 4)
    total_s = len(df_match)

    # Build player-per-score mapping for heatmap
    heat_players: dict[tuple[int, int], list[str]] = {}
    for _, row in df_match.iterrows():
        hg = int(row["home_goals_bol"])
        ag = int(row["away_goals_bol"])
        heat_players.setdefault((hg, ag), []).append(str(row["who"]))

    # Header row (away goals)
    header_row = '<div class="heat-row">'
    header_row += '<div class="heat-label" style="width:80px;min-width:80px;padding:0;"></div>'
    for a in range(max_a + 1):
        header_row += f'<div class="heat-cell-lg" style="font-size:0.6rem;font-weight:700;color:var(--text-muted);background:transparent;">{a}</div>'
    header_row += '</div>\n'

    # Data rows (home goals)
    data_rows = ""
    for h in range(max_h + 1):
        data_rows += '<div class="heat-row">'
        data_rows += f'<div class="heat-label">{h}</div>'
        for a in range(max_a + 1):
            cnt = len(df_match[(df_match["home_goals_bol"] == h) & (df_match["away_goals_bol"] == a)])
            pct = round(cnt / total_s * 100) if total_s else 0
            if cnt:
                if h > a:
                    z = "success"
                    zc = "34,197,94"
                elif h == a:
                    z = "warning"
                    zc = "245,158,11"
                else:
                    z = "danger"
                    zc = "239,68,68"
                if pct >= 30:
                    bg = f"var(--{z})"
                    fc = "#fff"
                elif pct >= 15:
                    bg = f"rgba({zc},0.7)"
                    fc = "#fff"
                elif pct >= 5:
                    bg = f"rgba({zc},0.4)"
                    fc = "var(--text)"
                else:
                    bg = f"rgba({zc},0.2)"
                    fc = "var(--text)"
            else:
                if h > a:
                    bg = "rgba(34,197,94,0.06)"
                elif h == a:
                    bg = "rgba(245,158,11,0.06)"
                else:
                    bg = "rgba(239,68,68,0.06)"
                fc = "var(--text-muted)"
            label = str(cnt) if cnt else ""
            players = heat_players.get((h, a), [])
            title = ", ".join(players).replace('"', "&quot;") if players else ""
            has_click = 'onclick="showHeatPlayers([&quot;' + '&quot;,&quot;'.join(players) + '&quot;],this)"' if players else ""
            data_rows += f'<div class="heat-cell-lg" style="background:{bg};color:{fc}" title="{title}" {has_click}>{label}</div>'
        data_rows += '</div>\n'

    score_heatmap = (
        '<div class="heatmap-match">'
        f'<div class="heatmap-top">{away_logo}<span>{away}</span></div>'
        '<div class="heatmap-body">'
        f'<div class="heatmap-away">{home_logo}<span>{home}</span></div>'
        f'<div class="heatmap-grid"><div class="heat-container">{header_row}{data_rows}</div></div>'
        '</div></div>'
        '<div class="heat-legend">👆 clique nos números para ver quem apostou</div>'
        '<div id="heatPopup" class="heat-popup" onclick="this.classList.remove(\'show\')"></div>'
        '<script>'
        'function showHeatPlayers(players,el){'
        "var p=document.getElementById('heatPopup');"
        "p.innerHTML='<strong>Boleiros:</strong><br>'+players.join('<br>');"
        'var r=el.getBoundingClientRect();'
        "p.style.left=Math.min(r.left,window.innerWidth-200)+'px';"
        "p.style.top=(r.bottom+4)+'px';"
        "p.classList.add('show');"
        'setTimeout(function(){document.addEventListener("click",function hide(e){if(!p.contains(e.target)&&e.target!=el){p.classList.remove("show");document.removeEventListener("click",hide)}})},0)}'
        '</script>'
    )

    # Build player-per-placar mapping
    placar_players: dict[str, list[str]] = {}
    for _, row in df_match.iterrows():
        placar = str(row["resultado_bol_placar"])
        placar_players.setdefault(placar, []).append(str(row["who"]))

    # Pre-game: placar distribution bars
    placar_counts = df_match["resultado_bol_placar"].value_counts().reset_index()
    placar_counts.columns = ["placar", "#"]
    placar_rows_resolved = []
    for _, pr in placar_counts.iterrows():
        parts = str(pr["placar"]).split(" x ")
        if len(parts) == 2:
            try:
                hg = int(parts[0])
                ag = int(parts[1])
            except ValueError:
                continue
        else:
            continue
        if hg > ag:
            rtype = 0  # home win
        elif hg == ag:
            rtype = 1  # draw
        else:
            rtype = 2  # away win
        placar_rows_resolved.append({"placar": pr["placar"], "#": pr["#"], "rtype": rtype, "hg": hg, "ag": ag, "total": hg + ag})
    placar_rows_resolved.sort(key=lambda x: (x["rtype"], -x["total"], -x["ag"] if x["rtype"] == 0 else (-x["hg"] if x["rtype"] == 2 else x["hg"])))
    total_p = sum(r["#"] for r in placar_rows_resolved)
    score_bars = ""
    bar_colors = {"home": "var(--success)", "draw": "var(--warning)", "away": "var(--danger)"}
    bar_bgs = {"home": "rgba(34,197,94,0.15)", "draw": "rgba(245,158,11,0.15)", "away": "rgba(239,68,68,0.15)"}
    for r in placar_rows_resolved:
        pct = round(r["#"] / total_p * 100)
        tcolor = "home" if r["rtype"] == 0 else ("draw" if r["rtype"] == 1 else "away")
        players = placar_players.get(r["placar"], [])
        title = ", ".join(players).replace('"', "&quot;") if players else ""
        escaped_players = [p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for p in players]
        player_list = "".join(f'<div class="bar-player">{ep}</div>' for ep in escaped_players)
        score_bars += (
            f'<div class="bar-row" onclick="this.classList.toggle(\'expanded\')" title="{title}">'
            f'<span class="bar-label">{r["placar"]}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{bar_colors[tcolor]}"></div></div>'
            f'<span class="bar-pct" style="color:{bar_colors[tcolor]}">{int(r["#"])} ({pct}%)</span>'
            f'<div class="bar-players">{player_list}</div>'
            f'</div>\n'
        )

    # Post-game: criteria distribution
    df_post = df_match["criterio"].value_counts().reset_index()
    df_post.columns = ["criterio", "#"]
    df_post.sort_values("criterio", inplace=True)
    criteria_bars = ""
    total_c = int(df_post["#"].sum())
    for _, row in df_post.iterrows():
        pct = round(row["#"] / total_c * 100)
        count = int(row["#"])
        criteria_bars += (
            f'<div class="bar-row">'
            f'<span class="bar-label">{row["criterio"]}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>'
            f'<span class="bar-pct">{pct}% ({count})</span>'
            f'</div>\n'
        )

    # Player predictions
    bonus_by_player = {}
    bonus_path = os.path.join(config._au_first_round(), "playoffs_scored.csv")
    if os.path.exists(bonus_path):
        df_bonus = pd.read_csv(bonus_path)
        df_bonus_phase = df_bonus[df_bonus["phase"] == phase]
        if not df_bonus_phase.empty:
            for _, br in df_bonus_phase.iterrows():
                who = str(br["boleiro"])
                if who not in bonus_by_player:
                    bonus_by_player[who] = {"correct": 0, "total": 0, "points": 0}
                bonus_by_player[who]["correct"] += int(br["correct"])
                bonus_by_player[who]["total"] += 1
                bonus_by_player[who]["points"] += int(br["points"])

    pred_rows = ""
    for _, row in df_match.iterrows():
        pts = int(row["pontos"])
        criterio_emoji = config.scoring_emoji(row.get("criterio", ""))
        css_var, css_bg, css_border = config.scoring_css_var(row.get("criterio", ""))
        if css_var:
            pts_color = css_var
            pts_bg = css_bg
            pts_border = css_border
        else:
            hex_color = config.scoring_color(row.get("criterio", ""))
            if hex_color:
                pts_color = hex_color
                pts_bg = hex_color + "1a"
                pts_border = hex_color + "40"
            else:
                pts_color = "var(--text-muted)"
                pts_bg = "transparent"
                pts_border = "var(--card-border)"
        bonus_text = ""
        bdata = bonus_by_player.get(row["who"])
        if bdata:
            if bdata["total"] > 0 and bdata["correct"] == bdata["total"] and bdata["points"] > 0 or bdata["points"] > 0:
                bonus_text = f' &middot; \U0001f3c6 Bônus: {bdata["correct"]}/{bdata["total"]} \u2705 +{bdata["points"]}pts'
            else:
                bonus_text = f' &middot; \U0001f3c6 Bônus: {bdata["total"]} picks \U0001f550'
        pred_rows += (
            f'<div class="pred-row">'
            f'{_avatar_html(row["who"])}'
            f'<div class="pred-info">'
            f'<div class="pred-name">{row["who"]}{bonus_text}</div>'
            f'<div class="pred-detail">Previsto: {row["resultado_bol_placar"]} | {criterio_emoji} {row["criterio"]}</div>'
            f'</div>'
            f'<div class="score-pill" style="color:{pts_color};background:{pts_bg};border:1px solid {pts_border}">+{pts} {criterio_emoji}</div>'
            f'</div>\n'
        )

    # Score display
    if has_result:
        parts = real_placar.split(" x ")
        pen_html = ""
        try:
            hp = df_match.iloc[0].get("home_pen")
            ap = df_match.iloc[0].get("away_pen")
            if pd.notna(hp) and pd.notna(ap):
                hp = int(hp)
                ap = int(ap)
                pen_html = f'<div class="penalty-score">{hp} - {ap} nos pênaltis</div>'
        except (ValueError, TypeError):
            pass
        score_html = f"""
<div class="score-card">
    <div class="team">{home_logo} <a href="../../times/{home}.html" style="color:var(--text);text-decoration:none;">{home}</a></div>
    <div class="score">{parts[0]} - {parts[1]}</div>
    <div class="team">{away_logo} <a href="../../times/{away}.html" style="color:var(--text);text-decoration:none;">{away}</a></div>
</div>
{pen_html}
<div style="text-align:center;"><span class="badge badge-success">Resultado Final</span></div>
"""
    else:
        score_html = f"""
<div class="score-card">
    <div class="team">{home_logo} <a href="../../times/{home}.html" style="color:var(--text);text-decoration:none;">{home}</a></div>
    <div class="score">vs</div>
    <div class="team">{away_logo} <a href="../../times/{away}.html" style="color:var(--text);text-decoration:none;">{away}</a></div>
</div>
<div style="text-align:center;"><span class="badge badge-warning">Aguardando resultado</span></div>
"""

    team_link = '../../times/{}.html'
    body = f"""
<div class="hero">
    <h1>{home_logo} <a href="../../times/{home}.html" style="color:var(--text);text-decoration:none;">{home}</a> x {away_logo} <a href="../../times/{away}.html" style="color:var(--text);text-decoration:none;">{away}</a></h1>
    <div class="subtitle">{date_str} {hour_str} | {phase}</div>
</div>

{score_html}

<div class="section">
    <div class="section-title">\U0001f52e Pre-Jogo - Votos por Time</div>
    <div class="card"><div class="bar-chart">{team_bars}</div></div>
</div>

<div class="section">
    <div class="section-title">\U0001f52e Pre-Jogo - Distribuicao de Placar</div>
    <div class="card">{score_heatmap}</div>
    <div class="card" style="margin-top:0.5rem;"><div class="bar-chart">{score_bars}</div><div class="heat-legend">👆 clique na linha para ver quem apostou</div></div>
</div>
"""

    if has_result:
        body += f"""
<div class="section">
    <div class="section-title">\U0001f4ca Pos-Jogo - Criterios</div>
    <div class="card"><div class="bar-chart">{criteria_bars}</div></div>
</div>
"""

    body += f"""
<div class="section">
    <div class="section-title">\U0001f4cb Previsoes dos Jogadores ({len(df_match)})</div>
    <div class="card">{pred_rows}</div>
</div>
"""
    return _page_frame(config, f"{home} x {away} - {config.report_title}", body, back_link="../../index.html")


# ------------------------------------------------------------------
# Arena (player comparison)
# ------------------------------------------------------------------

def _build_arena(config: ChampionshipConfig, df_valid: pd.DataFrame) -> str:
    """Build the arena.html player comparison page."""
    players = sorted(df_valid["who"].unique())
    options = "".join(f'<option value="{p}">{p}</option>' for p in players)

    # Load bonus data for badge
    bonus_by_player = {}
    bonus_path = os.path.join(config._au_first_round(), "playoffs_scored.csv")
    if os.path.exists(bonus_path):
        df_bonus_arena = pd.read_csv(bonus_path)
        if not df_bonus_arena.empty:
            for _, br in df_bonus_arena.iterrows():
                who = str(br["boleiro"])
                if who not in bonus_by_player:
                    bonus_by_player[who] = {"correct": 0, "total": 0, "points": 0}
                bonus_by_player[who]["correct"] += int(br["correct"])
                bonus_by_player[who]["total"] += 1
                bonus_by_player[who]["points"] += int(br["points"])

    # Embed player data as JSON
    player_json = {}
    for p in players:
        df_p = df_valid[df_valid["who"] == p].copy()
        df_p["date"] = pd.to_datetime(df_p["date"])
        daily = df_p.groupby("date")["pontos"].sum().reset_index()
        daily["date_str"] = daily["date"].dt.strftime("%d/%m")
        daily["cum"] = daily["pontos"].cumsum()
        recent = df_p.sort_values("date", ascending=False)
        bdata = bonus_by_player.get(p, {})
        player_json[p] = {
            "total": int(df_p["pontos"].sum()),
            "avg": round(df_p["pontos"].mean(), 1),
            "games": len(df_p),
            "bonus": bdata.get("points", 0),
            "bonus_correct": bdata.get("correct", 0),
            "bonus_total": bdata.get("total", 0),
            "daily": [{"date": r["date_str"], "pts": int(r["pontos"])} for _, r in daily.iterrows()],
            "cumulative": [{"date": r["date_str"], "cum": int(r["cum"])} for _, r in daily.iterrows()],
            "recent": [{"match": f"{r['home_team']} {r['resultado_real_placar']} {r['away_team']}", "pts": int(r["pontos"]), "date": pd.to_datetime(r["date"]).strftime("%d/%m")} for _, r in recent.iterrows()]
        }

    # Compute championship leader
    df_totals = df_valid.groupby("who", as_index=False)["pontos"].sum()
    df_totals.sort_values("pontos", ascending=False, inplace=True)
    leader_name = str(df_totals.iloc[0]["who"]) if not df_totals.empty else ""

    import json
    json_str = json.dumps({
        "players": player_json,
        "leader": leader_name,
    }, ensure_ascii=False)

    js_code = r"""
const arenaData = DATA_PLACEHOLDER;
const playerData = arenaData.players;
const leaderName = arenaData.leader;

function getCSSVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function updateArena() {
    const p1 = document.getElementById('player1').value;
    const p2 = document.getElementById('player2').value;
    const content = document.getElementById('arena-content');

    if (!p1 || !p2) {
        content.style.display = 'none';
        return;
    }

    content.style.display = 'block';
    const d1 = playerData[p1];
    const d2 = playerData[p2];

    document.getElementById('p1-total').querySelector('.value').textContent = d1.total;
    document.getElementById('p2-total').querySelector('.value').textContent = d2.total;
    document.getElementById('p1-avg').querySelector('.value').textContent = d1.avg;
    document.getElementById('p2-avg').querySelector('.value').textContent = d2.avg;
    document.getElementById('p1-games').querySelector('.value').textContent = d1.games;
    document.getElementById('p2-games').querySelector('.value').textContent = d2.games;

    const p1BonusEl = document.getElementById('p1-bonus').querySelector('.value');
    const p2BonusEl = document.getElementById('p2-bonus').querySelector('.value');
    if (d1.bonus_total > 0) {
        p1BonusEl.textContent = '+' + d1.bonus + 'pts (' + d1.bonus_correct + '/' + d1.bonus_total + ' \u2705)';
    } else {
        p1BonusEl.textContent = '-';
    }
    if (d2.bonus_total > 0) {
        p2BonusEl.textContent = '+' + d2.bonus + 'pts (' + d2.bonus_correct + '/' + d2.bonus_total + ' \u2705)';
    } else {
        p2BonusEl.textContent = '-';
    }

    const voceColor = getCSSVar('--voce');
    const bolaoColor = getCSSVar('--bolao');
    const leaderColor = getCSSVar('--leader');
    const gridColor = getCSSVar('--card-border');
    const axisColor = getCSSVar('--text-muted');
    const legendTextColor = getCSSVar('--text');

    // Determine if leader should be shown (neither selected player is the leader)
    const showLeader = leaderName && leaderName !== p1 && leaderName !== p2;
    const dLeader = showLeader ? playerData[leaderName] : null;

    // Cumulative line chart
    const cumDiv = document.getElementById('cumulative-comparison');
    cumDiv.innerHTML = '<div style="position:relative;"><canvas id="cum-chart" width="600" height="250" style="width:100%;height:250px;cursor:crosshair;"></canvas><div id="cum-tooltip" style="display:none;position:absolute;background:var(--card-bg);border:1px solid var(--card-border);border-radius:8px;padding:0.5rem 0.75rem;font-size:0.75rem;pointer-events:none;z-index:100;box-shadow:0 4px 12px var(--shadow-color);"></div></div>';
    const canvas = document.getElementById('cum-chart');
    const tooltip = document.getElementById('cum-tooltip');
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = 250 * dpr;
    ctx.scale(dpr, dpr);
    const W = rect.width;
    const H = 250;
    const padL = 40, padR = 10, padT = 10, padB = 30;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    let allCumDates = [...new Set([...d1.cumulative.map(c => c.date), ...d2.cumulative.map(c => c.date)])];
    if (showLeader && dLeader) {
        allCumDates = [...new Set([...allCumDates, ...dLeader.cumulative.map(c => c.date)])];
    }
    allCumDates.sort();

    const last1 = d1.cumulative.length > 0 ? d1.cumulative[d1.cumulative.length-1].cum : 0;
    const last2 = d2.cumulative.length > 0 ? d2.cumulative[d2.cumulative.length-1].cum : 0;
    const lastLeader = showLeader && dLeader && dLeader.cumulative.length > 0 ? dLeader.cumulative[dLeader.cumulative.length-1].cum : 0;
    const maxCum = Math.max(last1, last2, lastLeader, 1);

    function buildSeries(data, dates) {
        return dates.map(function(date) {
            const entry = data.find(c => c.date === date);
            return entry ? entry.cum : 0;
        });
    }
    const s1 = buildSeries(d1.cumulative, allCumDates);
    const s2 = buildSeries(d2.cumulative, allCumDates);
    const sLeader = showLeader ? buildSeries(dLeader.cumulative, allCumDates) : null;

    function getPointX(i) { return padL + (plotW / Math.max(allCumDates.length - 1, 1)) * i; }
    function getPointY(val) { return padT + plotH - (val / maxCum) * plotH; }

    ctx.clearRect(0, 0, W, H);

    // Grid lines
    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 0.5;
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
        const y = padT + (plotH / gridLines) * i;
        ctx.beginPath();
        ctx.moveTo(padL, y);
        ctx.lineTo(W - padR, y);
        ctx.stroke();
        const val = Math.round(maxCum - (maxCum / gridLines) * i);
        ctx.fillStyle = axisColor;
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText(val, padL - 4, y + 3);
    }

    function drawLine(series, color, lineWidth, dotRadius) {
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth || 2;
        ctx.beginPath();
        series.forEach(function(val, i) {
            const x = getPointX(i);
            const y = getPointY(val);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
        series.forEach(function(val, i) {
            const x = getPointX(i);
            const y = getPointY(val);
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(x, y, dotRadius || 3, 0, Math.PI * 2);
            ctx.fill();
        });
    }

    // Draw leader line first (behind)
    if (showLeader && sLeader) {
        drawLine(sLeader, leaderColor, 1.5, 2);
    }
    drawLine(s1, voceColor);
    drawLine(s2, bolaoColor);

    // X-axis labels
    ctx.fillStyle = axisColor;
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'center';
    const step = Math.max(1, Math.floor(allCumDates.length / 8));
    allCumDates.forEach(function(date, i) {
        if (i % step === 0 || i === allCumDates.length - 1) {
            const x = getPointX(i);
            ctx.fillText(date, x, H - 5);
        }
    });

    // Legend - bottom right
    const legendY = H - padB - 30;
    const legendStartX = W - padR - 80;
    const legendItemH = 14;
    let legendIdx = 0;

    if (showLeader) {
        ctx.fillStyle = leaderColor;
        ctx.fillRect(legendStartX, legendY + legendIdx * legendItemH, 12, 12);
        ctx.fillStyle = legendTextColor;
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(leaderName, legendStartX + 16, legendY + legendIdx * legendItemH + 10);
        legendIdx++;
    }
    ctx.fillStyle = voceColor;
    ctx.fillRect(legendStartX, legendY + legendIdx * legendItemH, 12, 12);
    ctx.fillStyle = legendTextColor;
    ctx.fillText(p1, legendStartX + 16, legendY + legendIdx * legendItemH + 10);
    legendIdx++;
    ctx.fillStyle = bolaoColor;
    ctx.fillRect(legendStartX, legendY + legendIdx * legendItemH, 12, 12);
    ctx.fillStyle = legendTextColor;
    ctx.fillText(p2, legendStartX + 16, legendY + legendIdx * legendItemH + 10);

    // Hover tooltip
    canvas.addEventListener('mousemove', function(e) {
        const r = canvas.getBoundingClientRect();
        const mx = e.clientX - r.left;
        const my = e.clientY - r.top;
        let closest = -1;
        let closestDist = 20;
        for (let i = 0; i < allCumDates.length; i++) {
            const dx = Math.abs(mx - getPointX(i));
            if (dx < closestDist) { closestDist = dx; closest = i; }
        }
        if (closest >= 0) {
            const v1 = s1[closest];
            const v2 = s2[closest];
            let tipHtml = '<div style="color:var(--text-muted);margin-bottom:0.25rem;">' + allCumDates[closest] + '</div>' +
                '<div style="color:' + voceColor + ';">' + p1 + ': <strong>' + v1 + '</strong> pts</div>' +
                '<div style="color:' + bolaoColor + ';">' + p2 + ': <strong>' + v2 + '</strong> pts</div>';
            if (showLeader && sLeader) {
                const vL = sLeader[closest];
                tipHtml = '<div style="color:var(--text-muted);margin-bottom:0.25rem;">' + allCumDates[closest] + '</div>' +
                    '<div style="color:' + leaderColor + ';">' + leaderName + ': <strong>' + vL + '</strong> pts</div>' +
                    '<div style="color:' + voceColor + ';">' + p1 + ': <strong>' + v1 + '</strong> pts</div>' +
                    '<div style="color:' + bolaoColor + ';">' + p2 + ': <strong>' + v2 + '</strong> pts</div>';
            }
            tooltip.style.display = 'block';
            tooltip.innerHTML = tipHtml;
            let tx = mx + 12;
            let ty = my - 10;
            if (tx + 120 > W) tx = mx - 130;
            if (ty < 0) ty = 10;
            tooltip.style.left = tx + 'px';
            tooltip.style.top = ty + 'px';
        } else {
            tooltip.style.display = 'none';
        }
    });
    canvas.addEventListener('mouseleave', function() {
        tooltip.style.display = 'none';
    });

    // Recent games comparison
    const recentDiv = document.getElementById('recent-comparison');
    const maxRecent = Math.max(...d1.recent.map(r => r.pts), ...d2.recent.map(r => r.pts), 1);
    let recentHtml = '';
    const allRecentKeys = [...new Set([...d1.recent.map(r => r.date + '|' + r.match), ...d2.recent.map(r => r.date + '|' + r.match)])];
    const recentMatches = [...new Set(allRecentKeys.map(k => k.split('|')[1]))];
    recentMatches.forEach(function(match) {
        const r1 = d1.recent.find(r => r.match === match);
        const r2 = d2.recent.find(r => r.match === match);
        if (!r1 && !r2) return;
        const pts1 = r1 ? r1.pts : 0;
        const pts2 = r2 ? r2.pts : 0;
        const pct1 = Math.round(pts1 / maxRecent * 100);
        const pct2 = Math.round(pts2 / maxRecent * 100);
        const dateLabel = r1 ? r1.date : r2.date;
        recentHtml += '<div style="margin-bottom:0.5rem;font-size:0.75rem;">' +
            '<div style="color:var(--text-muted);margin-bottom:0.15rem;font-size:0.7rem;">' + dateLabel + ' \u2014 ' + match + '</div>' +
            '<div style="display:flex;align-items:center;gap:0.25rem;">' +
            '<span style="min-width:30px;color:var(--voce);font-size:0.7rem;">P1</span>' +
            '<div class="bar-track" style="height:12px;flex:1;"><div class="bar-fill" style="width:' + pct1 + '%;background:var(--voce);"></div></div>' +
            '<span style="min-width:20px;text-align:right;font-size:0.75rem;">' + pts1 + '</span>' +
            '</div>' +
            '<div style="display:flex;align-items:center;gap:0.25rem;">' +
            '<span style="min-width:30px;color:var(--bolao);font-size:0.7rem;">P2</span>' +
            '<div class="bar-track" style="height:12px;flex:1;"><div class="bar-fill" style="width:' + pct2 + '%;background:var(--bolao);"></div></div>' +
            '<span style="min-width:20px;text-align:right;font-size:0.75rem;">' + pts2 + '</span>' +
            '</div>' +
            '</div>';
    });
    recentDiv.innerHTML = recentHtml;
}
"""

    body = f"""
<div class="hero">
    <h1>\u2694\ufe0f Arena</h1>
    <div class="subtitle">Compare dois boleiros</div>
</div>

<div class="card" style="margin:1rem 0.75rem;">
    <div class="grid-2">
        <div>
            <label class="arena-label" for="player1">Jogador 1</label>
            <select id="player1" class="arena-select" onchange="updateArena()">
                <option value="">Selecione...</option>
                {options}
            </select>
        </div>
        <div>
            <label class="arena-label" for="player2">Jogador 2</label>
            <select id="player2" class="arena-select" onchange="updateArena()">
                <option value="">Selecione...</option>
                {options}
            </select>
        </div>
    </div>
</div>

<div id="arena-content" style="display:none;">
    <div class="stat-row" style="grid-template-columns:repeat(3,1fr);">
        <div class="stat-card" id="p1-total">
            <div class="value" style="color:var(--voce)">-</div>
            <div class="label">Total Jogos</div>
        </div>
        <div class="stat-card" style="background:var(--card-border);">
            <div class="value" style="font-size:1.2rem;">VS</div>
            <div class="label">Comparacao</div>
            <div class="label"></div>
        </div>
        <div class="stat-card" id="p2-total">
            <div class="value" style="color:var(--bolao)">-</div>
            <div class="label">Total Jogos</div>
        </div>
    </div>

    <div class="stat-row" style="grid-template-columns:repeat(4,1fr);">
        <div class="stat-card" id="p1-avg">
            <div class="value" style="font-size:1.1rem;color:var(--voce)">-</div>
            <div class="label">Media/Jogo</div>
        </div>
        <div class="stat-card" id="p1-games">
            <div class="value" style="font-size:1.1rem;color:var(--voce)">-</div>
            <div class="label">Jogos</div>
        </div>
        <div class="stat-card" id="p2-avg">
            <div class="value" style="font-size:1.1rem;color:var(--bolao)">-</div>
            <div class="label">Media/Jogo</div>
        </div>
        <div class="stat-card" id="p2-games">
            <div class="value" style="font-size:1.1rem;color:var(--bolao)">-</div>
            <div class="label">Jogos</div>
        </div>
    </div>

    <div class="stat-row" style="grid-template-columns:repeat(2,1fr);">
        <div class="stat-card" id="p1-bonus">
            <div class="value" style="font-size:1.1rem;color:var(--voce)">-</div>
            <div class="label">\U0001f3c6 Bônus Times</div>
        </div>
        <div class="stat-card" id="p2-bonus">
            <div class="value" style="font-size:1.1rem;color:var(--bolao)">-</div>
            <div class="label">\U0001f3c6 Bônus Times</div>
        </div>
    </div>

    <div class="card">
        <div class="card-title">Pontos por Dia</div>
        <div id="daily-comparison"></div>
    </div>

    <div class="card">
        <div class="card-title">Acumulado por Dia</div>
        <div id="cumulative-comparison"></div>
    </div>

    <div class="card">
        <div class="card-title">Todos os Jogos</div>
        <div id="recent-comparison"></div>
    </div>
</div>

<script>
{js_code.replace('DATA_PLACEHOLDER', json_str)}
</script>
"""
    return _page_frame(config, f"Arena - {config.report_title}", body, back_link="index.html")


# ------------------------------------------------------------------
# Ranking Evolution page
# ------------------------------------------------------------------


def _build_ranking_evolution(config: ChampionshipConfig) -> str:
    """Show rank position over time (toggleable per player, inverted Y-axis)."""
    csv_path = _norm(os.path.join(config._au_first_round(), "ranking_history.csv"))
    if not os.path.exists(csv_path):
        return _page_frame(config, f"Evolu\u00e7\u00e3o - {config.report_title}", "<div class='hero'><h1>\U0001f4ca Evolu\u00e7\u00e3o do Ranking</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados.</div></div>")
    df = pd.read_csv(csv_path, sep=",")
    players = sorted(df["boleiro"].unique())
    all_dates = sorted(df["date"].unique())

    player_json = {}
    for p in players:
        dp = df[df["boleiro"] == p].sort_values("date")
        player_json[p] = {
            "ranks": [int(r) for r in dp["rank"]],
            "cums": [int(c) for c in dp["cumulative_points"]],
        }

    import json
    max_rank = len(players)
    json_str = json.dumps({
        "players": player_json,
        "dates": all_dates,
        "max_rank": max_rank,
    }, ensure_ascii=False)

    # Toggle buttons
    import re as _re
    toggle_btns = ""
    for i, p in enumerate(players):
        safe = _re.sub(r"\s+", "_", p)
        color_idx = i % 8
        colors = ["#f5c518", "#3b82f6", "#22c55e", "#ef4444", "#a855f7", "#ec4899", "#f97316", "#14b8a6"]
        toggle_btns += (
            f'<button id="tb-{safe}" class="toggle-btn" '
            f'onclick="togglePlayer(\'{p}\')" '
            f'style="border-left:4px solid {colors[color_idx]};">{p}</button>\n'
        )

    js_code = r"""
const data = DATA_PLACEHOLDER;
const COLORS = ['#f5c518', '#3b82f6', '#22c55e', '#ef4444', '#a855f7', '#ec4899', '#f97316', '#14b8a6'];
const activePlayers = new Set();

function togglePlayer(name) {
    const safe = name.replace(/\s+/g, '_');
    const btn = document.getElementById('tb-' + safe);
    if (activePlayers.has(name)) {
        activePlayers.delete(name);
        btn.classList.remove('active');
    } else {
        activePlayers.add(name);
        btn.classList.add('active');
    }
    drawChart();
}

function drawChart() {
    const canvas = document.getElementById('rank-chart');
    if (!canvas) return;
    const tooltip = document.getElementById('rank-tooltip');
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = 250 * dpr;
    ctx.scale(dpr, dpr);
    const W = rect.width;
    const H = 250;
    const padL = 44, padR = 12, padT = 24, padB = 30;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    const dates = data.dates;
    const maxRank = data.max_rank;
    ctx.clearRect(0, 0, W, H);

    // Grid
    ctx.strokeStyle = '#30363d';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {
        const y = padT + (plotH / 4) * i;
        ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
        ctx.fillStyle = '#8899aa';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'right';
        // Inverted Y: position 1 at top
        const pos = 1 + Math.round((maxRank - 1) * (i / 4));
        ctx.fillText(pos + '\u00ba', padL - 4, y + 3);
    }

    // X axis
    ctx.fillStyle = '#8899aa';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'center';
    const step = Math.max(1, Math.floor(dates.length / 7));
    dates.forEach(function(d, i) {
        if (i % step === 0 || i === dates.length - 1) {
            const x = padL + (plotW / Math.max(dates.length - 1, 1)) * i;
            ctx.fillText(d.slice(5), x, H - 6);
        }
    });

    function getX(i) { return padL + (plotW / Math.max(dates.length - 1, 1)) * i; }
    function getY(rank) { return padT + ((rank - 1) / maxRank) * plotH; }

    // Draw only active players
    let idx = 0;
    activePlayers.forEach(function(name) {
        const p = data.players[name];
        if (!p) return;
        const color = COLORS[idx % COLORS.length];
        idx++;
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        p.ranks.forEach(function(r, i) {
            const x = getX(i);
            const y = getY(r);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();

        // Dots
        p.ranks.forEach(function(r, i) {
            const x = getX(i);
            const y = getY(r);
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(x, y, 3.5, 0, Math.PI * 2);
            ctx.fill();
        });
    });

    // Tooltip
    if (!canvas._listener) {
        canvas._listener = true;
        canvas.addEventListener('mousemove', function(e) {
            const r = canvas.getBoundingClientRect();
            const mx = e.clientX - r.left;
            const my = e.clientY - r.top;
            let closest = -1, closestDist = 20;
            for (let i = 0; i < dates.length; i++) {
                const dx = Math.abs(mx - getX(i));
                if (dx < closestDist) { closestDist = dx; closest = i; }
            }
            if (closest >= 0 && activePlayers.size > 0) {
                let tip = '<div style="color:var(--text-muted);margin-bottom:0.25rem;">' + dates[closest] + '</div>';
                let cIdx = 0;
                activePlayers.forEach(function(name) {
                    const rank = data.players[name].ranks[closest];
                    const cum = data.players[name].cums[closest];
                    const color = COLORS[cIdx % COLORS.length];
                    cIdx++;
                    tip += '<div style="color:' + color + ';">' + name + ': <strong>' + rank + '\u00ba</strong> (' + cum + ' pts)</div>';
                });
                tooltip.style.display = 'block';
                tooltip.innerHTML = tip;
                tooltip.style.left = Math.min(mx + 12, W - 140) + 'px';
                tooltip.style.top = Math.max(my - 10, 5) + 'px';
            } else {
                tooltip.style.display = 'none';
            }
        });
        canvas.addEventListener('mouseleave', function() { tooltip.style.display = 'none'; });
    }
}
document.addEventListener('DOMContentLoaded', drawChart);
"""

    # Table
    table_rows = ""
    for p in players:
        dp = df[df["boleiro"] == p].sort_values("date")
        if dp.empty:
            continue
        last = dp.iloc[-1]
        table_rows += f"""
<tr><td style="padding:0.3rem 0.5rem;"><a href="boleiros/{p}.html" style="color:var(--accent);">{p}</a></td><td style="padding:0.3rem 0.5rem;font-weight:700;">{int(last['rank'])}\u00ba</td><td style="padding:0.3rem 0.5rem;">{int(last['cumulative_points'])} pts</td><td style="padding:0.3rem 0.5rem;color:var(--text-muted);font-size:0.8rem;">{int(last['leader_distance'])} do lider</td></tr>"""

    body = f"""
<div class="hero">
    <h1>\U0001f4c8 Evolucao no Ranking</h1>
    <div class="subtitle">Clique nos jogadores abaixo para ligar/desligar</div>
</div>

<div class="card">
    <div class="card-title">Grafico (passe o mouse sobre as linhas)</div>
    <div style="position:relative;">
        <canvas id="rank-chart" width="600" height="250" style="width:100%;height:250px;cursor:crosshair;"></canvas>
        <div id="rank-tooltip" style="display:none;position:absolute;background:var(--card-bg);border:1px solid var(--card-border);border-radius:8px;padding:0.5rem 0.75rem;font-size:0.75rem;pointer-events:none;z-index:100;box-shadow:0 4px 12px var(--shadow-color);"></div>
    </div>
</div>

<div class="card">
    <div class="card-title">Jogadores (clique para ligar/desligar)</div>
    <div style="display:flex;flex-wrap:wrap;gap:0.4rem;">
        {toggle_btns}
    </div>
</div>

<div class="card">
    <div class="card-title">Classificacao Atual</div>
    <table style="width:100%;font-size:0.8rem;border-collapse:collapse;">
        <thead>
            <tr style="border-bottom:1px solid var(--card-border);">
                <th style="text-align:left;padding:0.3rem 0.5rem;">Jogador</th>
                <th style="text-align:left;padding:0.3rem 0.5rem;">#</th>
                <th style="text-align:left;padding:0.3rem 0.5rem;">Pts</th>
                <th style="text-align:left;padding:0.3rem 0.5rem;">Dist</th>
            </tr>
        </thead>
        <tbody>{table_rows}</tbody>
    </table>
</div>

<style>
.toggle-btn {{
    padding: 0.35rem 0.7rem;
    border: 1px solid var(--card-border);
    border-radius: 6px;
    background: var(--card-bg);
    color: var(--text-muted);
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.2s;
}}
.toggle-btn.active {{
    background: var(--accent);
    color: var(--text-inverse);
    border-color: var(--accent);
}}
</style>

<script>
{js_code.replace('DATA_PLACEHOLDER', json_str)}
</script>
"""
    return _page_frame(config, f"Evolucao - {config.report_title}", body, back_link="index.html")


# ------------------------------------------------------------------
# Boldômetro page
# ------------------------------------------------------------------


def _build_boldometer(config: ChampionshipConfig) -> str:
    """Scatter plot: boldness vs average points per game."""
    bold_path = _norm(os.path.join(config._au_first_round(), "boldness_index.csv"))
    if not os.path.exists(bold_path):
        return _page_frame(config, f"Boldômetro - {config.report_title}", "<div class='hero'><h1>\U0001f4ca Boldômetro</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados.</div></div>")
    df_bold = pd.read_csv(bold_path, sep=",")
    df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
    df_avg = df_valid.groupby("who")["pontos"].mean().reset_index()
    df_avg.columns = ["boleiro", "avg_pts_per_game"]
    df = df_bold.merge(df_avg, on="boleiro", how="left")

    players = []
    for _, r in df.iterrows():
        players.append({
            "name": r["boleiro"],
            "boldness": float(r["boldness_score"]),
            "avg_pts": float(r["avg_pts_per_game"]),
            "avg_goals": float(r["avg_total_goals_bol"]),
            "games": int(r["games"]),
        })

    import json
    json_str = json.dumps(players, ensure_ascii=False)

    # Example rows for table
    example_rows = ""
    sorted_by_bold = sorted(players, key=lambda p: p["boldness"], reverse=True)
    for p in sorted_by_bold[:3]:
        example_rows += f"<tr><td>{p['name']}</td><td>{p['boldness']:+.2f}</td><td>{p['avg_pts']:.1f}</td><td style='font-size:0.8rem;color:var(--text-muted);'>{p['avg_goals']:.1f} gols/jogo</td></tr>\n"
    example_rows += "<tr style='border-top:1px solid var(--card-border);'><td colspan='4' style='text-align:center;font-style:italic;'>... e mais " + str(len(players) - 3) + " jogadores</td></tr>\n"

    js_code = r"""
const players = DATA_PLACEHOLDER;
const canvas = document.getElementById('scatter');
const tooltip = document.getElementById('scatter-tooltip');
const ctx = canvas.getContext('2d');
const dpr = window.devicePixelRatio || 1;
const rect = canvas.getBoundingClientRect();
canvas.width = rect.width * dpr;
canvas.height = 380 * dpr;
ctx.scale(dpr, dpr);
const W = rect.width;
const H = 380;
const padL = 55, padR = 20, padT = 30, padB = 50;
const plotW = W - padL - padR;
const plotH = H - padT - padB;

const xs = players.map(p => p.boldness);
const ys = players.map(p => p.avg_pts);
const minX = Math.min(...xs, -0.3) - 0.3;
const maxX = Math.max(...xs, 0.3) + 0.3;
const minY = Math.max(0, Math.min(...ys) - 0.3);
const maxY = Math.max(...ys) + 0.3;

function getX(v) { return padL + ((v - minX) / (maxX - minX)) * plotW; }
function getY(v) { return padT + plotH - ((v - minY) / (maxY - minY)) * plotH; }

ctx.clearRect(0, 0, W, H);

// Draw quadrant backgrounds (stronger opacity)
const zeroX = getX(0);
const avgY = ys.reduce((a,b) => a+b, 0) / ys.length;
const avgYPx = getY(avgY);

// Top-left: Green (efficient - low boldness, high pts)
ctx.fillStyle = 'rgba(34,197,94,0.12)';
ctx.fillRect(padL, padT, zeroX - padL, avgYPx - padT);
// Top-right: Yellow (risky - high boldness, high pts)
ctx.fillStyle = 'rgba(234,179,8,0.12)';
ctx.fillRect(zeroX, padT, padL + plotW - zeroX, avgYPx - padT);
// Bottom-left: Blue-gray (conservative - low boldness, low pts)
ctx.fillStyle = 'rgba(100,116,139,0.12)';
ctx.fillRect(padL, avgYPx, zeroX - padL, padT + plotH - avgYPx);
// Bottom-right: Red (bad - high boldness, low pts)
ctx.fillStyle = 'rgba(239,68,68,0.12)';
ctx.fillRect(zeroX, avgYPx, padL + plotW - zeroX, padT + plotH - avgYPx);

// Grid
ctx.strokeStyle = '#30363d';
ctx.lineWidth = 0.5;
for (let i = 0; i <= 4; i++) {
    const x = padL + (plotW / 4) * i;
    const y = padT + (plotH / 4) * i;
    ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, padT + plotH); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + plotW, y); ctx.stroke();
}

// Quadrant labels
ctx.font = 'bold 10px sans-serif';
ctx.textAlign = 'center';
ctx.fillStyle = 'rgba(34,197,94,0.7)';
ctx.fillText('EFICIENTE', padL + (zeroX - padL) / 2, padT + 14);
ctx.fillStyle = 'rgba(234,179,8,0.7)';
ctx.fillText('OUSADO', zeroX + (padL + plotW - zeroX) / 2, padT + 14);
ctx.fillStyle = 'rgba(100,116,139,0.7)';
ctx.fillText('CONSERVADOR', padL + (zeroX - padL) / 2, padT + plotH - 10);
ctx.fillStyle = 'rgba(239,68,68,0.7)';
ctx.fillText('ARRISCADO', zeroX + (padL + plotW - zeroX) / 2, padT + plotH - 10);

// Axis labels
ctx.fillStyle = '#8899aa';
ctx.font = '10px sans-serif';
ctx.textAlign = 'center';
ctx.fillText('\u2190 Mais conservador (aposta menos gols)', padL + plotW/4, H - 10);
ctx.fillText('Mais ousado (aposta mais gols) \u2192', padL + plotW*3/4, H - 10);
ctx.save();
ctx.translate(12, padT + plotH/2);
ctx.rotate(-Math.PI/2);
ctx.fillText('Media de pontos por jogo \u2191', 0, 0);
ctx.restore();

// Zero line (boldness = bolao avg)
ctx.strokeStyle = 'rgba(245,197,24,0.4)';
ctx.lineWidth = 1;
ctx.setLineDash([4, 4]);
ctx.beginPath(); ctx.moveTo(zeroX, padT); ctx.lineTo(zeroX, padT + plotH); ctx.stroke();
ctx.setLineDash([]);

// Average pts line
ctx.strokeStyle = 'rgba(34,197,94,0.4)';
ctx.lineWidth = 1;
ctx.setLineDash([4, 4]);
ctx.beginPath(); ctx.moveTo(padL, avgYPx); ctx.lineTo(padL + plotW, avgYPx); ctx.stroke();
ctx.setLineDash([]);

// Points
players.forEach(function(p) {
    const x = getX(p.boldness);
    const y = getY(p.avg_pts);
    const radius = 8;
    ctx.fillStyle = '#f5c518';
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#000';
    ctx.font = 'bold 8px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const initial = p.name.charAt(0).toUpperCase();
    ctx.fillText(initial, x, y);
});

// Hover tooltip
canvas.onmousemove = function(e) {
    const r = canvas.getBoundingClientRect();
    const mx = e.clientX - r.left;
    const my = e.clientY - r.top;
    let found = null;
    players.forEach(function(p) {
        const x = getX(p.boldness);
        const y = getY(p.avg_pts);
        const d = Math.sqrt((mx-x)**2 + (my-y)**2);
        if (d < 15) found = p;
    });
    if (found) {
        let quadrant = found.boldness <= 0 && found.avg_pts >= avgY ? 'Eficiente' :
                       found.boldness > 0 && found.avg_pts >= avgY ? 'Ousado' :
                       found.boldness <= 0 && found.avg_pts < avgY ? 'Conservador' : 'Arriscado';
        tooltip.style.display = 'block';
        tooltip.innerHTML = '<strong>' + found.name + '</strong><br>' +
            'Ousadia: ' + found.boldness.toFixed(2) + ' (media ' + found.avg_goals.toFixed(1) + ' gols/jogo)<br>' +
            'Media pts/jogo: ' + found.avg_pts.toFixed(2) + '<br>' +
            'Jogos: ' + found.games + '<br>' +
            'Perfil: ' + quadrant;
        const tx = Math.min(mx + 12, W - 160);
        tooltip.style.left = tx + 'px';
        tooltip.style.top = Math.max(my - 35, 5) + 'px';
    } else {
        tooltip.style.display = 'none';
    }
};
canvas.onmouseleave = function() { tooltip.style.display = 'none'; };
"""

    body = f"""
<div class="hero">
    <h1>\U0001f4ca Boldometro</h1>
    <div class="subtitle">Ousadia vs Aproveitamento — Quem aposta alto e acerta?</div>
</div>

<div class="card" style="margin:1rem 0.75rem;">
    <div class="card-title">O que e o Boldometro?</div>
    <div style="font-size:0.85rem;">
        <p style="margin-bottom:0.5rem;">
            <strong>Ousadia</strong> (eixo X): diferenca entre a <strong>media de gols totais</strong> que voce apostou por jogo
            e a media do bolaao. Se voce aposta sempre 3x0 e a media do bolaao e 2.5 gols, sua ousadia e <strong>+0.5</strong>.
        </p>
        <p style="margin-bottom:0.5rem;">
            <strong>Aproveitamento</strong> (eixo Y): sua <strong>media de pontos por jogo</strong>. Quanto maior, melhor.
        </p>
        <p>
            <strong>Exemplo:</strong> Se voce aposta 1x0 toda partida, sua ousadia e baixa (negativa). Se aposta 5x3, e alta (positiva).
        </p>
    </div>
</div>

<div class="card">
    <div style="position:relative;">
        <canvas id="scatter" width="600" height="380" style="width:100%;height:380px;cursor:crosshair;"></canvas>
        <div id="scatter-tooltip" style="display:none;position:absolute;background:var(--card-bg);border:1px solid var(--card-border);border-radius:8px;padding:0.5rem 0.75rem;font-size:0.75rem;pointer-events:none;z-index:100;box-shadow:0 4px 12px var(--shadow-color);"></div>
    </div>
</div>

<div class="card">
    <div class="card-title">Quadrantes</div>
    <table style="width:100%;font-size:0.85rem;border-collapse:collapse;">
        <tr style="border-bottom:1px solid var(--card-border);"><td style="padding:0.4rem;"><span style="color:#22c55e;font-weight:700;">\u25a0</span> EFICIENTE</td><td style="padding:0.4rem;color:var(--text-muted);">Ousadia baixa (aposta poucos gols), pontuacao alta = voce e conservador e acerta muito</td></tr>
        <tr style="border-bottom:1px solid var(--card-border);"><td style="padding:0.4rem;"><span style="color:#eab308;font-weight:700;">\u25a0</span> OUSADO</td><td style="padding:0.4rem;color:var(--text-muted);">Ousadia alta (aposta muitos gols), pontuacao alta = voce arrisca e acerta</td></tr>
        <tr style="border-bottom:1px solid var(--card-border);"><td style="padding:0.4rem;"><span style="color:#64748b;font-weight:700;">\u25a0</span> CONSERVADOR</td><td style="padding:0.4rem;color:var(--text-muted);">Ousadia baixa (aposta poucos gols), pontuacao baixa = joga seguro mas nao acerta</td></tr>
        <tr><td style="padding:0.4rem;"><span style="color:#ef4444;font-weight:700;">\u25a0</span> ARRISCADO</td><td style="padding:0.4rem;color:var(--text-muted);">Ousadia alta (aposta muitos gols), pontuacao baixa = aposta muitos gols mas erra</td></tr>
    </table>
</div>

<div class="card">
    <div class="card-title">Exemplos — Os mais ousados</div>
    <table style="width:100%;font-size:0.85rem;border-collapse:collapse;">
        <thead>
            <tr style="border-bottom:1px solid var(--card-border);">
                <th style="text-align:left;padding:0.4rem;">Jogador</th>
                <th style="text-align:left;padding:0.4rem;">Ousadia</th>
                <th style="text-align:left;padding:0.4rem;">Media pts</th>
                <th style="text-align:left;padding:0.4rem;">Detalhe</th>
            </tr>
        </thead>
        <tbody>
            {example_rows}
        </tbody>
    </table>
</div>

<script>
{js_code.replace('DATA_PLACEHOLDER', json_str)}
</script>
"""
    return _page_frame(config, f"Boldometro - {config.report_title}", body, back_link="index.html")


# ------------------------------------------------------------------
# Raio-X Radar page
# ------------------------------------------------------------------


def _build_bolao_xray(config: ChampionshipConfig) -> str:
    """Bolão X-ray: meta-analysis of the entire sweepstake — no per-player focus."""
    df_all = pd.read_csv(config.gold_all_path(), sep=",")
    df_valid = df_all[df_all["valido"] == 1].copy() if "valido" in df_all.columns else df_all.copy()
    if df_valid.empty:
        return _page_frame(config, f"Raio-X do Bol\u00e3o - {config.report_title}", "<div class='hero'><h1>\U0001f50d Raio-X do Bol\u00e3o</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados. ainda</div></div>", active_nav="bolao_xray.html")
    df_results = pd.read_csv(config.results_file, sep=",").dropna(subset=["home_goals"])

    # Build resultado_real_placar from raw columns
    df_results["resultado_real_placar"] = df_results.apply(
        lambda r: f"{int(r['home_goals'])} x {int(r['away_goals'])}"
        if pd.notna(r.get("home_goals")) and pd.notna(r.get("away_goals"))
        else "",
        axis=1,
    )

    # Build a lookup: match -> real placar (from first prediction with result)
    match_real_result = df_valid.dropna(subset=["home_goals_real"]).groupby("match").agg(
        home_goals_real=("home_goals_real", "first"),
        away_goals_real=("away_goals_real", "first"),
    ).reset_index()
    match_real_result["real_placar"] = match_real_result.apply(
        lambda r: f"{int(r['home_goals_real'])} x {int(r['away_goals_real'])}", axis=1
    )

    # ----- Snapshot numbers -----
    n_players = df_valid["who"].nunique()
    n_matches = df_valid["match"].nunique()
    n_predictions = len(df_valid)
    total_pts = int(df_valid["pontos"].sum())
    avg_pts_player = round(total_pts / n_players, 1) if n_players else 0
    max_possible = _max_points_per_game(config) * n_matches * n_players
    overall_aproveitamento = round(total_pts / max_possible * 100, 1) if max_possible > 0 else 0

    # ----- Ranking table (moved from overview) -----
    score_names = config.scoring_rule_names()
    agg_cols = ["pontos"] + [c for c in score_names if c in df_valid.columns]
    df_rank = df_valid.groupby("who", as_index=False)[agg_cols].sum()
    df_rank.sort_values("pontos", ascending=False, inplace=True)
    df_rank.reset_index(drop=True, inplace=True)
    df_rank["#"] = range(1, len(df_rank) + 1)
    rank_rows = ""
    for _, row in df_rank.iterrows():
        rank_num = int(row["#"])
        medal = "\U0001f947" if rank_num == 1 else "\U0001f948" if rank_num == 2 else "\U0001f949" if rank_num == 3 else ""
        rank_class = f"rank-{rank_num}" if rank_num <= 3 else ""
        cells = f'<td>{medal} {rank_num}</td><td><a href="boleiros/{row["who"]}.html">{row["who"]}</a></td>'
        cells += f'<td style="font-weight:700;color:var(--accent)">{int(row["pontos"])}</td>'
        for sn in score_names:
            if sn in row.index:
                val = int(row[sn]) if pd.notna(row[sn]) else 0
                cells += f"<td>{val}</td>"
        rank_rows += f'<tr class="{rank_class}">{cells}</tr>\n'
    rank_header = ""
    for sn in score_names:
        emoji = config.scoring_emoji(sn)
        h = f"{emoji} " if emoji else ""
        h += sn.split("-")[0].strip()
        rank_header += f"<th>{h}</th>"

    # ----- Heatmap: player (row) x day (column), color = points -----
    df_heat = df_valid.groupby(["who", "date"], as_index=False)["pontos"].sum()
    # Sort players alphabetically
    player_order = sorted(df_heat["who"].unique())
    date_order = sorted(df_heat["date"].unique())

    # Theoretical max points per day = matches_that_day * max_points_per_game
    matches_per_day = df_valid.groupby("date")["match"].nunique()
    max_pts_per_game = _max_points_per_game(config)

    # Pivot: rows=players, cols=dates
    heat_pivot = df_heat.pivot(index="who", columns="date", values="pontos").fillna(0)
    heat_pivot = heat_pivot.reindex(player_order)
    heat_pivot = heat_pivot[date_order]

    # Color scale: red (0%) → green (100%) via simple RGB
    def _heat_color(pct: float) -> str:
        r = int(200 - pct * 160)
        g = int(55 + pct * 165)
        b = 55
        return f"rgb({r},{g},{b})"

    heat_html = ""
    for player in player_order:
        row = heat_pivot.loc[player]
        cells = ""
        for day in date_order:
            val = int(row[day])
            day_max = int(matches_per_day.get(day, 1) * max_pts_per_game)
            pct = val / day_max if day_max > 0 else 0
            display_val = f"{round(pct * 100)}%"
            bg = _heat_color(pct)
            cells += (
                f'<div class="heat-cell" style="background:{bg};" '
                f'title="{player}: {val} pts de {day_max} max possivel ({display_val})">{display_val}</div>'
            )
        heat_html += (
            f'<div class="heat-row">'
            f'<div class="heat-label">{player}</div>'
            f'<div class="heat-cells">{cells}</div>'
            f'</div>\n'
        )

    # Header row (wrap cells in .heat-cells too, to match data rows alignment)
    header_cells = ""
    for day in date_order:
        d = pd.to_datetime(day).strftime("%d/%m")
        header_cells += f'<div class="heat-cell-header">{d}</div>'
    heat_header = f'<div class="heat-row"><div class="heat-label">Jogador</div><div class="heat-cells">{header_cells}</div></div>\n'

    # Average row: mean points per player per day
    avg_cells = ""
    for day in date_order:
        day_vals = heat_pivot[day].values
        avg = round(sum(day_vals) / len(day_vals), 1)
        avg_cells += f'<div class="heat-cell-header" style="font-weight:600;">{avg}</div>'
    heat_avg = f'<div class="heat-row"><div class="heat-total-label">Media pts/dia</div><div class="heat-cells">{avg_cells}</div></div>\n'

    # Aproveitamento: average of INDIVIDUAL player pcts (each player's pts / theoretical max)
    pct_cells = ""
    for day in date_order:
        day_max = int(matches_per_day.get(day, 1) * max_pts_per_game)
        day_vals = heat_pivot[day].values
        # Each player's individual pct
        individual_pcts = [v / day_max for v in day_vals if day_max > 0]
        avg_pct = round(sum(individual_pcts) / len(individual_pcts) * 100) if individual_pcts else 0
        bg = _heat_color(avg_pct / 100)
        pct_cells += f'<div class="heat-cell" style="background:{bg};">{avg_pct}%</div>'
    heat_pct_row = f'<div class="heat-row"><div class="heat-total-label">Aproveitamento</div><div class="heat-cells">{pct_cells}</div></div>\n'

    # Total row: max possivel per day
    total_cells = ""
    for day in date_order:
        day_max = int(matches_per_day.get(day, 1) * max_pts_per_game)
        total_cells += f'<div class="heat-cell-header" style="font-weight:700;">{day_max}</div>'
    heat_total = f'<div class="heat-row"><div class="heat-total-label">Max possivel</div><div class="heat-cells">{total_cells}</div></div>\n'

    # ----- Hit type distribution (using actual scoring rules from config) -----
    rule_map = {r.name: r.points for r in config.scoring_rules}
    # Order the rules as they appear in config (priority = their index order)
    tipo_order = [r.name for r in config.scoring_rules]

    def _rule_color(rname: str) -> str:
        css_vars = config.scoring_css_var(rname)
        return css_vars[0] if css_vars and css_vars[0] else "var(--text-muted)"

    tipo_counts = df_valid["criterio"].value_counts()
    tipo_rows = ""
    largest_tipo_count = max((int(tipo_counts.get(t, 0)) for t in tipo_order), default=1)
    for t in tipo_order:
        cnt = int(tipo_counts.get(t, 0))
        pts_per = rule_map.get(t, 0)
        pct = round(cnt / n_predictions * 100, 1) if n_predictions else 0
        bar_w = max(cnt / largest_tipo_count * 100, 1)
        name_part = t.split("-", 1)[1] if "-" in t else t
        label = f"{name_part} (+{pts_per}p)" if pts_per > 0 else name_part
        color = _rule_color(t)
        tipo_rows += f"""
        <tr>
            <td style="padding:0.3rem 0.5rem;"><span style="color:{color};font-weight:700;">\u25a0</span> {label}</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;font-weight:600;">{cnt}</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;color:var(--text-muted);">{pct}%</td>
            <td style="padding:0.3rem 0.5rem;width:30%;"><div class="bar-track"><div class="bar-fill" style="width:{bar_w:.0f}%;background:{color};height:10px;"></div></div></td>
        </tr>"""

    # Exact-score rule name from config (e.g. "1-Placar exato")
    exact_rule_name = next((r.name for r in config.scoring_rules if r.rule == "exact_score"), "1-Placar exato")
    exact_points = next((r.points for r in config.scoring_rules if r.rule == "exact_score"), 12)

    # ----- Match predictability: percent who got EXACT SCORE (+{exact_points}) -----
    match_stats = df_valid.groupby("match").agg(
        total=("pontos", "count"),
        exact=("criterio", lambda x: (x == exact_rule_name).sum()),
    ).reset_index()
    match_stats["pct"] = (match_stats["exact"] / match_stats["total"] * 100).round(1)
    match_info = df_valid[["match", "home_team", "away_team"]].drop_duplicates("match")
    match_stats = match_stats.merge(match_info, on="match", how="left")
    match_stats = match_stats.merge(match_real_result[["match", "real_placar"]], on="match", how="left")
    match_stats["real_placar"] = match_stats["real_placar"].fillna("?")

    def _match_rows(subset):
        html = ""
        for _, r in subset.iterrows():
            html += f"<tr><td style='padding:0.3rem 0.5rem;font-size:0.75rem;'>{r['home_team']} vs {r['away_team']}</td><td style='padding:0.3rem 0.5rem;text-align:center;font-weight:600;'>{r['real_placar']}</td><td style='padding:0.3rem 0.5rem;text-align:right;font-weight:600;'>{r['pct']}%</td><td style='padding:0.3rem 0.5rem;text-align:right;color:var(--text-muted);'>{int(r['exact'])}/{int(r['total'])}</td></tr>"
        return html

    top_pred = match_stats.nlargest(10, "pct")
    top_pred_html = _match_rows(top_pred)
    worst_pred = match_stats.nsmallest(10, "pct")
    worst_pred_html = _match_rows(worst_pred)

    # ----- Points histogram: distribution of total points per match -----
    match_pts_total = df_valid.groupby("match")["pontos"].sum().reset_index()
    # Bucket by 20-point ranges
    max_pts_match = int(match_pts_total["pontos"].max())
    bucket_size = 20
    num_buckets = max(1, (max_pts_match // bucket_size) + 1)
    hist_buckets = {}
    for i in range(num_buckets):
        low = i * bucket_size
        high = (i + 1) * bucket_size
        label = f"{low}-{high}"
        count = int(((match_pts_total["pontos"] >= low) & (match_pts_total["pontos"] < high)).sum())
        if count > 0:
            hist_buckets[label] = count
    max_hist = max(hist_buckets.values()) if hist_buckets else 1
    hist_rows = ""
    for label, count in sorted(hist_buckets.items(), key=lambda x: int(x[0].split("-")[0])):
        bar_w = max(count / max_hist * 100, 1)
        hist_rows += f"""
        <tr>
            <td style="padding:0.3rem 0.5rem;font-weight:600;">{label}</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;">{count}</td>
            <td style="padding:0.3rem 0.5rem;width:40%;"><div class="bar-track"><div class="bar-fill" style="width:{bar_w:.0f}%;background:var(--accent);height:12px;"></div></div></td>
        </tr>"""

    # ----- Most predicted scorelines -----
    score_counts = df_valid["resultado_bol_placar"].value_counts().head(10)
    score_rows = ""
    max_score_count = score_counts.iloc[0] if not score_counts.empty else 1
    for placar, cnt in score_counts.items():
        pct = round(cnt / n_predictions * 100, 1) if n_predictions else 0
        bar_w = max(cnt / max_score_count * 100, 1)
        score_rows += f"""
        <tr>
            <td style="padding:0.3rem 0.5rem;font-weight:600;font-size:0.9rem;">{placar}</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;">{cnt}</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;color:var(--text-muted);">{pct}%</td>
            <td style="padding:0.3rem 0.5rem;width:30%;"><div class="bar-track"><div class="bar-fill" style="width:{bar_w:.0f}%;background:var(--accent);height:10px;"></div></div></td>
        </tr>"""

    # ----- Actual score distribution -----
    actual_scores = df_results["resultado_real_placar"].value_counts().head(10)
    actual_rows = ""
    for placar, cnt in actual_scores.items():
        actual_rows += f"""
        <tr><td style="padding:0.3rem 0.5rem;font-weight:600;">{placar}</td><td style="padding:0.3rem 0.5rem;text-align:right;">{cnt}</td></tr>"""

    body = f"""
<div class="hero">
    <h1>\U0001f50d Raio-X do Bol\u00e3o</h1>
    <div class="subtitle">Como o bol\u00e3o inteiro est\u00e1 se comportando</div>
</div>

<!-- Snapshot -->
<div class="stat-row" style="grid-template-columns:repeat(3,1fr);margin:0.75rem;">
    <div class="stat-card stat-card-sm">
        <div class="value" style="color:var(--accent);">{n_players}</div>
        <div class="label">Participantes</div>
    </div>
    <div class="stat-card stat-card-sm">
        <div class="value" style="color:var(--accent);">{n_matches}</div>
        <div class="label">Partidas</div>
    </div>
    <div class="stat-card stat-card-sm">
        <div class="value" style="color:var(--accent);">{n_predictions}</div>
        <div class="label">Palpites</div>
    </div>
</div>
<div class="stat-row" style="grid-template-columns:repeat(3,1fr);margin:0 0.75rem 0.75rem;">
    <div class="stat-card stat-card-sm">
        <div class="value" style="color:var(--voce);">{total_pts}</div>
        <div class="label">Total Pontos</div>
    </div>
    <div class="stat-card stat-card-sm">
        <div class="value" style="color:var(--voce);">{avg_pts_player}</div>
        <div class="label">M\u00e9dia por jogador</div>
    </div>
    <div class="stat-card stat-card-sm">
        <div class="value" style="color:var(--voce);">{overall_aproveitamento}%</div>
        <div class="label">Aproveitamento geral</div>
    </div>
</div>

<!-- Heatmap: player x day -->
<div class="card">
    <div class="card-title">Heatmap: Pontos por dia</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Cada coluna \u00e9 um dia, cada linha \u00e9 um jogador (ordenado do melhor para o pior). A cor varia de <span style="color:rgb(200,55,55);font-weight:700;">\u25a0 vermelho (0%)</span> a <span style="color:rgb(55,220,55);font-weight:700;">\u25a0 verde (100%)</span> conforme o percentual de pontos que o jogador fez em rela\u00e7\u00e3o ao <strong>m\u00e1ximo te\u00f3rico</strong> daquele dia (n\u00ba de jogos \u00d7 {max_pts_per_game} pts). A \u00faltima linha mostra esse m\u00e1ximo te\u00f3rico.</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Role horizontalmente se a tabela n\u00e3o couber na tela.</div>
    <details style="font-size:0.7rem;color:var(--text-muted);margin-top:0.5rem;">
        <summary style="cursor:pointer;font-weight:600;">Como verificar se os n\u00fameros est\u00e3o certos?</summary>
        <ul style="padding-left:1rem;margin-top:0.3rem;">
            <li><strong>Max poss\u00edvel</strong> = n\u00famero de jogos do dia \u00d7 {max_pts_per_game} pts (placar exato). Ex: 3 jogos = {3 * max_pts_per_game} pts m\u00e1x.</li>
            <li><strong>M\u00e9dia pts/dia</strong> = soma dos pontos de todos os jogadores \u00f7 n\u00famero de participantes.</li>
            <li><strong>Aproveitamento</strong> = m\u00e9dia dos percentuais individuais. Para cada jogador: pts dele \u00f7 max te\u00f3rico, depois tira-se a m\u00e9dia entre todos.</li>
            <li>Para validar: pegue um dia, para cada jogador calcule % = pts dele \u00f7 max te\u00f3rico, depois tire a m\u00e9dia. O resultado deve bater com o "Aproveitamento".</li>
        </ul>
    </details>
    <div class="heat-container">
        {heat_header}
        {heat_html}
        {heat_avg}
        {heat_pct_row}
        {heat_total}
    </div>
</div>

<!-- Hit Type Distribution (now with real rule names and points from config) -->
<div class="card">
    <div class="card-title">Distribui\u00e7\u00e3o dos acertos</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Quantos palpites em cada categoria (conforme regras do campeonato)</div>
    <table style="width:100%;font-size:0.8rem;border-collapse:collapse;">
        <tr style="border-bottom:1px solid var(--card-border);color:var(--text-muted);font-size:0.7rem;">
            <th style="text-align:left;padding:0.3rem 0.5rem;">Tipo</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">Qtde</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">%</th>
            <th style="padding:0.3rem 0.5rem;"></th>
        </tr>
        {tipo_rows}
    </table>
</div>

<!-- Points histogram: how many total points per match -->
<div class="card">
    <div class="card-title">Histograma: Pontos por partida</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Quantas partidas renderam X pontos totais (somando todos os jogadores)</div>
    <table style="width:100%;font-size:0.8rem;border-collapse:collapse;">
        <tr style="border-bottom:1px solid var(--card-border);color:var(--text-muted);font-size:0.7rem;">
            <th style="text-align:left;padding:0.3rem 0.5rem;">Faixa de pontos</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">Partidas</th>
            <th style="padding:0.3rem 0.5rem;"></th>
        </tr>
        {hist_rows}
    </table>
</div>

<!-- Most predictable matches (with actual result) -->
<div class="card">
    <div class="card-title">Partidas mais previs\u00edveis</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">As 10 partidas com mais acertos de <strong>placar exato (+{exact_points}p)</strong> — a coluna "Acertaram" mostra quantos jogadores cravaram o placar certo.</div>
    <table style="width:100%;font-size:0.8rem;border-collapse:collapse;">
        <tr style="border-bottom:1px solid var(--card-border);color:var(--text-muted);font-size:0.7rem;">
            <th style="text-align:left;padding:0.3rem 0.5rem;">Partida</th>
            <th style="text-align:center;padding:0.3rem 0.5rem;">Resultado</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">% placar exato</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">Acertaram (+{exact_points}p)</th>
        </tr>
        {top_pred_html}
    </table>
</div>

<!-- Least predictable matches (with actual result) -->
<div class="card">
    <div class="card-title">Partidas menos previs\u00edveis</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">As 10 partidas com menos acertos de <strong>placar exato (+{exact_points}p)</strong> — quase ningu\u00e9m cravou o placar certo.</div>
    <table style="width:100%;font-size:0.8rem;border-collapse:collapse;">
        <tr style="border-bottom:1px solid var(--card-border);color:var(--text-muted);font-size:0.7rem;">
            <th style="text-align:left;padding:0.3rem 0.5rem;">Partida</th>
            <th style="text-align:center;padding:0.3rem 0.5rem;">Resultado</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">% placar exato</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">Acertaram (+{exact_points}p)</th>
        </tr>
        {worst_pred_html}
    </table>
</div>

<!-- Top-10 predicted scorelines -->
<div class="card">
    <div class="card-title">Placares mais apostados</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Os 10 placares que o bol\u00e3o mais apostou (previstos)</div>
    <table style="width:100%;font-size:0.8rem;border-collapse:collapse;">
        <tr style="border-bottom:1px solid var(--card-border);color:var(--text-muted);font-size:0.7rem;">
            <th style="text-align:left;padding:0.3rem 0.5rem;">Placar</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">Apostas</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">%</th>
            <th style="padding:0.3rem 0.5rem;"></th>
        </tr>
        {score_rows}
    </table>
</div>

<!-- Actual score distribution -->
<div class="card">
    <div class="card-title">Placares reais mais comuns</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Os 10 placares que mais aconteceram de verdade</div>
    <table style="width:100%;font-size:0.8rem;border-collapse:collapse;">
        <tr style="border-bottom:1px solid var(--card-border);color:var(--text-muted);font-size:0.7rem;">
            <th style="text-align:left;padding:0.3rem 0.5rem;">Placar</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">Ocorr\u00eancias</th>
        </tr>
        {actual_rows}
    </table>
</div>
"""
    return _page_frame(config, f"Raio-X do Bolão - {config.report_title}", body, back_link="index.html")


# ------------------------------------------------------------------
# Round Winners page
# ------------------------------------------------------------------


def _build_day_winners(config: ChampionshipConfig) -> str:
    """Show day-by-day winners, zebras, and highlights with day selector."""
    df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
    if df_valid.empty:
        return _page_frame(config, "Vencedores do Dia - sem dados", "<div class='hero'><h1>\U0001f3c6 Vencedores do Dia</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados.</div></div>", back_link="index.html")
    df_all = pd.read_csv(config.gold_all_path(), sep=",")
    df_results = pd.read_csv(config.results_file, sep=",")
    upset_path = _norm(os.path.join(config._au_first_round(), "upset_tracker.csv"))
    df_upset = pd.read_csv(upset_path, sep=",") if os.path.exists(upset_path) else pd.DataFrame()
    max_pts = _max_points_per_game(config)

    # Get unique days from games.csv (extract date part since it includes hour)
    df_results["date_only"] = df_results["date"].str.extract(r"(\d{4}-\d{2}-\d{2})", expand=False)
    days = sorted(df_results.dropna(subset=["home_goals"])["date_only"].unique())
    if len(days) == 0:
        days = sorted(df_valid["date"].unique())

    # Pre-build content per day
    day_content = {}
    for day in days:
        day_predictions = df_valid[df_valid["date"] == day]
        day_results = df_results[df_results["date_only"] == day].dropna(subset=["home_goals"])
        if day_predictions.empty:
            continue

        # Day winner: who scored most points this day
        day_pts = day_predictions.groupby("who")["pontos"].sum()
        winner = day_pts.idxmax()
        winner_pts = int(day_pts.max())
        runner_up = day_pts.nlargest(2).index[-1] if len(day_pts) >= 2 else ""
        runner_up_pts = int(day_pts.nlargest(2).iloc[-1]) if len(day_pts) >= 2 else 0

        # Average pts
        avg_pts = round(day_pts.mean(), 1)

        # Matches this day
        matches_this_day = day_predictions["match"].unique()

        # Upsets: matches where the favorite (most predicted winner) was wrong
        day_upsets = df_upset[df_upset["match"].isin(matches_this_day)]
        upsets = day_upsets[day_upsets["is_upset"] == 1]
        upset_list = []
        for _, u in upsets.iterrows():
            upset_list.append(f"{u['home_team']} vs {u['away_team']}: favorito {u['favorite']} perdeu")

        # Most original correct pick
        day_all = df_all[df_all["match"].isin(matches_this_day)]
        original_pick = ""
        if not day_all.empty:
            hits = day_all[day_all["pontos"] > 0]
            if not hits.empty:
                rarity = hits.groupby(["match", "resultado_bol_placar"]).size().reset_index(name="count")
                rarest = rarity.nsmallest(1, "count").iloc[0]
                match_info = hits[
                    (hits["match"] == rarest["match"])
                    & (hits["resultado_bol_placar"] == rarest["resultado_bol_placar"])
                ]
                if not match_info.empty:
                    row = match_info.iloc[0]
                    original_pick = (
                        f"{row['home_team']} {row['resultado_bol_placar']} {row['away_team']} "
                        f"por {row['who']} ({int(row['pontos'])} pts)"
                    )

        # Results summary
        result_lines = ""
        for _, r in day_results.iterrows():
            hg = int(r["home_goals"])
            ag = int(r["away_goals"])
            result_lines += f"<div style='font-size:0.85rem;padding:0.2rem 0;'>{r['home_team']} {hg}-{ag} {r['away_team']}</div>\n"

        day_content[day] = {
            "winner": winner,
            "winner_pts": winner_pts,
            "runner_up": runner_up,
            "runner_up_pts": runner_up_pts,
            "avg_pts": avg_pts,
            "upsets": upset_list,
            "original_pick": original_pick,
            "result_lines": result_lines,
        }

    if not day_content:
        return _page_frame(config, "Vencedores do Dia - sem dados", "<div class='hero'><h1>Vencedores do Dia</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados.</div></div>", back_link="index.html")

    # Day selector options
    day_options = "".join(f'<option value="{d}">{pd.to_datetime(d).strftime("%d/%m (%a)")}</option>' for d in sorted(day_content.keys()))

    # Pre-render all cards (hidden via JS)
    card_html = {}
    for day, content in day_content.items():
        upset_html = ""
        if content["upsets"]:
            for u in content["upsets"]:
                upset_html += f'<div style="font-size:0.85rem;padding:0.2rem 0;color:var(--danger);">\U0001f4a5 {u}</div>\n'
        else:
            upset_html = '<div style="font-size:0.85rem;color:var(--text-muted);font-style:italic;">Nenhuma zebra neste dia</div>\n'

        original_html = ""
        if content["original_pick"]:
            original_html = f'<div style="font-size:0.85rem;margin-top:0.5rem;"><span style="color:var(--accent);font-weight:600;">\U0001f3af Palpite mais original:</span> {content["original_pick"]}</div>\n'
        else:
            original_html = '<div style="font-size:0.85rem;color:var(--text-muted);font-style:italic;">Nenhum palpite original neste dia</div>\n'

        date_display = pd.to_datetime(day).strftime("%d/%m/%Y")

        card_html[day] = f"""
<div class="card" id="day-card-{day}" style="display:none;">
    <div class="stat-row" style="grid-template-columns:repeat(3,1fr);">
        <div class="stat-card stat-card-sm">
            <div class="value" style="color:var(--voce);font-size:1.3rem;">{content["winner_pts"]}</div>
            <div class="label">Melhor do dia</div>
            <div style="font-size:0.8rem;"><a href="boleiros/{content['winner']}.html" style="color:var(--accent);">{content['winner']}</a></div>
        </div>
        <div class="stat-card stat-card-sm">
            <div class="value" style="font-size:1.1rem;">{content["avg_pts"]}</div>
            <div class="label">Media do dia</div>
        </div>
        <div class="stat-card stat-card-sm">
            <div class="value" style="font-size:1.1rem;">{len(content['upsets'])}</div>
            <div class="label">Zebras</div>
        </div>
    </div>
"""
        if content["runner_up"]:
            card_html[day] += f'<div style="font-size:0.85rem;margin-top:0.5rem;">\U0001f948 Vice: {content["runner_up"]} ({content["runner_up_pts"]} pts)</div>\n'

        card_html[day] += f"""
    <div style="margin-top:0.75rem;">
        <div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);margin-bottom:0.25rem;">Resultados do dia</div>
        {content['result_lines']}
    </div>

    <div style="margin-top:0.75rem;">
        <div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);margin-bottom:0.25rem;">\U0001f4a5 Zebras</div>
        <div style="font-size:0.8rem;color:var(--text-muted);margin-bottom:0.25rem;">
            Zebra = quando o time mais votado como vencedor PERDEU ou empatou. O favorito errou.
        </div>
        {upset_html}
    </div>

    <div style="margin-top:0.75rem;">
        {original_html}
    </div>
</div>
"""

    # JS for day switching
    js_code = """
function showDay(day) {
    document.querySelectorAll('[id^="day-card-"]').forEach(function(el) {
        el.style.display = 'none';
    });
    const card = document.getElementById('day-card-' + day);
    if (card) card.style.display = 'block';
}
function onDayChange() {
    const sel = document.getElementById('day-select');
    showDay(sel.value);
}
"""

    body = f"""
<div class="hero">
    <h1>\U0001f3c6 Vencedores do Dia</h1>
    <div class="subtitle">Quem venceu cada dia, zebras e palpites originais</div>
</div>

<div class="card" style="margin:1rem 0.75rem;">
    <label class="arena-label" for="day-select">Selecione o dia</label>
    <select id="day-select" class="arena-select" onchange="onDayChange()">
        {day_options}
    </select>
</div>

<div id="day-cards-container">
    {''.join(card_html.values())}
</div>

<div class="card" style="margin:1rem 0.75rem 0.25rem;font-size:0.85rem;color:var(--text-muted);">
    <p><strong>Criterio de Zebra:</strong> Em cada partida, o sistema calcula o time mais votado como vencedor (o "favorito" do bolaao).
    Se o favorito perdeu ou empatou, a partida e marcada como ZEBRA. Quanto mais zebras, mais imprevisivel foi o dia.</p>
</div>
<div class="card" style="margin:0.25rem 0.75rem 1rem;font-size:0.85rem;color:var(--text-muted);">
    <p><strong>\U0001f3af Palpite mais original:</strong> Dentre todos os palpites <strong>corretos</strong> do dia, o sistema procura o placar que <strong>menos pessoas acertaram</strong>.
    Ou seja, a aposta certa que foi a mais incomum — quase ningu\u00e9m acreditou naquele placar, mas o jogador acertou.
    N\u00e3o \u00e9 necessariamente o maior pontuador do dia; \u00e9 o reconhecimento de uma "aposta ousada que deu certo".</p>
    <p style="margin-top:0.3rem;">Exemplo: Se todo mundo acertou Brasil 2 x 0 Argentina, mas s\u00f3 uma pessoa acertou Alemanha 3 x 2 Fran\u00e7a,
    essa pessoa leva o "palpite mais original" — mesmo que n\u00e3o seja a l\u00edder de pontos do dia.</p>
</div>

<script>
{js_code}
// Show first day on load
document.addEventListener('DOMContentLoaded', function() {{
    const sel = document.getElementById('day-select');
    if (sel && sel.value) showDay(sel.value);
}});
</script>
"""
    return _page_frame(config, f"Vencedores do Dia - {config.report_title}", body, back_link="index.html")


# ------------------------------------------------------------------
# Zebras & Favoritos
# ------------------------------------------------------------------

def _build_zebras(config: ChampionshipConfig) -> str:
    """Show all upset matches, ranking of zebra predictors, and impact analysis."""
    upset_path = _norm(os.path.join(config._au_first_round(), "upset_tracker.csv"))
    if not os.path.exists(upset_path):
        return _page_frame(config, "Zebras", "<div class='hero'><h1>\U0001f993 Zebras & Favoritos</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados.</div></div>", active_nav="zebras.html")

    df_upset = pd.read_csv(upset_path, sep=",")

    if "is_upset" not in df_upset.columns:
        df_upset["is_upset"] = 0

    total_matches = len(df_upset)
    upset_matches = df_upset[df_upset["is_upset"] == 1]
    num_upsets = len(upset_matches)
    upset_pct = round(num_upsets / total_matches * 100, 1) if total_matches else 0

    # Parse players_correct column
    def _parse_correct(val: str) -> list[str]:
        if pd.isna(val) or not val:
            return []
        return [p.strip() for p in str(val).split("|")]

    # Build zebra cards
    zebra_cards = ""
    # Sort by most impactful first (more votes for favorite = bigger upset)
    upset_sorted = upset_matches.sort_values("favorite_votes", ascending=False) if not upset_matches.empty else upset_matches

    for _, row in upset_sorted.iterrows():
        home = str(row.get("home_team", ""))
        away = str(row.get("away_team", ""))
        favorite = str(row.get("favorite", "?"))
        real_winner = str(row.get("real_winner", "?"))
        fav_votes = int(row.get("favorite_votes", 0))
        total_votes = int(row.get("total_votes", 0))
        num_correct = int(row.get("num_correct", 0))
        players_correct = _parse_correct(row.get("players_correct", ""))

        fav_pct = round(fav_votes / total_votes * 100) if total_votes else 0
        players_html = " ".join(f'<span class="tag">{p}</span>' for p in players_correct) if players_correct else '<span style="color:var(--text-muted);font-style:italic;">ningu\u00e9m acertou</span>'

        # Determine upset magnitude
        if fav_pct >= 80:
            magnitude = "\U0001f4a5 ZEBRA MONSTRA"
        elif fav_pct >= 60:
            magnitude = "\U0001f4a5 Zebra Grande"
        elif fav_pct >= 40:
            magnitude = "\U0001f4a5 Zebra Media"
        else:
            magnitude = "\U0001f4a5 Zebra Leve"

        zebra_cards += f"""
<div class="zebra-card upset">
    <div class="zebra-header">
        <span class="zebra-badge upset">{magnitude}</span>
        <span style="font-size:0.75rem;color:var(--text-muted);">{fav_votes}/{total_votes} ({fav_pct}%) acreditavam no {favorite}</span>
    </div>
    <div class="zebra-matchup">{home} vs {away}</div>
    <div class="zebra-detail">
        Favorito: <strong>{favorite}</strong> | Resultado: <strong>{real_winner}</strong><br>
        Acertaram essa zebra: {num_correct} jogadores
    </div>
    <div class="zebra-players">{players_html}</div>
</div>
"""

    # No upsets message
    if not zebra_cards:
        zebra_cards = '<div class="card" style="text-align:center;color:var(--text-muted);font-style:italic;padding:2rem 1rem;">\U0001f614 Nenhuma zebra ate agora — o bolao esta muito previsivel!</div>'

    # Rank zebra predictors (who got the most upsets right)
    correct_counter: dict[str, int] = {}
    for _, row in upset_matches.iterrows():
        for p in _parse_correct(row.get("players_correct", "")):
            correct_counter[p] = correct_counter.get(p, 0) + 1

    zebra_king_rows = ""
    if correct_counter:
        sorted_kings = sorted(correct_counter.items(), key=lambda x: -x[1])
        for i, (name, count) in enumerate(sorted_kings):
            medal = "\U0001f947" if i == 0 else "\U0001f948" if i == 1 else "\U0001f949" if i == 2 else ""
            zebra_king_rows += f"<tr><td>{medal} {i+1}</td><td><a href='boleiros/{name}.html'>{name}</a></td><td style='font-weight:700;color:var(--accent);'>{count}</td></tr>\n"
    else:
        zebra_king_rows = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted);font-style:italic;">Nenhum dado</td></tr>'

    # Non-upset matches (favorites that won) — show a few
    non_upsets = df_upset[df_upset["is_upset"] == 0].head(6)
    fav_won_cards = ""
    for _, row in non_upsets.iterrows():
        home = str(row.get("home_team", ""))
        away = str(row.get("away_team", ""))
        favorite = str(row.get("favorite", "?"))
        fav_votes = int(row.get("favorite_votes", 0))
        total_votes = int(row.get("total_votes", 0))
        fav_pct = round(fav_votes / total_votes * 100) if total_votes else 0
        fav_won_cards += f"""
<div class="zebra-card">
    <div class="zebra-header">
        <span class="zebra-badge favorite">Favorito Venceu</span>
        <span style="font-size:0.75rem;color:var(--text-muted);">{fav_pct}% no favorito</span>
    </div>
    <div class="zebra-matchup">{home} vs {away}</div>
    <div class="zebra-detail">Favorito {favorite} confirmou</div>
</div>
"""

    # --- Partidas Mais Dificies (difficulty ranking) ---
    gold_all = config.gold_all_path()
    df_pred = pd.read_csv(gold_all, sep=",") if os.path.exists(gold_all) else pd.DataFrame()

    diff_matches = []
    for _, row in df_upset.iterrows():
        match = str(row.get("match", ""))
        home = str(row.get("home_team", ""))
        away = str(row.get("away_team", ""))
        favorite = str(row.get("favorite", "?"))
        real_winner = str(row.get("real_winner", "?"))
        fav_votes = int(row.get("favorite_votes", 0))
        total_votes = int(row.get("total_votes", 0))
        is_upset = int(row.get("is_upset", 0))
        num_correct = int(row.get("num_correct", 0))

        if total_votes == 0:
            continue

        exact_score_count = 0
        if not df_pred.empty:
            df_m = df_pred[df_pred["match"] == match]
            if not df_m.empty:
                exact_score_count = len(df_m[
                    (df_m["home_goals_bol"] == df_m["home_goals_real"]) &
                    (df_m["away_goals_bol"] == df_m["away_goals_real"])
                ])

        winner_wrong_pct = 100 - round(num_correct / total_votes * 100)
        exact_pct = round(exact_score_count / total_votes * 100)
        difficulty = winner_wrong_pct * 0.6 + exact_pct * 0.4
        if is_upset:
            difficulty = difficulty * 1.3 + 10

        diff_matches.append({
            "home": home, "away": away, "favorite": favorite,
            "real_winner": real_winner, "num_correct": num_correct,
            "total_votes": total_votes, "is_upset": is_upset,
            "difficulty": round(difficulty, 1),
        })

    diff_cards = ""
    if diff_matches:
        diff_matches.sort(key=lambda x: -x["difficulty"])
        max_diff = diff_matches[0]["difficulty"]
        for i, m in enumerate(diff_matches[:10], 1):
            medal = "\U0001f947" if i == 1 else "\U0001f948" if i == 2 else "\U0001f949" if i == 3 else ""
            upset_tag = '<span style="display:inline-block;font-size:0.65rem;background:rgba(239,68,68,0.2);color:var(--danger);padding:0.15rem 0.5rem;border-radius:999px;margin-left:0.5rem;">\U0001f993 ZEBRA</span>' if m["is_upset"] else ""
            bar_pct = round(m["difficulty"] / max_diff * 100)
            bar_color = "var(--danger)" if m["is_upset"] else "var(--warning)"

            diff_cards += f"""
<div style="margin-bottom:0.75rem;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-weight:700;font-size:0.9rem;">{medal} {m["home"]} vs {m["away"]}{upset_tag}</span>
        <span style="font-weight:700;color:var(--accent);font-size:0.85rem;">{m["difficulty"]}</span>
    </div>
    <div class="bar-track" style="height:5px;margin:0.25rem 0;">
        <div class="bar-fill" style="width:{bar_pct}%;height:5px;background:{bar_color};border-radius:3px;"></div>
    </div>
    <div style="display:flex;gap:0.5rem;font-size:0.7rem;color:var(--text-muted);flex-wrap:wrap;">
        <span>{m["num_correct"]}/{m["total_votes"]} acertaram</span>
        <span>Favorito: {m["favorite"]}</span>
        <span>Resultado: {m["real_winner"]}</span>
    </div>
</div>
"""
    if not diff_cards:
        diff_cards = '<div class="empty-state">Nenhum dado dispon\u00edvel</div>'

    body = f"""
<div class="hero">
    <h1>\U0001f993 Zebras & Favoritos</h1>
    <div class="subtitle">Partidas onde o bolaao inteiro errou — e quem acertou</div>
</div>

<div class="card" style="margin:1rem 0.75rem;">
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;">
        <div class="mini-stat">
            <div class="val">{total_matches}</div>
            <div class="lbl">Partidas</div>
        </div>
        <div class="mini-stat">
            <div class="val" style="color:var(--danger);">{num_upsets}</div>
            <div class="lbl">Zebras</div>
        </div>
        <div class="mini-stat">
            <div class="val">{upset_pct}%</div>
            <div class="lbl">% de Zebras</div>
        </div>
    </div>
</div>

<div class="section">
    <div class="section-title">\U0001f4a5 Zebras do Torneio</div>
    {zebra_cards}
</div>

<div class="section">
    <div class="section-title">\U0001f451 Rei das Zebras</div>
    <div class="card" style="overflow-x:auto;">
        <table class="rank-table">
            <thead><tr><th>#</th><th>Boleiro</th><th>Zebras acertadas</th></tr></thead>
            <tbody>{zebra_king_rows}</tbody>
        </table>
    </div>
</div>

<div class="section">
    <div class="section-title">\U0001f480 Partidas Mais Dif\u00edceis</div>
    <div class="card" style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;padding:0.5rem 0.75rem;">
        <strong>\U0001f4a1 C\u00e1lculo:</strong> <strong>% que errou o vencedor</strong> (peso 60%) + <strong>raridade do placar exato</strong> (peso 40%). Se foi zebra, ganha b\u00f4nus de +30% + 10pts. Quanto maior, mais a partida derrubou o bol\u00e3o.
    </div>
    <div class="card">{diff_cards}</div>
</div>

<div class="section">
    <div class="section-title">\U00002705 Favoritos que Confirmaram</div>
    {fav_won_cards}
</div>

<div class="card" style="margin:0.75rem;font-size:0.8rem;color:var(--text-muted);">
    <p><strong>\U0001f4a1 O que e uma Zebra?</strong> Quando o time mais votado como vencedor pelo bolaao PERDEU ou empatou. Quanto maior a porcentagem de votos no favorito, maior a zebra.</p>
</div>
"""
    return _page_frame(config, f"Zebras - {config.report_title}", body, active_nav="zebras.html")


# ------------------------------------------------------------------
# Momentum & Sequencias
# ------------------------------------------------------------------

def _build_momentum(config: ChampionshipConfig) -> str:
    """Show current streaks, longest streaks, hot/cold players."""
    gold_dir = config._au_first_round()
    consistency_path = _norm(os.path.join(gold_dir, "consistency.csv"))
    ranking_path = _norm(os.path.join(gold_dir, "ranking_history.csv"))

    if not os.path.exists(consistency_path):
        return _page_frame(config, "Momento", "<div class='hero'><h1>\U0001f525 Momento</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados.</div></div>", active_nav="momentum.html")

    df_cons = pd.read_csv(consistency_path, sep=",")

    # Current streak for each player
    df_cons_sorted = df_cons.sort_values(["boleiro", "date"])
    current_streaks: dict[str, dict] = {}
    longest_hot: dict[str, int] = {}
    longest_cold: dict[str, int] = {}

    for boleiro in df_cons["boleiro"].unique():
        df_b = df_cons_sorted[df_cons_sorted["boleiro"] == boleiro]
        # Current streak
        streak_type = ""
        streak_len = 0
        for _, r in reversed(list(df_b.iterrows())):
            st = r.get("streak_type", "")
            if st == "hit":
                if streak_type == "" or streak_type == "hit":
                    streak_type = "hit"
                    streak_len += 1
                else:
                    break
            elif st == "miss":
                if streak_type == "" or streak_type == "miss":
                    streak_type = "miss"
                    streak_len += 1
                else:
                    break
            else:
                break
        current_streaks[boleiro] = {"type": streak_type, "length": streak_len}

        # Longest streaks
        df_b = df_b.reset_index(drop=True)
        hot_max = 0
        cold_max = 0
        cur_hot = 0
        cur_cold = 0
        for _, r in df_b.iterrows():
            st = r.get("streak_type", "")
            if st == "hit":
                cur_hot += 1
                cur_cold = 0
                hot_max = max(hot_max, cur_hot)
            elif st == "miss":
                cur_cold += 1
                cur_hot = 0
                cold_max = max(cold_max, cur_cold)
            else:
                cur_hot = 0
                cur_cold = 0
        longest_hot[boleiro] = hot_max
        longest_cold[boleiro] = cold_max

    # Load avg points for ranking
    df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
    df_avg = df_valid.groupby("who")["pontos"].mean().reset_index()
    df_avg.columns = ["boleiro", "avg_pts"]

    # Build streak bars for current
    players = sorted(current_streaks.keys())
    streak_rows = ""
    for p in players:
        info = current_streaks[p]
        is_hot = info["type"] == "hit"
        is_cold = info["type"] == "miss"
        if is_hot:
            pct = min(info["length"] / 10 * 100, 100)
            fill_class = "hot"
            icon = "\U0001f525"
            label = f"{info['length']} acertos"
        elif is_cold:
            pct = min(info["length"] / 10 * 100, 100)
            fill_class = "cold"
            icon = "\U0001f4a9"
            label = f"{info['length']} erros"
        else:
            pct = 0
            fill_class = ""
            icon = "\U0001f504"
            label = "sem streak"

        avg = df_avg.loc[df_avg["boleiro"] == p, "avg_pts"].values
        avg_str = f"{avg[0]:.1f}" if len(avg) else "-"

        streak_rows += f"""
<div class="streak-row">
    <span>{icon}</span>
    <span class="streak-name"><a href="boleiros/{p}.html">{p}</a></span>
    <span style="font-size:0.75rem;color:var(--text-muted);min-width:25px;">{avg_str}</span>
    <div class="streak-bar-mini"><div class="fill {fill_class}" style="width:{pct}%"></div></div>
    <span class="streak-val">{label}</span>
</div>
"""

    # Longest streaks table
    longest_rows = ""
    all_players_both = set(list(longest_hot.keys()) + list(longest_cold.keys()))
    for p in sorted(all_players_both):
        hot = longest_hot.get(p, 0)
        cold = longest_cold.get(p, 0)
        longest_rows += f"<tr><td><a href='boleiros/{p}.html'>{p}</a></td><td style='color:var(--success);font-weight:700;'>{hot}</td><td style='color:var(--danger);font-weight:700;'>{cold}</td></tr>\n"

    # Current hot streak champions
    hot_players = {p: v for p, v in current_streaks.items() if v["type"] == "hit"}
    top_hot = sorted(hot_players.items(), key=lambda x: -x[1]["length"])[:3]
    hot_championships = ""
    for i, (p, v) in enumerate(top_hot):
        medal = "\U0001f947" if i == 0 else "\U0001f948" if i == 1 else "\U0001f949"
        hot_championships += f"<tr><td>{medal}</td><td><a href='boleiros/{p}.html'>{p}</a></td><td style='font-weight:700;color:var(--success)'>{v['length']} acertos</td></tr>\n"

    if not hot_championships:
        hot_championships = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted);font-style:italic;">Ninguem em streak quente</td></tr>'

    # Cold streak champions
    cold_players = {p: v for p, v in current_streaks.items() if v["type"] == "miss"}
    top_cold = sorted(cold_players.items(), key=lambda x: -x[1]["length"])[:3]
    cold_championships = ""
    for i, (p, v) in enumerate(top_cold):
        medal = "\U0001f947" if i == 0 else "\U0001f948" if i == 1 else "\U0001f949"
        cold_championships += f"<tr><td>{medal}</td><td><a href='boleiros/{p}.html'>{p}</a></td><td style='font-weight:700;color:var(--danger)'>{v['length']} erros</td></tr>\n"

    if not cold_championships:
        cold_championships = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted);font-style:italic;">Ninguem em streak fria</td></tr>'

    body = f"""
<div class="hero">
    <h1>\U0001f525 Momento</h1>
    <div class="subtitle">Sequencias quentes e frias de cada jogador</div>
</div>

<div class="section">
    <div class="section-title">\U0001f4aa Momento Atual</div>
    <div class="card">
        <div style="display:flex;gap:0.75rem;padding:0 0 0.5rem;font-size:0.7rem;color:var(--text-muted);">
            <span style="flex:1;">Jogador</span>
            <span style="min-width:25px;">M\u00e9dia</span>
            <span style="flex:0 0 80px;">Sequ\u00eancia</span>
            <span style="min-width:50px;text-align:right;">Atual</span>
        </div>
        {streak_rows}
    </div>
</div>

<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:0.75rem;margin:0 0.75rem;">
    <div class="card" style="margin:0;">
        <div class="card-title">\U0001f525 Maiores Sequencias Quentes</div>
        <table class="rank-table">
            <thead><tr><th></th><th>Jogador</th><th>Streak</th></tr></thead>
            <tbody>{hot_championships}</tbody>
        </table>
    </div>
    <div class="card" style="margin:0;">
        <div class="card-title">\U0001f4a9 Maiores Sequencias Frias</div>
        <table class="rank-table">
            <thead><tr><th></th><th>Jogador</th><th>Streak</th></tr></thead>
            <tbody>{cold_championships}</tbody>
        </table>
    </div>
</div>

<div class="section">
    <div class="section-title">\U0001f4ca Maiores Sequencias (Geral)</div>
    <div class="card" style="overflow-x:auto;">
        <table class="rank-table">
            <thead><tr><th>Jogador</th><th>\U0001f525 Maior sequ\u00eancia de acertos</th><th>\U0001f4a9 Maior sequ\u00eancia de erros</th></tr></thead>
            <tbody>{longest_rows}</tbody>
        </table>
    </div>
</div>

<div class="card" style="margin:0.75rem;font-size:0.8rem;color:var(--text-muted);">
    <p><strong>\U0001f4a1 O que \u00e9 streak?</strong> Uma sequ\u00eancia de acertos (qualquer pontua\u00e7\u00e3o > 0) ou erros (0 pontos) consecutivos. O "momento atual" mostra a streak MAIS RECENTE de cada jogador.</p>
</div>
"""
    return _page_frame(config, f"Momento - {config.report_title}", body, active_nav="momentum.html")


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------

# --- Analytics HTML helpers (guarded by real results) ---


def _analytics_cleanup(config: ChampionshipConfig, html_base: str) -> None:
    """Delete stale analytics HTML files when no real results exist."""
    if os.path.exists(config.games_file):
        df_games = pd.read_csv(config.games_file, sep=",")
        has_results = not df_games.empty and "home_goals" in df_games.columns and df_games["home_goals"].notna().any()
    else:
        has_results = False
    if not has_results:
        stale = [
            "ranking_evolution.html",
            "boldometer.html",
            "bolao_xray.html",
            "day_winners.html",
            "zebras.html",
            "momentum.html",
        ]
        for name in stale:
            path = _norm(os.path.join(html_base, name))
            if os.path.exists(path):
                os.remove(path)
                print_colored(f"\tremoved stale {name}", "yellow")


def _build_ranking_evolution_page(config: ChampionshipConfig, html_base: str) -> None:
    path = _norm(os.path.join(html_base, "ranking_evolution.html"))
    print_colored("generating ranking_evolution.html", "blue")
    _save(path, _build_ranking_evolution(config))


def _build_boldometer_page(config: ChampionshipConfig, html_base: str) -> None:
    path = _norm(os.path.join(html_base, "boldometer.html"))
    print_colored("generating boldometer.html", "blue")
    _save(path, _build_boldometer(config))


def _build_bolao_xray_page(config: ChampionshipConfig, html_base: str) -> None:
    path = _norm(os.path.join(html_base, "bolao_xray.html"))
    print_colored("generating bolao_xray.html", "blue")
    _save(path, _build_bolao_xray(config))


def _build_day_winners_page(config: ChampionshipConfig, html_base: str) -> None:
    path = _norm(os.path.join(html_base, "day_winners.html"))
    print_colored("generating day_winners.html", "blue")
    _save(path, _build_day_winners(config))


def _build_zebras_page(config: ChampionshipConfig, html_base: str) -> None:
    path = _norm(os.path.join(html_base, "zebras.html"))
    print_colored("generating zebras.html", "blue")
    _save(path, _build_zebras(config))


def _build_momentum_page(config: ChampionshipConfig, html_base: str) -> None:
    path = _norm(os.path.join(html_base, "momentum.html"))
    print_colored("generating momentum.html", "blue")
    _save(path, _build_momentum(config))


def _has_any_valid(config: ChampionshipConfig) -> bool:
    """Check if gold_valid file has at least one row with valido=1."""
    path = config.gold_valid_path()
    if not os.path.exists(path):
        return False
    df = pd.read_csv(path, sep=",")
    if df.empty:
        return False
    if "valido" in df.columns:
        return df["valido"].eq(1).any()
    return False


def generate_html_reports(config: ChampionshipConfig) -> None:
    """Generate all HTML reports from gold-layer data."""
    html_base = _norm(os.path.join(config.reports_dir, "html"))

    # Create / recreate HTML directories (clean jogos to avoid stale files)
    dirs = [
        html_base,
        _norm(os.path.join(html_base, "boleiros")),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    # Clean jogos dirs to avoid stale HTML files from old runs
    jogos_base = _norm(os.path.join(html_base, "jogos"))
    if os.path.exists(jogos_base):
        shutil.rmtree(jogos_base)
    os.makedirs(_norm(os.path.join(jogos_base, config.group_phase_label)))
    for pr in (config.playoff_rounds or []):
        os.makedirs(_norm(os.path.join(jogos_base, pr.key)), exist_ok=True)

    # Load gold data
    gold_all = config.gold_all_path()
    if not os.path.exists(gold_all):
        print_colored(f"no gold data found at {gold_all}, skipping HTML reports", "yellow")
        return
    df_all = pd.read_csv(gold_all, sep=",")

    # --- Per-player ---
    # Use valid if available and non-empty, otherwise fall back to all predictions
    # so boleiro pages are generated even before the tournament starts
    # (all predictions have valido=0 and gold_valid has 0 data rows).
    gold_all = config.gold_all_path()
    if not os.path.exists(gold_all):
        print_colored(f"no gold data found at {gold_all}, skipping HTML reports", "yellow")
        return
    df_all = pd.read_csv(gold_all, sep=",")
    gold_valid = config.gold_valid_path()
    if os.path.exists(gold_valid):
        df_valid = pd.read_csv(gold_valid, sep=",")
        if df_valid.empty:
            df_valid = df_all.copy()
    else:
        df_valid = df_all.copy()
    for boleiro in sorted(df_valid["who"].unique()):
        print_colored(f"generating boleiro html: {boleiro}", "blue")
        html = _build_boleiro(config, boleiro)
        path = _norm(os.path.join(html_base, "boleiros", f"{boleiro}.html"))
        _save(path, html)

    # --- Arena (player comparison) ---
    print_colored("generating arena.html", "blue")
    arena_html = _build_arena(config, df_valid)
    _save(_norm(os.path.join(html_base, "arena.html")), arena_html)

    # --- Per-match (group phase) ---
    group_matches = df_all[df_all["match"].notna()].groupby("match")
    for match, df_match in group_matches:
        print_colored(f"generating match html: {match}", "blue")
        html = _build_match(config, match, config.group_phase_label, df_match)
        first = df_match.iloc[0]
        hour = first.get('hour', '')
        hour_str = str(int(hour)) if pd.notna(hour) and isinstance(hour, (int, float)) else str(hour)
        filename = f"{first['date']}_{hour_str}_{match}.html"
        path = _norm(os.path.join(html_base, "jogos", config.group_phase_label, filename))
        _save(path, html)

    # --- Per-match (playoff rounds) ---
    for pr in (config.playoff_rounds or []):
        phase = pr.key
        playoff_valid_path = config.gold_playoff_valid_path(phase)
        if not os.path.exists(playoff_valid_path):
            continue
        df_phase = pd.read_csv(playoff_valid_path, sep=",")
        if df_phase.empty:
            continue
        phase_matches = df_phase[df_phase["match"].notna()].groupby("match")
        for match, df_match in phase_matches:
            print_colored(f"generating match html: {phase} {match}", "blue")
            html = _build_match(config, match, pr.name, df_match)
            first = df_match.iloc[0]
            hour = first.get('hour', '')
            hour_str = str(int(hour)) if pd.notna(hour) and isinstance(hour, (int, float)) else str(hour)
            filename = f"{first['date']}_{hour_str}_{match}.html"
            path = _norm(os.path.join(html_base, "jogos", phase, filename))
            _save(path, html)

    # --- Analytics-dependent pages ------------------------------------
    # If games.csv has no real results yet, delete any stale HTML files
    # so the user doesn't see outdated data. Pages are regenerated below
    # with placeholder "no data" messages when CSVs are missing.
    _analytics_cleanup(config, html_base)
    # Build pages (each builder handles missing data gracefully)
    _build_ranking_evolution_page(config, html_base)
    _build_boldometer_page(config, html_base)
    _build_bolao_xray_page(config, html_base)
    _build_day_winners_page(config, html_base)
    _build_zebras_page(config, html_base)
    _build_momentum_page(config, html_base)

    # --- New views ---
    build_group_standings_page(config, html_base)
    build_similarity_matrix_page(config, html_base)
    build_round_predictions_page(config, html_base)
    build_round_matrix_page(config, html_base)
    build_all_team_pages(config, html_base)
