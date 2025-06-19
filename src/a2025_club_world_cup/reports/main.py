# python -m src.a2025_club_world_cup.reports.main
import os
import webbrowser

from src.a2025_club_world_cup.reports.index import create_index_html
from src.a2025_club_world_cup.reports.main_html import main as main_html
from src.a2025_club_world_cup.reports.main_md import main as main_md


def main():
    main_md()
    main_html()
    create_index_html()

    file_path = os.path.abspath(
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "docs",
            "html",
            "index.html",
        )
    )
    webbrowser.open(f"file://{file_path}")


if __name__ == "__main__":
    main()
