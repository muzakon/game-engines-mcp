"""Parser adapters for different documentation formats."""

from .unreal import parse_blueprint_html, parse_unreal_cpp_html
from .unity import classify_page, guide_type_for, parse_unity_html

__all__ = [
    "classify_page",
    "guide_type_for",
    "parse_blueprint_html",
    "parse_unity_html",
    "parse_unreal_cpp_html",
]
