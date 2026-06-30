"""The `add` command: guided mint, capture, and bind (spec AC2).

Orchestrates the Phase 1 substrate (:mod:`cas.store`, :mod:`cas.slots`,
:mod:`cas.labels`) with the Phase 2 boundaries (:mod:`cas.setup_token`,
:mod:`cas.chrome`, :mod:`cas.io`). The flow is the ONLY mechanism that produces
a valid record.

Sequence:
  1. (provided label only) fail-fast collision resolve before the browser ritual (AC2.8)
  2. launch ``claude setup-token`` over a pty; capture the OAuth URL (AC2.1)
  3. route the URL to a chosen Chrome profile / print it (AC2.2) + direct the user
     to the consent page's account display (AC2.3)
  4. auto-scrape the oat from stdout (AC2.4)
  5. liveness-check the oat (AC2.5); abort on failure
  6. retype-confirm the email (AC2.6)
  7. resolve the final unique label — default = email local-part (AC2.1/AC2.8)
  8. warn on a duplicate email binding, require confirm (AC2.7)
  9. write the record (chmod 600 via the store) + create the slot dir; print a
     summary (AC2.7)

Dependencies are injected (store / io / minter / router / liveness / today) so the
subprocess and browser boundaries can be mocked; defaults wire the real ones.
"""

from __future__ import annotations

import datetime
from typing import Callable, Optional

from . import chrome, setup_token
from .errors import InvalidLabelError, MintError
from .io import ConsoleIO, IO
from .labels import default_label_from_email, validate_label
from .slots import create_slot
from .store import Record, Store


def _today() -> str:
    return datetime.date.today().isoformat()


def _resolve_unique_label(store: Store, io: IO, proposed: str) -> str:
    """Return a filesystem-safe label that does not yet exist (AC2.8).

    Re-prompts on an invalid OR colliding label; the write is blocked until a
    usable, unique one is given.
    """
    label = proposed
    while True:
        try:
            validate_label(label)
        except InvalidLabelError as exc:
            io.warn(str(exc))
            label = io.prompt("Enter a label: ").strip()
            continue
        if store.exists(label):
            io.warn(f"label '{label}' already exists in the store")
            label = io.prompt("Enter a different label: ").strip()
            continue
        return label


def _confirm_email(io: IO) -> Optional[str]:
    """AC2.6: prompt for the consent-page email, echo it back, require a confirm.

    Returns the confirmed address, or ``None`` if the user declines to confirm
    and declines to retry (the flow then aborts).
    """
    while True:
        email = io.prompt("Type the email shown on the consent page: ").strip()
        if not email:
            io.warn("email cannot be empty")
            continue
        if io.confirm(f"You typed: {email!r} — is that the account on the consent page?"):
            return email
        if not io.confirm("Re-enter the email?"):
            return None


def run_add(
    label_arg: Optional[str],
    *,
    store: Optional[Store] = None,
    io: Optional[IO] = None,
    minter: Optional[setup_token.SetupTokenMinter] = None,
    router: Optional[chrome.ChromeRouter] = None,
    liveness: Optional[Callable[[str], bool]] = None,
    today: Optional[Callable[[], str]] = None,
) -> int:
    """Run the guided `add` flow. Returns a process exit code (0 = bound)."""
    store = store if store is not None else Store()
    io = io if io is not None else ConsoleIO()
    minter = minter if minter is not None else setup_token.SetupTokenMinter()
    router = router if router is not None else chrome.ChromeRouter()
    liveness = liveness if liveness is not None else setup_token.liveness_check
    today = today if today is not None else _today

    # AC2.8 — for an explicitly provided label, deconflict BEFORE the browser
    # ritual so the user is not made to authorize only to hit a collision.
    pre_label: Optional[str] = None
    if label_arg is not None:
        pre_label = _resolve_unique_label(store, io, label_arg.strip())

    # AC2.1/AC2.2/AC2.3 — mint; the URL callback routes it and directs the user
    # to the consent-page account check.
    chosen_profile: dict[str, Optional[str]] = {"name": None}

    def on_url(url: str) -> None:
        chosen_profile["name"] = router.route(url, io)
        io.info("")
        io.info('On the consent page, read the "Logged in as <email>" line.')
        io.info(
            "If it shows the WRONG account, use the Switch-account link BEFORE "
            "approving the authorization."
        )

    try:
        oat = minter.mint(on_url)  # AC2.4 auto-scrape; never asks the user to paste
    except MintError as exc:
        io.error(str(exc))
        return 1

    # AC2.5 — liveness gate.
    if not liveness(oat):
        io.error(
            "liveness check failed: the captured token did not authenticate "
            '(expected loggedIn: true, authMethod: "oauth_token"). Aborting.'
        )
        return 1

    # AC2.6 — human attestation of the email.
    email = _confirm_email(io)
    if email is None:
        io.error("aborted: email not confirmed.")
        return 1

    # AC2.1/AC2.8 — final label. Default = email local-part, confirmed.
    if pre_label is not None:
        label = pre_label
    else:
        proposed = default_label_from_email(email)
        if proposed and io.confirm(f"Use '{proposed}' (email local-part) as the label?"):
            label = _resolve_unique_label(store, io, proposed)
        else:
            label = _resolve_unique_label(store, io, io.prompt("Enter a label: ").strip())

    # AC2.7 — duplicate-email warning (non-blocking; dup bindings are permitted).
    dups = store.labels_for_email(email)
    if dups:
        io.warn(f"{email} is already bound under: {', '.join(dups)}")
        if not io.confirm("Bind it again under a new label?"):
            io.error("aborted: duplicate binding declined.")
            return 1

    # AC2.7 — write (store enforces chmod 600) + create the slot dir.
    record = Record(
        email=email,
        oat=oat,
        mint_date=today(),
        mint_profile=chosen_profile["name"],
    )
    store.write(label, record)
    create_slot(label)

    io.info("")
    io.info("Bound successfully:")
    io.info(f"  label:      {label}")
    io.info(f"  email:      {email}")
    io.info(f"  mint date:  {record.mint_date}")
    if record.mint_profile:
        io.info(f"  profile:    {record.mint_profile}")
    return 0
