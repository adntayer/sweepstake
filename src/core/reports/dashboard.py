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
from src.core.reports.html import (
    ZEBRA_GRANDE_EMOJI,
    ZEBRA_GRANDE_LABEL,
    ZEBRA_MONSTRA_EMOJI,
    ZEBRA_MONSTRA_LABEL,
)
from src.core.reports.utils import compute_pending_matches


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


def _short_name(name: str, config: ChampionshipConfig | None = None) -> str:
    """Shorten phase names for table headers.

    If ``config`` is provided, its ``phase_abbreviations`` mapping is
    checked first (exact match).  Falls back to Portuguese substring matching
    for legacy compatibility.
    """
    n = name.strip()
    if config and n in config.phase_abbreviations:
        return config.phase_abbreviations[n]
    nl = n.lower()
    if "segunda" in nl:
        return "2\u00aa Fase"
    if "oitavas" in nl:
        return "8as"
    if "quartas" in nl:
        return "4as"
    if "semi" in nl:
        return "Semi"
    if "terceiro" in nl or nl == "3\u00ba lugar":
        return "3\u00ba"
    if "final" in nl:
        return "Final"
    return n


# ------------------------------------------------------------------
# Shared CSS
# ------------------------------------------------------------------

_CSS_DASHBOARD = """
* { box-sizing: border-box; margin: 0; padding: 0; }

/* ── Typography ── */
:root {
    --font-display: 'Space Grotesk', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
}

body {
    font-family: var(--font-body);
    background: var(--bg);
    color: var(--text);
    font-size: 16px;
    line-height: 1.6;
    -webkit-text-size-adjust: 100%;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

h1, h2, h3, h4 {
    font-family: var(--font-display);
    font-weight: 600;
    letter-spacing: -0.01em;
}

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }

/* ── Hero ── */
.hero {
    background: var(--bg);
    padding: 1.75rem 1rem 1.25rem;
    text-align: center;
    color: var(--text);
    border-bottom: 1px solid var(--card-border);
    position: relative;
}
.hero h1 {
    font-family: var(--font-display);
    font-size: 1.65rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    margin-bottom: 0.2rem;
}
.hero .subtitle {
    font-family: var(--font-body);
    font-size: 0.85rem;
    color: var(--text-muted);
    font-weight: 400;
}

/* ── Section ── */
.section { margin: 1rem 0; }
.section-title {
    font-family: var(--font-display);
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0 0.75rem;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    letter-spacing: -0.01em;
}

/* ── Card ── */
.card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 6px;
    padding: 1rem;
    margin: 0 0.75rem;
}

/* ── Live badge ── */
.live-badge {
    position: absolute;
    top: -0.25rem;
    right: 0.75rem;
    background: var(--danger);
    color: var(--text);
    font-size: 0.55rem;
    font-weight: 600;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    z-index: 1;
    font-family: var(--font-mono);
    letter-spacing: 0.02em;
}

/* ── Score card ── */
.result-card {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 1rem;
    padding: 1.25rem 1rem;
}
.result-card .team { flex: 1; text-align: center; font-size: 1rem; font-weight: 500; }
.result-card .score {
    font-family: var(--font-mono);
    color: var(--accent);
    font-size: 1.75rem;
    font-weight: 700;
    white-space: nowrap;
    letter-spacing: 0.02em;
}
.result-card .date {
    text-align: center;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--text-muted);
    margin-top: 0.25rem;
}

/* ── Leaderboard ── */
.lb-row {
    display: flex;
    align-items: center;
    padding: 0.5rem 0;
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
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 0.75rem;
    flex-shrink: 0;
}
.lb-rank-1 { background: var(--accent); color: var(--text-inverse); }
.lb-rank-2 { background: var(--silver); color: var(--text-inverse); }
.lb-rank-3 { background: var(--bronze); color: var(--text); }
.lb-rank-n { background: var(--card-border); color: var(--text-muted); }
.lb-name { flex: 1; font-weight: 500; font-size: 0.85rem; font-family: var(--font-body); }
.lb-pts {
    font-family: var(--font-mono);
    font-weight: 700;
    color: var(--accent);
    font-size: 0.9rem;
    flex-shrink: 0;
}

/* ── Stat row / stat card ── */
.stat-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
    padding: 0.75rem;
}
.stat-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 6px;
    padding: 0.75rem;
    text-align: center;
}
.stat-card .value {
    font-family: var(--font-display);
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: -0.02em;
}
.stat-card .label {
    font-family: var(--font-body);
    font-size: 0.65rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.25rem;
}

/* ── Rank table ── */
.rank-table { width: 100%; border-collapse: collapse; }
.rank-table th {
    font-family: var(--font-mono);
    text-align: left; padding: 0.4rem 0.5rem;
    font-size: 0.6rem; font-weight: 400;
    color: var(--text-muted);
    border-bottom: 1px solid var(--card-border);
    white-space: nowrap;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.rank-table td {
    font-family: var(--font-body);
    padding: 0.4rem 0.5rem;
    border-bottom: 1px solid var(--card-border);
    white-space: nowrap;
    font-size: 0.8rem;
}
.rank-table tr:nth-child(even) { background: var(--zebra-stripe); }
.rank-table .rank-1 td { background: var(--accent-highlight); }
.rank-table .rank-2 td { background: var(--silver-highlight); }
.rank-table .rank-3 td { background: var(--bronze-highlight); }
.rank-table th.sort-asc::after,
table[data-sortable] th.sort-asc::after { content:" \u25b2"; font-size:0.6rem; }
.rank-table th.sort-desc::after,
table[data-sortable] th.sort-desc::after { content:" \u25bc"; font-size:0.6rem; }

/* ── Horizontal scroll for upcoming games ── */
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
    border-radius: 6px;
    padding: 0.5rem 0.75rem;
    text-align: center;
    min-width: 130px;
    display: block;
    text-decoration: none;
    color: inherit;
}
.game-card .matchup { font-family: var(--font-display); font-weight: 600; font-size: 0.8rem; margin: 0.25rem 0; letter-spacing: -0.01em; }
.game-card .datetime { font-family: var(--font-mono); font-size: 0.65rem; color: var(--text-muted); }
.game-card .badge-live {
    display: inline-block;
    background: var(--danger);
    color: var(--text);
    font-size: 0.55rem;
    font-weight: 600;
    padding: 0.1rem 0.4rem;
    border-radius: 999px;
    margin-bottom: 0.25rem;
    font-family: var(--font-mono);
    letter-spacing: 0.02em;
}

/* ── Player grid ── */
.player-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
    padding: 0 0.75rem;
}
.player-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 6px;
    padding: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    transition: border-color 0.15s;
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
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 0.9rem;
    flex-shrink: 0;
}
.player-name {
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 0.85rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.player-pts {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--text-muted);
}

/* ── Accordion ── */
details {
    margin: 0.5rem 0.75rem;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 6px;
    overflow: hidden;
}
summary {
    padding: 0.85rem 1rem;
    cursor: pointer;
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 0.85rem;
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
    padding: 0.35rem 0;
    font-size: 0.8rem;
    border-bottom: 1px solid var(--card-border);
}
details .content a:last-child { border-bottom: none; }

/* ── Compact accordion (emoji legend) ── */
details.accordion-emoji { margin: 0.75rem 0.75rem 0.5rem; }
details.accordion-emoji summary { padding: 0.35rem 0.6rem; font-size: 0.7rem; min-height: 32px; }
details.accordion-emoji .content { padding: 0.25rem 0.6rem 0.4rem; }
details.accordion-emoji .emoji-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.2rem 0;
    font-size: 0.65rem;
    border-bottom: 1px solid var(--card-border);
}
details.accordion-emoji .emoji-row:last-child { border-bottom: none; }
details.accordion-emoji .emoji-row .e { font-size: 0.85rem; width: 1.2rem; text-align: center; flex-shrink: 0; }
details.accordion-emoji .emoji-row .pts { color: var(--accent); font-weight: 600; width: 1.8rem; text-align: right; flex-shrink: 0; font-family: var(--font-mono); }

/* ── Footer ── */
.footer {
    text-align: center;
    padding: 2rem 1rem;
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.65rem;
}

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 1.5rem 1rem;
    color: var(--text-muted);
    font-size: 0.85rem;
}

/* ── Bottom navigation bar ── */
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
    padding: 0.15rem 0;
    padding-bottom: max(0.15rem, env(safe-area-inset-bottom));
    box-shadow: 0 -2px 10px var(--shadow-color);
}
.bottom-nav a {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.05rem;
    padding: 0.25rem 0.5rem;
    font-family: var(--font-body);
    font-size: 0.55rem;
    font-weight: 500;
    color: var(--text-muted);
    text-decoration: none;
    min-height: 44px;
    justify-content: center;
    border-radius: 6px;
    transition: color 0.15s;
    -webkit-tap-highlight-color: transparent;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}
.bottom-nav a:active { background: var(--hover-overlay); }
.bottom-nav a .nav-icon { font-size: 1rem; line-height: 1; }
.bottom-nav a.active { color: var(--accent); }
body { padding-bottom: 65px; }

/* ── Trend indicators ── */
.trend-up { color: var(--success); }
.trend-down { color: var(--danger); }
.trend-flat { color: var(--text-muted); }

/* ── Hot streak indicator ── */
.hot-streak {
    display: inline-block;
    font-size: 0.85rem;
    animation: pulse-fire 1.5s ease-in-out infinite;
}
@keyframes pulse-fire {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.15); }
}

/* ── Status badges for match results ── */
.badge-result { display:inline-block; padding:0.1rem 0.35rem; border-radius:999px; font-size:0.6rem; font-weight:600; margin-left:0.3rem; font-family:var(--font-mono); }
.badge-result.green { background:var(--success); color:#fff; }
.badge-result.yellow { background:var(--warning); color:var(--text-inverse); }
.badge-result.blue { background:var(--primary); color:#fff; }

/* ── Pending summary badge in hero ── */
.hero-badge { display:inline-flex; align-items:center; gap:0.4rem; margin-top:0.4rem; padding:0.25rem 0.7rem; border-radius:999px; font-size:0.75rem; font-family:var(--font-mono); letter-spacing:0.02em; }
.hero-badge.green { background:rgba(45,157,106,0.2); }
.hero-badge.yellow { background:rgba(212,165,69,0.2); }
.hero-badge.gray { background:rgba(123,142,166,0.15); color:var(--text-muted); }

/* ── Team logos ── */
.team-logo { width: 28px; height: 28px; object-fit: contain; vertical-align: middle; border-radius: 3px; }
.team-logo-sm { width: 24px; height: 24px; object-fit: contain; vertical-align: middle; border-radius: 2px; }
.team-logo-lg { width: 48px; height: 48px; object-fit: contain; vertical-align: middle; border-radius: 4px; }

/* ── Responsive ── */
@media (max-width: 359px) {
    .hero h1 { font-size: 1.3rem; }
    .hero .subtitle { font-size: 0.8rem; }
    .bottom-nav a { font-size: 0.5rem; }
    .bottom-nav a .nav-icon { font-size: 0.9rem; }
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
.rank-table th.sort-asc::after { content:" \u25b2"; font-size:0.6rem; }
.rank-table th.sort-desc::after { content:" \u25bc"; font-size:0.6rem; }
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
    """Build the full ranking table with trend indicators, badges, and per-phase bonus."""
    df_valid = _load_gold_data(config)
    if df_valid.empty:
        return "<div class='empty-state'>Nenhum participante encontrado</div>"

    # --- Load playoff match points ---
    playoff_pts: dict[str, int] = {}
    for pr in (config.playoff_rounds or []):
        phase_path = config.gold_playoff_valid_path(pr.key)
        if os.path.exists(phase_path):
            df_phase = pd.read_csv(phase_path, sep=",")
            for who, grp in df_phase.groupby("who"):
                playoff_pts[who] = playoff_pts.get(who, 0) + int(grp["pontos"].sum())

    # --- Load bonus points from playoffs_scored.csv (per phase) ---
    bonus_pts: dict[str, int] = {}
    bonus_by_phase: dict[str, dict[str, int]] = {}  # {phase: {boleiro: points}}
    play_phase_order: list[str] = [pr.key for pr in (config.playoff_rounds or [])]
    play_phase_emoji: dict[str, str] = dict(config.phase_emojis) if config.phase_emojis else {
        "segunda_fase": "\U0001f3c6", "oitavas": "\U0001f3c1",
        "quartas": "\U0001f525", "semi": "\U0001f3af",
        "terceiro_lugar": "\U0001f949", "final": "\U0001f3c6",
    }
    play_phase_name: dict[str, str] = {pr.key: _short_name(pr.name, config) for pr in (config.playoff_rounds or [])}
    for pk in play_phase_order:
        bonus_by_phase[pk] = {}
    bonus_path = _norm(os.path.join(config._au_first_round(), "playoffs_scored.csv"))
    if os.path.exists(bonus_path):
        df_bonus = pd.read_csv(bonus_path, sep=",")
        for _, row in df_bonus.iterrows():
            b = row["boleiro"]
            ph = str(row["phase"])
            pts = int(row["points"])
            if ph in bonus_by_phase:
                bonus_by_phase[ph][b] = bonus_by_phase[ph].get(b, 0) + pts
            bonus_pts[b] = bonus_pts.get(b, 0) + pts

    # ── Check which playoff phases have games in games.csv ──
    phases_in_games: set[str] = set()
    if os.path.exists(config.games_file):
        df_g = pd.read_csv(config.games_file, sep=",")
        if "round" in df_g.columns:
            phases_in_games = set(df_g["round"].astype(str).str.strip().unique())

    # Trend based on rank change (more reliable than raw points across phases)
    trend_map: dict[str, str] = {}
    gold_dir = config._au_first_round()
    rank_path = _norm(os.path.join(gold_dir, "ranking_history.csv"))
    if os.path.exists(rank_path):
        df_rank_trend = pd.read_csv(rank_path, sep=",")
        df_rank_trend = df_rank_trend.sort_values(["boleiro", "date"])
        for who in df_rank_trend["boleiro"].unique():
            df_w = df_rank_trend[df_rank_trend["boleiro"] == who]
            if len(df_w) >= 2:
                prev_r = int(df_w.iloc[-2]["rank"])
                curr_r = int(df_w.iloc[-1]["rank"])
                if curr_r < prev_r:
                    trend_map[who] = '<span class="trend-up">\u25b2</span>'
                elif curr_r > prev_r:
                    trend_map[who] = '<span class="trend-down">\u25bc</span>'
                else:
                    trend_map[who] = '<span class="trend-flat">\u25b6</span>'
    # Compute badges for all players
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
        try:
            df_upset = pd.read_csv(upset_path, sep=",")
        except pd.errors.EmptyDataError:
            df_upset = pd.DataFrame()
        # Only count matches with real results (same filter as zebra page / _build_zebra_counter)
        df_upset = df_upset[df_upset["real_winner"].notna() & (df_upset["real_winner"] != "")].copy() if "real_winner" in df_upset.columns else df_upset
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

    # ── Group data only (pontos used as base; playoff match points added separately) ──
    score_names = config.scoring_rule_names()
    agg_cols = ["pontos"] + [c for c in score_names if c in df_valid.columns]
    df_rank = df_valid.groupby("who", as_index=False)[agg_cols].sum()
    # Add playoff match points and bonus team points per player
    df_rank["playoff_pts"] = df_rank["who"].map(playoff_pts).fillna(0).astype(int)
    df_rank["bonus_pts"] = df_rank["who"].map(bonus_pts).fillna(0).astype(int)
    df_rank["zebra_pts"] = df_rank["who"].map(zebra_counts).fillna(0).astype(int)
    # Penalty points (from config.yaml)
    df_rank["penalty_pts"] = df_rank["who"].map(lambda w: config.total_penalty(w)).fillna(0).astype(int)
    # Total = jogos + bonus - penalty
    df_rank["total_pts"] = df_rank["pontos"] + df_rank["playoff_pts"] + df_rank["bonus_pts"] - df_rank["penalty_pts"]
    df_rank.sort_values(["total_pts", "who"], ascending=[False, True], inplace=True)
    df_rank.reset_index(drop=True, inplace=True)
    df_rank["#"] = range(1, len(df_rank) + 1)

    # Only show penalty column if any player has a penalty > 0
    has_penalty = df_rank["penalty_pts"].sum() > 0

    # ── Header: # | Boleiro | Total | Bônus | 🎯1 | 🥅2 | 📊3 | 🤝4 | 🔶5 | ✔6 | ⚖7 | 👊8 | ❌9 | ❓99 | 🦓Z ──
    rank_header_combined = '<th>#</th><th>Boleiro</th>'
    rank_header_combined += '<th style="text-align:right;font-size:0.65rem;">Total</th>'
    rank_header_combined += '<th style="text-align:right;font-size:0.65rem;">B\u00f4nus</th>'
    if has_penalty:
        rank_header_combined += '<th style="text-align:right;font-size:0.65rem;color:var(--danger);">Pen.</th>'
    for rn in score_names:
        em = config.scoring_emoji(rn)
        m = re.match(r"^(\d+)", rn)
        num = m.group(1) if m else ""
        lbl = f"{em} {num}" if em else num
        rank_header_combined += f'<th style="text-align:right;font-size:0.6rem;">{lbl}</th>'
    rank_header_combined += '<th style="text-align:right;font-size:0.6rem;">\U0001f993 Z</th>'

    # Build rows with badges, trend, and delta-do-líder
    leader_total = int(df_rank.iloc[0]["total_pts"]) if len(df_rank) > 0 else 0
    rank_rows_updated = ""
    for _, row in df_rank.iterrows():
        rank_num = int(row["#"])
        medal_symbol = "\U0001f947" if rank_num == 1 else "\U0001f948" if rank_num == 2 else "\U0001f949" if rank_num == 3 else ""
        rank_class = f"rank-{rank_num}" if rank_num <= 3 else ""
        trend = trend_map.get(row["who"], "&nbsp;")
        badges_str = " ".join(badge_map.get(row["who"], []))
        who_name = row["who"]
        who_display = f"\U0001f916 {who_name}" if who_name.startswith("LLM") else who_name
        total_display = int(row["total_pts"])
        bonus_display = int(row["bonus_pts"])
        zebra_display = int(row["zebra_pts"])
        penalty_display = int(row["penalty_pts"])
        delta = leader_total - total_display
        delta_str = f'<span style="color:var(--text-muted);font-weight:600;font-size:0.7rem;">({-delta})</span>' if delta > 0 else '<span style="color:var(--accent);font-size:0.7rem;">(0)</span>'
        cells = f'<td>{medal_symbol} {rank_num}</td><td><a href="boleiros/{who_name}.html">{who_display}</a> {delta_str} {trend} <span style="font-size:0.75rem;">{badges_str}</span></td>'
        cells += f'<td style="font-weight:700;color:var(--accent);text-align:right;">{total_display}</td>'
        cells += f'<td style="text-align:right;color:var(--warning);">{bonus_display}</td>'
        if has_penalty:
            pen_color = "var(--danger)" if penalty_display > 0 else "var(--text-muted)"
            pen_val = f"-{penalty_display}" if penalty_display > 0 else "-"
            cells += f'<td style="text-align:right;color:{pen_color};">{pen_val}</td>'
        for rn in score_names:
            val = int(row.get(rn, 0))
            clr = "var(--success)" if val > 0 else "var(--text-muted)"
            cells += f'<td style="text-align:right;color:{clr};">{val}</td>'
        cells += f'<td style="text-align:right;color:var(--danger);">{"\U0001f993 " if zebra_display > 0 else ""}{zebra_display if zebra_display > 0 else "-"}</td>'
        rank_rows_updated += f'<tr class="{rank_class}">{cells}</tr>\n'

    return f"""
<div style="overflow-x:auto;">
    <table class="rank-table">
        <thead><tr>{rank_header_combined}</tr></thead>
        <tbody>{rank_rows_updated}</tbody>
    </table>
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
    _parts: list[pd.DataFrame] = []
    _gp = _load_gold_data(config)
    if not _gp.empty:
        _parts.append(_gp)
    for pr in (config.playoff_rounds or []):
        pp = config.gold_playoff_all_path(pr.key)
        if os.path.exists(pp):
            df_pp = pd.read_csv(pp, sep=",")
            if not df_pp.empty and "who" in df_pp.columns:
                _parts.append(df_pp)
    if not _parts:
        return ""
    df_valid = pd.concat(_parts, ignore_index=True) if len(_parts) > 1 else _parts[0]
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
    _parts: list[pd.DataFrame] = []
    _gp = _load_gold_data(config)
    if not _gp.empty:
        _parts.append(_gp)
    for pr in (config.playoff_rounds or []):
        pp = config.gold_playoff_all_path(pr.key)
        if os.path.exists(pp):
            df_pp = pd.read_csv(pp, sep=",")
            if not df_pp.empty and "who" in df_pp.columns:
                _parts.append(df_pp)
    if not _parts:
        return ""
    df_valid = pd.concat(_parts, ignore_index=True) if len(_parts) > 1 else _parts[0]

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
        bg_color = "rgba(220,60,60,0.15)" if pct > 20 else "rgba(45,157,106,0.15)" if pct < 10 else "rgba(212,165,69,0.15)"
        return f'<span style="display:inline-flex;align-items:center;gap:0.4rem;background:{bg_color};padding:0.25rem 0.7rem;border-radius:999px;font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.01em;"><span>\U0001f993</span> <strong>{num_upsets}</strong> zebras em {total} ({pct}%)</span>\n'
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return ""


def _build_bottom_nav_dashboard(prefix: str = "", config: ChampionshipConfig | None = None) -> str:
    """Build the bottom navigation for the dashboard."""
    if config and config.nav_items:
        items = [(ni["href"], ni.get("icon", ""), ni["label"]) for ni in config.nav_items]
    else:
        items = [
            ("index.html", "\U0001f3e0", "In\u00edcio"),
            ("bolao_xray.html", "\U0001f50d", "Raio-X"),
            ("arena.html", "\u2694\ufe0f", "Arena"),
            ("zebras.html", "\U0001f993", "Zebras"),
            ("palpites.html", "\U0001f4cb", "Palpites"),
            ("boleiros.html", "\U0001f465", "Boleiros"),
        ]
    links = ""
    for href, icon, label in items:
        cls = ' class="active"' if href == "index.html" else ""
        links += f'<a href="{prefix}{href}"{cls}><span class="nav-icon">{icon}</span>{label}</a>\n'
    return f'<nav class="bottom-nav">{links}</nav>'


def _build_match_hour_lookup(config: ChampionshipConfig) -> dict[str, tuple[str, str]]:
    """Build match_slug -> (date, hour) lookup from gold prediction data.
    
    The hour from predictions (Excel) is the source of truth for match page
    filenames; games.csv may have a different hour for the same match.
    """
    lookup: dict[str, tuple[str, str]] = {}
    gold_all = config.gold_all_path()
    if os.path.exists(gold_all):
        try:
            df_gold = pd.read_csv(gold_all, sep=",")
            if not df_gold.empty and "match" in df_gold.columns:
                for _, g_row in df_gold.drop_duplicates("match").iterrows():
                    m = str(g_row.get("match", ""))
                    d = str(g_row.get("date", ""))
                    h = str(g_row.get("hour", ""))
                    if m and d:
                        lookup[m] = (d, h)
        except Exception:
            pass
    for pr in (config.playoff_rounds or []):
        pp = config.gold_playoff_all_path(pr.key)
        if os.path.exists(pp):
            try:
                df_pp = pd.read_csv(pp, sep=",")
                if not df_pp.empty and "match" in df_pp.columns:
                    for _, g_row in df_pp.drop_duplicates("match").iterrows():
                        m = str(g_row.get("match", ""))
                        d = str(g_row.get("date", ""))
                        h = str(g_row.get("hour", ""))
                        if m and d and m not in lookup:
                            lookup[m] = (d, h)
            except Exception:
                pass
    return lookup


def _build_live_games(config: ChampionshipConfig, now_str: str) -> str:
    """Build a card for each match currently marked as 'live' in games.csv."""
    df = pd.read_csv(config.results_file, sep=",")
    live = df[df["time_elapsed"] == "live"].copy()
    if live.empty:
        return ""

    _match_hour = _build_match_hour_lookup(config)

    rev_map = {v: k for k, v in config.team_name_mapping.items()}
    cards = ""
    for _, row in live.iterrows():
        home = str(row["home_team"])
        away = str(row["away_team"])
        hg = int(row["home_goals"]) if pd.notna(row.get("home_goals")) else 0
        ag = int(row["away_goals"]) if pd.notna(row.get("away_goals")) else 0
        match_slug = str(row.get("match", ""))
        round_val = row.get("round", "")

        # Determine phase directory for the match HTML link
        try:
            int(round_val)
            phase_dir = config.group_phase_label
        except (ValueError, TypeError):
            phase_dir = str(round_val) if round_val else config.group_phase_label

        # Use hour from gold prediction data (not games.csv) so the href matches
        # the actual filename on disk (which uses the Excel/prediction hour).
        gold_info = _match_hour.get(match_slug)
        if gold_info:
            date_part, hour_part = gold_info
        else:
            # Fallback: parse from games.csv "YYYY-MM-DD HHh" format
            date_parts = str(row["date"]).split(" ")
            date_part = date_parts[0] if date_parts else str(row["date"])
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
        <div class="date">{date_part}</div>
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
    match_slug = str(last.get("match", ""))
    round_val = last.get("round", "")

    # Determine phase directory for the match HTML link
    try:
        int(round_val)
        phase_dir = config.group_phase_label
    except (ValueError, TypeError):
        phase_dir = str(round_val) if round_val else config.group_phase_label

    # Use hour from gold prediction data (not games.csv) so the href matches
    # the actual filename on disk (which uses the Excel/prediction hour).
    _match_hour = _build_match_hour_lookup(config)
    gold_info = _match_hour.get(match_slug)
    if gold_info:
        date_part, hour_part = gold_info
    else:
        # Fallback: parse from games.csv "YYYY-MM-DD HHh" format
        date = str(last["date"])
        date_parts = date.split(" ")
        date_part = date_parts[0] if date_parts else date
        hour_part = date_parts[1].strip() if len(date_parts) > 1 else ""

    # Link to the per-match page
    game_href = f"jogos/{phase_dir}/{date_part}_{hour_part}_{match_slug}.html" if match_slug else ""

    # Reconstruct full date display from parts
    date = f"{date_part} {hour_part}" if hour_part else date_part

    rev_map = {v: k for k, v in config.team_name_mapping.items()}
    home_logo = _team_logo_tag(rev_map.get(home, home), config, cls="team-logo-sm", start=config.reports_dir + "/html")
    away_logo = _team_logo_tag(rev_map.get(away, away), config, cls="team-logo-sm", start=config.reports_dir + "/html")

    # Check if the last match was a zebra
    zebra_badge = ""
    try:
        upset_path = os.path.join(config._au_first_round(), "upset_tracker.csv")
        if os.path.exists(upset_path):
            df_upset = pd.read_csv(upset_path, sep=",")
            if match_slug:
                upset_row = df_upset[df_upset["match"] == match_slug]
                if not upset_row.empty and int(upset_row.iloc[0].get("is_upset", 0)) == 1:
                    nc = int(upset_row.iloc[0].get("num_correct", 999))
                    fav = upset_row.iloc[0].get("favorite", "?")
                    nc = int(upset_row.iloc[0].get("num_correct", 999))
                    fav = upset_row.iloc[0].get("favorite", "?")
                    label = ZEBRA_MONSTRA_LABEL if nc <= 2 else ZEBRA_GRANDE_LABEL
                    zebra_badge = f'<div style="text-align:center;margin-top:0.3rem;"><span class="badge badge-danger">{label}</span> <span style="font-size:0.7rem;color:var(--text-muted);">{nc} acertaram \u2014 favorito {fav} n\u00e3o venceu</span></div>'
    except Exception:
        pass

    ver_jogo_link = f'<div style="text-align:center;margin-top:0.4rem;"><a href="{game_href}" style="font-size:0.75rem;font-weight:600;color:var(--accent);text-decoration:none;">\U0001f4fa ver jogo</a></div>' if game_href else ""

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
        {ver_jogo_link}
    </div>
</div>
"""


def _slug_from_filename(filename: str) -> str:
    """Extract match slug from an HTML filename.

    Pattern: YYYY-MM-DD_HHh_<slug>.html -> <slug>
    """
    base = os.path.basename(filename).replace(".html", "")
    m = re.match(r"\d{4}-\d{2}-\d{2}_\d{1,2}h(?:\d{2})?_(.+)", base)
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
                    nc = int(r.get("num_correct", 999))
                    upset_icons[str(r["match"])] = ZEBRA_MONSTRA_EMOJI if nc <= 2 else ZEBRA_GRANDE_EMOJI
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
            out += f'<a href="{href}" style="display:flex;align-items:center;justify-content:space-between;background:var(--card-bg);border:1px solid var(--card-border);border-radius:8px;padding:0.45rem 0.7rem;font-size:0.75rem;font-weight:500;color:var(--text);text-decoration:none;transition:border-color 0.15s;" onmouseover="this.style.borderColor=\'var(--accent)\'" onmouseout="this.style.borderColor=\'var(--card-border)\'"><span style="display:flex;align-items:center;gap:0.3rem;"><span style="font-size:0.65rem;color:var(--text-muted);">{date_part}</span>{home_logo}{home_slug}{score_str or " vs "}{away_logo}{away_slug}</span> <span style="display:flex;align-items:center;gap:0.2rem;">{zebra_icon}{badge}</span></a>\n'
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

    # Find the round index that contains the next upcoming game.
    # Default to -1 (all closed) so the Segunda Fase section below is visible
    # when all group-phase matches are finished.
    open_round = -1
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

    # Playoff rounds (all wrapped in accordions)
    playoff_emojis = {"segunda_fase": "\U0001f3c6", "oitavas": "\U0001f3c1", "quartas": "\U0001f525", "semi": "\U0001f3af", "terceiro_lugar": "\U0001f949", "final": "\U0001f3c6"}

    # Determine which playoff phase has today's or the next upcoming match.
    # Extract dates from filenames (YYYY-MM-DD_HHh_…).
    today_str = datetime.now().strftime("%Y-%m-%d")
    open_playoff_phase: str | None = None
    best_phase_date: str | None = None
    for pr in config.playoff_rounds:
        po_dir = _norm(os.path.join(html_base, "jogos", pr.key))
        po_files = sorted(glob(_norm(os.path.join(po_dir, "*.html"))))
        po_files = [f for f in po_files if "index" not in f]
        if not po_files:
            continue
        # Check if this phase has a match today
        for fp in po_files:
            base = os.path.basename(fp)
            date_candidate = base[:10]  # YYYY-MM-DD from filename start
            if date_candidate == today_str:
                open_playoff_phase = pr.key
                break
        if open_playoff_phase:
            break
        # Track earliest future date as fallback
        for fp in po_files:
            base = os.path.basename(fp)
            date_candidate = base[:10]
            if date_candidate > today_str:
                if best_phase_date is None or date_candidate < best_phase_date:
                    best_phase_date = date_candidate
                    open_playoff_phase = pr.key
                break  # files are sorted, first is earliest

    for pr in config.playoff_rounds:
        po_dir = _norm(os.path.join(html_base, "jogos", pr.key))
        po_files = sorted(glob(_norm(os.path.join(po_dir, "*.html"))))
        po_files = [f for f in po_files if "index" not in f]
        emoji = playoff_emojis.get(pr.key, "")

        po_links = _build_compact_grid(po_files, results_map)

        is_open = pr.key == open_playoff_phase
        sections += f"""
<div class="section">
    <div class="section-title">{emoji} {pr.name} ({len(po_files)})</div>
    <div style="margin:0 0.75rem;">
        <details {"open" if is_open else ""}>
            <summary style="padding:0.6rem 0.75rem;font-size:0.8rem;">{pr.name} ({len(po_files)})</summary>
            <div class="content" style="padding:0.5rem 0.75rem 0.75rem;">{po_links}</div>
        </details>
    </div>
</div>
"""

    return sections






# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def _build_badge_accordion(config: ChampionshipConfig) -> str:
    """Build a single accordion explaining each badge (like 'Legenda dos acertos')."""
    badges = [
        ("\U0001f525", "Embrazado", "streak \u2265 3 acertos consecutivos"),
        ("\U0001f993", "Caçador de Zebras", "top 3 que mais acertaram zebras"),
        ("\U0001f40d", "Líder", "1\u00ba lugar geral no ranking"),
        ("\U0001f4a5", "Ousado", "aposta acima da média do bolão"),
        ("\U0001F9CA", "Conservador", "aposta abaixo da média do bolão"),
        ("\U0001f3af", "Especialista", "maior precisão em time (\u2265 3 palpites, >50%)"),
    ]
    rows = "".join(
        f'<div class="emoji-row">'
        f'<span class="e">{emoji}</span>'
        f'<span class="desc">{label}</span>'
        f'<span class="pts" style="font-weight:400;color:var(--text-muted);font-size:0.6rem;width:auto;text-align:left;">{desc}</span>'
        f'</div>\n'
        for emoji, label, desc in badges
    )
    return f"""<details class="accordion-emoji">
<summary>\U0001f3c6 Legenda das classificações</summary>
<div class="content">{rows}</div>
</details>
"""


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
        '<div class="emoji-row">'
        '<span class="e">\U0001f993</span>'
        '<span class="desc">Zebra acertada (favorito n\u00e3o venceu e \u226570% erraram)</span>'
        '<span class="pts">contagem</span>'
        '</div>\n'
    )
    return f"""<details class="accordion-emoji">
<summary>\U0001f9e9 Legenda dos acertos</summary>
<div class="content">{rows}</div>
</details>
"""


def _copy_sorttable_js(html_base: str) -> None:
    _src = _norm(os.path.join(os.path.dirname(__file__), "sorttable.js"))
    _dst = _norm(os.path.join(html_base, "sorttable.js"))
    try:
        with open(_src, "rb") as f:
            _c = f.read()
        with open(_dst, "wb") as f:
            f.write(_c)
    except Exception as e:
        print_colored(f"  [ERROR] Failed to copy sorttable.js: {e}", "red")

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
    badge_accordion = _build_badge_accordion(config)
    emoji_accordion = _build_emoji_accordion(config)
    # Temperature bar color: derived from zebra percentage (if available)
    # Higher zebra % -> warmer (reddish-gold), lower -> cooler (blue)
    temp_color = "var(--primary)"
    if zebra_counter:
        import re as _re
        _zp = _re.search(r'<strong>(\d+)</strong> zebras em (\d+)', zebra_counter)
        if _zp:
            _num_z = int(_zp.group(1))
            _total_z = int(_zp.group(2))
            if _total_z > 0:
                _pct = _num_z / _total_z
                if _pct > 0.25:
                    temp_color = "#dc3c3c"
                elif _pct > 0.15:
                    temp_color = "#d4a545"
                else:
                    temp_color = "#2d9d6a"

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.report_title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
    {config.theme.to_css_vars()}
    {_CSS_DASHBOARD}
    </style>
</head>
<body>

<div class="hero" style="--temp-color:{temp_color};">
    <div class="temp-bar"></div>
    <h1>{config.report_title}</h1>
    <div class="subtitle">Bol\u00e3o da Copa</div>
    <div style="margin-top:0.4rem;display:flex;justify-content:center;gap:0.5rem;flex-wrap:wrap;">
        {zebra_counter}
        <span style="font-family:var(--font-mono);font-size:0.6rem;color:var(--text-muted);letter-spacing:0.02em;">{now_str}</span>
    </div>
</div>

{live_games}

{last_result}

{upcoming}

<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;margin:0 0.75rem;">
    <a href="tabela_real.html">
        <div class="card" style="text-align:center;padding:0.75rem 0.5rem;">
            <div style="font-family:var(--font-display);font-weight:600;font-size:0.85rem;">\U0001f3c6 Grupos</div>
        </div>
    </a>
    <a href="times.html">
        <div class="card" style="text-align:center;padding:0.75rem 0.5rem;">
            <div style="font-family:var(--font-display);font-weight:600;font-size:0.85rem;">\U0001f3c6 Times</div>
        </div>
    </a>
    <a href="arena.html">
        <div class="card" style="text-align:center;padding:0.75rem 0.5rem;">
            <div style="font-family:var(--font-display);font-weight:600;font-size:0.85rem;">\u2694\ufe0f Arena</div>
        </div>
    </a>
    <a href="rodadas.html">
        <div class="card" style="text-align:center;padding:0.75rem 0.5rem;">
            <div style="font-family:var(--font-display);font-weight:600;font-size:0.85rem;">\U0001f4ca Rodadas</div>
        </div>
    </a>
</div>

{badge_accordion}

{emoji_accordion}

<div class="section">
    <div class="section-title">\U0001f3c6 Ranking</div>
    <div class="card">{full_ranking}</div>
</div>

<div class="section">
    <div class="section-title">\U0001f4c2 Jogos por Fase</div>
    {phase_buttons}
</div>

{_build_bottom_nav_dashboard(config=config)}

<script src="sorttable.js"></script>
</body>
</html>"""

    html_base = _norm(os.path.join(config.reports_dir, "html"))
    os.makedirs(html_base, exist_ok=True)
    with open(_norm(config.index_html_path()), "w", encoding="utf-8") as f:
        f.write(html_content)

    print_colored("index.html created", "green")


def _build_insights(
    config: ChampionshipConfig,
    boldness_map: dict[str, float],
    streak_data: dict[str, tuple[str, int]],
    timing_map: dict[str, float],
    arq_map: dict[str, dict[str, str]],
    total_pts: dict[str, int],
    player_games: dict[str, int],
    player_scored: dict[str, int],
    zebra_counts_b: dict[str, int],
) -> str:
    """Build the insights/records section for boleiros.html."""
    _player_link = lambda n: f'<a href="boleiros/{n}.html" style="font-weight:600;">{n}</a>'
    _v = lambda n, v: f"<tr><td>{n}</td><td style='text-align:right;font-weight:700;color:var(--accent);'>{v}</td></tr>"

    rows_left = ""
    rows_right = ""

    # 1. Highest total score
    if total_pts:
        top = max(total_pts, key=total_pts.get)
        rows_left += _v(f"\U0001f3c6 Maior Pontua\u00e7\u00e3o", f"{_player_link(top)} {total_pts[top]}")

    # 2. Best average
    best_mn, best_mv = "", 0
    for p in total_pts:
        ng = player_games.get(p, 0)
        if ng >= 5 and total_pts[p]/ng > best_mv: best_mv, best_mn = total_pts[p]/ng, p
    if best_mn:
        rows_right += _v(f"\U0001f4c8 Melhor M\u00e9dia", f"{_player_link(best_mn)} {best_mv:.2f}")

    # 3. Most exact scores
    score_names = config.scoring_rule_names()
    exact_col = next((c for c in score_names if c.startswith("1-")), "")
    gold_dir = config._au_first_round()
    _gp = _load_gold_data(config)
    _full_parts = [_gp]
    for pr in (config.playoff_rounds or []):
        pp = config.gold_playoff_all_path(pr.key)
        if os.path.exists(pp):
            df_pp = pd.read_csv(pp, sep=",")
            if not df_pp.empty and "who" in df_pp.columns: _full_parts.append(df_pp)
    _full = pd.concat(_full_parts, ignore_index=True) if len(_full_parts) > 1 else _full_parts[0]

    if exact_col and exact_col in _full.columns:
        df_v = _full[_full.get("valido", 0) == 1] if "valido" in _full.columns else _full
        exact_counts = df_v.groupby("who")[exact_col].sum().to_dict()
        if exact_counts:
            top_exact = max(exact_counts, key=exact_counts.get)
            rows_left += _v(f"\U0001f3af Mais Placar Exato", f"{_player_link(top_exact)} {int(exact_counts[top_exact])}")

    # 4. Highest boldness
    if boldness_map:
        top_bold = max(boldness_map, key=lambda p: abs(boldness_map[p]))
        bv = boldness_map[top_bold]
        lbl = "\U0001f4a5 Ousado" if bv > 0 else "\U0001F9CA Conservador"
        rows_right += _v(f"{lbl}", f"{_player_link(top_bold)} {bv:+.2f}")

    # 5. Longest hit streak
    if streak_data:
        top_streak = max(((p, l) for p, (t, l) in streak_data.items() if t == "hit"), key=lambda x: x[1], default=("", 0))
        if top_streak[0]:
            rows_left += _v(f"\U0001f525 Maior Streak Acertos", f"{_player_link(top_streak[0])} {top_streak[1]}")

    # 6. Longest miss streak
    miss_data = [(p, l) for p, (t, l) in streak_data.items() if t == "miss"]
    if miss_data:
        top_miss = max(miss_data, key=lambda x: x[1])
        rows_right += _v(f"\U0001f4a9 Maior Streak Erros", f"{_player_link(top_miss[0])} {top_miss[1]}")

    # 7. Earliest predictor
    if timing_map:
        top_early = max(timing_map, key=timing_map.get)
        rows_left += _v(f"\U0001f4c5 Mais Cedo (lead)", f"{_player_link(top_early)} {timing_map[top_early]:.0f}d")

    # 8. Most zebras
    if zebra_counts_b:
        top_zebra = max(zebra_counts_b, key=zebra_counts_b.get)
        rows_right += _v(f"\U0001f993 Mais Zebras", f"{_player_link(top_zebra)} {zebra_counts_b[top_zebra]}")

    # 9. Best aproveitamento
    best_ap_name, best_ap_val = "", 0
    for p in total_pts:
        ng, ns = player_games.get(p, 0), player_scored.get(p, 0)
        if ng >= 5:
            a = ns / ng * 100
            if a > best_ap_val: best_ap_val, best_ap_name = a, p
    if best_ap_name:
        rows_left += _v(f"\u2705 Melhor Aproveitamento", f"{_player_link(best_ap_name)} {best_ap_val:.1f}%")

    # 10. Most games played
    if player_games:
        top_games = max(player_games, key=player_games.get)
        rows_right += _v(f"\U0001f3b2 Mais Palpites", f"{_player_link(top_games)} {player_games[top_games]}")

    return f"""<div class="section">
    <div class="section-title">\U0001f4ca Recordes &amp; Insights</div>
    <div class="card">
        <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
            <tr>
                <td style="width:50%;vertical-align:top;padding-right:0.5rem;">
                    <table style="width:100%;border-collapse:collapse;">{rows_left}</table>
                </td>
                <td style="width:50%;vertical-align:top;padding-left:0.5rem;border-left:1px solid var(--card-border);">
                    <table style="width:100%;border-collapse:collapse;">{rows_right}</table>
                </td>
            </tr>
        </table>
    </div>
</div>"""


def generate_boleiros_index(config: ChampionshipConfig) -> None:
    """Create boleiros.html — central directory listing all players with links to their pages."""
    print_colored("creating boleiros.html", "sand")
    html_base = _norm(os.path.join(config.reports_dir, "html"))

    _all_parts: list[pd.DataFrame] = []
    _gp = _load_gold_data(config)
    if not _gp.empty:
        _all_parts.append(_gp)
    for pr in (config.playoff_rounds or []):
        pp = config.gold_playoff_valid_path(pr.key)
        if os.path.exists(pp):
            df_pp = pd.read_csv(pp, sep=",")
            if not df_pp.empty and "who" in df_pp.columns:
                _all_parts.append(df_pp)
    df_all_pts = pd.concat(_all_parts, ignore_index=True).groupby("who", as_index=False)["pontos"].sum() if _all_parts else pd.DataFrame()

    # ── Full gold data (not grouped) for per-player stats ──
    _full_gold: pd.DataFrame = pd.concat(_all_parts, ignore_index=True) if _all_parts else pd.DataFrame()

    # ── Separate group-only match points ──
    grupos_pts: dict[str, int] = {}
    if not _gp.empty:
        df_grupos = _gp.groupby("who", as_index=False)["pontos"].sum()
        for _, r in df_grupos.iterrows():
            grupos_pts[r["who"]] = int(r["pontos"])

    # ── Phase labels ──
    play_phase_order: list[str] = [pr.key for pr in (config.playoff_rounds or [])]
    play_phase_name: dict[str, str] = {pr.key: _short_name(pr.name, config) for pr in (config.playoff_rounds or [])}
    play_phase_emoji: dict[str, str] = dict(config.phase_emojis) if config.phase_emojis else {
        "segunda_fase": "\U0001f3c6", "oitavas": "\U0001f3c1",
        "quartas": "\U0001f525", "semi": "\U0001f3af",
        "terceiro_lugar": "\U0001f949", "final": "\U0001f3c6",
    }

    # ── Load bonus points from playoffs_scored.csv ──
    bonus_pts: dict[str, int] = {}
    bonus_path = _norm(os.path.join(config._au_first_round(), "playoffs_scored.csv"))
    if os.path.exists(bonus_path):
        df_bonus = pd.read_csv(bonus_path, sep=",")
        for _, r in df_bonus.iterrows():
            b = r["boleiro"]
            pts = int(r["points"])
            bonus_pts[b] = bonus_pts.get(b, 0) + pts

    # ── Bonus by phase (per-phase "Bônus" columns) ──
    ck = config.champion_phase_key
    all_bonus_phases: list[str] = play_phase_order + ([ck] if ck not in play_phase_order else [])
    bonus_phase_name: dict[str, str] = {**play_phase_name, ck: "Campe\u00e3o"}
    bonus_phase_emoji: dict[str, str] = {**play_phase_emoji, ck: "\U0001f3c6"}
    bonus_by_phase: dict[str, dict[str, int]] = {pk: {} for pk in all_bonus_phases}
    if os.path.exists(bonus_path):
        df_bonus2 = pd.read_csv(bonus_path, sep=",")
        for _, r in df_bonus2.iterrows():
            b = r["boleiro"]
            ph = str(r["phase"])
            pts = int(r["points"])
            if ph in bonus_by_phase:
                bonus_by_phase[ph][b] = bonus_by_phase[ph].get(b, 0) + pts

    # ── Match points per phase (for per-phase "Só Jogos" columns) ──
    # grupo_pts = group match points (already loaded via _gp)
    match_pts_by_phase: dict[str, dict[str, int]] = {pk: {} for pk in play_phase_order}
    for pr in (config.playoff_rounds or []):
        pp = config.gold_playoff_valid_path(pr.key)
        if os.path.exists(pp):
            df_pp = pd.read_csv(pp, sep=",")
            if not df_pp.empty and "who" in df_pp.columns and "pontos" in df_pp.columns:
                for who, grp in df_pp.groupby("who"):
                    match_pts_by_phase[pr.key][who] = int(grp["pontos"].sum())

    # ── Zebra count per player (same filter as ranking table) ──
    zebra_counts_b: dict[str, int] = {}
    upset_path_b = _norm(os.path.join(config._au_first_round(), "upset_tracker.csv"))
    if os.path.exists(upset_path_b):
        try:
            df_upset_b = pd.read_csv(upset_path_b, sep=",")
        except pd.errors.EmptyDataError:
            df_upset_b = pd.DataFrame()
        df_upset_b = df_upset_b[df_upset_b["real_winner"].notna() & (df_upset_b["real_winner"] != "")].copy() if "real_winner" in df_upset_b.columns else df_upset_b
        upset_only_b = df_upset_b[df_upset_b.get("is_upset", 0) == 1]
        for _, r in upset_only_b.iterrows():
            for p in [x.strip() for x in str(r.get("players_correct", "")).split("|") if x.strip()]:
                zebra_counts_b[p] = zebra_counts_b.get(p, 0) + 1

    # ── Per-player extra stats from full gold data ──
    player_games: dict[str, int] = {}       # total valid predictions
    player_scored: dict[str, int] = {}      # count of predictions with pontos > 0
    if not _full_gold.empty and "who" in _full_gold.columns:
        df_valid = _full_gold[_full_gold.get("valido", 0) == 1]
        if not df_valid.empty:
            _g = df_valid.groupby("who")
            player_games = _g.size().to_dict()
            player_scored = _g.apply(lambda x: (x["pontos"] > 0).sum()).to_dict()

    # ── Build scores per player ──
    jogos_pts: dict[str, int] = {}  # total match points (group + playoff)
    if not df_all_pts.empty:
        for _, r in df_all_pts.iterrows():
            jogos_pts[r["who"]] = int(r["pontos"])
    all_players = set(jogos_pts.keys()) | set(bonus_pts.keys())
    total_pts: dict[str, int] = {}
    penalty_pts: dict[str, int] = {}
    for p in all_players:
        pen = config.total_penalty(p)
        jog = jogos_pts.get(p, 0)
        bon = bonus_pts.get(p, 0)
        penalty_pts[p] = pen
        total_pts[p] = jog + bon - pen
    has_penalty = any(v > 0 for v in penalty_pts.values())

    # Headers: per-phase breakdown (placares, bonus, final, ant+final)
    header_cols = '<th style="text-align:center;">#</th><th>Jogador</th>'
    header_cols += '<th style="text-align:right;font-size:0.6rem;color:var(--warning);">Total</th>'
    header_cols += '<th style="text-align:right;font-size:0.55rem;color:var(--text-muted);">1\u00aa Fase<br><span style="font-weight:400;">Placares</span></th>'
    for pk in all_bonus_phases:
        em = bonus_phase_emoji.get(pk, "")
        nm = bonus_phase_name.get(pk, pk)
        header_cols += f'<th style="text-align:right;font-size:0.55rem;color:var(--success);">{em} {nm}<br><span style="font-weight:400;">Bonus</span></th>'
        header_cols += f'<th style="text-align:right;font-size:0.55rem;color:var(--warning);">{em} {nm}<br><span style="font-weight:400;">Placar</span></th>'
        header_cols += f'<th style="text-align:right;font-size:0.55rem;color:var(--accent);">{em} {nm}<br><span style="font-weight:400;">Final</span></th>'
        header_cols += f'<th style="text-align:right;font-size:0.55rem;color:var(--text-muted);">{em} {nm}<br><span style="font-weight:400;">Ant+Final</span></th>'

    player_rows = ""
    if total_pts:
        sorted_players = sorted(total_pts.items(), key=lambda x: (-x[1], x[0]))
        rank = 1
        for name, total in sorted_players:
            medal = "\U0001f947" if rank == 1 else "\U0001f948" if rank == 2 else "\U0001f949" if rank == 3 else f"<span style='color:var(--text-muted);'>{rank}</span>"
            cells = f'<td style="padding:0.4rem 0.5rem;text-align:center;">{medal}</td>'
            cells += f'<td style="padding:0.4rem 0.5rem;"><a href="boleiros/{name}.html" style="font-weight:600;">{name}</a></td>'
            cells += f'<td style="padding:0.4rem 0.5rem;font-weight:700;color:var(--accent);text-align:right;">{total}</td>'
            gp = grupos_pts.get(name, 0)
            cells += f'<td style="padding:0.4rem 0.5rem;text-align:right;color:var(--text-muted);">{gp}</td>'
            cumulative = gp
            for pk in all_bonus_phases:
                placar = match_pts_by_phase.get(pk, {}).get(name, 0)
                bonus = bonus_by_phase.get(pk, {}).get(name, 0)
                final = placar + bonus
                cumulative += final
                bc = "var(--success)" if bonus > 0 else "var(--text-muted)"
                pc = "var(--warning)" if placar > 0 else "var(--text-muted)"
                fc = "var(--accent)" if final > 0 else "var(--text-muted)"
                cells += f'<td style="padding:0.4rem 0.5rem;text-align:right;color:{bc};">{bonus}</td>'
                cells += f'<td style="padding:0.4rem 0.5rem;text-align:right;color:{pc};">{placar}</td>'
                cells += f'<td style="padding:0.4rem 0.5rem;text-align:right;color:{fc};">{final}</td>'
                cells += f'<td style="padding:0.4rem 0.5rem;text-align:right;color:var(--text-muted);">{cumulative}</td>'
            player_rows += f"<tr>{cells}</tr>\n"
            rank += 1

    # ── Load extra data sources ──
    gold_dir = config._au_first_round()
    # Boldness
    boldness_map: dict[str, float] = {}
    bold_path = _norm(os.path.join(gold_dir, "boldness_index.csv"))
    if os.path.exists(bold_path):
        for _, r in pd.read_csv(bold_path, sep=",").iterrows():
            boldness_map[r["boleiro"]] = float(r["boldness_score"])
    # Prediction timing
    timing_map: dict[str, float] = {}
    timing_path = _norm(os.path.join(gold_dir, "prediction_timing.csv"))
    if os.path.exists(timing_path):
        for _, r in pd.read_csv(timing_path, sep=",").iterrows():
            timing_map[r["boleiro"]] = float(r["lead_days"])
    # Consistency
    streak_data: dict[str, tuple[str, int]] = {}
    cons_path = _norm(os.path.join(gold_dir, "consistency.csv"))
    if os.path.exists(cons_path):
        for boleiro, grp in pd.read_csv(cons_path, sep=",").groupby("boleiro"):
            grp = grp.sort_values("date")
            _sl, _st = 0, ""
            for _, r in reversed(list(grp.iterrows())):
                st = r.get("streak_type", "")
                if st == "hit" and (_st == "" or _st == "hit"): _st, _sl = "hit", _sl + 1
                elif st == "miss" and (_st == "" or _st == "miss"): _st, _sl = "miss", _sl + 1
                else: break
            if _st: streak_data[boleiro] = (_st, _sl)
    # Archetypes
    arq_map: dict[str, dict[str, str]] = {}
    arq_path = _norm(os.path.join(gold_dir, "arquetipos_classification.csv"))
    if os.path.exists(arq_path):
        for _, r in pd.read_csv(arq_path, sep=",").iterrows():
            arq_map[r["boleiro"]] = {"emoji": str(r.get("arquetipo_emoji", "")), "nome": str(r.get("arquetipo", ""))}

    # ── Aggregate stats ──
    n_players = len(total_pts)
    total_preds = sum(player_games.values())
    total_zebras = sum(zebra_counts_b.values())

    # Best Média (avg pts per game, >=3 games)
    best_media_name, best_media_val = "", 0
    for p in total_pts:
        ng = player_games.get(p, 0)
        if ng >= 3:
            m = total_pts[p] / ng
            if m > best_media_val: best_media_val, best_media_name = m, p
    # Best Aprov% (>=3 games)
    best_aprov_name, best_aprov_val = "", 0
    for p in total_pts:
        ng, ns = player_games.get(p, 0), player_scored.get(p, 0)
        if ng >= 3:
            a = ns / ng * 100
            if a > best_aprov_val: best_aprov_val, best_aprov_name = a, p
    # Most zebras
    best_zebra_name, best_zebra_val = "", 0
    for p, z in zebra_counts_b.items():
        if not p or p.strip().lower() in ("nan", "none", ""): continue
        if z > best_zebra_val: best_zebra_val, best_zebra_name = z, p
    # Highest boldness (>=10 games)
    best_bold_name, best_bold_val = "", 0.0
    for p, b in boldness_map.items():
        ng = player_games.get(p, 0)
        if ng >= 10 and abs(b) > abs(best_bold_val): best_bold_val, best_bold_name = b, p
    # Longest hit streak
    best_streak_name, best_streak_len = "", 0
    for p, (t, l) in streak_data.items():
        if t == "hit" and l > best_streak_len: best_streak_len, best_streak_name = l, p
    # Average metrics across all players
    all_media = [total_pts[p] / max(player_games.get(p, 1), 1) for p in total_pts if player_games.get(p, 0) >= 3]
    avg_media = sum(all_media) / len(all_media) if all_media else 0
    all_lead = [v for v in timing_map.values() if v > 0]
    avg_lead = sum(all_lead) / len(all_lead) if all_lead else 0
    all_bold = [abs(boldness_map[p]) for p in total_pts if p in boldness_map and player_games.get(p, 0) >= 10]
    avg_bold = sum(all_bold) / len(all_bold) if all_bold else 0
    # Total exact scores
    score_names = config.scoring_rule_names()
    exact_col = next((c for c in score_names if c.startswith("1-")), "")
    total_exact = 0
    if exact_col and exact_col in _full_gold.columns:
        total_exact = int(_full_gold[_full_gold["valido"] == 1][exact_col].sum()) if "valido" in _full_gold.columns else int(_full_gold[exact_col].sum())
    # Most exact scores
    best_exact_name, best_exact_val = "", 0
    if exact_col and exact_col in _full_gold.columns and "who" in _full_gold.columns:
        df_v = _full_gold[_full_gold.get("valido", 0) == 1] if "valido" in _full_gold.columns else _full_gold
        for who, grp in df_v.groupby("who"):
            ec = int(grp[exact_col].sum())
            if ec > best_exact_val: best_exact_val, best_exact_name = ec, who

    stats_cards = ""
    if n_players:
        stats_cards = f"""<div class="stat-row" style="grid-template-columns:repeat(3,1fr);">
    <div class="stat-card">
        <div class="value" style="font-size:1.3rem;">{n_players}</div>
        <div class="label">Participantes</div>
    </div>
    <div class="stat-card">
        <div class="value" style="font-size:1.3rem;">{total_preds}</div>
        <div class="label">Palpites V\u00e1lidos</div>
    </div>
    <div class="stat-card">
        <div class="value" style="font-size:1.3rem;">\U0001f993 {total_zebras}</div>
        <div class="label">Zebras Acertadas</div>
    </div>
</div>
<div class="stat-row" style="grid-template-columns:repeat(3,1fr);margin-top:0;">
    <div class="stat-card">
        <div class="value" style="font-size:1rem;color:var(--success);">{best_media_name}</div>
        <div class="label">Melhor M\u00e9dia ({best_media_val:.2f})</div>
    </div>
    <div class="stat-card">
        <div class="value" style="font-size:1rem;color:var(--voce);">{best_aprov_name}</div>
        <div class="label">Melhor Aprov% ({best_aprov_val:.1f}%)</div>
    </div>
    <div class="stat-card">
        <div class="value" style="font-size:1rem;color:var(--danger);">{best_zebra_name or "---"}</div>
        <div class="label">Mais Zebras ({best_zebra_val})</div>
    </div>
</div>
<div class="stat-row" style="grid-template-columns:repeat(3,1fr);margin-top:0;">
    <div class="stat-card">
        <div class="value" style="font-size:1rem;color:var(--warning);">{best_bold_name}</div>
        <div class="label">\U0001f4a5 Maior Ousadia ({best_bold_val:+.2f})</div>
    </div>
    <div class="stat-card">
        <div class="value" style="font-size:1rem;color:var(--success);">{best_streak_name or "---"}</div>
        <div class="label">\U0001f525 Maior Streak ({best_streak_len})</div>
    </div>
    <div class="stat-card">
        <div class="value" style="font-size:1rem;color:var(--accent);">{best_exact_name}</div>
        <div class="label">\U0001f3af Mais Placar Exato ({best_exact_val})</div>
    </div>
</div>"""

    body = f"""<div class="hero">
    <h1>\U0001f465 Boleiros</h1>
    <div class="subtitle">Todos os participantes do bol\u00e3o</div>
</div>
{stats_cards}
<div class="section">
    <div class="card" style="padding:0;">
        <div style="overflow-x:auto;">
            <table class="rank-table">
                <thead><tr>
                    {header_cols}
                </tr></thead>
                <tbody>{player_rows}</tbody>
            </table>
        </div>
    </div>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Boleiros - {config.report_title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
    {config.theme.to_css_vars()}
    {_CSS_DASHBOARD}
    </style>
</head>
<body>
{body}
<div style="text-align:center;padding:2rem 1rem 5rem;color:var(--text-muted);font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.02em;">
    atualizado \u00e0s {datetime.now(pytz.timezone(config.timezone)).strftime("%d/%m/%Y %H:%M:%S")}
</div>
""" + _build_bottom_nav_dashboard(config=config) + """
<script src="sorttable.js"></script>
</body>
</html>"""
    path = _norm(os.path.join(html_base, "boleiros.html"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print_colored("boleiros.html created", "green")
