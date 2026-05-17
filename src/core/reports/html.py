"""Convert Markdown reports to styled HTML."""

from __future__ import annotations

import os
from glob import glob

import markdown

from src.core.config import ChampionshipConfig
from src.core.printing import print_colored


def _norm(path: str) -> str:
    """Normalize a path to the current OS format."""
    return os.path.normpath(path)


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
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


def _save_html(filepath: str, body_html: str, title: str) -> None:
    """Write an HTML file with the standard template."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(_HTML_TEMPLATE.format(title=title, body_html=body_html))


def generate_html_reports(config: ChampionshipConfig) -> None:
    """Convert all Markdown reports to HTML."""
    md_base = _norm(os.path.join(config.reports_dir, "md"))
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

    # Find all MD files
    md_paths = glob(_norm(os.path.join(md_base, "**", "*.md")), recursive=True)

    for file_path in sorted(md_paths):
        print_colored(f"transforming md to html '{file_path}'", "blue")
        with open(file_path, encoding="utf-8") as f:
            md_content = f.read()

        html_content = markdown.markdown(md_content, extensions=["tables"])

        # Replace md path with html path
        html_path = _norm(
            file_path.replace(".md", ".html")
            .replace(f"{os.sep}md{os.sep}", f"{os.sep}html{os.sep}")
            .replace("/md/", "/html/")
            .replace("\\md\\", "\\html\\")
        )

        _save_html(
            filepath=html_path,
            body_html=html_content,
            title=config.report_title,
        )
