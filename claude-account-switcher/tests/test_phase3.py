"""Phase 3 acceptance tests — the `run` per-process runner (spec.md:64-71).

Each test names the AC leaf it covers. The subprocess boundary is mocked (per
the phase brief): a fake launcher stands in for the real Popen + tee, recording
the command and the env it was handed and returning a scripted exit code +
captured-output tail. The pure helpers (env build, `--` split, auth matcher,
exit-code normalization) are exercised directly against real values.
"""

from __future__ import annotations

import os

import pytest

from cas import run as run_mod
from cas.io import IO
from cas.run import (
    build_child_env,
    looks_like_auth_failure,
    normalize_exit_code,
    run_command,
    split_double_dash,
)
from cas.store import Record, Store

OAT = "sk-ant-oat01-LIVEtoken_value-123"
EMAIL = "levi@example.com"


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

    def shown(self) -> str:
        return "\n".join(self.out + self.notices + self.warns + self.errors)


class FakeLauncher:
    """Stands in for the real Popen + tee. Records (cmd, env); returns scripted."""

    def __init__(self, returncode=0, captured=None):
        self.returncode = returncode
        self.captured = captured
        self.calls: list[tuple] = []

    def __call__(self, cmd, env):
        self.calls.append((list(cmd), dict(env)))
        return self.returncode, self.captured


def _seed(store: Store, label="work", email=EMAIL, oat=OAT):
    store.write(label, Record(email=email, oat=oat, mint_date="2026-06-29"))


# --- AC3.1: exactly two extra env vars, child-only -------------------------

def test_injects_exactly_config_dir_and_oat(home):
    from cas import paths

    store = Store()
    _seed(store)
    io = FakeIO()
    launcher = FakeLauncher()
    rc = run_command("work", ["claude", "-p", "hi"], store=store, io=io, launcher=launcher)
    assert rc == 0
    cmd, env = launcher.calls[0]
    assert cmd == ["claude", "-p", "hi"]
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == OAT
    assert env["CLAUDE_CONFIG_DIR"] == str(paths.slot_dir("work"))
    # exactly two keys added relative to the parent process env
    extra = set(env) - set(os.environ)
    assert extra == {"CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CONFIG_DIR"} - set(os.environ)
    # and every inherited key is unchanged
    for k, v in os.environ.items():
        if k not in ("CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CONFIG_DIR"):
            assert env[k] == v


def test_build_child_env_points_config_dir_at_the_slot(home):
    from cas import paths

    rec = Record(email=EMAIL, oat=OAT, mint_date="2026-06-29")
    env = build_child_env("work", rec)
    assert env["CLAUDE_CONFIG_DIR"] == str(paths.slot_dir("work"))
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == OAT


# --- AC3.2: oat never leaks to the parent env or to stdout -----------------

def test_oat_never_enters_parent_env(home, monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    store = Store()
    _seed(store)
    io = FakeIO()
    run_command("work", ["claude"], store=store, io=io, launcher=FakeLauncher())
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in os.environ


def test_oat_never_printed_to_any_stream(home):
    store = Store()
    _seed(store)
    io = FakeIO()
    run_command("work", ["claude"], store=store, io=io, launcher=FakeLauncher())
    assert OAT not in io.shown()


# --- AC3.3: identity echo from the stored email, no live lookup ------------

def test_prints_running_as_label_and_email(home):
    store = Store()
    _seed(store)
    io = FakeIO()
    run_command("work", ["claude"], store=store, io=io, launcher=FakeLauncher())
    assert any("running as work (levi@example.com)" in n for n in io.notices)


def test_identity_echo_uses_stored_email_not_a_lookup(home):
    # The email comes straight off the record; there is no network/CLI hook to
    # mock, which is the point — a wrong stored email would surface verbatim.
    store = Store()
    _seed(store, email="bound-at-mint@x.com")
    io = FakeIO()
    run_command("work", ["claude"], store=store, io=io, launcher=FakeLauncher())
    assert any("bound-at-mint@x.com" in n for n in io.notices)


# --- AC3.4: concurrent isolation, no collision, no parent mutation ---------

def test_two_runs_get_isolated_envs(home):
    store = Store()
    _seed(store, label="work", email="w@x.com", oat="sk-ant-oat01-WORK")
    _seed(store, label="play", email="p@x.com", oat="sk-ant-oat01-PLAY")
    from cas import paths

    l1, l2 = FakeLauncher(), FakeLauncher()
    run_command("work", ["claude"], store=store, io=FakeIO(), launcher=l1)
    run_command("play", ["claude"], store=store, io=FakeIO(), launcher=l2)

    env1 = l1.calls[0][1]
    env2 = l2.calls[0][1]
    assert env1["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat01-WORK"
    assert env2["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat01-PLAY"
    assert env1["CLAUDE_CONFIG_DIR"] == str(paths.slot_dir("work"))
    assert env2["CLAUDE_CONFIG_DIR"] == str(paths.slot_dir("play"))
    # no collision: the two child envs disagree on exactly the injected vars
    assert env1["CLAUDE_CODE_OAUTH_TOKEN"] != env2["CLAUDE_CODE_OAUTH_TOKEN"]
    assert env1["CLAUDE_CONFIG_DIR"] != env2["CLAUDE_CONFIG_DIR"]
    # parent shell untouched
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in os.environ or os.environ.get(
        "CLAUDE_CODE_OAUTH_TOKEN"
    ) not in ("sk-ant-oat01-WORK", "sk-ant-oat01-PLAY")


# --- AC3.5: unknown label fails before any launch --------------------------

def test_unknown_label_fails_without_launching(home):
    store = Store()
    _seed(store, label="work")
    _seed(store, label="play")
    io = FakeIO()
    launcher = FakeLauncher()
    rc = run_command("ghost", ["claude"], store=store, io=io, launcher=launcher)
    assert rc == run_mod.NO_SUCH_LABEL
    assert launcher.calls == []  # nothing launched
    # error lists the available labels
    joined = " ".join(io.errors)
    assert "ghost" in joined and "play" in joined and "work" in joined


def test_unknown_label_with_empty_store_points_to_add(home):
    store = Store()
    io = FakeIO()
    rc = run_command("ghost", ["claude"], store=store, io=io, launcher=FakeLauncher())
    assert rc == run_mod.NO_SUCH_LABEL
    assert any("cas add" in e for e in io.errors)


# --- AC3.6: surface stderr unmodified + best-effort auth guidance ----------

def test_auth_failure_signal_triggers_remint_guidance(home):
    store = Store()
    _seed(store)
    io = FakeIO()
    # the real dead-token output, on stdout, exit 1 (verified against CLI v2.1.197)
    captured = "Failed to authenticate. API Error: 401 Invalid bearer token\n"
    launcher = FakeLauncher(returncode=1, captured=captured)
    rc = run_command("work", ["claude", "-p", "hi"], store=store, io=io, launcher=launcher)
    assert rc == 1
    guidance = " ".join(io.errors)
    assert "cas rm work" in guidance and "cas add" in guidance


def test_nonzero_exit_without_auth_signal_prints_no_guidance(home):
    store = Store()
    _seed(store)
    io = FakeIO()
    launcher = FakeLauncher(returncode=3, captured="some unrelated runtime error\n")
    rc = run_command("work", ["claude"], store=store, io=io, launcher=launcher)
    assert rc == 3
    assert not io.errors  # no false-positive guidance


def test_clean_exit_prints_no_guidance(home):
    store = Store()
    _seed(store)
    io = FakeIO()
    launcher = FakeLauncher(returncode=0, captured="Hello!\n")
    rc = run_command("work", ["claude"], store=store, io=io, launcher=launcher)
    assert rc == 0
    assert not io.errors


def test_command_not_found_is_reported(home):
    store = Store()
    _seed(store)
    io = FakeIO()

    def boom(cmd, env):
        raise FileNotFoundError(cmd[0])

    rc = run_command("work", ["nope-binary"], store=store, io=io, launcher=boom)
    assert rc == run_mod.COMMAND_NOT_FOUND
    assert any("nope-binary" in e for e in io.errors)


# --- pure helpers ----------------------------------------------------------

def test_looks_like_auth_failure_matches_real_probe_output():
    assert looks_like_auth_failure(
        "Failed to authenticate. API Error: 401 Invalid bearer token"
    )
    assert looks_like_auth_failure("API Error: 401 unauthorized")
    assert looks_like_auth_failure('{"type":"authentication_error"}')


def test_looks_like_auth_failure_is_conservative():
    assert not looks_like_auth_failure("compilation failed: 401 lines processed")
    assert not looks_like_auth_failure("connection reset by peer")
    assert not looks_like_auth_failure("")


def test_split_double_dash_basic():
    before, after = split_double_dash(["run", "work", "--", "claude", "-p"])
    assert before == ["run", "work"]
    assert after == ["claude", "-p"]


def test_split_double_dash_only_first_separator_consumed():
    before, after = split_double_dash(["run", "x", "--", "claude", "--", "y"])
    assert before == ["run", "x"]
    assert after == ["claude", "--", "y"]  # child gets its own `--` verbatim


def test_split_double_dash_absent_vs_trailing():
    assert split_double_dash(["add", "work"]) == (["add", "work"], None)
    assert split_double_dash(["run", "work", "--"]) == (["run", "work"], [])


def test_normalize_exit_code_signal_convention():
    assert normalize_exit_code(0) == 0
    assert normalize_exit_code(3) == 3
    assert normalize_exit_code(-2) == 130  # SIGINT -> 128 + 2
    assert normalize_exit_code(-15) == 143  # SIGTERM -> 128 + 15


# --- CLI dispatch (the `--` boundary through main) -------------------------

def test_main_routes_run_command_after_double_dash(monkeypatch):
    from cas import cli

    seen = {}

    def fake_run(label, cmd):
        seen["label"] = label
        seen["cmd"] = cmd
        return 0

    monkeypatch.setattr(cli, "run_command", fake_run)
    rc = cli.main(["run", "work", "--", "claude", "-p", "--verbose"])
    assert rc == 0
    assert seen["label"] == "work"
    assert seen["cmd"] == ["claude", "-p", "--verbose"]  # child flags untouched


def test_main_run_without_command_errors(monkeypatch):
    from cas import cli

    # parser.error raises SystemExit(2)
    with pytest.raises(SystemExit):
        cli.main(["run", "work"])

    with pytest.raises(SystemExit):
        cli.main(["run", "work", "--"])  # `--` present but empty command
