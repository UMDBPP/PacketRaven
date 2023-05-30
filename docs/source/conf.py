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

# -- Path setup --------------------------------------------------------------
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
extensions = [
    "sphinx_mdinclude",
    "sphinx_rtd_theme"
]

# -- Options for HTML output -------------------------------------------------
html_theme = "sphinx_rtd_theme"

# -- Extension configuration -------------------------------------------------
source_suffix = [".rst", ".md"]
