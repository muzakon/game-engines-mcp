"""Parser adapters for different documentation formats.

Each parser takes an HTML file path and a docs root, and returns one or
more :class:`~src.models.ApiRecord` / :class:`~src.models.GuideRecord`
instances.
"""

from .godot import parse_godot_html
from .unreal import parse_blueprint_html, parse_unreal_cpp_html
from .unity import classify_page, guide_type_for, parse_unity_html

__all__ = [
    "classify_page",
    "guide_type_for",
    "parse_godot_html",
    "parse_blueprint_html",
    "parse_unity_html",
    "parse_unreal_cpp_html",
]
