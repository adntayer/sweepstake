# python -m src.a2025_club_world_cup.reports.index
import os
import re
from datetime import datetime, timedelta
from glob import glob

import pandas as pd
import pytz

from src.services.printing import print_colored


def generate_links(base_dir):
    links = []
    list_files = sorted(glob(base_dir, recursive=True))
    for e, file in enumerate(list_files, 1):
        if file != "index.html":
            href = file.replace("\\", "/").replace(
                "src/a2025_club_world_cup/docs/html/", ""
            )
            label = (
                file.replace("\\", "/")
                .split("/")[-1]
                .replace(".html", "")
                .replace("_", " ")
                .replace("-vs-", " vs ")
                .replace("h ", "h | ")
            )
            links.append(f'<li>{e:2} -->> <a href="{href}">{label}</a></li><br>')

    return sorted(links)


def get_upcomming_gamonth(links_html):
    tz_sp = pytz.timezone("America/Sao_Paulo")
    now = datetime.now(tz_sp) - timedelta(minutes=60 * 3)

    list_next_gamonth = []
    for item in sorted(links_html):
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})_(\d{2})h", item)
        if match:
            year, month, day, hour = map(int, match.groups())
            data_jogo = tz_sp.localize(datetime(year, month, day, hour))
            if data_jogo > now:
                list_next_gamonth.append(item)

    return sorted(list_next_gamonth)


def create_index_html():
    print_colored("creting index", "sand")
    base_path = os.path.join("src", "a2025_club_world_cup", "docs", "html")

    df_gamonth_official = pd.read_csv(
        os.path.join("src", "a2025_club_world_cup", "data", "jogos_1afase.csv"), sep=","
    )
    df_gamonth_official.dropna(subset=["home_goals"], inplace=True)
    df_gamonth_official_last_one = df_gamonth_official.tail(1)
    (
        last_game_data,
        last_game_home,
        _,
        last_game_home_goals,
        _,
        last_game_away_goals,
        _,
        last_game_away,
        _,
    ) = df_gamonth_official_last_one.values[0]
    last_game_home_goals = int(last_game_home_goals)
    last_game_away_goals = int(last_game_away_goals)

    links_boleiros = generate_links(os.path.join(base_path, "boleiros", "*.html"))
    links_1afase = generate_links(os.path.join(base_path, "jogos", "1afase", "*.html"))
    links_oitavas = []  # generate_links(os.path.join(base_path, "jogos", "oitavas", "*.html"))
    links_quartas = []  # generate_links(os.path.join(base_path, "jogos", "quartas", "*.html"))
    links_semi = []  # generate_links(os.path.join(base_path, "jogos", "semi", "*.html"))
    links_final = []  # generate_links(os.path.join(base_path, "jogos", "final", "*.html"))
    tz_sp = pytz.timezone("America/Sao_Paulo")
    now_sp = datetime.now(tz_sp).strftime("%d/%m/%Y %H:%M:%S")
    list_all_links = (
        links_1afase + links_oitavas + links_quartas + links_semi + links_final
    )
    list_upcomming_gamonth = get_upcomming_gamonth(list_all_links)
    list_upcomming_gamonth = list_upcomming_gamonth[:4]

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>2025 Club World Cup</title>
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
        <p><i>atualizado às {now_sp}</i></p>
        <h1>🏆 2025 Club World Cup</h1>
        <h2>📊 Overview</h2>
        <p><a href="overview.html">Veja um overview do bolão</a></p>
        <br>
        <h3> Último jogo com resultado </h3>
        <h4>{last_game_data} || {last_game_home} <b>{last_game_home_goals}</b> x <b>{last_game_away_goals}</b> {last_game_away}  </h4>
    </div>

    <div class="section">
        <p></p>
        <h2>🕒 Próximos jogos</h2>
        <ul>{"".join(list_upcomming_gamonth)}</ul>
    </div>

    <div class="section flex-container">
        <div class="column">
            <h4>👥 Boleiros</h4>
            <ul>{"".join(links_boleiros)}</ul>
        </div>

        <div class="column">
            <h4>⚽ 1ª Fase</h4>
            <ul>{"".join(links_1afase)}</ul>
        </div>

        <div class="column">
            <h4>🏁 Oitavas</h4>
            <ul>{"".join(links_oitavas)}</ul>
        </div>

        <div class="column">
            <h4>🔥 Quartas</h4>
            <ul>{"".join(links_quartas)}</ul>
        </div>

        <div class="column">
            <h4>🎯 Semifinais</h4>
            <ul>{"".join(links_semi)}</ul>
        </div>

        <div class="column">
            <h4>🏆 Final</h4>
            <ul>{"".join(links_final)}</ul>
        </div>
    </div>
</body>
</html>"""

    with open(
        os.path.join("src", "a2025_club_world_cup", "docs", "html", "index.html"),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(html_content)

    print_colored("index created", "green")


if __name__ == "__main__":
    create_index_html()
