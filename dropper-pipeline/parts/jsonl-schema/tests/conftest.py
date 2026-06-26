"""Shared test isolation.

Every test runs with the lake- and Dropper-location env vars pointed at a
throwaway tmp dir, so nothing ever touches Levi's real `collevity_lake.jsonl` or
`Dropper_excel.xlsm`. Tests that pass an explicit `pool_path=`/`xlsm_path=` are
unaffected (explicit args win); this only guards the no-arg default-resolution
paths (e.g. `sync_sources()`).
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_real_data(tmp_path, monkeypatch):
    monkeypatch.setenv("COLLEVITY_LAKE", str(tmp_path / "lake.jsonl"))
    monkeypatch.setenv("COLLEVITY_DROPPER_XLSM", str(tmp_path / "no-such-dropper.xlsm"))
