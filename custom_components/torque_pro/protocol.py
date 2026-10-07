"""Parse Torque Pro "Upload to web server" requests (no Home Assistant imports)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
import re

# Torque sends standard OBD PIDs both padded and unpadded ("k05" and "k5"), so PIDs are
# normalised through int(): "05", "5" -> "5"; "ff1005" -> "ff1005".
_PID = re.compile(r"[0-9a-fA-F]+")
_VALUE_KEY = re.compile(r"k([0-9a-fA-F]+)")
_META_KEYS = {
    "userFullName": "full_name",
    "userShortName": "short_name",
    "userUnit": "user_unit",
    "defaultUnit": "default_unit",
}

PID_LONGITUDE = "ff1005"
PID_LATITUDE = "ff1006"
PID_GPS_ACCURACY = "ff1239"


def normalise_pid(raw: str) -> str | None:
    """Return the canonical PID (lower-case hex without leading zeros) or None."""
    if not _PID.fullmatch(raw):
        return None
    return format(int(raw, 16), "x")


@dataclass(slots=True)
class Upload:
    """One request from the app."""

    phone_id: str | None
    session: str | None
    time_ms: int | None
    email: str | None
    values: dict[str, float] = field(default_factory=dict)
    # pid -> {"full_name": .., "short_name": .., "user_unit": .., "default_unit": ..}
    meta: dict[str, dict[str, str]] = field(default_factory=dict)
    profile: dict[str, str] = field(default_factory=dict)
    notice: str | None = None
    notice_class: str | None = None

    @property
    def profile_name(self) -> str | None:
        return self.profile.get("Name") or None


def _number(text: str) -> float | None:
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value == value and value not in (float("inf"), float("-inf")) else None


def parse_upload(items: Iterable[tuple[str, str]]) -> Upload:
    """Parse the query (or form) items of one upload. Unknown keys are ignored.

    Keys may repeat (Torque sends GPS keys twice); the first value wins.
    """
    upload = Upload(phone_id=None, session=None, time_ms=None, email=None)
    seen: set[str] = set()
    for key, value in items:
        if key in seen:
            continue
        seen.add(key)
        if key == "id":
            upload.phone_id = value or None
        elif key == "session":
            upload.session = value or None
        elif key == "eml":
            upload.email = value or None
        elif key == "time":
            upload.time_ms = int(value) if value.isdigit() else None
        elif key == "notice":
            upload.notice = value or None
        elif key == "noticeClass":
            upload.notice_class = value or None
        elif key.startswith("profile") and len(key) > len("profile"):
            upload.profile[key[len("profile"):]] = value
        elif match := _VALUE_KEY.fullmatch(key):
            pid = normalise_pid(match.group(1))
            number = _number(value)
            if pid is not None and number is not None:
                upload.values[pid] = number
        else:
            for prefix, name in _META_KEYS.items():
                if key.startswith(prefix):
                    pid = normalise_pid(key[len(prefix):])
                    if pid is not None:
                        upload.meta.setdefault(pid, {})[name] = value.strip()
                    break
    return upload
