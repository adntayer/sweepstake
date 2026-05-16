"""Tests for src.core.loader (pure functions only)."""

from __future__ import annotations

import pandas as pd

from src.core.config import (
    ChampionshipConfig,
    ExcelLayout,
    FirstRoundLayout,
    PlayoffsLayout,
)
from src.core.loader import (
    _clean_dataframe,
    _extract_who,
    _make_match_key,
    _normalize_types,
)


def _make_cfg() -> ChampionshipConfig:
    return ChampionshipConfig(
        id="test", name="Test", year=2025,
        excel_layout=ExcelLayout(
            first_round=FirstRoundLayout(matches=48),
            playoffs=PlayoffsLayout(
                name_split_char="-",
                name_split_index=1,
            ),
        ),
    )


# ------------------------------------------------------------------
# _extract_who
# ------------------------------------------------------------------

class TestExtractWho:
    def test_standard_filename(self):
        cfg = _make_cfg()
        result = _extract_who("data/raw/Tabela Geral 2025 - John Doe.xls", cfg)
        assert result == "John Doe"

    def test_xlsx_extension(self):
        cfg = _make_cfg()
        result = _extract_who("data/raw/Tabela Geral 2025 - Jane.xlsx", cfg)
        assert result == "Jane"

    def test_strips_whitespace(self):
        cfg = _make_cfg()
        result = _extract_who("data/raw/Tabela Geral 2025 -  Bob  .xls", cfg)
        assert result == "Bob"

    def test_custom_split_char(self):
        cfg = ChampionshipConfig(
            id="test", name="Test", year=2025,
            excel_layout=ExcelLayout(
                first_round=FirstRoundLayout(matches=48),
                playoffs=PlayoffsLayout(
                    name_split_char="_",
                    name_split_index=1,
                ),
            ),
        )
        result = _extract_who("data/raw/prediction_Alice.xls", cfg)
        assert result == "Alice"


# ------------------------------------------------------------------
# _clean_dataframe
# ------------------------------------------------------------------

class TestCleanDataframe:
    def test_adds_who_column(self):
        df = pd.DataFrame({"date": ["2025-01-01"], "home_team": ["A"]})
        result = _clean_dataframe(df, "Bob")
        assert "who" in result.columns
        assert result["who"].iloc[0] == "Bob"

    def test_drops_all_nan_rows(self):
        df = pd.DataFrame({
            "date": ["2025-01-01", None, "2025-01-02"],
            "home_team": ["A", None, "B"],
        })
        result = _clean_dataframe(df, "Bob")
        assert len(result) == 2

    def test_drops_grupo_rows(self):
        df = pd.DataFrame({
            "date": ["2025-01-01", "GRUPO A", "2025-01-02"],
            "home_team": ["A", "X", "B"],
        })
        result = _clean_dataframe(df, "Bob")
        assert "GRUPO" not in result["date"].values

    def test_does_not_mutate_original(self):
        df = pd.DataFrame({"date": ["2025-01-01"], "home_team": ["A"]})
        original_len = len(df)
        _clean_dataframe(df, "Bob")
        assert "who" not in df.columns


# ------------------------------------------------------------------
# _normalize_types
# ------------------------------------------------------------------

class TestNormalizeTypes:
    def test_casts_goals_to_float(self):
        df = pd.DataFrame({
            "home_goals": [2.0, 1.0],
            "away_goals": [1.0, 0.0],
            "home_pen": [0.0, 0.0],
            "away_pen": [0.0, 0.0],
            "date": ["2025-01-01", "2025-01-02"],
        })
        result = _normalize_types(df)
        assert result["home_goals"].dtype == float
        assert result["away_goals"].dtype == float

    def test_formats_date(self):
        df = pd.DataFrame({
            "date": ["2025-01-01", "2025-02-15"],
            "home_goals": [1, 2],
            "away_goals": [0, 1],
            "home_pen": [0, 0],
            "away_pen": [0, 0],
        })
        result = _normalize_types(df)
        assert result["date"].iloc[0] == "2025-01-01"

    def test_does_not_mutate_original(self):
        df = pd.DataFrame({
            "date": ["2025-01-01"],
            "home_goals": [1],
            "away_goals": [0],
            "home_pen": [0],
            "away_pen": [0],
        })
        _normalize_types(df)
        assert df["home_goals"].dtype != float


# ------------------------------------------------------------------
# _make_match_key
# ------------------------------------------------------------------

class TestMakeMatchKey:
    def test_basic(self):
        df = pd.DataFrame({
            "home_team": ["Flamengo"],
            "away_team": ["Palmeiras"],
        })
        result = _make_match_key(df)
        assert result["match"].iloc[0] == "flamengo-vs-palmeiras"

    def test_strips_and_lowercase(self):
        df = pd.DataFrame({
            "home_team": [" Real Madrid "],
            "away_team": ["Barcelona"],
        })
        result = _make_match_key(df)
        assert result["match"].iloc[0] == "real_madrid-vs-barcelona"

    def test_replaces_spaces(self):
        df = pd.DataFrame({
            "home_team": ["Bayern Munich"],
            "away_team": ["PSG"],
        })
        result = _make_match_key(df)
        assert result["match"].iloc[0] == "bayern_munich-vs-psg"

    def test_does_not_mutate_original(self):
        df = pd.DataFrame({
            "home_team": ["A"],
            "away_team": ["B"],
        })
        _make_match_key(df)
        assert "match" not in df.columns
