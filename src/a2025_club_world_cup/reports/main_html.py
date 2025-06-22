# python -m src.a2025_club_world_cup.reports.main_html
import os
from glob import glob

import markdown

from src.services.printing import print_colored


def save_html_report(filepath: str, body_html: str):
    html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 12px;
            max-width: 1200px;
            margin: 2rem auto;
            padding: 2rem;
            background-color: #f8f9fa;
            color: #212529;
        }}

        h1, h2, h3 {{
            color: #343a40;
        }}

        .table-container {{
            width: 100%;
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 2rem 0;
            table-layout: fixed;
            word-wrap: break-word;
            font-size: 12px;
        }}

        th, td {{
            padding: 8px 10px;
            border: 1px solid #dee2e6;
            text-align: center;
        }}

        th {{
            background-color: #343a40;
            color: white;
            position: sticky;
            top: 0;
            z-index: 2;
            font-size: 12px;
        }}

        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}

        tr:hover {{
            background-color: #e9ecef;
        }}

        a {{
            color: #0d6efd;
            text-decoration: none;
            font-size: 12px;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        .note {{
            font-style: italic;
            font-size: 12px;
            color: #6c757d;
        }}

        hr {{
            margin: 3rem 0;
            border: none;
            border-top: 1px solid #ced4da;
        }}

        @media (max-width: 768px) {{
            body {{
                font-size: 12px;
            }}
            th, td {{
                font-size: 12px;
                padding: 6px 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="table-container">
        {body_html}
    </div>
</body>
</html>
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_template)


def main():
    paths_mds = os.path.join("src", "a2025_club_world_cup", "docs", "md")
    list_mds = glob(os.path.join(paths_mds, "**", "*.md"), recursive=True)

    list_html_folder_paths = [
        os.path.join("src", "a2025_club_world_cup", "docs", "html"),
        os.path.join("src", "a2025_club_world_cup", "docs", "html", "boleiros"),
        os.path.join("src", "a2025_club_world_cup", "docs", "html", "jogos", "1afase"),
        os.path.join("src", "a2025_club_world_cup", "docs", "html", "jogos", "oitavas"),
        os.path.join("src", "a2025_club_world_cup", "docs", "html", "jogos", "quartas"),
        os.path.join("src", "a2025_club_world_cup", "docs", "html", "jogos", "semi"),
        os.path.join("src", "a2025_club_world_cup", "docs", "html", "jogos", "final"),
    ]
    for path in list_html_folder_paths:
        os.makedirs(path, exist_ok=True)

    for file_path in list_mds:
        print_colored(f"transforming md to html '{file_path}'", "blue")
        with open(file_path, encoding="utf-8") as f:
            md_content = f.read()

        html_content = markdown.markdown(md_content, extensions=["tables"])
        html_path = (
            file_path.replace(".md", ".html")
            .replace("\\md\\", "\\html\\")
            .replace("/md/", "/html/")
        )

        save_html_report(filepath=html_path, body_html=html_content)


if __name__ == "__main__":
    main()
