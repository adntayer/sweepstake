"""Generate the index.html dashboard."""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from glob import glob

import pandas as pd
import pytz

from src.core.config import ChampionshipConfig
from src.services.printing import print_colored


def _norm(path: str) -> str:
    """Normalize a path to the current OS format."""
    return os.path.normpath(path)


def _generate_links(base_dir: str, config: ChampionshipConfig) -> list[str]:
    """Generate HTML link items for a directory of report files."""
    links = []
    files = sorted(glob(_norm(base_dir), recursive=True))
    for idx, file in enumerate(files, 1):
        if file.endswith("index.html"):
            continue
        href = file.replace("\\", "/").replace(
            f"{config.reports_dir.replace(chr(92), '/')}/html/", ""
        )
        label = (
            file.replace("\\", "/")
            .split("/")[-1]
            .replace(".html", "")
            .replace("_", " ")
            .replace("-vs-", " vs ")
            .replace("h ", "h | ")
        )
        links.append(f'<li>{idx:2} -->> <a href="{href}">{label}</a></li><br>')
    return sorted(links)


def _get_upcoming_games(
    all_links: list[str], config: ChampionshipConfig
) -> list[str]:
    """Filter links to only upcoming games (after now - 3h buffer)."""
    tz = pytz.timezone(config.timezone)
    now = datetime.now(tz) - timedelta(minutes=60 * 3)

    upcoming = []
    for item in sorted(all_links):
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})_(\d{2})h", item)
        if match:
            year, month, day, hour = map(int, match.groups())
            game_dt = tz.localize(datetime(year, month, day, hour))
            if game_dt > now:
                upcoming.append(item)
    return sorted(upcoming)


def generate_dashboard(config: ChampionshipConfig) -> None:
    """Create the index.html dashboard."""
    print_colored("creating index", "sand")

    html_base = _norm(os.path.join(config.reports_dir, "html"))

    # Last game with result
    df_results = pd.read_csv(config.results_file, sep=",")
    df_results.dropna(subset=["home_goals"], inplace=True)
    last_row = df_results.tail(1).values[0]
    (
        last_date,
        last_home,
        _,
        last_home_goals,
        _,
        last_away_goals,
        _,
        last_away,
        _,
    ) = last_row
    last_home_goals = int(last_home_goals)
    last_away_goals = int(last_away_goals)

    # Generate links per section
    links_boleiros = _generate_links(
        _norm(os.path.join(html_base, "boleiros", "*.html")), config
    )
    links_group = _generate_links(
        _norm(os.path.join(html_base, "jogos", config.group_phase_label, "*.html")),
        config,
    )

    # Playoff round links (empty if no rounds defined)
    links_playoff = {}
    for pr in config.playoff_rounds:
        links_playoff[pr.key] = _generate_links(
            _norm(os.path.join(html_base, "jogos", pr.key, "*.html")), config
        )

    tz = pytz.timezone(config.timezone)
    now_str = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")

    # All game links for upcoming calculation
    all_game_links = links_group
    for pr in config.playoff_rounds:
        all_game_links += links_playoff.get(pr.key, [])

    upcoming = _get_upcoming_games(all_game_links, config)[:4]

    # Build playoff section HTML
    playoff_sections = ""
    for pr in config.playoff_rounds:
        playoff_sections += f"""
        <div class="column">
            <h4>{pr.name}</h4>
            <ul>{"".join(links_playoff.get(pr.key, []))}</ul>
        </div>
"""

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{config.report_title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
        }}
        h2, h4 {{
            color: #34495e;
        }}
        a {{
            color: #2980b9;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        ul {{
            list-style-type: none;
            padding-left: 0;
        }}
        li {{
            padding: 4px 0;
        }}
        .section {{
            background: #fff;
            padding: 20px;
            border-radius: 6px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .flex-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 30px;
            justify-content: flex-start;
        }}
        .column {{
            flex: 1;
            min-width: 220px;
            max-width: 280px;
        }}
    </style>
</head>
<body>
    <div class="section">
        <p><i>atualizado as {now_str}</i></p>
        <h1>{config.report_title}</h1>
        <h2>Overview</h2>
        <p><a href="overview.html">Veja um overview do bolao</a></p>
        <br>
        <h3> Ultimo jogo com resultado </h3>
        <h4>{last_date} || {last_home} <b>{last_home_goals}</b> x <b>{last_away_goals}</b> {last_away}  </h4>
    </div>

    <div class="section">
        <p></p>
        <h2>Proximos jogos</h2>
        <ul>{"".join(upcoming)}</ul>
    </div>

    <div class="section flex-container">
        <div class="column">
            <h4>Boleiros</h4>
            <ul>{"".join(links_boleiros)}</ul>
        </div>

        <div class="column">
            <h4>{config.group_phase_label}</h4>
            <ul>{"".join(links_group)}</ul>
        </div>
{playoff_sections}
    </div>
</body>
</html>"""

    os.makedirs(_norm(html_base), exist_ok=True)
    with open(_norm(config.index_html_path()), "w", encoding="utf-8") as f:
        f.write(html_content)

    print_colored("index created", "green")
