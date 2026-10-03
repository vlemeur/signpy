"""Provide paths to packaged application assets."""

from pathlib import Path

PATH_STATIC = Path(__file__).resolve().parent / "static"
PATH_LOGO = PATH_STATIC / "sign-language.png"
PATH_SIGN_CAPTURE = PATH_STATIC / "sign_capture"
PATH_LSF_ALPHABET = PATH_STATIC / "lsf_alphabet"
