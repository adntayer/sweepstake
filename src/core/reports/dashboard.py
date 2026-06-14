"""Generate the index.html dashboard - mobile-first with hero, leaderboard, player grid."""

from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime, timedelta
from glob import glob

import pandas as pd
import pytz

from src.core.config import ChampionshipConfig
from src.core.logo_fetcher import _team_logo_tag
from src.core.printing import print_colored
from src.core.reports.utils import compute_pending_matches
from src.core.reports.html import ZEBRA_MONSTRA_EMOJI, ZEBRA_GRANDE_EMOJI, ZEBRA_MONSTRA_LABEL, ZEBRA_GRANDE_LABEL


def _norm(path: str) -> str:
    """Normalize a path to the current OS format."""
    return os.path.normpath(path)


def _load_gold_data(config: ChampionshipConfig) -> pd.DataFrame:
    """Load gold data — prefers valid, falls back to all predictions.

    This ensures the dashboard shows participants even when no real
    results exist yet (all predictions have ``valido=0``).
    """
    valid_path = config.gold_valid_path()
    all_path = config.gold_all_path()
    if os.path.exists(valid_path):
        df = pd.read_csv(valid_path, sep=",")
        if not df.empty:
            return df
    if os.path.exists(all_path):
        df = pd.read_csv(all_path, sep=",")
        if not df.empty and "who" in df.columns:
            return df
    return pd.DataFrame()


def _initials(name: str) -> str:
    """Get initials from a name (max 2 chars)."""
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


# ------------------------------------------------------------------
# Shared CSS
# ------------------------------------------------------------------

_CSS_DASHBOARD = """
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

/* Hero */
.hero {
    background: var(--bg);
    padding: 2rem 1rem;
    text-align: center;
    color: var(--text);
    border-bottom: 1px solid var(--card-border);
}
.hero h1 { font-size: 1.75rem; margin-bottom: 0.25rem; }
.hero .subtitle { font-size: 1rem; opacity: 0.85; }

/* Section */
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

/* Card */
.card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 1rem;
    margin: 0 0.75rem;
}

/* Live badge */
.live-badge {
    position: absolute;
    top: -0.25rem;
    right: 0.75rem;
    background: var(--danger);
    color: var(--text);
    font-size: 0.6rem;
    font-weight: 700;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    z-index: 1;
}

/* Score card (last result) */
.result-card {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 1rem;
    padding: 1.25rem 1rem;
}
.result-card .team { flex: 1; text-align: center; font-size: 1rem; font-weight: 600; }
.result-card .score {
    color: var(--accent);
    font-size: 1.75rem;
    font-weight: 700;
    white-space: nowrap;
}
.result-card .date {
    text-align: center;
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 0.25rem;
}

/* Leaderboard */
.lb-row {
    display: flex;
    align-items: center;
    padding: 0.6rem 0;
    border-bottom: 1px solid var(--card-border);
    gap: 0.75rem;
}
.lb-row:last-child { border-bottom: none; }
.lb-rank {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.8rem;
    flex-shrink: 0;
}
.lb-rank-1 { background: var(--accent); color: var(--text-inverse); }
.lb-rank-2 { background: var(--silver); color: var(--text-inverse); }
.lb-rank-3 { background: var(--bronze); color: var(--text); }
.lb-rank-n { background: var(--card-border); color: var(--text-muted); }
.lb-name { flex: 1; font-weight: 600; font-size: 0.9rem; }
.lb-pts {
    font-weight: 700;
    color: var(--accent);
    font-size: 0.95rem;
    flex-shrink: 0;
}

/* Rank table (copied from html.py for the full ranking) */
.rank-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.rank-table th { text-align: left; padding: 0.4rem 0.5rem; font-size: 0.7rem; color: var(--text-muted); border-bottom: 1px solid var(--card-border); white-space: nowrap; }
.rank-table td { padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--card-border); white-space: nowrap; }
.rank-table tr:nth-child(even) { background: var(--zebra-stripe); }
.rank-table .rank-1 td { background: var(--accent-highlight); }
.rank-table .rank-2 td { background: var(--silver-highlight); }
.rank-table .rank-3 td { background: var(--bronze-highlight); }

/* Horizontal scroll for upcoming games */
.scroll-row {
    display: flex;
    overflow-x: auto;
    gap: 0.75rem;
    padding: 0.75rem;
    -webkit-overflow-scrolling: touch;
    scroll-snap-type: x mandatory;
}
.scroll-row::-webkit-scrollbar { height: 4px; }
.scroll-row::-webkit-scrollbar-thumb { background: var(--card-border); border-radius: 4px; }

.game-card, a.game-card {
    flex: 0 0 auto;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 10px;
    padding: 0.5rem 0.75rem;
    text-align: center;
    min-width: 140px;
    display: block;
    text-decoration: none;
    color: inherit;
}
.game-card .matchup { font-weight: 600; font-size: 0.85rem; margin: 0.25rem 0; }
.game-card .datetime { font-size: 0.7rem; color: var(--text-muted); }
.game-card .badge-live {
    display: inline-block;
    background: var(--danger);
    color: var(--text);
    font-size: 0.6rem;
    font-weight: 700;
    padding: 0.1rem 0.4rem;
    border-radius: 999px;
    margin-bottom: 0.25rem;
}

/* Player grid */
.player-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
    padding: 0 0.75rem;
}
.player-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 10px;
    padding: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    transition: border-color 0.2s;
}
.player-card:hover { border-color: var(--accent); }
.player-card:active { border-color: var(--accent); background: var(--player-card-active); }
.player-avatar {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: var(--primary);
    color: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.9rem;
    flex-shrink: 0;
}
.player-name {
    font-weight: 600;
    font-size: 0.85rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.player-pts {
    font-size: 0.75rem;
    color: var(--text-muted);
}

/* Accordion */
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
details .content { padding: 0.5rem 1rem; }
details .content a {
    display: block;
    padding: 0.4rem 0;
    font-size: 0.85rem;
    border-bottom: 1px solid var(--card-border);
}
details .content a:last-child { border-bottom: none; }

/* Compact accordion (emoji legend) */
details.accordion-emoji { margin: 0.75rem 0.75rem 0.5rem; }
details.accordion-emoji summary { padding: 0.4rem 0.6rem; font-size: 0.75rem; min-height: 32px; }
details.accordion-emoji .content { padding: 0.25rem 0.6rem 0.4rem; }
details.accordion-emoji .emoji-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.2rem 0;
    font-size: 0.7rem;
    border-bottom: 1px solid var(--card-border);
}
details.accordion-emoji .emoji-row:last-child { border-bottom: none; }
details.accordion-emoji .emoji-row .e { font-size: 0.9rem; width: 1.2rem; text-align: center; flex-shrink: 0; }
details.accordion-emoji .emoji-row .pts { color: var(--accent); font-weight: 600; width: 1.8rem; text-align: right; flex-shrink: 0; }

/* Footer */
.footer {
    text-align: center;
    padding: 2rem 1rem;
    color: var(--text-muted);
    font-size: 0.75rem;
}

/* Empty state */
.empty-state {
    text-align: center;
    padding: 1.5rem 1rem;
    color: var(--text-muted);
    font-size: 0.85rem;
    font-style: italic;
}

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

/* Status badges for match results */
.badge-result { display:inline-block; padding:0.1rem 0.4rem; border-radius:999px; font-size:0.65rem; font-weight:600; margin-left:0.3rem; }
.badge-result.green { background:var(--success); color:#fff; }
.badge-result.yellow { background:var(--warning); color:var(--text-inverse); }
.badge-result.blue { background:var(--primary); color:#fff; }

/* Pending summary badge in hero */
.hero-badge { display:inline-flex; align-items:center; gap:0.4rem; margin-top:0.4rem; padding:0.3rem 0.8rem; border-radius:999px; font-size:0.8rem; }
.hero-badge.green { background:rgba(34,197,94,0.2); }
.hero-badge.yellow { background:rgba(245,158,11,0.2); }
.hero-badge.gray { background:rgba(136,153,170,0.2); color:var(--text-muted); }

/* Responsive */
/* Team logos */
.team-logo { width: 28px; height: 28px; object-fit: contain; vertical-align: middle; border-radius: 4px; }
.team-logo-sm { width: 24px; height: 24px; object-fit: contain; vertical-align: middle; border-radius: 3px; }
.team-logo-lg { width: 48px; height: 48px; object-fit: contain; vertical-align: middle; border-radius: 6px; }

@media (max-width: 359px) {
    .hero h1 { font-size: 1.4rem; }
    .hero .subtitle { font-size: 0.85rem; }
    .bottom-nav a { font-size: 0.55rem; }
    .bottom-nav a .nav-icon { font-size: 1rem; }
}
@media (min-width: 768px) {
    body { max-width: 800px; margin: 0 auto; }
    .player-grid { grid-template-columns: repeat(3, 1fr); }
    .game-card { flex: 0 0 45%; }
}
@media (min-width: 1024px) {
    .player-grid { grid-template-columns: repeat(4, 1fr); }
    .game-card { flex: 0 0 30%; }
}
"""


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _get_upcoming_games(html_base: str, config: ChampionshipConfig, limit: int = 4) -> list[dict]:
    """Find upcoming game HTML files and return structured data."""
    tz = pytz.timezone(config.timezone)
    now = datetime.now(tz) - timedelta(minutes=60 * 3)

    games = []

    # Scan group phase
    group_dir = _norm(os.path.join(html_base, "jogos", config.group_phase_label))
    for fp in sorted(glob(_norm(os.path.join(group_dir, "*.html")))):
        if "index" in fp:
            continue
        info = _parse_game_file(fp, config)
        if info and info["dt"] > now:
            games.append(info)

    # Scan playoff phases
    for pr in (config.playoff_rounds or []):
        po_dir = _norm(os.path.join(html_base, "jogos", pr.key))
        for fp in sorted(glob(_norm(os.path.join(po_dir, "*.html")))):
            if "index" in fp:
                continue
            info = _parse_game_file(fp, config)
            if info and info["dt"] > now:
                games.append(info)

    games.sort(key=lambda g: g["dt"])
    return games[:limit]


def _parse_game_file(filepath: str, config: ChampionshipConfig) -> dict | None:
    """Extract game info from an HTML filename."""
    fname = os.path.basename(filepath).replace(".html", "")
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})_(\d{1,2})h", fname)
    if not match:
        return None

    year, month, day, hour = map(int, match.groups())
    tz = pytz.timezone(config.timezone)
    dt = tz.localize(datetime(year, month, day, hour))

    # Extract teams from filename
    rest = fname[match.end():]
    teams = rest.replace("_vs_", " vs ").replace("_", " ").lstrip("_").replace("-vs-", " vs ").strip()
    raw_teams = rest.lstrip("_").split("-vs-")
    home_team = raw_teams[0].replace("_", " ").strip() if len(raw_teams) > 0 else ""
    away_team = raw_teams[1].replace("_", " ").strip() if len(raw_teams) > 1 else ""

    href = filepath.replace("\\", "/").replace(
        f"{config.reports_dir.replace(chr(92), '/')}/html/", ""
    )

    return {"dt": dt, "teams": teams, "home_team": home_team, "away_team": away_team, "href": href, "date_str": f"{day:02d}/{month:02d} {hour:02d}h"}


def _build_full_ranking(config: ChampionshipConfig) -> str:
    """Build the full ranking table with trend indicators and badges."""
    df_valid = _load_gold_data(config)
    if df_valid.empty:
        return "<div class='empty-state'>Nenhum participante encontrado</div>"

    # Compute trend: compare last 3 days vs previous 3 days
    df_valid["date_dt"] = pd.to_datetime(df_valid["date"])
    all_dates = sorted(df_valid["date_dt"].unique())
    trend_map: dict[str, str] = {}
    if len(all_dates) >= 6:
        recent_dates = all_dates[-3:]
        prev_dates = all_dates[-6:-3]
        df_recent = df_valid[df_valid["date_dt"].isin(recent_dates)].groupby("who")["pontos"].sum()
        df_prev = df_valid[df_valid["date_dt"].isin(prev_dates)].groupby("who")["pontos"].sum()
        for who in df_valid["who"].unique():
            r = df_recent.get(who, 0)
            p = df_prev.get(who, 0)
            if r > p:
                trend_map[who] = '<span class="trend-up">\u25b2</span>'
            elif r < p:
                trend_map[who] = '<span class="trend-down">\u25bc</span>'
            else:
                trend_map[who] = '<span class="trend-flat">\u25b6</span>'

    # Compute badges for all players
    gold_dir = config._au_first_round()
    badge_map: dict[str, list[str]] = {}

    # Hot streak badge (consistency.csv)
    cons_path = _norm(os.path.join(gold_dir, "consistency.csv"))
    if os.path.exists(cons_path):
        df_cons = pd.read_csv(cons_path, sep=",")
        for boleiro in df_cons["boleiro"].unique():
            df_b = df_cons[df_cons["boleiro"] == boleiro].sort_values("date")
            streak_len = 0
            streak_type = ""
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
            if streak_type == "hit" and streak_len >= 3:
                badge_map.setdefault(boleiro, []).append("\U0001f525")

    # Zebra hunter badge
    zebra_counts: dict[str, int] = {}
    upset_path = _norm(os.path.join(gold_dir, "upset_tracker.csv"))
    if os.path.exists(upset_path):
        df_upset = pd.read_csv(upset_path, sep=",")
        upset_only = df_upset[df_upset.get("is_upset", 0) == 1]
        for _, r in upset_only.iterrows():
            for p in [x.strip() for x in str(r.get("players_correct", "")).split("|") if x.strip()]:
                zebra_counts[p] = zebra_counts.get(p, 0) + 1
        sorted_zebras = sorted(zebra_counts.items(), key=lambda x: -x[1])
        if len(sorted_zebras) >= 3:
            for name, _ in sorted_zebras[:3]:
                badge_map.setdefault(name, []).append("\U0001f993")

    # Boldness badge
    bold_path = _norm(os.path.join(gold_dir, "boldness_index.csv"))
    if os.path.exists(bold_path):
        df_bold = pd.read_csv(bold_path, sep=",")
        for _, r in df_bold.iterrows():
            bs = float(r["boldness_score"])
            if bs > 0.3:
                badge_map.setdefault(r["boleiro"], []).append("\U0001f4a5")
            elif bs < -0.3:
                badge_map.setdefault(r["boleiro"], []).append("\U0001F9CA")

    # Leader badge
    rank_path = _norm(os.path.join(gold_dir, "ranking_history.csv"))
    if os.path.exists(rank_path):
        df_rank_hist = pd.read_csv(rank_path, sep=",")
        df_rank_hist = df_rank_hist.sort_values("date")
        latest_date = df_rank_hist["date"].iloc[-1] if not df_rank_hist.empty else None
        if latest_date:
            df_latest = df_rank_hist[df_rank_hist["date"] == latest_date]
            top = df_latest.loc[df_latest["rank"].idxmin()] if not df_latest.empty else None
            if top is not None:
                badge_map.setdefault(top["boleiro"], []).append("\U0001f40d")

    score_names = config.scoring_rule_names()
    agg_cols = ["pontos"] + [c for c in score_names if c in df_valid.columns]
    df_rank = df_valid.groupby("who", as_index=False)[agg_cols].sum()
    df_rank.sort_values(["pontos", "who"], ascending=[False, True], inplace=True)
    df_rank.reset_index(drop=True, inplace=True)
    df_rank["#"] = range(1, len(df_rank) + 1)
    rank_rows = ""
    for _, row in df_rank.iterrows():
        rank_num = int(row["#"])
        medal = "\U0001f947" if rank_num == 1 else "\U0001f948" if rank_num == 2 else "\U0001f949" if rank_num == 3 else ""
        rank_class = f"rank-{rank_num}" if rank_num <= 3 else ""
        trend = trend_map.get(row["who"], "&nbsp;")
        badges = " ".join(badge_map.get(row["who"], []))
        who_name = row["who"]
        who_display = f"🤖 {who_name}" if who_name.startswith("LLM") else who_name
        cells = f'<td>{medal} {rank_num}</td><td><a href="boleiros/{who_name}.html">{who_display}</a> {trend} <span style="font-size:0.75rem;">{badges}</span></td>'
        cells += f'<td style="font-weight:700;color:var(--accent)">{int(row["pontos"])}</td>'
        for sn in score_names:
            if sn in row.index:
                val = int(row[sn]) if pd.notna(row[sn]) else 0
                cells += f"<td>{val}</td>"
        num_z = zebra_counts.get(row["who"], 0)
        cells += f'<td style="font-weight:600;color:{"var(--danger)" if num_z > 0 else "var(--text-muted)"};">{num_z}</td>'
        rank_rows += f'<tr class="{rank_class}">{cells}</tr>\n'
    rank_header = ""
    for sn in score_names:
        emoji = config.scoring_emoji(sn)
        h = f"{emoji} " if emoji else ""
        h += sn.split("-")[0].strip()
        rank_header += f"<th>{h}</th>"
    rank_header += '<th style="color:var(--danger);">\U0001f993 Z</th>'
    return f"""
<div style="overflow-x:auto;">
    <table class="rank-table">
        <thead><tr><th>#</th><th>Boleiro</th><th>Jogos</th>{rank_header}</tr></thead>
        <tbody>{rank_rows}</tbody>
    </table>
    <div style="font-size:0.65rem;color:var(--text-muted);padding:0.3rem 0.75rem;text-align:right;">
        Jogos = pontos dos palpites (n\u00e3o inclui b\u00f4nus de times)
    </div>
</div>"""


def _build_upcoming_games(config: ChampionshipConfig) -> str:
    """Build the upcoming games section (first 5, no scroll)."""
    html_base = _norm(os.path.join(config.reports_dir, "html"))
    games = _get_upcoming_games(html_base, config, limit=5)

    if not games:
        return ""

    cards = ""
    rev_map_pt = {_strip_accents(v.lower()): k for k, v in config.team_name_mapping.items()}
    for g in games:
        home_en = rev_map_pt.get(_strip_accents(g["home_team"].lower()), g["home_team"])
        away_en = rev_map_pt.get(_strip_accents(g["away_team"].lower()), g["away_team"])
        home_logo = _team_logo_tag(home_en, config , cls="team-logo-sm", start=config.reports_dir + "/html")
        away_logo = _team_logo_tag(away_en, config , cls="team-logo-sm", start=config.reports_dir + "/html")
        home_slug = config.team_slugs.get(home_en, "")
        away_slug = config.team_slugs.get(away_en, "")
        cards += (
            f'<a href="{g["href"]}" class="game-card">'
            f'<div class="badge-live">PROXIMO</div>'
            f'<div class="datetime">{g["date_str"]}</div>'
            f'<div class="matchup">{home_logo}{home_slug} vs {away_logo}{away_slug}</div>'
            f'</a>\n'
        )

    return f"""
<div class="section">
    <div class="section-title">\U0001f552 Proximos Jogos</div>
    <div style="display:flex;flex-wrap:wrap;gap:0.5rem;padding:0 0.75rem;">{cards}</div>
</div>
"""


def _build_player_grid(config: ChampionshipConfig) -> str:
    """Build the player avatar grid with points and hot streak indicators."""
    df_valid = _load_gold_data(config)
    if df_valid.empty:
        return ""
    df_pts = df_valid.groupby("who", as_index=False)["pontos"].sum()
    df_pts.sort_values(["pontos", "who"], ascending=[False, True], inplace=True)

    # Check for hot streaks from consistency.csv
    hot_players: set[str] = set()
    cons_path = _norm(os.path.join(config._au_first_round(), "consistency.csv"))
    if os.path.exists(cons_path):
        df_cons = pd.read_csv(cons_path, sep=",")
        for boleiro in df_cons["boleiro"].unique():
            df_b = df_cons[df_cons["boleiro"] == boleiro].sort_values("date")
            streak_len = 0
            for _, r in reversed(list(df_b.iterrows())):
                st = r.get("streak_type", "")
                if st == "hit":
                    streak_len += 1
                else:
                    break
            if streak_len >= 3:
                hot_players.add(boleiro)

    cards = ""
    for _, row in df_pts.iterrows():
        name = row["who"]
        pts = int(row["pontos"])
        hot_badge = '<span class="hot-streak">\U0001f525</span>' if name in hot_players else ""
        cards += (
            f'<a href="boleiros/{name}.html" class="player-card">'
            f'<div class="player-avatar">{_initials(name)}</div>'
            f'<div>'
            f'<div class="player-name">{name} {hot_badge}</div>'
            f'<div class="player-pts">{pts} <span style="font-size:0.6rem;color:var(--text-muted);font-weight:400;">jogos</span></div>'
            f'</div>'
            f'</a>\n'
        )

    return f"""
<div class="section">
    <div class="section-title">\U0001f465 Boleiros ({len(df_pts)})</div>
    <div class="player-grid">{cards}</div>
</div>
"""


def _build_distribution_bars(config: ChampionshipConfig) -> str:
    """Build a distribution bar showing how many players are in each score bracket."""
    df_valid = _load_gold_data(config)
    if df_valid.empty:
        return ""

    df_pts = df_valid.groupby("who")["pontos"].sum()
    if df_pts.empty:
        return ""

    max_pts = int(df_pts.max())
    # Create buckets of 50 points
    bucket_size = 50
    num_buckets = max(1, (max_pts // bucket_size) + 1)

    buckets = {}
    for i in range(num_buckets):
        low = i * bucket_size
        high = (i + 1) * bucket_size
        label = f"{low}-{high}"
        count = int(((df_pts >= low) & (df_pts < high)).sum())
        if count > 0:
            buckets[label] = count

    if not buckets:
        return ""

    max_count = max(buckets.values())
    bars = ""
    for label, count in sorted(buckets.items()):
        pct = round(count / max_count * 100) if max_count > 0 else 0
        bars += (
            f'<div class="bar-row" style="margin-bottom:0.2rem;">'
            f'<span class="bar-label">{label}</span>'
            f'<div class="bar-track" style="height:16px;">'
            f'<div class="bar-fill" style="width:{pct}%;background:var(--accent);height:16px;"></div>'
            f'</div>'
            f'<span class="bar-pct">{count}</span>'
            f'</div>\n'
        )

    return f"""
<div class="section">
    <div class="section-title">\U0001f4ca Distribuicao da Pontuacao</div>
    <div class="card">
        <div style="font-size:0.8rem;color:var(--text-muted);margin-bottom:0.5rem;">
            Quantos jogadores estao em cada faixa de pontuacao
        </div>
        <div class="bar-chart">{bars}</div>
    </div>
</div>
"""


def _build_zebra_counter(config: ChampionshipConfig) -> str:
    """Show a zebra counter card for the dashboard hero."""
    upset_path = _norm(os.path.join(config._au_first_round(), "upset_tracker.csv"))
    if not os.path.exists(upset_path):
        return ""
    try:
        df_upset = pd.read_csv(upset_path, sep=",")
        df_upset = df_upset[df_upset["real_winner"].notna() & (df_upset["real_winner"] != "")].copy()
        total = len(df_upset)
        upsets = df_upset[df_upset.get("is_upset", 0) == 1] if "is_upset" in df_upset.columns else pd.DataFrame()
        num_upsets = len(upsets)
        pct = round(num_upsets / total * 100, 1) if total else 0
        return f'<div style="display:inline-flex;align-items:center;gap:0.5rem;margin-top:0.5rem;background:rgba(239,68,68,0.2);padding:0.3rem 0.8rem;border-radius:999px;font-size:0.8rem;"><span>\U0001f993</span> <strong>{num_upsets}</strong> zebras em {total} jogos ({pct}%)</div>\n'
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return ""


def _build_bottom_nav_dashboard(prefix: str = "") -> str:
    """Build the bottom navigation for the dashboard."""
    items = [
        ("index.html", "\U0001f3e0", "In\u00edcio"),
        ("arena.html", "\u2694\ufe0f", "Arena"),
        ("zebras.html", "\U0001f993", "Zebras"),
        ("palpites.html", "\U0001f4cb", "Palpites"),
        ("bolao_xray.html", "\U0001f50d", "Raio-X"),
    ]
    links = ""
    for href, icon, label in items:
        cls = ' class="active"' if href == "index.html" else ""
        links += f'<a href="{prefix}{href}"{cls}><span class="nav-icon">{icon}</span>{label}</a>\n'
    return f'<nav class="bottom-nav">{links}</nav>'


def _build_live_games(config: ChampionshipConfig, now_str: str) -> str:
    """Build a card for each match currently marked as 'live' in games.csv."""
    df = pd.read_csv(config.results_file, sep=",")
    live = df[df["time_elapsed"] == "live"].copy()
    if live.empty:
        return ""

    rev_map = {v: k for k, v in config.team_name_mapping.items()}
    cards = ""
    for _, row in live.iterrows():
        home = str(row["home_team"])
        away = str(row["away_team"])
        hg = int(row["home_goals"]) if pd.notna(row.get("home_goals")) else 0
        ag = int(row["away_goals"]) if pd.notna(row.get("away_goals")) else 0
        date = str(row["date"])
        match_slug = str(row.get("match", ""))
        round_val = row.get("round", "")

        # Determine phase directory for the match HTML link
        try:
            int(round_val)
            phase_dir = config.group_phase_label
        except (ValueError, TypeError):
            phase_dir = str(round_val) if round_val else config.group_phase_label

        # Parse date_part and hour_part from "YYYY-MM-DD HHh" format
        # hour keeps the "h" suffix to match the gold data hour format (e.g. "13h")
        date_parts = date.split(" ")
        date_part = date_parts[0] if date_parts else date
        hour_part = date_parts[1].strip() if len(date_parts) > 1 else ""

        # Link to the per-match page
        game_href = f"jogos/{phase_dir}/{date_part}_{hour_part}_{match_slug}.html"

        home_logo = _team_logo_tag(rev_map.get(home, home), config, cls="team-logo-sm", start=config.reports_dir + "/html")
        away_logo = _team_logo_tag(rev_map.get(away, away), config, cls="team-logo-sm", start=config.reports_dir + "/html")

        cards += f"""
    <div class="card" style="position:relative;">
        <div class="live-badge">\U0001f534 AO VIVO</div>
        <div class="result-card">
            <div class="team">{home_logo} {home}</div>
            <div class="score">{hg} - {ag}</div>
            <div class="team">{away_logo} {away}</div>
        </div>
        <div class="date">{date}</div>
        <div style="text-align:center;font-size:0.65rem;color:var(--text-muted);padding-bottom:0.3rem;">atualizado \u00e0s {now_str}</div>
        <div style="text-align:center;"><a href="{game_href}" style="font-size:0.75rem;font-weight:600;color:var(--accent);text-decoration:none;">\U0001f4fa ver jogo</a></div>
    </div>
"""
    return f"""
<div class="section">
    <div class="section-title">\U0001f4fa Ao Vivo</div>
    <div style="display:flex;flex-direction:column;gap:0.75rem;padding:0 0.75rem;">{cards}</div>
</div>
"""


def _build_last_result(config: ChampionshipConfig) -> str:
    """Build the last result card from *finished* matches only."""
    df_results = pd.read_csv(config.results_file, sep=",")
    df_results = df_results[df_results["time_elapsed"] == "finished"].copy()
    df_results.dropna(subset=["home_goals"], inplace=True)
    if df_results.empty:
        return ""

    # Sort by date (and hour if available) to get the most recent result
    sort_cols = ["date"]
    if "hour" in df_results.columns:
        sort_cols.append("hour")
    df_results = df_results.sort_values(sort_cols, ascending=True)
    last = df_results.iloc[-1]
    home = str(last["home_team"])
    away = str(last["away_team"])
    hg = int(last["home_goals"])
    ag = int(last["away_goals"])
    date = str(last["date"])

    rev_map = {v: k for k, v in config.team_name_mapping.items()}
    home_logo = _team_logo_tag(rev_map.get(home, home), config, cls="team-logo-sm", start=config.reports_dir + "/html")
    away_logo = _team_logo_tag(rev_map.get(away, away), config, cls="team-logo-sm", start=config.reports_dir + "/html")

    # Check if the last match was a zebra
    zebra_badge = ""
    try:
        upset_path = os.path.join(config._au_first_round(), "upset_tracker.csv")
        if os.path.exists(upset_path):
            df_upset = pd.read_csv(upset_path, sep=",")
            match_slug = str(last.get("match", ""))
            if match_slug:
                upset_row = df_upset[df_upset["match"] == match_slug]
                if not upset_row.empty and int(upset_row.iloc[0].get("is_upset", 0)) == 1:
                    wwpct = int(upset_row.iloc[0].get("winner_wrong_pct", 0))
                    fav = upset_row.iloc[0].get("favorite", "?")
                    label = ZEBRA_MONSTRA_LABEL if wwpct >= 90 else ZEBRA_GRANDE_LABEL
                    zebra_badge = f'<div style="text-align:center;margin-top:0.3rem;"><span class="badge badge-danger">{label}</span> <span style="font-size:0.7rem;color:var(--text-muted);">{wwpct}% erraram \u2014 favorito {fav} n\u00e3o venceu</span></div>'
    except Exception:
        pass

    return f"""
<div class="section">
    <div class="section-title">\U0001f4ca Ultimo Resultado</div>
    <div class="card">
        <div class="result-card">
            <div class="team">{home_logo} {home}</div>
            <div class="score">{hg} - {ag}</div>
            <div class="team">{away_logo} {away}</div>
        </div>
        <div class="date">{date}</div>
        {zebra_badge}
    </div>
</div>
"""


def _slug_from_filename(filename: str) -> str:
    """Extract match slug from an HTML filename.

    Pattern: YYYY-MM-DD_HHh_<slug>.html -> <slug>
    """
    base = os.path.basename(filename).replace(".html", "")
    m = re.match(r"\d{4}-\d{2}-\d{2}_\d{1,2}h_(.+)", base)
    if m:
        return m.group(1)
    return base


def _status_badge(slug: str, slug_status: dict[str, str]) -> str:
    """Return a small colored badge for the match status."""
    status = slug_status.get(slug, "result")
    if status == "result":
        return '<span class="badge-result green">\u2705</span>'
    if status == "pending":
        return '<span class="badge-result yellow">\u23f3</span>'
    return '<span class="badge-result blue">\U0001f52e</span>'


def _strip_accents(text: str) -> str:
    """Remove diacritics/accents from a string (e.g. São -> Sao)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c)
    )


def _build_phase_buttons(config: ChampionshipConfig, slug_status: dict[str, str] | None = None) -> str:
    """Build phase sections with compact button-style game links, grouped by round."""
    if slug_status is None:
        slug_status = {}
    html_base = _norm(os.path.join(config.reports_dir, "html"))
    sections = ""

    rev_map_pt = {_strip_accents(v.lower()): k for k, v in config.team_name_mapping.items()}

    # Load upset data for zebra indicators
    upset_icons: dict[str, str] = {}
    upset_path = os.path.join(config._au_first_round(), "upset_tracker.csv")
    if os.path.exists(upset_path):
        try:
            df_upset_slugs = pd.read_csv(upset_path, sep=",")
            for _, r in df_upset_slugs.iterrows():
                if int(r.get("is_upset", 0)) == 1:
                    wwpct = int(r.get("winner_wrong_pct", 0))
                    upset_icons[str(r["match"])] = ZEBRA_MONSTRA_EMOJI if wwpct >= 90 else ZEBRA_GRANDE_EMOJI
        except Exception:
            pass

    # Load results for score display
    results_map: dict[str, tuple[str, str]] = {}
    results_path = config.results_file
    if os.path.exists(results_path):
        try:
            df_res = pd.read_csv(results_path, sep=",")
            for _, r in df_res.iterrows():
                ms = str(r.get("match", ""))
                hg = r.get("home_goals", "")
                ag = r.get("away_goals", "")
                if ms:
                    hg_str = str(int(float(hg))) if pd.notna(hg) and str(hg).strip() else ""
                    ag_str = str(int(float(ag))) if pd.notna(ag) and str(ag).strip() else ""
                    results_map[ms] = (hg_str, ag_str)
        except Exception:
            pass

    def _team_part(fp: str, side: str) -> tuple[str, str, str]:
        slug = _slug_from_filename(fp)
        parts = slug.split("-vs-")
        if len(parts) < 2:
            return ("", "", "")
        idx = 0 if side == "home" else 1
        pt_name = parts[idx].replace("_", " ").strip()
        en_name = rev_map_pt.get(_strip_accents(pt_name.lower()), pt_name)
        logo = _team_logo_tag(en_name, config, cls="team-logo-sm", start=config.reports_dir + "/html")
        slug_code = config.team_slugs.get(en_name, "")
        return (pt_name, logo, slug_code)

    def _build_compact_grid(file_list: list[str], results_map: dict[str, tuple[str, str]] | None = None) -> str:
        out = '<div style="display:flex;flex-direction:column;gap:0.25rem;">'
        for fp in file_list:
            href = fp.replace("\\", "/").replace(
                f"{config.reports_dir.replace(chr(92), '/')}/html/", ""
            )
            raw_date = (
                os.path.basename(fp)
                .replace(".html", "")
            )
            # Extract date part
            date_part = ""
            m = re.match(r"(\d{4}-\d{2}-\d{2}_\d{1,2}h)", raw_date)
            if m:
                date_part = m.group(1).replace("_", " ").replace("h", "h | ")
            else:
                date_part = ""
            slug = _slug_from_filename(fp)
            badge = _status_badge(slug, slug_status)
            zebra_icon = upset_icons.get(slug, "")
            home_name, home_logo, home_slug = _team_part(fp, "home")
            away_name, away_logo, away_slug = _team_part(fp, "away")
            # Look up score from results_map
            score_str = ""
            if results_map:
                hg, ag = results_map.get(slug, ("", ""))
                if hg and ag:
                    score_str = f' <span style="font-weight:700;color:var(--accent);">{hg}</span> vs <span style="font-weight:700;color:var(--accent);">{ag}</span> '
            out += f'<a href="{href}" style="display:flex;align-items:center;justify-content:space-between;background:var(--card-bg);border:1px solid var(--card-border);border-radius:8px;padding:0.45rem 0.7rem;font-size:0.75rem;font-weight:500;color:var(--text);text-decoration:none;transition:border-color 0.15s;" onmouseover="this.style.borderColor=\'var(--accent)\'" onmouseout="this.style.borderColor=\'var(--card-border)\'"><span style="display:flex;align-items:center;gap:0.3rem;"><span style="font-size:0.65rem;color:var(--text-muted);">{date_part}</span>{home_logo}{home_slug}{score_str or f" vs "}{away_logo}{away_slug}</span> <span style="display:flex;align-items:center;gap:0.2rem;">{zebra_icon}{badge}</span></a>\n'
        out += "</div>"
        return out if file_list else '<div class="empty-state">Nenhum jogo disponivel ainda</div>'

    # Group phase – split into 3 rounds of 24 games each
    group_dir = _norm(os.path.join(html_base, "jogos", config.group_phase_label))
    group_files = sorted(glob(_norm(os.path.join(group_dir, "*.html"))))
    group_files = [f for f in group_files if "index" not in f]

    group_size = len(group_files)
    round_size = max(1, group_size // 3)
    round_labels = ["1\u00aa Rodada", "2\u00aa Rodada", "3\u00aa Rodada"]

    # Build chunks first so we can find which round has the next game
    chunks: list[list[str]] = []
    for i in range(3):
        start = i * round_size
        end = start + round_size if i < 2 else group_size
        chunks.append(group_files[start:end])

    # Find the round index that contains the next upcoming game
    open_round = 0
    for idx, chk in enumerate(chunks):
        for fp in chk:
            slug = _slug_from_filename(fp)
            if slug_status.get(slug) in ("pending", "future"):
                open_round = idx
                break
        else:
            continue
        break

    sections += f"""<div class="section">
    <div class="section-title">\u26bd {config.group_phase_label} ({group_size})</div>
    <div style="margin:0 0.75rem;">
"""
    for i in range(3):
        chunk = chunks[i]
        if chunk:
            links = _build_compact_grid(chunk, results_map)
            sections += f"""<details {"open" if i == open_round else ""}>
    <summary style="padding:0.6rem 0.75rem;font-size:0.8rem;">{round_labels[i]} ({len(chunk)})</summary>
    <div class="content" style="padding:0.5rem 0.75rem 0.75rem;">{links}</div>
</details>
"""
    sections += """    </div>
</div>
"""

    # Playoff rounds
    playoff_emojis = {"segunda_fase": "\U0001f3c6", "oitavas": "\U0001f3c1", "quartas": "\U0001f525", "semi": "\U0001f3af", "terceiro_lugar": "\U0001f949", "final": "\U0001f3c6"}
    for pr in config.playoff_rounds:
        po_dir = _norm(os.path.join(html_base, "jogos", pr.key))
        po_files = sorted(glob(_norm(os.path.join(po_dir, "*.html"))))
        po_files = [f for f in po_files if "index" not in f]
        emoji = playoff_emojis.get(pr.key, "")

        po_links = _build_compact_grid(po_files, results_map)

        sections += f"""
<div class="section">
    <div class="section-title">{emoji} {pr.name} ({len(po_files)})</div>
    <div style="margin:0 0.75rem;">{po_links}</div>
</div>
"""

    return sections






# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def _build_bonus_times_card(config: ChampionshipConfig) -> str:
    """Build bonus times leaderboard card for the dashboard."""
    bonus_path = os.path.join(config._au_first_round(), "playoffs_scored.csv")
    if not os.path.exists(bonus_path):
        return ""
    df = pd.read_csv(bonus_path)
    if df.empty:
        return ""

    top_pts = (
        df.groupby("boleiro")["points"]
        .sum()
        .sort_values(ascending=False)
        .head(3)
        .reset_index()
    )
    top_pts_html = ""
    for i, (_, r) in enumerate(top_pts.iterrows(), 1):
        medal = "\U0001f947" if i == 1 else "\U0001f948" if i == 2 else "\U0001f949"
        top_pts_html += (
            f'<div class="bar-row">'
            f'<span class="bar-label">{medal} {r["boleiro"]}</span>'
            f'<span class="bar-pct">+{int(r["points"])}pts</span>'
            f'</div>\n'
        )

    acc = df.groupby("boleiro").agg(
        correct=("correct", "sum"), total=("correct", "count")
    )
    acc = acc[acc["total"] >= 5].copy()
    if not acc.empty:
        acc["rate"] = (acc["correct"] / acc["total"] * 100).round(0)
        top_acc = acc.sort_values("rate", ascending=False).head(3).reset_index()
    else:
        top_acc = pd.DataFrame()

    top_acc_html = ""
    for i, (_, r) in enumerate(top_acc.iterrows(), 1):
        medal = "\U0001f947" if i == 1 else "\U0001f948" if i == 2 else "\U0001f949"
        top_acc_html += (
            f'<div class="bar-row">'
            f'<span class="bar-label">{medal} {r["boleiro"]}</span>'
            f'<span class="bar-pct">{int(r["correct"])}/{int(r["total"])} - {int(r["rate"])}%</span>'
            f'</div>\n'
        )

    html = '<div class="section"><div class="section-title">\U0001f3c6 Bônus Times (extra)</div><div class="card">'
    if top_pts_html:
        html += '<div style="margin-bottom:0.75rem;"><strong>Maiores Pontuadores</strong></div>'
        html += f'<div class="bar-chart">{top_pts_html}</div>'
    if top_acc_html:
        html += '<div style="margin-top:0.75rem;margin-bottom:0.75rem;"><strong>Maiores Acertadores</strong></div>'
        html += f'<div class="bar-chart">{top_acc_html}</div>'
    html += "</div></div>\n"
    return html


def _build_emoji_accordion(config: ChampionshipConfig) -> str:
    """Build a compact accordion explaining each scoring emoji."""
    rows = ""
    for r in sorted(config.scoring_rules, key=lambda x: x.priority):
        emoji = r.emoji or ""
        desc = r.description or ""
        pts = r.points
        rows += (
            f'<div class="emoji-row">'
            f'<span class="e">{emoji}</span>'
            f'<span class="desc">{desc}</span>'
            f'<span class="pts">+{pts}</span>'
            f'</div>\n'
        )
    rows += (
        f'<div class="emoji-row">'
        f'<span class="e">\U0001f993</span>'
        f'<span class="desc">Zebra acertada (favorito n\u00e3o venceu e \u226570% erraram)</span>'
        f'<span class="pts">contagem</span>'
        f'</div>\n'
    )
    return f"""<details class="accordion-emoji">
<summary>\U0001f9e9 Legenda dos acertos</summary>
<div class="content">{rows}</div>
</details>
"""


def generate_dashboard(config: ChampionshipConfig) -> None:
    """Create the index.html dashboard."""
    if not os.path.exists(config.gold_valid_path()) and not os.path.exists(config.gold_all_path()):
        print_colored(f"no gold data at {config.gold_valid_path()} or {config.gold_all_path()}, skipping dashboard", "yellow")
        return
    print_colored("creating index.html dashboard", "sand")

    tz = pytz.timezone(config.timezone)
    now_str = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")

    pending_data = compute_pending_matches(config)
    slug_status: dict[str, str] = {}
    for s in pending_data["pending_slugs"]:
        slug_status[s] = "pending"
    for s in pending_data["future_slugs"]:
        slug_status[s] = "future"

    last_result = _build_last_result(config)
    live_games = _build_live_games(config, now_str)
    full_ranking = _build_full_ranking(config)
    upcoming = _build_upcoming_games(config)
    phase_buttons = _build_phase_buttons(config, slug_status)
    zebra_counter = _build_zebra_counter(config)
    badge_legend = """<div class="card" style="margin:0.75rem;font-size:0.7rem;color:var(--text-muted);display:flex;flex-wrap:wrap;gap:0.25rem 1rem;padding:0.5rem 0.75rem;">
    <span>\U0001f525 Embrazado (streak \u2265 3 acertos)</span>
    <span>\U0001f993 Ca\u00e7ador de Zebras (top 3 em zebras)</span>
    <span>\U0001f40d L\u00edder (1\u00ba lugar geral)</span>
    <span>\U0001f4a5 Ousado (aposta acima da m\u00e9dia)</span>
    <span>\U0001F9CA Conservador (aposta abaixo da m\u00e9dia)</span>
    <span>\U0001f3af Especialista (maior precis\u00e3o em time)</span>
</div>
"""
    emoji_accordion = _build_emoji_accordion(config)
    bonus_card = _build_bonus_times_card(config)
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.report_title}</title>
    <style>
    {config.theme.to_css_vars()}
    {_CSS_DASHBOARD}
    </style>
</head>
<body>

<div class="hero">
    <h1>\U0001f3c6 {config.report_title}</h1>
    <div class="subtitle">Painel do Bolao</div>
    {zebra_counter}
</div>
<div style="text-align:center;font-size:0.75rem;color:var(--text-muted);padding:0 0.75rem 0.5rem;">
    atualizado \u00e0s {now_str}
</div>

{badge_legend}

{live_games}

{last_result}

<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;margin:0 0.75rem;">
    <a href="tabela_real.html">
        <div class="card" style="text-align:center;font-weight:600;border-color:var(--accent);padding:0.75rem 0.5rem;">
            \U0001f3c6 Grupos
        </div>
    </a>
    <a href="rodadas.html">
        <div class="card" style="text-align:center;font-weight:600;padding:0.75rem 0.5rem;">
            \U0001f4ca Rodadas
        </div>
    </a>
    <a href="times.html">
        <div class="card" style="text-align:center;font-weight:600;padding:0.75rem 0.5rem;">
            \U0001f3c6 Times
        </div>
    </a>
    <a href="similaridade.html">
        <div class="card" style="text-align:center;font-weight:600;padding:0.75rem 0.5rem;">
            \U0001f9ee S\u00f3sia
        </div>
    </a>
    <a href="palpites.html">
        <div class="card" style="text-align:center;font-weight:600;padding:0.75rem 0.5rem;">
            \U0001f4cb Palpites
        </div>
    </a>
    <a href="ranking_evolution.html">
        <div class="card" style="text-align:center;font-weight:600;padding:0.75rem 0.5rem;">
            \U0001f4c8 Evolucao
        </div>
    </a>
    <a href="boldometer.html">
        <div class="card" style="text-align:center;font-weight:600;padding:0.75rem 0.5rem;">
            \U0001f4ca Boldometro
        </div>
    </a>
    <a href="zebras.html">
        <div class="card" style="text-align:center;font-weight:600;padding:0.75rem 0.5rem;">
            \U0001f993 Zebras
        </div>
    </a>
    <a href="bolao_xray.html">
        <div class="card" style="text-align:center;font-weight:600;padding:0.75rem 0.5rem;">
            \U0001f50d Raio-X
        </div>
    </a>
</div>

{emoji_accordion}

<div class="section">
    <div class="section-title">\U0001f3c6 Ranking</div>
    <div class="card">{full_ranking}</div>
</div>

{bonus_card}

{upcoming}

<div class="section">
    <div class="section-title">\U0001f4c2 Jogos por Fase</div>
    {phase_buttons}
</div>

{_build_bottom_nav_dashboard()}

</body>
</html>"""

    html_base = _norm(os.path.join(config.reports_dir, "html"))
    os.makedirs(html_base, exist_ok=True)
    with open(_norm(config.index_html_path()), "w", encoding="utf-8") as f:
        f.write(html_content)

    print_colored("index.html created", "green")
