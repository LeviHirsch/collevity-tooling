"""Phase 4 acceptance tests — `list`, `use`, `rm` (spec.md:73-90).

Each test names the AC leaf it covers. The two live subprocess boundaries are
mocked (per the phase brief): a fake ``login_email`` stands in for the default-dir
``claude auth status`` probe, and a fake ``launcher`` stands in for the real
``claude auth login``. Pure helpers (age humanizer, email parser, table layout)
are exercised directly against real values.
"""

from __future__ import annotations

import datetime

import pytest

from cas import listing, removal, switch
from cas.io import IO
from cas.listing import (
    format_listing,
    humanize_age,
    parse_login_email,
    run_list,
)
from cas.paths import slot_dir
from cas.removal import run_rm
from cas.slots import create_slot, slot_exists
from cas.store import Record, Store
from cas.switch import run_use

TODAY = datetime.date(2026, 6, 30)


# --- test doubles ----------------------------------------------------------

class FakeIO(IO):
    """Records everything shown, per stream."""

    def __init__(self):
        self.out: list[str] = []
        self.notices: list[str] = []
        self.warns: list[str] = []
        self.errors: list[str] = []

    def info(self, msg: str = "") -> None:
        self.out.append(msg)

    def notice(self, msg: str) -> None:
        self.notices.append(msg)

    def warn(self, msg: str) -> None:
        self.warns.append(msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def stdout(self) -> str:
        return "\n".join(self.out)

    def shown(self) -> str:
        return "\n".join(self.out + self.notices + self.warns + self.errors)


def _seed(store: Store, label, email, mint_date="2026-05-19", oat=None):
    store.write(
        label,
        Record(email=email, oat=oat or f"sk-ant-oat01-{label}", mint_date=mint_date),
    )


# ===========================================================================
# AC4 — list
# ===========================================================================

# --- AC4.1: one row per label with label, email, human-readable oat age ----

def test_list_shows_label_email_and_age(home):
    store = Store()
    _seed(store, "work", "levi@example.com", mint_date="2026-05-19")  # 42 days
    io = FakeIO()
    rc = run_list(store=store, io=io, login_email=lambda: None, today=lambda: TODAY)
    assert rc == 0
    out = io.stdout()
    assert "work" in out
    assert "levi@example.com" in out
    assert "42 days" in out


def test_humanize_age_units():
    assert humanize_age("2026-06-30", TODAY) == "today"
    assert humanize_age("2026-06-29", TODAY) == "1 day"
    assert humanize_age("2026-05-19", TODAY) == "42 days"
    # clock skew (mint in the "future") clamps to today rather than going negative
    assert humanize_age("2026-07-05", TODAY) == "today"
    # a malformed date renders a row instead of crashing list
    assert humanize_age("not-a-date", TODAY) == "unknown"


def test_list_empty_store_points_to_add(home):
    store = Store()
    io = FakeIO()
    rc = run_list(store=store, io=io, login_email=lambda: None, today=lambda: TODAY)
    assert rc == 0
    assert any("cas add" in line for line in io.out)


# --- AC4.2: match default-dir auth-status email; mark active / note no match -

def test_list_marks_active_login_row(home):
    store = Store()
    _seed(store, "work", "levi@example.com")
    _seed(store, "play", "levi2@example.com")
    io = FakeIO()
    run_list(
        store=store,
        io=io,
        login_email=lambda: "levi@example.com",
        today=lambda: TODAY,
    )
    lines = io.stdout().splitlines()
    work_line = next(l for l in lines if "work" in l)
    play_line = next(l for l in lines if "play" in l)
    # the arrow gutter marks only the matching row
    assert work_line.startswith("→")
    assert not play_line.startswith("→")
    assert "no active interactive login matched" not in io.stdout()


def test_list_appends_note_when_no_match(home):
    store = Store()
    _seed(store, "work", "levi@example.com")
    io = FakeIO()
    run_list(
        store=store,
        io=io,
        login_email=lambda: "someone-else@example.com",
        today=lambda: TODAY,
    )
    assert "no active interactive login matched" in io.stdout()
    assert not io.stdout().splitlines()[1].startswith("→")  # row not marked active


def test_list_note_when_probe_returns_none(home):
    # claude missing / logged out / oat-only path -> None -> degrade to no match
    store = Store()
    _seed(store, "work", "levi@example.com")
    io = FakeIO()
    run_list(store=store, io=io, login_email=lambda: None, today=lambda: TODAY)
    assert "no active interactive login matched" in io.stdout()


def test_list_email_match_is_case_insensitive(home):
    store = Store()
    _seed(store, "work", "Levi@Example.com")
    io = FakeIO()
    run_list(
        store=store,
        io=io,
        login_email=lambda: "levi@example.com",
        today=lambda: TODAY,
    )
    work_line = next(l for l in io.stdout().splitlines() if "work" in l)
    assert work_line.startswith("→")


def test_list_marks_all_rows_sharing_the_active_email(home):
    # duplicate bindings are permitted (AC1.2); both rows for the email are active
    store = Store()
    _seed(store, "work", "levi@example.com")
    _seed(store, "spare", "levi@example.com")
    io = FakeIO()
    run_list(
        store=store,
        io=io,
        login_email=lambda: "levi@example.com",
        today=lambda: TODAY,
    )
    active = [l for l in io.stdout().splitlines() if l.startswith("→")]
    assert len(active) == 2


def test_parse_login_email_prefers_email_field():
    assert parse_login_email('{"loggedIn": true, "email": "a@b.com"}', "") == "a@b.com"
    assert parse_login_email("Logged in as a@b.com", "") == "a@b.com"
    assert parse_login_email("Email = A@B.COM", "") == "a@b.com"
    assert parse_login_email("not logged in", "") is None
    assert parse_login_email("", "") is None


def test_default_login_email_strips_slot_env(home, monkeypatch):
    # AC4.2: the probe runs against the DEFAULT config dir — slot env is stripped.
    seen = {}

    def fake_run(cmd, env, capture_output, text, timeout):
        seen["cmd"] = cmd
        seen["env"] = env

        class R:
            stdout = '{"email": "x@y.com"}'
            stderr = ""

        return R()

    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/some/slot")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-LEAK")
    monkeypatch.setattr(listing.subprocess, "run", fake_run)
    email = listing.default_login_email(claude_bin="claude")
    assert email == "x@y.com"
    assert seen["cmd"] == ["claude", "auth", "status"]
    assert "CLAUDE_CONFIG_DIR" not in seen["env"]
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in seen["env"]


def test_default_login_email_returns_none_when_binary_missing(home, monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("claude")

    monkeypatch.setattr(listing.subprocess, "run", boom)
    assert listing.default_login_email(claude_bin="claude") is None


# --- AC4.3: unambiguous in a plain terminal, no flag/pipe ------------------

def test_format_listing_aligns_and_marks_without_flags(home):
    recs = {
        "work": Record(email="levi@example.com", oat="x", mint_date="2026-05-19"),
        "play": Record(email="p@x.com", oat="x", mint_date="2026-06-29"),
    }
    table = format_listing(recs, active_labels={"work"}, today=TODAY)
    lines = table.splitlines()
    assert lines[0].startswith("  ")  # header has the plain gutter
    assert "LABEL" in lines[0] and "EMAIL" in lines[0] and "AGE" in lines[0]
    work_line = next(l for l in lines if "work" in l)
    play_line = next(l for l in lines if "play" in l)
    assert work_line.startswith("→ ")  # active marked
    assert play_line.startswith("  ")  # inactive plain
    # columns align: the email field starts at the same offset on every data row
    assert work_line.index("levi@example.com") == play_line.index("p@x.com")


# ===========================================================================
# AC5 — use
# ===========================================================================

class FakeLoginLauncher:
    def __init__(self, returncode=0):
        self.returncode = returncode
        self.calls: list[list] = []

    def __call__(self, cmd):
        self.calls.append(list(cmd))
        return self.returncode


# --- AC5.1: invoke `claude auth login --email <stored-email>` --------------

def test_use_invokes_auth_login_with_stored_email(home):
    store = Store()
    _seed(store, "work", "levi@example.com")
    io = FakeIO()
    launcher = FakeLoginLauncher()
    rc = run_use("work", store=store, io=io, launcher=launcher, claude_bin="claude")
    assert rc == 0
    assert launcher.calls[0] == ["claude", "auth", "login", "--email", "levi@example.com"]


def test_use_echoes_identity_and_consent_reminder(home):
    store = Store()
    _seed(store, "work", "levi@example.com")
    io = FakeIO()
    run_use("work", store=store, io=io, launcher=FakeLoginLauncher(), claude_bin="claude")
    joined = "\n".join(io.notices)
    assert "switching to work (levi@example.com)" in joined
    assert "consent page" in joined and "levi@example.com" in joined


def test_use_propagates_login_exit_code(home):
    store = Store()
    _seed(store, "work", "levi@example.com")
    io = FakeIO()
    rc = run_use(
        "work", store=store, io=io, launcher=FakeLoginLauncher(returncode=7),
        claude_bin="claude",
    )
    assert rc == 7


def test_use_normalizes_signal_exit(home):
    store = Store()
    _seed(store, "work", "levi@example.com")
    io = FakeIO()
    rc = run_use(
        "work", store=store, io=io, launcher=FakeLoginLauncher(returncode=-2),
        claude_bin="claude",
    )
    assert rc == 130  # 128 + SIGINT


def test_use_missing_binary_is_reported(home):
    store = Store()
    _seed(store, "work", "levi@example.com")
    io = FakeIO()

    def boom(cmd):
        raise FileNotFoundError(cmd[0])

    rc = run_use("work", store=store, io=io, launcher=boom, claude_bin="claude")
    assert rc == switch.COMMAND_NOT_FOUND
    assert any("command not found" in e for e in io.errors)


# --- AC5.3: unknown label fails BEFORE any auth subcommand -----------------

def test_use_unknown_label_fails_without_invoking_login(home):
    store = Store()
    _seed(store, "work", "levi@example.com")
    io = FakeIO()
    launcher = FakeLoginLauncher()
    rc = run_use("ghost", store=store, io=io, launcher=launcher, claude_bin="claude")
    assert rc == switch.NO_SUCH_LABEL
    assert launcher.calls == []  # no auth subcommand invoked
    assert any("ghost" in e and "work" in e for e in io.errors)


def test_use_unknown_label_empty_store_points_to_add(home):
    store = Store()
    io = FakeIO()
    rc = run_use("ghost", store=store, io=io, launcher=FakeLoginLauncher(), claude_bin="claude")
    assert rc == switch.NO_SUCH_LABEL
    assert any("cas add" in e for e in io.errors)


# ===========================================================================
# AC6 — rm
# ===========================================================================

# --- AC6.1: remove the record and confirm ----------------------------------

def test_rm_removes_record_and_confirms(home):
    store = Store()
    _seed(store, "work", "levi@example.com")
    io = FakeIO()
    rc = run_rm("work", store=store, io=io)
    assert rc == 0
    assert store.read("work") is None
    assert any("removed 'work'" in line for line in io.out)


# --- AC6.2: server-side revocation guidance with the safe-ID warning -------

def test_rm_prints_revocation_guidance_with_safe_id(home):
    store = Store()
    _seed(store, "work", "levi@example.com", mint_date="2026-05-19")
    io = FakeIO()
    run_rm("work", store=store, io=io)
    out = io.stdout()
    assert "Authorization tokens" in out
    assert "user:inference" in out
    assert "2026-05-19" in out  # mint date disambiguates the entry
    # the explicit don't-revoke warning naming the multi-scope device-login markers
    assert "user:sessions:claude_code" in out
    assert "user:profile" in out
    assert "Do NOT revoke" in out


# --- AC6.3: slot config dir deleted unconditionally and reported -----------

def test_rm_deletes_slot_dir_and_reports(home):
    store = Store()
    _seed(store, "work", "levi@example.com")
    create_slot("work")
    assert slot_exists("work")
    io = FakeIO()
    run_rm("work", store=store, io=io)
    assert not slot_dir("work").exists()
    assert any("deleted slot config dir" in line for line in io.out)


def test_rm_reports_when_no_slot_dir_present(home):
    store = Store()
    _seed(store, "work", "levi@example.com")  # record but no slot dir created
    io = FakeIO()
    run_rm("work", store=store, io=io)
    assert any("no slot config dir" in line for line in io.out)


# --- AC6.4: unknown label fails with a clear error -------------------------

def test_rm_unknown_label_fails(home):
    store = Store()
    _seed(store, "work", "levi@example.com")
    io = FakeIO()
    rc = run_rm("ghost", store=store, io=io)
    assert rc == removal.NO_SUCH_LABEL
    assert store.read("work") is not None  # untouched
    assert any("ghost" in e for e in io.errors)


def test_rm_unknown_label_empty_store_points_to_add(home):
    store = Store()
    io = FakeIO()
    rc = run_rm("ghost", store=store, io=io)
    assert rc == removal.NO_SUCH_LABEL
    assert any("cas add" in e for e in io.errors)


# ===========================================================================
# CLI dispatch
# ===========================================================================

def test_main_routes_list(monkeypatch):
    from cas import cli

    called = {}

    def fake_list():
        called["hit"] = True
        return 0

    monkeypatch.setattr(cli, "run_list", fake_list)
    assert cli.main(["list"]) == 0
    assert called["hit"]


def test_main_routes_use(monkeypatch):
    from cas import cli

    seen = {}

    def fake_use(label):
        seen["label"] = label
        return 0

    monkeypatch.setattr(cli, "run_use", fake_use)
    assert cli.main(["use", "work"]) == 0
    assert seen["label"] == "work"


def test_main_routes_rm(monkeypatch):
    from cas import cli

    seen = {}

    def fake_rm(label):
        seen["label"] = label
        return 0

    monkeypatch.setattr(cli, "run_rm", fake_rm)
    assert cli.main(["rm", "work"]) == 0
    assert seen["label"] == "work"
