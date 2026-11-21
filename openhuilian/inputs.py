"""Locate private, user-supplied firmware inputs outside the source tree."""
import os
from pathlib import Path


def _input(path, variable):
    value = path or os.environ.get(variable)
    if not value:
        raise SystemExit(f"Supply an input path or set {variable}")
    result = Path(value).expanduser()
    if not result.is_file():
        raise SystemExit(f"{variable}: input file not found: {result}")
    return result


def stock_up(path=None):
    return _input(path, "OPENHUILIAN_STOCK_UP")


def mask_rom(path=None):
    return _input(path, "OPENHUILIAN_MASK_ROM")
