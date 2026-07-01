"""The `rm` command: drop the record and guide server-side revocation (spec AC6).

``rm <label>`` removes the record from the store and deletes the slot config dir
(AC6.1/AC6.3) — both fully local, both regenerable by re-running ``add``. Neither
holds anything the server still honors after revocation, so removal is
unconditional and reports exactly what it did.

Local deletion does NOT revoke the oat server-side: the ``sk-ant-oat01-…`` token
is a 1-year bearer credential that remains valid on Anthropic's side until the
user revokes it in the dashboard. So ``rm`` prints step-by-step revocation
guidance (AC6.2) and — critically — the safe-ID rule: the setup-token oat is
``user:inference`` scope ONLY; the multi-scope device-login entries
(``user:sessions:claude_code`` + ``user:profile``) must NOT be revoked, or the
user logs themselves out of interactive Claude. The mint date (echoed here and
shown by ``list``) disambiguates which entry to revoke.
"""

from __future__ import annotations

from typing import Optional

from .io import ConsoleIO, IO
from .slots import remove_slot
from .store import Store

#: Exit code when the label is unknown (AC6.4 — clear error, nothing removed).
NO_SUCH_LABEL = 2


def _revocation_guidance(email: str, mint_date: str) -> list[str]:
    """The AC6.2 server-side revocation walkthrough, with the safe-ID warning."""
    return [
        "",
        "The local record is gone, but the oat is still LIVE on Anthropic's side.",
        "Revoke it server-side to fully retire this credential:",
        "  1. Open Settings → Claude Code → Authorization tokens in your browser.",
        f"  2. Find the entry for {email} minted on {mint_date}, whose scope is",
        "     'user:inference' ONLY (the setup-token oat carries no other scope).",
        "  3. Revoke THAT entry.",
        "",
        "  ⚠  Do NOT revoke your device-login entries — they are recognizable by",
        "     'user:sessions:claude_code' and 'user:profile' in the scope list.",
        "     The setup-token oat has neither; revoking a device login would log",
        "     you out of interactive Claude.",
    ]


def run_rm(
    label: str,
    *,
    store: Optional[Store] = None,
    io: Optional[IO] = None,
) -> int:
    """Remove ``label`` and print revocation guidance. Returns an exit code."""
    store = store if store is not None else Store()
    io = io if io is not None else ConsoleIO()

    # AC6.4 — a missing label is a clear error; nothing is removed.
    record = store.read(label)
    if record is None:
        labels = store.labels()
        if labels:
            io.error(
                f"no slot named {label!r}. Available labels: {', '.join(labels)}"
            )
        else:
            io.error(
                f"no slot named {label!r}. No slots exist yet — run 'cas add' first."
            )
        return NO_SUCH_LABEL

    # Capture the fields needed for guidance BEFORE the record is deleted.
    email = record.email
    mint_date = record.mint_date

    # AC6.1 — drop the record and confirm.
    store.delete(label)
    io.info(f"removed '{label}' ({email}) from the store.")

    # AC6.3 — delete the slot config dir unconditionally and report it.
    if remove_slot(label):
        io.info(f"deleted slot config dir for '{label}'.")
    else:
        io.info(f"no slot config dir for '{label}' to delete.")

    # AC6.2 — server-side revocation walkthrough with the safe-ID warning.
    for line in _revocation_guidance(email, mint_date):
        io.info(line)

    return 0
