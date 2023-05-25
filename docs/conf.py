# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
import os
from os import PathLike
from pathlib import Path
from datetime import datetime
import sys

try:
    import tomllib
except ImportError:
    import tomli as tomllib

def repository_root(path: PathLike = None) -> Path:
    if path is None:
        path = __file__
    if not isinstance(path, Path):
        path = Path(path)
    if path.is_file():
        path = path.parent
    if ".git" in (child.name for child in path.iterdir()) or path == path.parent:
        return path
    else:
        return repository_root(path.parent)


ROOT = repository_root()

sys.path.insert(0, str(ROOT))

# -- Project information -----------------------------------------------------
with open(ROOT / "Cargo.toml", "rb") as configuration_file:
    metadata = tomllib.load(configuration_file)["package"]

project = metadata["name"]
author = ", ".join(metadata["authors"])
copyright = ", ".join(f"{datetime.now():%Y-%m-%d}, {author}" for author in metadata["authors"])
version = metadata["version"]
release = version

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "m2r2",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

root_doc = "source/index"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "alabaster"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

# -- Extension configuration -------------------------------------------------
source_suffix = [".rst", ".md"]
