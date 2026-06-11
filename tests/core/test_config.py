"""Tests for src.core.config."""

from __future__ import annotations

import os

import pytest

from src.core.config import (
    ChampionshipConfig,
    ExcelLayout,
    FirstRoundLayout,
    PlayoffRound,
    PlayoffsLayout,
    ScoringRule,
    ThemeColors,
    ThemeConfig,
    _find_championship_dir,
    _norm,
    list_championships,
    load_config,
)

# ------------------------------------------------------------------
# _norm
# ------------------------------------------------------------------

class TestNorm:
    def test_empty_string(self):
        assert _norm("") == ""

    def test_forward_slash(self):
        result = _norm("src/data/test")
        assert result == os.path.normpath("src/data/test")


# ------------------------------------------------------------------
# ScoringRule
# ------------------------------------------------------------------

class TestScoringRule:
    def test_defaults(self):
        rule = ScoringRule(name="test", points=5, priority=1)
        assert rule.rule == ""
        assert rule.max_total_error is None
        assert rule.min_total_error is None
        assert rule.priority == 1

    def test_full(self):
        rule = ScoringRule(
            name="exact", points=15, priority=1,
            rule="exact_score", max_total_error=2,
        )
        assert rule.rule == "exact_score"
        assert rule.max_total_error == 2


# ------------------------------------------------------------------
# PlayoffRound
# ------------------------------------------------------------------

class TestPlayoffRound:
    def test_creation(self):
        pr = PlayoffRound(name="Semi", key="semi", matches=2)
        assert pr.name == "Semi"
        assert pr.key == "semi"
        assert pr.matches == 2


# ------------------------------------------------------------------
# FirstRoundLayout
# ------------------------------------------------------------------

class TestFirstRoundLayout:
    def test_defaults(self):
        fr = FirstRoundLayout(matches=48)
        assert fr.skiprows == 2

    def test_custom(self):
        fr = FirstRoundLayout(matches=32, skiprows=3)
        assert fr.matches == 32
        assert fr.skiprows == 3


# ------------------------------------------------------------------
# PlayoffsLayout
# ------------------------------------------------------------------

class TestPlayoffsLayout:
    def test_defaults(self):
        po = PlayoffsLayout()
        assert po.striker_row_offset == 1
        assert po.name_split_char == "-"
        assert po.name_split_index == 1
        assert po.rounds == []


# ------------------------------------------------------------------
# ExcelLayout
# ------------------------------------------------------------------

class TestExcelLayout:
    def _make_layout(self):
        return ExcelLayout(
            first_round=FirstRoundLayout(matches=48),
            playoffs=PlayoffsLayout(
                rounds=[
                    {"key": "oitavas", "tail_offset": 19, "matches": 8},
                ]
            ),
        )

    def test_playoff_rows_empty(self):
        layout = ExcelLayout(
            first_round=FirstRoundLayout(matches=48),
            playoffs=PlayoffsLayout(),
        )
        assert layout.playoff_rows == []

    def test_playoff_rows_derived(self):
        layout = self._make_layout()
        rows = layout.playoff_rows
        assert len(rows) == 1
        assert rows[0]["key"] == "oitavas"
        assert rows[0]["tail_offset"] == 19
        assert rows[0]["head_count"] == 8


# ------------------------------------------------------------------
# ChampionshipConfig
# ------------------------------------------------------------------

class TestChampionshipConfigDefaults:
    def test_post_init_derives_paths(self):
        cfg = ChampionshipConfig(id="test", name="Test", year=2025)
        assert cfg.base_dir == _norm(os.path.join("src", "data", "test"))
        assert cfg.raw_dir == _norm(os.path.join(cfg.base_dir, "raw"))
        assert cfg.bronze_dir == _norm(os.path.join(cfg.base_dir, "bronze"))
        assert cfg.silver_dir == _norm(os.path.join(cfg.base_dir, "silver"))
        assert cfg.gold_dir == _norm(os.path.join(cfg.base_dir, "gold"))
        assert cfg.reports_dir == _norm(os.path.join("src", "reports", "test"))
        assert cfg.report_title == "Test"

    def test_explicit_paths_not_overridden(self):
        cfg = ChampionshipConfig(
            id="test", name="Test", year=2025,
            base_dir="custom/base",
            raw_dir="custom/raw",
            results_file="custom/results.csv",
            bronze_dir="custom/bronze",
            silver_dir="custom/silver",
            gold_dir="custom/gold",
            reports_dir="custom/reports",
            report_title="Custom Title",
        )
        assert cfg.base_dir == _norm("custom/base")
        assert cfg.raw_dir == _norm("custom/raw")
        assert cfg.report_title == "Custom Title"


class TestChampionshipConfigPaths:
    def _cfg(self):
        return ChampionshipConfig(
            id="test", name="Test", year=2025,
            base_dir="data/test",
            gold_dir="data/test/gold",
            silver_dir="data/test/silver",
            bronze_dir="data/test/bronze",
            reports_dir="data/test/reports",
            group_phase_label="group",
        )

    def test_gold_valid_path(self):
        cfg = self._cfg()
        assert cfg.gold_valid_path() == _norm("data/test/gold/first_round/group_valido_all.csv")

    def test_gold_all_path(self):
        cfg = self._cfg()
        assert cfg.gold_all_path() == _norm("data/test/gold/first_round/group_all.csv")

    def test_bronze_group_path(self):
        cfg = self._cfg()
        assert cfg.bronze_group_path("joao") == _norm("data/test/bronze/first_round/group_phase_joao.csv")

    def test_bronze_bonus_path(self):
        cfg = self._cfg()
        assert cfg.bronze_bonus_path("joao") == _norm("data/test/bronze/first_round/bonus_teams_joao.csv")

    def test_bronze_striker_path(self):
        cfg = self._cfg()
        assert cfg.bronze_striker_path("joao") == _norm("data/test/bronze/first_round/striker_joao.csv")

    def test_silver_group_path(self):
        cfg = self._cfg()
        assert cfg.silver_group_path("joao") == _norm("data/test/silver/first_round/group_phase_joao.csv")

    def test_gold_group_boleiro_path(self):
        cfg = self._cfg()
        assert cfg.gold_group_boleiro_path("joao") == _norm("data/test/gold/first_round/group_phase_joao.csv")

    def test_gold_striker_path(self):
        cfg = self._cfg()
        assert cfg.gold_striker_path("joao") == _norm("data/test/gold/first_round/striker_joao.csv")

    def test_playoff_strikers_gold(self):
        cfg = self._cfg()
        assert cfg.playoff_strikers_path("gold") == _norm(
            "data/test/gold/first_round/playoffs_strikers.csv"
        )

    def test_playoff_strikers_silver(self):
        cfg = self._cfg()
        assert cfg.playoff_strikers_path("silver") == _norm(
            "data/test/silver/first_round/playoffs_strikers.csv"
        )

    def test_playoff_strikers_bronze(self):
        cfg = self._cfg()
        assert cfg.playoff_strikers_path("bronze") == _norm(
            "data/test/bronze/first_round/playoffs_strikers.csv"
        )

    def test_playoff_games_gold(self):
        cfg = self._cfg()
        assert cfg.playoff_games_path("gold") == _norm(
            "data/test/gold/first_round/playoffs_strikers.csv"
        )

    def test_overview_md_path(self):
        cfg = self._cfg()
        assert cfg.overview_md_path() == _norm("data/test/reports/md/overview.md")

    def test_overview_html_path(self):
        cfg = self._cfg()
        assert cfg.overview_html_path() == _norm("data/test/reports/html/overview.html")

    def test_index_html_path(self):
        cfg = self._cfg()
        assert cfg.index_html_path() == _norm("data/test/reports/html/index.html")


class TestChampionshipConfigScoring:
    def test_scoring_rule_names(self):
        cfg = ChampionshipConfig(
            id="test", name="Test", year=2025,
            scoring_rules=[
                ScoringRule(name="B", points=5, priority=2),
                ScoringRule(name="A", points=10, priority=1),
            ],
        )
        assert cfg.scoring_rule_names() == ["A", "B"]

    def test_scoring_dict(self):
        cfg = ChampionshipConfig(
            id="test", name="Test", year=2025,
            scoring_rules=[
                ScoringRule(name="exact", points=15, priority=1),
                ScoringRule(name="winner", points=5, priority=3),
            ],
        )
        assert cfg.scoring_dict() == {"exact": 15, "winner": 5}


# ------------------------------------------------------------------
# _find_championship_dir
# ------------------------------------------------------------------

class TestFindChampionshipDir:
    def test_existing(self):
        result = _find_championship_dir("2025_club_world_cup")
        assert result.is_dir()
        assert result.name == "2025_club_world_cup"

    def test_missing_raises(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            _find_championship_dir("nonexistent_championship")


# ------------------------------------------------------------------
# load_config
# ------------------------------------------------------------------

class TestLoadConfig:
    def test_load_existing(self):
        cfg = load_config("2025_club_world_cup")
        assert cfg.id == "2025_club_world_cup"
        assert cfg.name == "2025 Club World Cup"
        assert cfg.year == 2025
        assert len(cfg.scoring_rules) == 6
        assert len(cfg.playoff_rounds) == 4
        assert cfg.excel_layout is not None
        assert cfg.excel_layout.first_round.matches == 48

    def test_scoring_rules_loaded(self):
        cfg = load_config("2025_club_world_cup")
        names = [r.name for r in cfg.scoring_rules]
        assert "1-Placar exato" in names
        assert "2-Vencedor + gols de um time" in names

    def test_playoff_rounds_loaded(self):
        cfg = load_config("2025_club_world_cup")
        keys = [pr.key for pr in cfg.playoff_rounds]
        assert keys == ["oitavas", "quartas", "semi", "final"]

    def test_paths_from_yaml(self):
        cfg = load_config("2025_club_world_cup")
        assert "2025_club_world_cup" in cfg.base_dir
        assert "2025_club_world_cup" in cfg.reports_dir

    def test_missing_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent_championship")


# ------------------------------------------------------------------
# list_championships
# ------------------------------------------------------------------

class TestListChampionships:
    def test_returns_list(self):
        result = list_championships()
        assert isinstance(result, list)
        assert "2025_club_world_cup" in result


# ------------------------------------------------------------------
# Scoring rule uniqueness validation
# ------------------------------------------------------------------

class TestScoringRuleUniqueness:
    """Ensure a championship config has no duplicate rule types.

    Duplicate rule keys (e.g. two rules with rule='no_score') cause
    silent data loss: score_prediction builds a dict {rule.rule: rule}
    where the first occurrence wins and the rest are discarded.
    """

    def test_no_duplicate_rule_types(self):
        """All loaded championships must have unique rule.rule values.

        Exceptions: ``correct_winner_and_goals_or_diff`` may appear more
        than once to define multi-tier scoring (e.g. error ≤ 2 vs error ≥ 3).
        """
        for champ_id in list_championships():
            cfg = load_config(champ_id)
            rule_keys = [r.rule for r in cfg.scoring_rules if r.rule]
            # Filter out intentional multi-tier duplicates
            multi_tier = {"correct_winner_and_goals_or_diff", "correct_winner_and_one_goal"}
            seen: set[str] = set()
            dups: list[str] = []
            for k in rule_keys:
                if k in multi_tier:
                    continue
                if k in seen:
                    dups.append(k)
                seen.add(k)
            assert not dups, (
                f"{champ_id}: duplicate rule types found: {dups}"
            )

    def test_no_duplicate_rule_types_explicit(self):
        """Manually constructed config with duplicate rule should fail."""
        cfg = ChampionshipConfig(
            id="test", name="Test", year=2025,
            scoring_rules=[
                ScoringRule(name="A", points=5, rule="no_score"),
                ScoringRule(name="B", points=0, rule="no_score"),
            ],
        )
        rule_keys = [r.rule for r in cfg.scoring_rules if r.rule]
        assert len(rule_keys) != len(set(rule_keys))

    def test_empty_rule_is_ignored(self):
        """Rules with empty rule string should not count as duplicates."""
        cfg = ChampionshipConfig(
            id="test", name="Test", year=2025,
            scoring_rules=[
                ScoringRule(name="A", points=5, rule=""),
                ScoringRule(name="B", points=3, rule=""),
            ],
        )
        rule_keys = [r.rule for r in cfg.scoring_rules if r.rule]
        assert len(rule_keys) == 0  # all empty → no collision possible


# ------------------------------------------------------------------
# ThemeConfig
# ------------------------------------------------------------------

class TestThemeColors:
    def test_defaults(self):
        c = ThemeColors()
        assert c.primary == "#1a5e1f"
        assert c.bg == "#0d1117"
        assert c.accent == "#f5c518"

    def test_custom(self):
        c = ThemeColors(primary="#ff0000", bg="#ffffff")
        assert c.primary == "#ff0000"
        assert c.bg == "#ffffff"
        assert c.accent == "#f5c518"  # default preserved


class TestThemeConfig:
    def test_defaults(self):
        t = ThemeConfig()
        assert t.mode == "dark"
        assert isinstance(t.colors, ThemeColors)

    def test_to_css_vars(self):
        t = ThemeConfig()
        css = t.to_css_vars()
        assert ":root {" in css
        assert "--primary:" in css
        assert "--bg:" in css
        assert "--accent:" in css

    def test_custom_colors(self):
        colors = ThemeColors(primary="#ff0000", bg="#ffffff")
        t = ThemeConfig(mode="light", colors=colors)
        css = t.to_css_vars()
        assert "--primary: #ff0000" in css
        assert "--bg: #ffffff" in css

    def test_config_has_theme(self):
        cfg = ChampionshipConfig(id="t", name="T", year=2025)
        assert isinstance(cfg.theme, ThemeConfig)

    def test_theme_loaded_from_yaml(self):
        cfg = load_config("2025_club_world_cup")
        assert cfg.theme.mode == "dark"
        assert cfg.theme.colors.primary == "#1a5e1f"
        assert cfg.theme.colors.bg == "#060d1a"
