"""Tests for src.core.reports helpers."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta

import pytz

from src.core.config import ChampionshipConfig, PlayoffRound, ThemeConfig
from src.core.reports.dashboard import _get_upcoming_games, _parse_game_file
from src.core.reports.html import _save


def _make_cfg(reports_dir: str = "reports/test") -> ChampionshipConfig:
    return ChampionshipConfig(
        id="test", name="Test", year=2025,
        reports_dir=reports_dir,
        report_title="Test Report",
        group_phase_label="group",
        playoff_rounds=[
            PlayoffRound(name="Semi", key="semi", matches=2),
        ],
        theme=ThemeConfig(),
    )


# ------------------------------------------------------------------
# dashboard._parse_game_file
# ------------------------------------------------------------------

class TestParseGameFile:
    def test_parses_valid_filename(self):
        cfg = _make_cfg()
        filepath = "reports/test/html/jogos/group/2025-06-14_21h_team_a-vs-team_b.html"
        result = _parse_game_file(filepath, cfg)
        assert result is not None
        assert result["date_str"] == "14/06 21h"
        assert "href" in result

    def test_returns_none_for_invalid_filename(self):
        cfg = _make_cfg()
        filepath = "reports/test/html/boleiros/Alice.html"
        result = _parse_game_file(filepath, cfg)
        assert result is None


# ------------------------------------------------------------------
# dashboard._get_upcoming_games
# ------------------------------------------------------------------

class TestGetUpcomingGames:
    def test_finds_future_games(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = _make_cfg(tmpdir)
            html_base = os.path.join(tmpdir, "html")
            game_dir = os.path.join(html_base, "jogos", "group")
            os.makedirs(game_dir)

            future = datetime.now(pytz.timezone(cfg.timezone)) + timedelta(hours=5)
            fname = f"{future.strftime('%Y-%m-%d')}_{future.strftime('%H')}h_team_a-vs-team_b.html"
            with open(os.path.join(game_dir, fname), "w") as f:
                f.write("<html></html>")

            result = _get_upcoming_games(html_base, cfg)
            assert len(result) == 1

    def test_ignores_past_games(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = _make_cfg(tmpdir)
            html_base = os.path.join(tmpdir, "html")
            game_dir = os.path.join(html_base, "jogos", "group")
            os.makedirs(game_dir)

            past = datetime.now(pytz.timezone(cfg.timezone)) - timedelta(hours=5)
            fname = f"{past.strftime('%Y-%m-%d')}_{past.strftime('%H')}h_team_a-vs-team_b.html"
            with open(os.path.join(game_dir, fname), "w") as f:
                f.write("<html></html>")

            result = _get_upcoming_games(html_base, cfg)
            assert len(result) == 0

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = _make_cfg(tmpdir)
            html_base = os.path.join(tmpdir, "html")
            os.makedirs(os.path.join(html_base, "jogos", "group"))
            result = _get_upcoming_games(html_base, cfg)
            assert result == []

    def test_returns_sorted_by_date(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = _make_cfg(tmpdir)
            html_base = os.path.join(tmpdir, "html")
            game_dir = os.path.join(html_base, "jogos", "group")
            os.makedirs(game_dir)

            tz = pytz.timezone(cfg.timezone)
            f1 = datetime.now(tz) + timedelta(hours=10)
            f2 = datetime.now(tz) + timedelta(hours=5)

            for dt, name in [(f1, "b"), (f2, "a")]:
                fname = f"{dt.strftime('%Y-%m-%d')}_{dt.strftime('%H')}h_team_{name}-vs-other.html"
                with open(os.path.join(game_dir, fname), "w") as f:
                    f.write("<html></html>")

            result = _get_upcoming_games(html_base, cfg)
            assert len(result) == 2
            assert result[0]["dt"] <= result[1]["dt"]


# ------------------------------------------------------------------
# html._save
# ------------------------------------------------------------------

class TestSaveHtml:
    def test_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "report.html")
            _save(path, "<!DOCTYPE html><html><body><h1>Hello</h1></body></html>")
            assert os.path.isfile(path)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            assert "<h1>Hello</h1>" in content

    def test_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "deep", "nested", "report.html")
            _save(path, "<p>test</p>")
            assert os.path.isfile(path)

    def test_writes_utf8(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "report.html")
            _save(path, "<p>Jo\u00e3o & Caf\u00e9</p>")
            with open(path, encoding="utf-8") as f:
                content = f.read()
            assert "Jo\u00e3o" in content
            assert "Caf\u00e9" in content
