"""Sphinx configuration."""
project = "signpy"
author = "Vincent LE MEUR"
copyright = f"2021, {author}"
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinx_autodoc_typehints", "sphinx_rtd_theme"]
autodoc_typehints = "description"
html_theme = "sphinx_rtd_theme"
