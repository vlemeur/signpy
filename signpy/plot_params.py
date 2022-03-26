"""This module provides default values for plotting parameters that you can use to produce nice graphs.
"""
LARGE = 20
SMALL = 15

PARAMS = {
    "figure.autolayout": True,
    "figure.figsize": (25, 12.5),
    "axes.titlesize": LARGE,
    "axes.labelsize": LARGE,
    "xtick.labelsize": LARGE,
    "ytick.labelsize": LARGE,
    "legend.fontsize": LARGE,
    "legend.title_fontsize": LARGE,
}

WEBAPP_PARAMS = {
    "figure.autolayout": True,
    "figure.figsize": (10, 6),
    "axes.titlesize": SMALL,
    "axes.labelsize": SMALL,
    "xtick.labelsize": SMALL,
    "ytick.labelsize": SMALL,
    "legend.fontsize": SMALL,
    "legend.title_fontsize": SMALL,
}