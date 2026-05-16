"""Tests for src.core.pipeline helpers."""

from __future__ import annotations

import os
import tempfile

import pandas as pd

from src.core.pipeline import _norm, _recreate_dirs, _save_csv

# ------------------------------------------------------------------
# _norm
# ------------------------------------------------------------------

class TestPipelineNorm:
    def test_normalizes_path(self):
        result = _norm("src/data/test")
        assert result == os.path.normpath("src/data/test")


# ------------------------------------------------------------------
# _recreate_dirs
# ------------------------------------------------------------------

class TestRecreateDirs:
    def test_creates_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dirs = [
                os.path.join(tmpdir, "root"),
                os.path.join(tmpdir, "root", "sub"),
            ]
            _recreate_dirs(dirs)
            assert os.path.isdir(dirs[0])
            assert os.path.isdir(dirs[1])

    def test_deletes_existing_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = os.path.join(tmpdir, "root")
            os.makedirs(root)
            old_file = os.path.join(root, "old.txt")
            with open(old_file, "w") as f:
                f.write("old")
            _recreate_dirs([root, os.path.join(root, "sub")])
            assert not os.path.exists(old_file)
            assert os.path.isdir(root)

    def test_empty_list(self):
        _recreate_dirs([])  # should not raise


# ------------------------------------------------------------------
# _save_csv
# ------------------------------------------------------------------

class TestSaveCsv:
    def test_saves_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "test.csv")
            df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
            _save_csv(df, path)
            assert os.path.isfile(path)
            loaded = pd.read_csv(path)
            assert list(loaded.columns) == ["a", "b"]
            assert len(loaded) == 2

    def test_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "deep", "nested", "dir", "test.csv")
            df = pd.DataFrame({"a": [1]})
            _save_csv(df, path)
            assert os.path.isfile(path)

    def test_csv_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.csv")
            df = pd.DataFrame({"a": [1.5], "b": ["x"]})
            _save_csv(df, path)
            with open(path) as f:
                content = f.read()
            assert "," in content
            assert "1.5" in content
            assert "index=False" not in content
