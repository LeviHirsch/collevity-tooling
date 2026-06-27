"""Phase 1 acceptance tests — store, slot lifecycle, label validation.

Each test names the AC leaf it covers (spec.md:47-51).
"""

from __future__ import annotations

import json
import os
import stat

import pytest

from cas import paths
from cas.errors import InvalidLabelError, LabelExistsError
from cas.labels import default_label_from_email, is_valid_label, validate_label
from cas.slots import create_slot, remove_slot, slot_exists
from cas.store import Record, Store


def _rec(email="levi@example.com", oat="sk-ant-oat01-abc", mint_date="2026-06-27",
         mint_profile=None):
    return Record(email=email, oat=oat, mint_date=mint_date, mint_profile=mint_profile)


def _mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


# --- AC1.1: store location, permissions, persistence ----------------------

def test_store_lives_under_collevity_home(home):
    Store().write("levi", _rec())
    assert paths.store_path() == home / "store.json"
    assert (home / "store.json").exists()


def test_store_file_is_chmod_600(home):
    Store().write("levi", _rec())
    assert _mode(paths.store_path()) == 0o600


def test_base_dir_outside_repo_and_icloud_by_default(monkeypatch):
    # With no override the base is a real home-dir path (the AC1.1 defense:
    # physical location outside repo/iCloud), not a path inside this tree.
    monkeypatch.delenv(paths.HOME_ENV, raising=False)
    base = paths.base_dir()
    assert base == paths.Path.home() / ".collevity"
    assert "iCloud" not in str(base)
    assert "collevity-tooling" not in str(base)


def test_records_survive_a_restart(home):
    Store().write("levi", _rec(email="a@x.com"))
    Store().write("work", _rec(email="b@y.com"))
    # A brand-new Store instance = a fresh process reading the same file.
    reopened = Store()
    assert reopened.read("levi").email == "a@x.com"
    assert reopened.read("work").email == "b@y.com"
    assert reopened.labels() == ["levi", "work"]


# --- AC1.2: record-per-label schema, not-found, duplicate emails ----------

def test_record_round_trips_all_fields(home):
    rec = _rec(email="e@x.com", oat="sk-ant-oat01-z", mint_date="2026-01-02",
               mint_profile="Profile 3")
    Store().write("levi", rec)
    got = Store().read("levi")
    assert (got.email, got.oat, got.mint_date, got.mint_profile) == (
        "e@x.com", "sk-ant-oat01-z", "2026-01-02", "Profile 3")


def test_on_disk_shape_is_object_keyed_by_label(home):
    Store().write("levi", _rec())
    raw = json.loads(paths.store_path().read_text())
    assert set(raw["levi"]) == {"email", "oat", "mint_date", "mint_profile"}


def test_reading_absent_label_returns_none_never_crashes(home):
    assert Store().read("nope") is None  # no file yet
    Store().write("levi", _rec())
    assert Store().read("still-nope") is None


def test_duplicate_email_across_labels_is_permitted(home):
    s = Store()
    s.write("levi", _rec(email="same@x.com"))
    s.write("levi-alt", _rec(email="same@x.com"))  # not rejected at schema level
    assert s.labels_for_email("same@x.com") == ["levi", "levi-alt"]


# --- AC1.3: slot config dir lifecycle -------------------------------------

def test_slot_dir_absent_before_create(home):
    assert not slot_exists("levi")
    assert not (home / "slots" / "levi").exists()


def test_create_slot_makes_dir_at_expected_path(home):
    path = create_slot("levi")
    assert path == home / "slots" / "levi"
    assert path.is_dir()
    assert slot_exists("levi")


def test_remove_slot_deletes_dir(home):
    create_slot("levi")
    assert remove_slot("levi") is True
    assert not slot_exists("levi")
    assert remove_slot("levi") is False  # idempotent, no crash


def test_store_write_does_not_create_slot(home):
    # Substrate primitives are separable: writing a record is NOT what makes the
    # slot dir appear (the add flow orchestrates both in phase 2).
    Store().write("levi", _rec())
    assert not slot_exists("levi")


# --- AC1.4: mint_profile present, accepts null ----------------------------

def test_mint_profile_defaults_to_null_and_is_present_on_disk(home):
    Store().write("levi", _rec(mint_profile=None))
    raw = json.loads(paths.store_path().read_text())
    assert "mint_profile" in raw["levi"]
    assert raw["levi"]["mint_profile"] is None
    assert Store().read("levi").mint_profile is None


def test_mint_profile_round_trips_a_value(home):
    Store().write("levi", _rec(mint_profile="Default"))
    assert Store().read("levi").mint_profile == "Default"


def test_record_from_dict_tolerates_missing_mint_profile():
    rec = Record.from_dict({"email": "e@x", "oat": "t", "mint_date": "2026-06-27"})
    assert rec.mint_profile is None


# --- AC1.5: label validation, default-from-email, uniqueness --------------

def test_default_label_is_email_local_part():
    assert default_label_from_email("levi@example.com") == "levi"
    assert default_label_from_email("a.b+c@host.org") == "a.b+c"


@pytest.mark.parametrize("bad", [
    "",            # empty
    "a/b",         # POSIX separator
    "a\\b",        # Windows separator
    "a\0b",        # null byte
    ".",           # traversal
    "..",          # traversal
])
def test_invalid_labels_are_rejected(bad):
    assert not is_valid_label(bad)
    with pytest.raises(InvalidLabelError):
        validate_label(bad)


@pytest.mark.parametrize("good", ["levi", "a.b+c", "work-2", "Levi_Main"])
def test_valid_labels_pass(good):
    validate_label(good)  # no raise
    assert is_valid_label(good)


def test_store_write_rejects_invalid_label(home):
    with pytest.raises(InvalidLabelError):
        Store().write("a/b", _rec())
    assert not paths.store_path().exists()  # nothing written


def test_collision_blocks_write_and_preserves_original(home):
    s = Store()
    s.write("levi", _rec(email="first@x.com"))
    with pytest.raises(LabelExistsError):
        s.write("levi", _rec(email="second@x.com"))
    assert s.read("levi").email == "first@x.com"  # untouched


def test_overwrite_flag_allows_replacing(home):
    s = Store()
    s.write("levi", _rec(email="first@x.com"))
    s.write("levi", _rec(email="second@x.com"), overwrite=True)
    assert s.read("levi").email == "second@x.com"


def test_delete_removes_record_and_returns_status(home):
    s = Store()
    s.write("levi", _rec())
    assert s.delete("levi") is True
    assert s.read("levi") is None
    assert s.delete("levi") is False  # absent, no crash
