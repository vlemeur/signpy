"""Regression tests for the Python 3.14 Streamlit migration."""

from pathlib import Path

from PIL import Image
from streamlit.testing.v1 import AppTest

from signpy.paths import PATH_LOGO

APP = Path(__file__).resolve().parents[1] / "signpy" / "signstream.py"


def test_packaged_logo() -> None:
    with Image.open(PATH_LOGO) as logo:
        logo.verify()


def test_app_home_page() -> None:
    app = AppTest.from_file(str(APP)).run(timeout=30)
    assert not app.exception
    assert [header.value for header in app.header] == ["1. Input ??", "2. Input ??"]
    assert app.sidebar.info[0].value == "Welcome to Python sign recognition app"


def test_other_page() -> None:
    app = AppTest.from_string("from signpy.signstream import other_tab\nother_tab()").run(
        timeout=30
    )
    assert not app.exception
    assert app.sidebar.info[0].value == "Bienvenue dans une section sans aucune utilité"
