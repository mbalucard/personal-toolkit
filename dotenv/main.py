from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _strip_quotes(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and ((v[0] == v[-1]) and v[0] in {"'", '"'}):
        return v[1:-1]
    return v


def _find_dotenv(start: Path) -> Optional[Path]:
    cur = start.resolve()
    for p in (cur, *cur.parents):
        candidate = p / ".env"
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def find_dotenv(
    filename: str = ".env",
    raise_error_if_not_found: bool = False,
    usecwd: bool = False,
) -> str:
    start = Path.cwd() if usecwd else Path.cwd()
    cur = start.resolve()
    for p in (cur, *cur.parents):
        candidate = p / filename
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    if raise_error_if_not_found:
        raise OSError(f"{filename} not found")
    return ""


def load_dotenv(dotenv_path: Optional[str | os.PathLike[str]] = None, *, override: bool = False) -> bool:
    path = Path(dotenv_path) if dotenv_path is not None else _find_dotenv(Path.cwd())
    if path is None:
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        value = _strip_quotes(v)
        if not key:
            continue
        if not override and key in os.environ:
            continue
        os.environ[key] = value

    return True


def dotenv_values(dotenv_path: str | os.PathLike[str], encoding: str = "utf-8") -> dict[str, str | None]:
    path = Path(dotenv_path)
    if not path.exists() or not path.is_file():
        return {}
    try:
        content = path.read_text(encoding=encoding)
    except OSError:
        return {}

    data: dict[str, str | None] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        if not key:
            continue
        data[key] = _strip_quotes(v)
    return data
