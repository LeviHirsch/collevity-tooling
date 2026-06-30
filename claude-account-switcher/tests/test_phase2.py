"""Phase 2 acceptance tests — the `add` guided mint/capture/bind flow.

Each test names the AC leaf it covers (spec.md:55-62). The subprocess + browser
boundaries are mocked (per the phase brief): a fake minter stands in for
``claude setup-token``, a fake liveness callable for ``auth status``, a fake
router for the browser, and a scripted :class:`FakeIO` for the interactive
prompts. Pure scrapers/parsers are exercised directly against real strings.
"""

from __future__ import annotations

import json

import pytest

from cas import chrome, setup_token
from cas.add import run_add
from cas.errors import MintError
from cas.io import IO
from cas.slots import slot_exists
from cas.store import Record, Store

URL = "https://claude.ai/oauth/authorize?code=abc123"
OAT = "sk-ant-oat01-LIVEtoken_value-123"


# --- test doubles ----------------------------------------------------------

class FakeIO(IO):
    """Scripts prompt/confirm/choose answers; records everything shown."""

    def __init__(self, prompts=None, confirms=None, chooses=None):
        self.prompts = list(prompts or [])
        self.confirms = list(confirms or [])
        self.chooses = list(chooses or [])
        self.out: list[str] = []
        self.warns: list[str] = []
        self.errors: list[str] = []

    def info(self, msg: str = "") -> None:
        self.out.append(msg)

    def warn(self, msg: str) -> None:
        self.warns.append(msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def prompt(self, msg: str) -> str:
        self.out.append(msg)
        return self.prompts.pop(0)

    def confirm(self, msg: str) -> bool:
        self.out.append(msg)
        return self.confirms.pop(0)

    def choose(self, msg, options):
        self.out.append(msg)
        return self.chooses.pop(0)

    def shown(self) -> str:
        return "\n".join(self.out + self.warns + self.errors)


class FakeMinter:
    def __init__(self, url=URL, oat=OAT):
        self.url = url
        self.oat = oat
        self.url_routed = None

    def mint(self, on_url):
        on_url(self.url)  # exercises routing + AC2.3 directives
        return self.oat


class FailingMinter:
    def mint(self, on_url):
        raise MintError("claude setup-token exited without printing an oat token")


class FakeRouter:
    def __init__(self, profile=None):
        self.profile = profile
        self.urls: list[str] = []

    def route(self, url, io):
        self.urls.append(url)
        return self.profile


def _run(label_arg, *, home, store=None, io=None, minter=None, router=None,
         liveness=True, profile=None):
    store = store if store is not None else Store()
    minter = minter if minter is not None else FakeMinter()
    router = router if router is not None else FakeRouter(profile=profile)
    rc = run_add(
        label_arg,
        store=store,
        io=io,
        minter=minter,
        router=router,
        liveness=(liveness if callable(liveness) else (lambda oat: liveness)),
        today=lambda: "2026-06-29",
    )
    return rc, store, io, router


# --- AC2.1 / AC2.4: launch, scrape URL + oat -------------------------------

def test_add_provided_label_writes_record_with_scraped_oat(home):
    io = FakeIO(prompts=["levi@example.com"], confirms=[True])
    rc, store, io, router = _run("work", home=home, io=io)
    assert rc == 0
    rec = store.read("work")
    assert rec.oat == OAT  # AC2.4: oat scraped, never pasted
    assert rec.email == "levi@example.com"
    assert rec.mint_date == "2026-06-29"
    assert router.urls == [URL]  # AC2.1 URL captured and routed


def test_mint_failure_aborts_without_writing(home):
    io = FakeIO()
    rc, store, io, _ = _run("work", home=home, io=io, minter=FailingMinter())
    assert rc == 1
    assert store.read("work") is None
    assert not slot_exists("work")
    assert io.errors  # clear error surfaced


def test_find_url_and_oat_scrape_from_interleaved_output():
    blob = (
        "\x1b[2mVisit this URL to authorize:\x1b[0m\n"
        f"   {URL}\n"
        "Waiting for authorization...\n"
        f"Your token: {OAT}\n"
    )
    assert setup_token.find_url(blob) == URL
    assert setup_token.find_oat(blob) == OAT


def test_find_oat_absent_returns_none():
    assert setup_token.find_oat("no token here") is None
    assert setup_token.find_url("no url here") is None


# --- AC2.2: Chrome-profile routing + always-print fallback -----------------

def test_selected_profile_recorded_in_mint_profile(home):
    io = FakeIO(prompts=["levi@example.com"], confirms=[True])
    rc, store, io, _ = _run("work", home=home, io=io, profile="Work")
    assert rc == 0
    assert store.read("work").mint_profile == "Work"


def test_no_profile_selected_leaves_mint_profile_null(home):
    io = FakeIO(prompts=["levi@example.com"], confirms=[True])
    rc, store, io, _ = _run("work", home=home, io=io, profile=None)
    assert store.read("work").mint_profile is None


def test_router_always_prints_url_and_opens_chosen_profile(tmp_path):
    local_state = {
        "profile": {"info_cache": {
            "Default": {"name": "Personal", "user_name": "a@x.com"},
            "Profile 1": {"name": "Work", "user_name": "b@y.com"},
        }}
    }
    p = tmp_path / "Local State"
    p.write_text(json.dumps(local_state))
    opened = {}

    def opener(url, directory):
        opened["url"] = url
        opened["dir"] = directory

    io = FakeIO(chooses=[1])  # sorted by name: Personal(0), Work(1)
    router = chrome.ChromeRouter(local_state_path=p, opener=opener, platform="darwin")
    name = router.route(URL, io)
    assert name == "Work"
    assert opened == {"url": URL, "dir": "Profile 1"}
    assert any(URL in line for line in io.out)  # printed regardless


def test_router_prints_when_profiles_unavailable(tmp_path):
    io = FakeIO()
    router = chrome.ChromeRouter(local_state_path=tmp_path / "nope", platform="linux")
    name = router.route(URL, io)
    assert name is None
    assert any(URL in line for line in io.out)


def test_router_records_selection_even_if_open_fails(tmp_path):
    local_state = {"profile": {"info_cache": {
        "Profile 1": {"name": "Work", "user_name": "b@y.com"}}}}
    p = tmp_path / "Local State"
    p.write_text(json.dumps(local_state))

    def boom(url, directory):
        raise RuntimeError("Chrome not running")

    io = FakeIO(chooses=[0])
    router = chrome.ChromeRouter(local_state_path=p, opener=boom, platform="darwin")
    name = router.route(URL, io)
    assert name == "Work"  # selection still recorded
    assert io.warns  # failure announced
    assert any(URL in line for line in io.out)


def test_parse_profiles_pure():
    state = {"profile": {"info_cache": {
        "Default": {"name": "Zed", "user_name": "z@x.com"},
        "Profile 2": {"name": "Abe", "user_name": "a@x.com"},
    }}}
    profiles = chrome.parse_profiles(state)
    assert [p.name for p in profiles] == ["Abe", "Zed"]  # sorted by name
    assert profiles[0].directory == "Profile 2"


# --- AC2.3: consent-page account-check directive ---------------------------

def test_user_directed_to_consent_page_account_display(home):
    io = FakeIO(prompts=["levi@example.com"], confirms=[True])
    _run("work", home=home, io=io)
    shown = io.shown()
    assert "Logged in as" in shown
    assert "Switch-account" in shown


# --- AC2.5: liveness gate --------------------------------------------------

def test_failed_liveness_aborts_before_any_write(home):
    io = FakeIO()  # email is never reached, so no prompts needed
    rc, store, io, _ = _run("work", home=home, io=io, liveness=False)
    assert rc == 1
    assert store.read("work") is None
    assert not slot_exists("work")
    assert any("liveness" in e for e in io.errors)


def test_liveness_receives_the_scraped_oat(home):
    seen = {}

    def liveness(oat):
        seen["oat"] = oat
        return True

    io = FakeIO(prompts=["levi@example.com"], confirms=[True])
    _run("work", home=home, io=io, liveness=liveness)
    assert seen["oat"] == OAT


def test_parse_auth_status_pure():
    assert setup_token.parse_auth_status(
        '{"loggedIn": true, "authMethod": "oauth_token"}', "") is True
    assert setup_token.parse_auth_status(
        '{"loggedIn": false, "authMethod": "oauth_token"}', "") is False
    assert setup_token.parse_auth_status(
        '{"loggedIn": true, "authMethod": "api_key"}', "") is False


# --- AC2.6: email retype-confirm -------------------------------------------

def test_email_retype_then_confirm_writes_typed_value(home):
    io = FakeIO(prompts=["levi@example.com"], confirms=[True])
    rc, store, io, _ = _run("work", home=home, io=io)
    assert rc == 0
    assert store.read("work").email == "levi@example.com"
    # echoed back before the confirm
    assert any("levi@example.com" in line for line in io.out)


def test_wrong_email_can_be_reentered_then_confirmed(home):
    # type wrong -> "correct?" No -> "re-enter?" Yes -> type right -> "correct?" Yes
    io = FakeIO(
        prompts=["wrong@x.com", "right@x.com"],
        confirms=[False, True, True],
    )
    rc, store, io, _ = _run("work", home=home, io=io)
    assert rc == 0
    assert store.read("work").email == "right@x.com"


def test_declining_email_confirmation_aborts(home):
    # type -> "correct?" No -> "re-enter?" No -> abort
    io = FakeIO(prompts=["levi@example.com"], confirms=[False, False])
    rc, store, io, _ = _run("work", home=home, io=io)
    assert rc == 1
    assert store.read("work") is None
    assert io.errors


# --- AC2.7: write, slot, summary, duplicate-email warn ---------------------

def test_successful_add_creates_slot_and_prints_summary(home):
    io = FakeIO(prompts=["levi@example.com"], confirms=[True])
    rc, store, io, _ = _run("work", home=home, io=io)
    assert rc == 0
    assert slot_exists("work")
    shown = io.shown()
    assert "work" in shown and "levi@example.com" in shown and "2026-06-29" in shown


def test_store_record_is_chmod_600(home):
    import os
    import stat

    from cas import paths
    io = FakeIO(prompts=["levi@example.com"], confirms=[True])
    _run("work", home=home, io=io)
    mode = stat.S_IMODE(os.stat(paths.store_path()).st_mode)
    assert mode == 0o600


def test_duplicate_email_warns_and_writes_on_confirm(home):
    store = Store()
    store.write("other", Record(email="dup@x.com", oat="sk-ant-oat01-old",
                                mint_date="2026-01-01"))
    # email confirm True, then duplicate-binding confirm True
    io = FakeIO(prompts=["dup@x.com"], confirms=[True, True])
    rc, store, io, _ = _run("work", home=home, store=store, io=io)
    assert rc == 0
    assert store.read("work").email == "dup@x.com"  # non-blocking; dup permitted
    assert io.warns


def test_duplicate_email_declined_aborts(home):
    store = Store()
    store.write("other", Record(email="dup@x.com", oat="sk-ant-oat01-old",
                                mint_date="2026-01-01"))
    io = FakeIO(prompts=["dup@x.com"], confirms=[True, False])
    rc, store, io, _ = _run("work", home=home, store=store, io=io)
    assert rc == 1
    assert store.read("work") is None


# --- AC2.1 / AC2.8: default label + collision ------------------------------

def test_no_label_defaults_to_email_local_part_after_confirm(home):
    # email confirm True, then "use 'levi'?" True
    io = FakeIO(prompts=["levi@example.com"], confirms=[True, True])
    rc, store, io, _ = _run(None, home=home, io=io)
    assert rc == 0
    assert store.read("levi") is not None
    assert slot_exists("levi")


def test_declining_default_label_prompts_for_custom(home):
    # email confirm True, "use 'levi'?" False, then type custom label
    io = FakeIO(prompts=["levi@example.com", "custom"], confirms=[True, False])
    rc, store, io, _ = _run(None, home=home, io=io)
    assert rc == 0
    assert store.read("custom") is not None
    assert store.read("levi") is None


def test_provided_label_collision_reprompts_before_mint(home):
    store = Store()
    store.write("work", Record(email="first@x.com", oat="sk-ant-oat01-first",
                               mint_date="2026-01-01"))
    # collision resolve happens first (prompt new label), then email + confirm
    io = FakeIO(prompts=["work2", "levi@example.com"], confirms=[True])
    rc, store, io, _ = _run("work", home=home, store=store, io=io)
    assert rc == 0
    assert store.read("work2").email == "levi@example.com"
    assert store.read("work").email == "first@x.com"  # original untouched


def test_default_label_collision_reprompts_for_unique(home):
    store = Store()
    store.write("levi", Record(email="someone-else@x.com", oat="sk-ant-oat01-x",
                               mint_date="2026-01-01"))
    # email confirm True, "use 'levi'?" True, collision -> prompt new label
    io = FakeIO(prompts=["levi@example.com", "levi2"], confirms=[True, True])
    rc, store, io, _ = _run(None, home=home, store=store, io=io)
    assert rc == 0
    assert store.read("levi2").email == "levi@example.com"
    assert store.read("levi").email == "someone-else@x.com"
