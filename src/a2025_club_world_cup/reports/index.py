# python -m src.a2025_club_world_cup.reports.index
import os
import re
from datetime import datetime, timedelta

import pytz

from src.services.printing import print_colored


def generate_links(base_dir):
    links = []
    for root, _, files in os.walk(base_dir):
        for e, file in enumerate(files, 1):
            if file.endswith(".html") and file != "index.html":
                path = os.path.join(root, file).replace("\\", "/")
                href = path.replace("src/a2025_club_world_cup/docs/html/", "")
                label = path.split("/")[-1].replace(".html", "")
                links.append(f'<li>{e:2} -->> <a href="{href}">{label}</a></li><br>')
    return links


def get_upcomming_games(links_html):
    tz_sp = pytz.timezone("America/Sao_Paulo")
    agora = datetime.now(tz_sp) - timedelta(minutes=60 * 3)

    jogos_futuros = []
    for item in links_html:
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})_(\d{2})h", item)
        if match:
            ano, mes, dia, hora = map(int, match.groups())
            data_jogo = tz_sp.localize(datetime(ano, mes, dia, hora))
            if data_jogo > agora:
                jogos_futuros.append(item)

    return jogos_futuros


def create_index_html():
    print_colored("creting index", "sand")
    base_path = os.path.join("src", "a2025_club_world_cup", "docs", "html")

    links_boleiros = generate_links(os.path.join(base_path, "boleiros"))
    links_1afase = generate_links(os.path.join(base_path, "jogos", "1afase"))
    links_oitavas = []  # generate_links(os.path.join(base_path, "jogos", "oitavas"))
    links_quartas = []  # generate_links(os.path.join(base_path, "jogos", "quartas"))
    links_semi = []  # generate_links(os.path.join(base_path, "jogos", "semi"))
    links_final = []  # generate_links(os.path.join(base_path, "jogos", "final"))
    tz_sp = pytz.timezone("America/Sao_Paulo")
    now_sp = datetime.now(tz_sp).strftime("%d/%m/%Y %H:%M:%S")
    list_all_links = (
        links_1afase + links_oitavas + links_quartas + links_semi + links_final
    )
    list_upcomming_games = get_upcomming_games(list_all_links)
    list_upcomming_games = list_upcomming_games[:4]

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
    </div>

    <div class="section">
        <p></p>
        <h2>🕒 Próximos jogos</h2>
        <ul>{"".join(list_upcomming_games)}</ul>
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
