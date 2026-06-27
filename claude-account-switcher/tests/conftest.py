"""Shared fixtures: redirect the store/slot tree into a temp dir per test.

Setting COLLEVITY_HOME makes every test hermetic — it never reads or writes the
real ``~/.collevity/``.
"""

from __future__ import annotations

import pytest

from cas import paths


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Point COLLEVITY_HOME at a fresh temp dir; return that base Path."""
    monkeypatch.setenv(paths.HOME_ENV, str(tmp_path))
    return tmp_path
