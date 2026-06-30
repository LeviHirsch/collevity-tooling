"""Route the mint OAuth URL into a chosen Chrome profile (spec AC2.2).

macOS/Chrome-only convenience (DEC-011/012). Behavior, per Levi's steer (DEC-015):
**always print the URL** (the guaranteed path — the user can open or paste it into
whatever context they intend) AND, when Chrome profiles can be read, offer to
also auto-open it in a user-selected profile (best-effort; unverified mechanism).

The Chrome profile's Google identity need NOT match the Claude account — the
consent page (AC2.3) is the account authority. This list only chooses a *context*.
No persistent profile↔account association is built (D-002); the selection is just
recorded into the ``mint_profile`` seam by the caller (AC2.7).

:func:`parse_profiles` is pure (directly unit-tested); :class:`ChromeRouter`
takes injectable ``local_state_path`` / ``opener`` / ``platform`` so the routing
behavior is testable without a real Chrome.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

# Chrome's profile registry on macOS.
_DEFAULT_LOCAL_STATE = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Google"
    / "Chrome"
    / "Local State"
)


@dataclass
class Profile:
    """One Chrome profile: the on-disk ``directory`` plus display ``name``/email."""

    directory: str
    name: str
    email: str


def parse_profiles(local_state: dict) -> list[Profile]:
    """Profiles from a parsed Chrome ``Local State`` dict, sorted by display name."""
    cache = (local_state.get("profile") or {}).get("info_cache") or {}
    profiles = [
        Profile(
            directory=directory,
            name=info.get("name") or directory,
            email=info.get("user_name") or "",
        )
        for directory, info in cache.items()
    ]
    profiles.sort(key=lambda p: p.name.lower())
    return profiles


def _default_opener(url: str, directory: str) -> None:
    """Best-effort macOS/Chrome open into ``directory`` (DEC-011/012 candidate).

    Unverified; raises on failure, which the router downgrades to the printed URL.
    """
    subprocess.run(
        ["open", "-na", "Google Chrome", "--args",
         f"--profile-directory={directory}", url],
        check=True,
    )


class ChromeRouter:
    def __init__(
        self,
        local_state_path: Optional[Path] = None,
        opener: Optional[Callable[[str, str], None]] = None,
        platform: Optional[str] = None,
    ) -> None:
        self.local_state_path = (
            Path(local_state_path) if local_state_path else _DEFAULT_LOCAL_STATE
        )
        self.opener = opener or _default_opener
        self.platform = platform if platform is not None else sys.platform

    def _load_profiles(self) -> Optional[list[Profile]]:
        """Profiles, or ``None`` when unavailable (non-mac, no Chrome, unreadable)."""
        if self.platform != "darwin":
            return None
        try:
            data = json.loads(self.local_state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return parse_profiles(data) or None

    def route(self, url: str, io) -> Optional[str]:
        """Print the URL (always); offer to auto-open it in a picked profile.

        Returns the chosen profile's display name (recorded as ``mint_profile``),
        or ``None`` if none was selected. The chosen path is announced (AC2.2).
        """
        profiles = self._load_profiles()
        chosen: Optional[Profile] = None
        if profiles:
            options = [f"{p.name}  <{p.email or 'no email'}>" for p in profiles]
            idx = io.choose(
                "Open the authorization URL in which Chrome profile?", options
            )
            if idx is not None:
                chosen = profiles[idx]

        # The print is the guaranteed path — always shown, regardless of auto-open.
        io.info("")
        io.info(
            "Authorization URL — open this in the context/account you intend to "
            "authorize:"
        )
        io.info(f"  {url}")

        if chosen is not None:
            try:
                self.opener(url, chosen.directory)
                io.info(f"Also opened it in Chrome profile: {chosen.name}")
            except Exception as exc:  # best-effort; the printed URL remains authoritative
                io.warn(
                    f"could not auto-open Chrome profile '{chosen.name}' ({exc}); "
                    "use the printed URL above."
                )
            # Record the selection even if the open failed: the user still chose
            # this context and reaches it via the printed URL (AC2.7).
            return chosen.name

        if profiles is None:
            io.info(
                "(Chrome profile list unavailable here — open or paste the URL "
                "into the context you want.)"
            )
        return None
