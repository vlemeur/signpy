"""Provide generic paths used in modules"""

from pathlib import Path

# Paths to folders
PATH_REPO = Path(".").parent.parent
PATH_STATIC = PATH_REPO / "static"

# Paths to files
PATH_LOGO = PATH_STATIC / "sign-language.png"