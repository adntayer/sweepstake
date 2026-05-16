"""Tests for src.core.reports helpers."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta

import pytz

from src.core.config import ChampionshipConfig, PlayoffRound
from src.core.reports.dashboard import _generate_links, _get_upcoming_games
from src.core.reports.html import _save_html


def _make_cfg(reports_dir: str = "reports/test") -> ChampionshipConfig:
    return ChampionshipConfig(
        id="test", name="Test", year=2025,
        reports_dir=reports_dir,
        report_title="Test Report",
        group_phase_label="group",
        playoff_rounds=[
            PlayoffRound(name="Semi", key="semi", matches=2),
        ],
    )


# ------------------------------------------------------------------
# dashboard._generate_links
# ------------------------------------------------------------------

class TestGenerateLinks:
    def test_generates_links(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_dir = os.path.join(tmpdir, "html", "boleiros")
            os.makedirs(html_dir)
            for name in ["Alice", "Bob"]:
                with open(os.path.join(html_dir, f"{name}.html"), "w") as f:
                    f.write("<html></html>")

            cfg = _make_cfg(tmpdir)
            pattern = os.path.join(html_dir, "*.html")
            links = _generate_links(pattern, cfg)

            assert len(links) == 2
            assert '<a href="boleiros/Alice.html">' in links[0] or '<a href="boleiros/Bob.html">' in links[0]

    def test_skips_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_dir = os.path.join(tmpdir, "html")
            os.makedirs(html_dir)
            with open(os.path.join(html_dir, "index.html"), "w") as f:
                f.write("<html></html>")
            with open(os.path.join(html_dir, "other.html"), "w") as f:
                f.write("<html></html>")

            cfg = _make_cfg(tmpdir)
            links = _generate_links(os.path.join(html_dir, "*.html"), cfg)
            assert len(links) == 1
            assert "index" not in links[0].lower() or "index.html" not in links[0]

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_dir = os.path.join(tmpdir, "html")
            os.makedirs(html_dir)
            cfg = _make_cfg(tmpdir)
            links = _generate_links(os.path.join(html_dir, "*.html"), cfg)
            assert links == []


# ------------------------------------------------------------------
# dashboard._get_upcoming_games
# ------------------------------------------------------------------

class TestGetUpcomingGames:
    def test_filters_future_games(self):
        cfg = _make_cfg()
        future = datetime.now(pytz.timezone(cfg.timezone)) + timedelta(hours=5)
        links = [
            f'jogos/group/{future.strftime("%Y-%m-%d")}_{future.strftime("%H")}h_match.html',
        ]
        result = _get_upcoming_games(links, cfg)
        assert len(result) == 1

    def test_filters_past_games(self):
        cfg = _make_cfg()
        past = datetime.now(pytz.timezone(cfg.timezone)) - timedelta(hours=5)
        links = [
            f'jogos/group/{past.strftime("%Y-%m-%d")}_{past.strftime("%H")}h_match.html',
        ]
        result = _get_upcoming_games(links, cfg)
        assert len(result) == 0

    def test_ignores_non_game_links(self):
        cfg = _make_cfg()
        links = ["boleiros/Alice.html", "overview.html"]
        result = _get_upcoming_games(links, cfg)
        assert result == []

    def test_returns_sorted(self):
        cfg = _make_cfg()
        future1 = datetime.now(pytz.timezone(cfg.timezone)) + timedelta(hours=5)
        future2 = datetime.now(pytz.timezone(cfg.timezone)) + timedelta(hours=10)
        links = [
            f'jogos/group/{future2.strftime("%Y-%m-%d")}_{future2.strftime("%H")}h_b.html',
            f'jogos/group/{future1.strftime("%Y-%m-%d")}_{future1.strftime("%H")}h_a.html',
        ]
        result = _get_upcoming_games(links, cfg)
        assert result == sorted(result)


# ------------------------------------------------------------------
# html._save_html
# ------------------------------------------------------------------

class TestSaveHtml:
    def test_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "report.html")
            _save_html(path, "<h1>Hello</h1>", "Test")
            assert os.path.isfile(path)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            assert "<h1>Hello</h1>" in content
            assert "<title>Test</title>" in content

    def test_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "deep", "nested", "report.html")
            _save_html(path, "<p>test</p>", "Title")
            assert os.path.isfile(path)

    def test_template_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "report.html")
            _save_html(path, "<p>body</p>", "MyTitle")
            with open(path, encoding="utf-8") as f:
                content = f.read()
            assert "<!DOCTYPE html>" in content
            assert "MyTitle" in content
            assert "<p>body</p>" in content
            assert "</html>" in content
