"""Generate rich mobile-first HTML reports directly from gold-layer CSV data.

Produces:
  - overview.html (ranking, stats, recent results)
  - Per-participant boleiros/<name>.html (X-ray analysis)
  - Per-match jogos/<phase>/<match>.html (prediction analysis)
"""

from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import pytz

from src.core.config import ChampionshipConfig
from src.core.printing import print_colored


def _norm(path: str) -> str:
    """Normalize a path to the current OS format."""
    return os.path.normpath(path)


# ------------------------------------------------------------------
# Shared CSS block (theme-driven)
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

/* Hero banner */
.hero {
    background: linear-gradient(135deg, var(--primary), var(--primary-light));
    padding: 1.5rem 1rem;
    text-align: center;
    color: #fff;
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
.badge-warning { background: var(--warning); color: #000; }
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
.bar-label { min-width: 80px; color: var(--text-muted); }
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
.rank-table tr:nth-child(even) { background: rgba(255,255,255,0.02); }
.rank-table .rank-1 td { background: rgba(245, 197, 24, 0.1); }
.rank-table .rank-2 td { background: rgba(192, 192, 192, 0.08); }
.rank-table .rank-3 td { background: rgba(205, 127, 50, 0.08); }

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
summary:hover { background: rgba(255,255,255,0.03); }
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

/* Responsive */
@media (min-width: 768px) {
    body { max-width: 800px; margin: 0 auto; }
    .stat-row { grid-template-columns: repeat(3, 1fr); }
}
"""


def _page_frame(config: ChampionshipConfig, title: str, body: str, back_link: str = "") -> str:
    """Wrap body content in the standard HTML page frame."""
    back_html = ""
    if back_link:
        back_html = f'<div class="back-nav"><a href="{back_link}">\u2190 Voltar</a></div>'

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
<div style="text-align:center;padding:2rem 1rem;color:var(--text-muted);font-size:0.75rem;">
    atualizado as {now_str}
</div>
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


def _build_daily_tracking(config: ChampionshipConfig, df_valid: pd.DataFrame, df_results: pd.DataFrame) -> str:
    """Build the daily tracking section for the overview page."""
    max_pts = _max_points_per_game(config)

    # Get last 3 days with results
    cols_res = ["date", "home_team", "home_goals", "away_goals", "away_team"]
    df_games = df_results[cols_res].dropna(how="any").copy()
    df_games["date"] = pd.to_datetime(df_games["date"]).dt.strftime("%Y-%m-%d")
    unique_dates = sorted(df_games["date"].unique(), reverse=True)[:3]

    if not unique_dates:
        return ""

    sections = ""
    for date_str in unique_dates:
        day_games = df_games[df_games["date"] == date_str]
        num_games = len(day_games)
        max_possible = max_pts * num_games

        # Get points for this day
        day_pts = df_valid[df_valid["date"] == date_str].groupby("who", as_index=False)["pontos"].sum()
        if day_pts.empty:
            continue

        # Calculate stats
        total_earned = int(day_pts["pontos"].sum())
        avg_earned = round(day_pts["pontos"].mean(), 1)
        best_player = day_pts.loc[day_pts["pontos"].idxmax()]
        best_name = best_player["who"]
        best_pts = int(best_player["pontos"])
        best_pct = round(best_pts / max_possible * 100) if max_possible > 0 else 0

        date_display = pd.to_datetime(date_str).strftime("%d/%m")

        # Build game results summary
        game_summary = ""
        for _, g in day_games.iterrows():
            hg = int(g["home_goals"])
            ag = int(g["away_goals"])
            game_summary += (
                f'<div class="pred-row" style="padding:0.4rem 0;">'
                f'<div class="pred-info">'
                f'<div class="pred-name" style="font-size:0.85rem">{g["home_team"]} {hg}-{ag} {g["away_team"]}</div>'
                f'</div>'
                f'</div>\n'
            )

        sections += f"""
<details>
    <summary>{date_display} — {num_games} jogos — max {max_possible} pts</summary>
    <div class="content">
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.5rem;margin-bottom:0.75rem;">
            <div class="stat-card" style="padding:0.5rem;">
                <div class="value" style="font-size:1.1rem">{total_earned}</div>
                <div class="label" style="font-size:0.6rem">Total pts</div>
            </div>
            <div class="stat-card" style="padding:0.5rem;">
                <div class="value" style="font-size:1.1rem">{avg_earned}</div>
                <div class="label" style="font-size:0.6rem">Media</div>
            </div>
            <div class="stat-card" style="padding:0.5rem;">
                <div class="value" style="font-size:1.1rem">{best_pct}%</div>
                <div class="label" style="font-size:0.6rem">Melhor</div>
            </div>
        </div>
        <div style="font-size:0.8rem;color:var(--text-muted);margin-bottom:0.5rem;">
            \U0001f3c6 {best_name}: {best_pts}/{max_possible} pts ({best_pct}%)
        </div>
        {game_summary}
    </div>
</details>
"""

    return f"""
<div class="section">
    <div class="section-title">\U0001f4c5 Acompanhamento Diario</div>
    {sections}
</div>
"""


# ------------------------------------------------------------------
# Overview page
# ------------------------------------------------------------------

def _build_overview(config: ChampionshipConfig) -> str:
    """Build the overview.html body."""
    df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
    df_results = pd.read_csv(config.results_file, sep=",")
    max_pts = _max_points_per_game(config)

    # Ranking
    score_names = config.scoring_rule_names()
    agg_cols = ["pontos"] + [c for c in score_names if c in df_valid.columns]
    df_rank = df_valid.groupby("who", as_index=False)[agg_cols].sum()
    df_rank.sort_values("pontos", ascending=False, inplace=True)
    df_rank.reset_index(drop=True, inplace=True)
    df_rank["#"] = range(1, len(df_rank) + 1)
    df_rank.rename(columns={"who": "boleiro"}, inplace=True)

    # Points by date (last 5 days)
    df_pts = df_valid.groupby(["who", "date"], as_index=False).agg({"pontos": "sum"})
    df_pts["date"] = pd.to_datetime(df_pts["date"])
    last_dts = sorted(df_pts["date"].unique())[-5:]
    df_last = df_pts[df_pts["date"].isin(last_dts)]
    if not df_last.empty:
        df_pivot = df_last.pivot(index="who", columns="date", values="pontos").fillna(0).astype(int)
        df_pivot.columns = [c.strftime("%d/%m") for c in df_pivot.columns]
        df_pivot["total"] = df_pivot.sum(axis=1)
        df_pivot.sort_values("total", ascending=False, inplace=True)
    else:
        df_pivot = pd.DataFrame()

    # Last results
    cols_res = ["date", "home_team", "home_goals", "away_goals", "away_team"]
    df_games = df_results[cols_res].dropna(how="any").sort_values("date", ascending=False).head(6)

    # Build ranking rows
    rank_rows = ""
    for _, row in df_rank.iterrows():
        rank_num = int(row["#"])
        medal = ""
        if rank_num == 1:
            medal = "\U0001f947"
        elif rank_num == 2:
            medal = "\U0001f948"
        elif rank_num == 3:
            medal = "\U0001f949"
        rank_class = f"rank-{rank_num}" if rank_num <= 3 else ""
        cells = f'<td>{medal} {rank_num}</td><td><a href="boleiros/{row["boleiro"]}.html">{row["boleiro"]}</a></td>'
        cells += f'<td style="font-weight:700;color:var(--accent)">{int(row["pontos"])}</td>'
        for sn in score_names:
            if sn in row.index:
                val = int(row[sn]) if pd.notna(row[sn]) else 0
                cells += f"<td>{val}</td>"
        rank_rows += f'<tr class="{rank_class}">{cells}</tr>\n'

    # Build points timeline bars with max possible context
    timeline_html = ""
    if not df_pivot.empty:
        # Calculate max possible per player based on their actual games in the shown days
        player_max_dict = {}
        for name in df_pivot.index:
            player_max = 0
            for col in df_pivot.columns:
                if col != "total":
                    # Count how many games this player had on this date
                    date_raw = pd.to_datetime(col, format="%d/%m", errors="coerce")
                    if pd.notna(date_raw):
                        date_str_raw = date_raw.strftime("%Y-%m-%d")
                        n = df_valid[(df_valid["who"] == name) & (df_valid["date"] == date_str_raw)].shape[0]
                        player_max += n * max_pts
            player_max_dict[name] = player_max

        max_val = df_pivot["total"].max()
        if max_val > 0:
            bar_rows = ""
            for name, row in df_pivot.head(10).iterrows():
                total = int(row["total"])
                max_possible = player_max_dict.get(name, 0)
                pct_of_max = round(total / max_possible * 100) if max_possible > 0 else 0
                pct_bar = int(total / max_val * 100)
                bar_rows += (
                    f'<div class="bar-row">'
                    f'<span class="bar-label">{name[:12]}</span>'
                    f'<div class="bar-track"><div class="bar-fill" style="width:{pct_bar}%"></div></div>'
                    f'<span class="bar-pct">{total}/{max_possible} ({pct_of_max}%)</span>'
                    f'</div>\n'
                )
            timeline_html = f'<div class="card"><div class="card-title">Pontuacao por jogador (ultimos dias)</div>{bar_rows}</div>'

    # Build last results with point distribution checklist
    result_rows = ""
    for _, row in df_games.iterrows():
        match_key = f"{row['home_team']}-{row['away_team']}".lower().replace(" ", "_")
        hg = int(row["home_goals"])
        ag = int(row["away_goals"])
        date_info = str(row["date"])

        # Get point distribution for this match
        match_pts = df_valid[df_valid["match"] == match_key] if "match" in df_valid.columns else pd.DataFrame()
        pts_dist = ""
        if not match_pts.empty:
            pts_counts = match_pts["pontos"].value_counts().sort_index(ascending=False)
            for pts, count in pts_counts.items():
                pts_int = int(pts)
                color = "var(--success)" if pts_int >= 7 else "var(--warning)" if pts_int >= 5 else "var(--text-muted)"
                pts_dist += f'<span style="color:{color};font-size:0.75rem;margin-right:0.5rem;">{pts_int}pts: {count}</span>'

        result_rows += (
            f'<div class="pred-row">'
            f'<div class="pred-info">'
            f'<div class="pred-name">{row["home_team"]} vs {row["away_team"]}</div>'
            f'<div class="pred-detail">{date_info}</div>'
            f'<div style="margin-top:0.25rem;">{pts_dist}</div>'
            f'</div>'
            f'<div class="pred-points" style="color:var(--accent)">{hg} - {ag}</div>'
            f'</div>\n'
        )

    daily_tracking = _build_daily_tracking(config, df_valid, df_results)

    body = f"""
<div class="hero">
    <h1>\U0001f3c6 {config.report_title}</h1>
    <div class="subtitle">Bolao Dashboard</div>
</div>

{daily_tracking}

<div class="section">
    <div class="section-title">\U0001f3c6 Ranking</div>
    <div class="card" style="overflow-x:auto;">
        <table class="rank-table">
            <thead><tr><th>#</th><th>Boleiro</th><th>Pts</th>"""
    for sn in score_names:
        body += f"<th>{sn.split('-')[0].strip()}</th>"
    body += f"""</tr></thead>
            <tbody>{rank_rows}</tbody>
        </table>
    </div>
</div>

{timeline_html}

<div class="section">
    <div class="section-title">\u26bd Ultimos Resultados</div>
    <div class="card">{result_rows}</div>
</div>
"""
    return _page_frame(config, f"Overview - {config.report_title}", body, back_link="index.html")


# ------------------------------------------------------------------
# Per-player page
# ------------------------------------------------------------------

def _build_boleiro(config: ChampionshipConfig, boleiro: str) -> str:
    """Build a per-player HTML report."""
    df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
    df_striker = pd.read_csv(config.playoff_strikers_path(), sep=",")
    max_pts = _max_points_per_game(config)

    df_bol = df_valid.loc[df_valid["who"] == boleiro].copy()
    df_bol = df_bol.sort_values(["date", "hour"], ascending=True)
    df_bol["pontos_acumulados"] = df_bol["pontos"].cumsum()

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
                pct_bar = int(pts / max_date_pts * 100)
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
                p_pct = int(p_pts / max_val * 100)
                b_pct = int(b_avg / max_val * 100)
                diff = p_pts - b_avg
                diff_color = "var(--success)" if diff >= 0 else "var(--danger)"
                diff_icon = "\u25b2" if diff >= 0 else "\u25bc"
                compare_bars += (
                    f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;font-size:0.8rem;">'
                    f'<span style="min-width:40px;color:var(--text-muted)">{row["date_str"]}</span>'
                    f'<div style="flex:1;">'
                    f'<div style="display:flex;align-items:center;gap:0.25rem;">'
                    f'<span style="min-width:40px;color:var(--accent)">Voce</span>'
                    f'<div class="bar-track" style="height:14px;"><div class="bar-fill" style="width:{p_pct}%;background:var(--accent)"></div></div>'
                    f'<span style="min-width:30px;text-align:right">{p_pts}</span>'
                    f'</div>'
                    f'<div style="display:flex;align-items:center;gap:0.25rem;">'
                    f'<span style="min-width:40px;color:var(--text-muted)">Bolao</span>'
                    f'<div class="bar-track" style="height:14px;"><div class="bar-fill" style="width:{b_pct}%"></div></div>'
                    f'<span style="min-width:30px;text-align:right">{b_avg}</span>'
                    f'</div>'
                    f'</div>'
                    f'<span style="color:{diff_color};min-width:40px;text-align:right;font-weight:700">{diff_icon}{abs(diff):.1f}</span>'
                    f'</div>\n'
                )

    # Match history rows (newest first)
    df_hist = df_bol.sort_values(["date", "hour"], ascending=False)
    history_rows = ""
    for _, row in df_hist.iterrows():
        pts = int(row["pontos"])
        pts_color = "var(--success)" if pts >= 7 else "var(--warning)" if pts >= 5 else "var(--text-muted)"
        pts_icon = "\u2705" if pts >= 7 else "\u26a0\ufe0f" if pts > 0 else "\u274c"
        date_str = pd.to_datetime(row["date"]).strftime("%d/%m")
        history_rows += (
            f'<div class="pred-row">'
            f'<div class="pred-info">'
            f'<div class="pred-name">{row["home_team"]} {row["resultado_real_placar"]} {row["away_team"]}</div>'
            f'<div class="pred-detail">Previsto: {row["resultado_bol_placar"]} | {row["criterio"]}</div>'
            f'<div class="pred-detail">{date_str}</div>'
            f'</div>'
            f'<div class="pred-points" style="color:{pts_color}">+{pts} {pts_icon}</div>'
            f'</div>\n'
        )

    body = f"""
<div class="hero">
    <h1>\U0001f464 {boleiro}</h1>
    <div class="subtitle">{config.report_title}</div>
</div>

<div class="stat-row" style="grid-template-columns:repeat(2,1fr);">
    <div class="stat-card">
        <div class="value">{total_pts}</div>
        <div class="label">Total</div>
    </div>
    <div class="stat-card">
        <div class="value">{avg_per_game}</div>
        <div class="label">Media/Jogo ({num_games})</div>
    </div>
</div>
<div class="stat-row" style="grid-template-columns:repeat(2,1fr);margin-top:0;">
    <div class="stat-card">
        <div class="value">{avg_per_day}</div>
        <div class="label">Media/Dia ({num_days})</div>
    </div>
    <div class="stat-card">
        <div class="value">{round(total_pts / (num_games * max_pts) * 100, 1) if num_games > 0 else 0}%</div>
        <div class="label">Aproveitamento</div>
    </div>
</div>
"""

    if striker_name:
        body += f'<div class="striker-badge"><span class="icon">\U0001f3af</span> Artilheiro: <strong>{striker_name}</strong></div>\n'

    if timeline_bars:
        body += f'<div class="card"><div class="card-title">Pontos por dia</div><div class="bar-chart">{timeline_bars}</div></div>\n'

    if compare_bars:
        body += f'<div class="card"><div class="card-title">Pontos por Dia — Voce vs Bolao</div><div style="padding:0.5rem 0;">{compare_bars}</div></div>\n'

    body += f"""
<div class="section">
    <div class="section-title">\U0001f4cb Historico de Jogos ({num_games})</div>
    <div class="card">{history_rows}</div>
</div>
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
            f'<span class="bar-pct">{pct}% ({count} de {total_t})</span>'
            f'</div>\n'
        )

    # Pre-game: score distribution
    df_pre_placar = df_match[["resultado_bol_time", "resultado_bol_placar"]].value_counts().reset_index()
    df_pre_placar.columns = ["vencedor", "placar", "#"]
    df_pre_placar.sort_values("#", ascending=False, inplace=True)
    score_bars = ""
    total_s = int(df_pre_placar["#"].sum())
    for _, row in df_pre_placar.head(8).iterrows():
        pct = round(row["#"] / total_s * 100)
        count = int(row["#"])
        score_bars += (
            f'<div class="bar-row">'
            f'<span class="bar-label">{row["placar"]}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>'
            f'<span class="bar-pct">{pct}% ({count})</span>'
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
    pred_rows = ""
    for _, row in df_match.iterrows():
        pts = int(row["pontos"])
        pts_color = "var(--success)" if pts >= 7 else "var(--warning)" if pts >= 5 else "var(--text-muted)"
        pts_icon = "\u2705" if pts >= 7 else "\u26a0\ufe0f" if pts > 0 else "\u274c"
        pred_rows += (
            f'<div class="pred-row">'
            f'{_avatar_html(row["who"])}'
            f'<div class="pred-info">'
            f'<div class="pred-name">{row["who"]}</div>'
            f'<div class="pred-detail">Previsto: {row["resultado_bol_placar"]} | {row["criterio"]}</div>'
            f'</div>'
            f'<div class="pred-points" style="color:{pts_color}">+{pts} {pts_icon}</div>'
            f'</div>\n'
        )

    # Score display
    if has_result:
        parts = real_placar.split(" x ")
        score_html = f"""
<div class="score-card">
    <div class="team">{home}</div>
    <div class="score">{parts[0]} - {parts[1]}</div>
    <div class="team">{away}</div>
</div>
<div style="text-align:center;"><span class="badge badge-success">Resultado Final</span></div>
"""
    else:
        score_html = f"""
<div class="score-card">
    <div class="team">{home}</div>
    <div class="score">vs</div>
    <div class="team">{away}</div>
</div>
<div style="text-align:center;"><span class="badge badge-warning">Aguardando resultado</span></div>
"""

    body = f"""
<div class="hero">
    <h1>\u26bd {home} x {away}</h1>
    <div class="subtitle">{date_str} {hour_str} | {phase}</div>
</div>

{score_html}

<div class="section">
    <div class="section-title">\U0001f52e Pre-Jogo - Votos por Time</div>
    <div class="card"><div class="bar-chart">{team_bars}</div></div>
</div>

<div class="section">
    <div class="section-title">\U0001f52e Pre-Jogo - Distribuicao de Placar</div>
    <div class="card"><div class="bar-chart">{score_bars}</div></div>
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

    # Embed player data as JSON
    player_json = {}
    for p in players:
        df_p = df_valid[df_valid["who"] == p].copy()
        df_p["date"] = pd.to_datetime(df_p["date"])
        daily = df_p.groupby("date")["pontos"].sum().reset_index()
        daily["date_str"] = daily["date"].dt.strftime("%d/%m")
        recent = df_p.sort_values("date", ascending=False).head(10)
        player_json[p] = {
            "total": int(df_p["pontos"].sum()),
            "avg": round(df_p["pontos"].mean(), 1),
            "games": len(df_p),
            "daily": [{"date": r["date_str"], "pts": int(r["pontos"])} for _, r in daily.iterrows()],
            "recent": [{"match": f"{r['home_team']} {r['resultado_real_placar']} {r['away_team']}", "pts": int(r["pontos"]), "date": pd.to_datetime(r["date"]).strftime("%d/%m")} for _, r in recent.iterrows()]
        }

    import json
    json_str = json.dumps(player_json, ensure_ascii=False)

    js_code = r"""
const playerData = PLAYER_DATA_PLACEHOLDER;

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

    // Daily comparison
    const dailyDiv = document.getElementById('daily-comparison');
    const allDates = [...new Set([...d1.daily.map(d => d.date), ...d2.daily.map(d => d.date)])].sort();
    const maxDaily = Math.max(...d1.daily.map(d => d.pts), ...d2.daily.map(d => d.pts), 1);

    let dailyHtml = '';
    allDates.forEach(function(date) {
        const v1 = d1.daily.find(d => d.date === date);
        const v2 = d2.daily.find(d => d.date === date);
        const pts1 = v1 ? v1.pts : 0;
        const pts2 = v2 ? v2.pts : 0;
        const pct1 = Math.round(pts1 / maxDaily * 100);
        const pct2 = Math.round(pts2 / maxDaily * 100);
        const diff = pts1 - pts2;
        const diffColor = diff >= 0 ? 'var(--success)' : 'var(--danger)';
        const diffIcon = diff >= 0 ? '\u25B2' : '\u25BC';

        dailyHtml += '<div style="margin-bottom:0.4rem;font-size:0.8rem;">' +
            '<div style="color:var(--text-muted);margin-bottom:0.15rem;">' + date + '</div>' +
            '<div style="display:flex;align-items:center;gap:0.25rem;">' +
            '<span style="min-width:30px;color:var(--accent);font-size:0.75rem;">P1</span>' +
            '<div class="bar-track" style="height:12px;flex:1;"><div class="bar-fill" style="width:' + pct1 + '%;background:var(--accent);"></div></div>' +
            '<span style="min-width:25px;text-align:right;font-size:0.75rem;">' + pts1 + '</span>' +
            '</div>' +
            '<div style="display:flex;align-items:center;gap:0.25rem;">' +
            '<span style="min-width:30px;color:var(--text-muted);font-size:0.75rem;">P2</span>' +
            '<div class="bar-track" style="height:12px;flex:1;"><div class="bar-fill" style="width:' + pct2 + '%;"></div></div>' +
            '<span style="min-width:25px;text-align:right;font-size:0.75rem;">' + pts2 + '</span>' +
            '</div>' +
            '<div style="text-align:right;color:' + diffColor + ';font-size:0.7rem;font-weight:700;">' + diffIcon + Math.abs(diff) + '</div>' +
            '</div>';
    });
    dailyDiv.innerHTML = dailyHtml;

    // Recent games comparison
    const recentDiv = document.getElementById('recent-comparison');
    const maxRecent = Math.max(...d1.recent.map(r => r.pts), ...d2.recent.map(r => r.pts), 1);
    let recentHtml = '';
    const maxLen = Math.max(d1.recent.length, d2.recent.length);
    for (let i = 0; i < maxLen; i++) {
        const r1 = d1.recent[i];
        const r2 = d2.recent[i];
        if (r1) {
            const pct1 = Math.round(r1.pts / maxRecent * 100);
            recentHtml += '<div style="margin-bottom:0.3rem;font-size:0.75rem;">' +
                '<div style="display:flex;align-items:center;gap:0.25rem;">' +
                '<span style="min-width:30px;color:var(--accent);">' + r1.date + '</span>' +
                '<div class="bar-track" style="height:10px;flex:1;"><div class="bar-fill" style="width:' + pct1 + '%;background:var(--accent);"></div></div>' +
                '<span style="min-width:20px;text-align:right;">' + r1.pts + '</span>' +
                '</div></div>';
        }
        if (r2) {
            const pct2 = Math.round(r2.pts / maxRecent * 100);
            recentHtml += '<div style="margin-bottom:0.3rem;font-size:0.75rem;">' +
                '<div style="display:flex;align-items:center;gap:0.25rem;">' +
                '<span style="min-width:30px;color:var(--text-muted);">' + r2.date + '</span>' +
                '<div class="bar-track" style="height:10px;flex:1;"><div class="bar-fill" style="width:' + pct2 + '%;"></div></div>' +
                '<span style="min-width:20px;text-align:right;">' + r2.pts + '</span>' +
                '</div></div>';
        }
    }
    recentDiv.innerHTML = recentHtml;
}
"""

    body = f"""
<div class="hero">
    <h1>\u2694\ufe0f Arena</h1>
    <div class="subtitle">Compare dois boleiros</div>
</div>

<div class="card" style="margin:1rem 0.75rem;">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
        <div>
            <label style="font-size:0.8rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Jogador 1</label>
            <select id="player1" onchange="updateArena()" style="width:100%;padding:0.5rem;background:var(--card-bg);color:var(--text);border:1px solid var(--card-border);border-radius:6px;font-size:0.9rem;">
                <option value="">Selecione...</option>
                {options}
            </select>
        </div>
        <div>
            <label style="font-size:0.8rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Jogador 2</label>
            <select id="player2" onchange="updateArena()" style="width:100%;padding:0.5rem;background:var(--card-bg);color:var(--text);border:1px solid var(--card-border);border-radius:6px;font-size:0.9rem;">
                <option value="">Selecione...</option>
                {options}
            </select>
        </div>
    </div>
</div>

<div id="arena-content" style="display:none;">
    <div class="stat-row" style="grid-template-columns:repeat(3,1fr);">
        <div class="stat-card" id="p1-total">
            <div class="value">-</div>
            <div class="label">Total</div>
        </div>
        <div class="stat-card" style="background:var(--card-border);">
            <div class="value" style="font-size:1.2rem;">VS</div>
            <div class="label">Comparacao</div>
        </div>
        <div class="stat-card" id="p2-total">
            <div class="value">-</div>
            <div class="label">Total</div>
        </div>
    </div>

    <div class="stat-row" style="grid-template-columns:repeat(4,1fr);">
        <div class="stat-card" id="p1-avg">
            <div class="value" style="font-size:1.1rem;">-</div>
            <div class="label">Media/Jogo</div>
        </div>
        <div class="stat-card" id="p1-games">
            <div class="value" style="font-size:1.1rem;">-</div>
            <div class="label">Jogos</div>
        </div>
        <div class="stat-card" id="p2-avg">
            <div class="value" style="font-size:1.1rem;">-</div>
            <div class="label">Media/Jogo</div>
        </div>
        <div class="stat-card" id="p2-games">
            <div class="value" style="font-size:1.1rem;">-</div>
            <div class="label">Jogos</div>
        </div>
    </div>

    <div class="card">
        <div class="card-title">Pontos por Dia</div>
        <div id="daily-comparison"></div>
    </div>

    <div class="card">
        <div class="card-title">Ultimos 10 Jogos</div>
        <div id="recent-comparison"></div>
    </div>
</div>

<script>
{js_code.replace('PLAYER_DATA_PLACEHOLDER', json_str)}
</script>
"""
    return _page_frame(config, f"Arena - {config.report_title}", body, back_link="index.html")


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------

def generate_html_reports(config: ChampionshipConfig) -> None:
    """Generate all HTML reports from gold-layer data."""
    html_base = _norm(os.path.join(config.reports_dir, "html"))

    # Create HTML directories
    dirs = [
        html_base,
        _norm(os.path.join(html_base, "boleiros")),
        _norm(os.path.join(html_base, "jogos", config.group_phase_label)),
    ]
    for pr in config.playoff_rounds:
        dirs.append(_norm(os.path.join(html_base, "jogos", pr.key)))
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    # Load gold data
    df_all = pd.read_csv(config.gold_all_path(), sep=",")

    # --- Overview ---
    print_colored("generating overview.html", "blue")
    overview_html = _build_overview(config)
    _save(config.overview_html_path(), overview_html)

    # --- Per-player ---
    df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
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
        filename = f"{first['date']}_{first.get('hour', '')}_{match}.html"
        path = _norm(os.path.join(html_base, "jogos", config.group_phase_label, filename))
        _save(path, html)

    # --- Per-match (playoff rounds) ---
    for pr in config.playoff_rounds:
        try:
            gold_path = config.gold_all_path(phase=pr.key)
            if os.path.exists(gold_path):
                df_po = pd.read_csv(gold_path, sep=",")
                po_matches = df_po[df_po["match"].notna()].groupby("match")
                for match, df_match in po_matches:
                    print_colored(f"generating playoff match html: {match}", "blue")
                    html = _build_match(config, match, pr.name, df_match)
                    first = df_match.iloc[0]
                    filename = f"{first['date']}_{first.get('hour', '')}_{match}.html"
                    path = _norm(os.path.join(html_base, "jogos", pr.key, filename))
                    _save(path, html)
        except Exception:
            pass
