# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import datetime
import os
import pathlib
import sys
import tomlkit

sys.path.insert(0, os.path.abspath("."))

# ON_RTD is whether we are on readthedocs.org
ON_RTD = os.environ.get("READTHEDOCS", None) == "True"
DOCS_PATH = pathlib.Path(__file__).parent.parent

# -- Project information -----------------------------------------------------

project = "tartufo"
author = "GoDaddy.com, LLC"

copyright_year = "2019"
now = datetime.datetime.now()
if now.year > 2019:
    copyright_year = "%s-%s" % (copyright_year, now.year)
copyright = "%s, GoDaddy.com, LLC" % copyright_year

with open(str(DOCS_PATH.parent / "pyproject.toml"), encoding="utf-8") as filename:
    version = tomlkit.loads(filename.read())["tool"]["poetry"]["version"]  # type: ignore
release = version

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "recommonmark",
    "sphinx_click",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
]
autodoc_typehints = "description"  # show type hints in doc body instead of signature
autoclass_content = "both"  # get docstring from class level and init simultaneously

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
# exclude_patterns = []

pygments_style = "sphinx"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = "alabaster"
if not ON_RTD:
    import sphinx_rtd_theme

    html_theme = "sphinx_rtd_theme"
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_logo = "_static/img/tartufo.png"

# If false, no module index is generated.
html_use_modindex = False

# If false, no index is generated.
html_use_index = False

# Set up linking to external Sphinx documetation
intersphinx_mapping = {
    "click": ("https://click.palletsprojects.com/en/7.x/", None),
    "python": ("https://docs.python.org/3", None),
    "pygit2": ("https://pygit2.readthedocs.io/en/stable/", None),
}
