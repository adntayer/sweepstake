# python -m src.a2025_club_world_cup.processing.main


from src.a2025_club_world_cup.processing.bronze_to_silver import (
    main as bronze_to_silver,
)
from src.a2025_club_world_cup.processing.raw_to_bronze import main as raw_to_bronze
from src.a2025_club_world_cup.processing.silver_to_gold import main as silver_to_gold


def main():
    raw_to_bronze()
    bronze_to_silver()
    silver_to_gold()


if __name__ == "__main__":
    main()
