# python -m src.a2025_club_world_cup.processing.silver_to_gold
import os
import shutil

import pandas as pd

from src.services.printing import print_colored


def main():
    print_colored("silver to gold", "sand")
    core_path = os.path.join("src", "a2025_club_world_cup", "data", "gold")
    if os.path.exists(core_path):
        shutil.rmtree(core_path)
        print_colored(
            f"Folder '{core_path}' and its contents deleted successfully.", "green"
        )
    else:
        print_colored(f"Folder '{core_path}' does not exist.", "gray")

    list_folder_paths = [
        core_path,
        os.path.join("src", "a2025_club_world_cup", "data", "gold", "1afase"),
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "gold",
            "playoffs",
            "full",
        ),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "gold", "playoffs", "oitavas"
        ),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "gold", "playoffs", "quartas"
        ),
        os.path.join("src", "a2025_club_world_cup", "data", "gold", "playoffs", "semi"),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "gold", "playoffs", "final"
        ),
    ]
    for path in list_folder_paths:
        os.makedirs(path, exist_ok=True)

    df_all = pd.read_csv(
        os.path.join(
            "src", "a2025_club_world_cup", "data", "silver", "1afase", "all_games.csv"
        ),
        sep=",",
    )
    output_path_all = os.path.join(
        "src",
        "a2025_club_world_cup",
        "data",
        "gold",
        "1afase",
        "1afase_all.csv",
    )
    output_path_valido = os.path.join(
        "src",
        "a2025_club_world_cup",
        "data",
        "gold",
        "1afase",
        "1afase_valido_all.csv",
    )

    df_criterios_onehot = pd.get_dummies(df_all["criterio"])
    df_all = pd.concat([df_all, df_criterios_onehot], axis=1)

    df_all.sort_values(by=["date", "hour", "who"]).to_csv(output_path_all, sep=",", decimal=".", index=False)

    df_all.query("valido==1").sort_values(by=["date", "hour", "who"]).to_csv(
        output_path_valido, sep=",", decimal=".", index=False
    )

    df_playoffs = pd.read_csv(
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "silver",
            "playoffs",
            "full",
            "playoffs_full_games.csv",
        ),
        sep=",",
    )
    df_playoffs.to_csv(
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "gold",
            "playoffs",
            "full",
            "playoffs_full_games.csv",
        ),
        sep=",",
        index=False,
    )

    df_strikers = pd.read_csv(
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "silver",
            "playoffs",
            "full",
            "playoffs_strikers.csv",
        ),
        sep=",",
    )
    df_strikers.to_csv(
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "gold",
            "playoffs",
            "full",
            "playoffs_strikers.csv",
        ),
        sep=",",
        index=False,
    )
    print_colored("silver to gold completed", "green")


if __name__ == "__main__":
    main()
