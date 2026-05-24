"""Generate the index.html dashboard - mobile-first with hero, leaderboard, player grid."""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from glob import glob

import pandas as pd
import pytz

from src.core.config import ChampionshipConfig
from src.core.printing import print_colored


def _norm(path: str) -> str:
    """Normalize a path to the current OS format."""
    return os.path.normpath(path)


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
    background: linear-gradient(135deg, var(--primary), var(--primary-light));
    padding: 2rem 1rem;
    text-align: center;
    color: var(--text);
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

.game-card {
    flex: 0 0 85%;
    scroll-snap-align: start;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
    min-width: 200px;
}
.game-card .matchup { font-weight: 700; font-size: 1rem; margin: 0.5rem 0; }
.game-card .datetime { font-size: 0.8rem; color: var(--text-muted); }
.game-card .badge-live {
    display: inline-block;
    background: var(--danger);
    color: var(--text);
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    margin-bottom: 0.5rem;
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

/* Responsive */
@media (max-width: 359px) {
    .hero h1 { font-size: 1.4rem; }
    .hero .subtitle { font-size: 0.85rem; }
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

    games.sort(key=lambda g: g["dt"])
    return games[:limit]


def _parse_game_file(filepath: str, config: ChampionshipConfig) -> dict | None:
    """Extract game info from an HTML filename."""
    fname = os.path.basename(filepath).replace(".html", "")
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})_(\d{2})h", fname)
    if not match:
        return None

    year, month, day, hour = map(int, match.groups())
    tz = pytz.timezone(config.timezone)
    dt = tz.localize(datetime(year, month, day, hour))

    # Extract teams from filename
    rest = fname[match.end():]
    teams = rest.replace("_vs_", " vs ").replace("_", " ")

    href = filepath.replace("\\", "/").replace(
        f"{config.reports_dir.replace(chr(92), '/')}/html/", ""
    )

    return {"dt": dt, "teams": teams, "href": href, "date_str": f"{day:02d}/{month:02d} {hour:02d}h"}


def _build_full_ranking(config: ChampionshipConfig) -> str:
    """Build the full ranking table (copied from Raio-X)."""
    df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
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
    return f"""
<div style="overflow-x:auto;">
    <table class="rank-table">
        <thead><tr><th>#</th><th>Boleiro</th><th>Pts</th>{rank_header}</tr></thead>
        <tbody>{rank_rows}</tbody>
    </table>
</div>"""


def _build_upcoming_games(config: ChampionshipConfig) -> str:
    """Build the upcoming games horizontal scroll section."""
    html_base = _norm(os.path.join(config.reports_dir, "html"))
    games = _get_upcoming_games(html_base, config)

    if not games:
        return ""

    cards = ""
    for g in games:
        cards += (
            f'<div class="game-card">'
            f'<div class="badge-live">PROXIMO</div>'
            f'<div class="datetime">{g["date_str"]}</div>'
            f'<div class="matchup"><a href="{g["href"]}">{g["teams"]}</a></div>'
            f'</div>\n'
        )

    return f"""
<div class="section">
    <div class="section-title">\U0001f552 Proximos Jogos</div>
    <div class="scroll-row">{cards}</div>
</div>
"""


def _build_player_grid(config: ChampionshipConfig) -> str:
    """Build the player avatar grid with points."""
    df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
    df_pts = df_valid.groupby("who", as_index=False)["pontos"].sum()
    df_pts.sort_values("pontos", ascending=False, inplace=True)

    cards = ""
    for _, row in df_pts.iterrows():
        name = row["who"]
        pts = int(row["pontos"])
        cards += (
            f'<a href="boleiros/{name}.html" class="player-card">'
            f'<div class="player-avatar">{_initials(name)}</div>'
            f'<div>'
            f'<div class="player-name">{name}</div>'
            f'<div class="player-pts">{pts} pts</div>'
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
    try:
        df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
    except (FileNotFoundError, pd.errors.EmptyDataError):
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


def _build_last_result(config: ChampionshipConfig) -> str:
    """Build the last result card."""
    df_results = pd.read_csv(config.results_file, sep=",")
    df_results.dropna(subset=["home_goals"], inplace=True)
    if df_results.empty:
        return ""

    last = df_results.tail(1).iloc[0]
    home = str(last["home_team"])
    away = str(last["away_team"])
    hg = int(last["home_goals"])
    ag = int(last["away_goals"])
    date = str(last["date"])

    return f"""
<div class="section">
    <div class="section-title">\U0001f4ca Ultimo Resultado</div>
    <div class="card">
        <div class="result-card">
            <div class="team">{home}</div>
            <div class="score">{hg} - {ag}</div>
            <div class="team">{away}</div>
        </div>
        <div class="date">{date}</div>
    </div>
</div>
"""


def _build_phase_accordion(config: ChampionshipConfig) -> str:
    """Build collapsible phase sections with game links."""
    html_base = _norm(os.path.join(config.reports_dir, "html"))
    sections = ""

    # Group phase
    group_dir = _norm(os.path.join(html_base, "jogos", config.group_phase_label))
    group_files = sorted(glob(_norm(os.path.join(group_dir, "*.html"))))
    group_files = [f for f in group_files if "index" not in f]

    links = ""
    for fp in group_files:
        href = fp.replace("\\", "/").replace(
            f"{config.reports_dir.replace(chr(92), '/')}/html/", ""
        )
        label = (
            os.path.basename(fp)
            .replace(".html", "")
            .replace("_", " ")
            .replace("-vs-", " vs ")
            .replace("h ", "h | ")
        )
        links += f'<a href="{href}">{label}</a>\n'

    if not links:
        links = '<div class="empty-state">Nenhum jogo disponivel ainda</div>'

    sections += f"""
<details open>
    <summary>\u26bd {config.group_phase_label} ({len(group_files)})</summary>
    <div class="content">{links}</div>
</details>
"""

    # Playoff rounds
    playoff_emojis = {"oitavas": "\U0001f3c1", "quartas": "\U0001f525", "semi": "\U0001f3af", "final": "\U0001f3c6"}
    for pr in config.playoff_rounds:
        po_dir = _norm(os.path.join(html_base, "jogos", pr.key))
        po_files = sorted(glob(_norm(os.path.join(po_dir, "*.html"))))
        po_files = [f for f in po_files if "index" not in f]
        emoji = playoff_emojis.get(pr.key, "")

        po_links = ""
        for fp in po_files:
            href = fp.replace("\\", "/").replace(
                f"{config.reports_dir.replace(chr(92), '/')}/html/", ""
            )
            label = (
                os.path.basename(fp)
                .replace(".html", "")
                .replace("_", " ")
                .replace("-vs-", " vs ")
                .replace("h ", "h | ")
            )
            po_links += f'<a href="{href}">{label}</a>\n'

        if not po_links:
            po_links = '<div class="empty-state">Nenhum jogo disponivel ainda</div>'

        sections += f"""
<details>
    <summary>{emoji} {pr.name} ({len(po_files)})</summary>
    <div class="content">{po_links}</div>
</details>
"""

    return sections


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def generate_dashboard(config: ChampionshipConfig) -> None:
    """Create the index.html dashboard."""
    print_colored("creating index.html dashboard", "sand")

    tz = pytz.timezone(config.timezone)
    now_str = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")

    last_result = _build_last_result(config)
    full_ranking = _build_full_ranking(config)
    upcoming = _build_upcoming_games(config)
    player_grid = _build_player_grid(config)
    phase_accordion = _build_phase_accordion(config)

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
    <div class="subtitle">Bolao Dashboard</div>
</div>

{last_result}

<div class="section">
    <div class="section-title">\U0001f3c6 Ranking</div>
    <div class="card">{full_ranking}</div>
</div>

<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:0.75rem;margin:0 0.75rem;">
    <a href="arena.html">
        <div class="card" style="text-align:center;font-weight:600;border-color:var(--accent);">
            \u2694\ufe0f Arena
        </div>
    </a>
    <a href="ranking_evolution.html">
        <div class="card" style="text-align:center;font-weight:600;">
            \U0001f4c8 Evolucao
        </div>
    </a>
    <a href="boldometer.html">
        <div class="card" style="text-align:center;font-weight:600;">
            \U0001f4ca Boldometro
        </div>
    </a>
    <a href="bolao_xray.html">
        <div class="card" style="text-align:center;font-weight:600;">
            \U0001f50d Raio-X
        </div>
    </a>
    <a href="day_winners.html">
        <div class="card" style="text-align:center;font-weight:600;border-color:var(--accent);">
            \U0001f3c6 Day Winners
        </div>
    </a>
</div>

{upcoming}

{player_grid}

<div class="section">
    <div class="section-title">\U0001f4c2 Jogos por Fase</div>
    {phase_accordion}
</div>

<div class="footer">
    atualizado às {now_str}
</div>

</body>
</html>"""

    html_base = _norm(os.path.join(config.reports_dir, "html"))
    os.makedirs(html_base, exist_ok=True)
    with open(_norm(config.index_html_path()), "w", encoding="utf-8") as f:
        f.write(html_content)

    print_colored("index.html created", "green")
