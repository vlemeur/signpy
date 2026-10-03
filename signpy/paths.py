"""Provide paths to packaged application assets."""

from pathlib import Path

PATH_STATIC = Path(__file__).resolve().parent / "static"
PATH_LOGO = PATH_STATIC / "sign-language.png"
