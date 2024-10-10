import sys
from dataclasses import asdict
from pathlib import Path

from sphinxawesome_theme import ThemeOptions
from sphinxawesome_theme.postprocess import Icons

sys.path.insert(0, str(Path(__file__).parent / "src"))

nitpicky = True
project = "python-erc7730"
copyright = "2024, Ledger"
author = "Ledger"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.githubpages",
    "sphinx.ext.viewcode",
    "sphinx.ext.linkcode",
    "sphinx.ext.autosummary",
    "sphinx.ext.graphviz",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.autosummary",
    "sphinxcontrib.mermaid",
    "sphinxcontrib.typer",
    "sphinxcontrib.apidoc",
    "sphinxcontrib.autodoc_pydantic",
    "myst_parser",
    "sphinx_github_style",
    "sphinx_issues",
    "sphinx_design",
]
myst_enable_extensions = [
    "fieldlist",
    "linkify",
    "substitution",
]
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
templates_path = ["templates"]
issues_github_path = "LedgerHQ/python-erc7730"
linkcode_url = "LedgerHQ/python-erc7730"
apidoc_module_dir = "../src"
apidoc_output_dir = "build/reference"
apidoc_separate_modules = True
autosummary_generate = True
autodoc_pydantic_model_show_json = False
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_validator_members = False
autodoc_pydantic_model_validator_summary = False
autodoc_pydantic_model_field_summary = False
autodoc_pydantic_model_hide_paramlist = True
autodoc_pydantic_model_hide_reused_validator = True
html_theme = "sphinxawesome_theme"
html_static_path = ["static"]
html_css_files = ["custom.css", "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.1.1/css/all.min.css"]
html_favicon = "static/ledger-icon.png"
html_logo = "static/ledger-icon.png"
html_title = "python-erc7730"
html_show_sphinx = False
html_permalinks_icon = Icons.permalinks_icon
html_context = {"default_mode": "light"}
html_theme_options = asdict(
    ThemeOptions(
        show_prev_next=False,
        show_scrolltop=True,
        show_breadcrumbs=True,
        breadcrumbs_separator=">",
    )
)
pygments_style = "friendly"
pygments_style_dark = "nord-darker"
todo_include_todos = True
mathjax3_config = {"displayAlign": "left"}
mermaid_version = "11.3.0"
