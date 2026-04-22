"""Tests for the HTML parser and classifier."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from unity_mcp.models import ApiRecord, GuideRecord
from unity_mcp.parser import (
    classify_page,
    discover_html_files,
    guide_type_for,
    parse_html_file,
)


# --- Sample HTML fixtures ---

SCRIPTREF_METHOD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><title>Unity - Scripting API: Transform.Rotate</title></head>
<body>
    <div id="DocsAnalyticsData" data-pagetype="scriptref"></div>
    <div id="content-wrap"><div class="content"><div class="section">
        <h1 class="heading inherit"><a href="Transform.html">Transform</a>.Rotate</h1>
        <div class="subsection"><h3>Description</h3>
            <p>Use Transform.Rotate to rotate GameObjects in a variety of ways.</p>
        </div>
        <div class="subsection"><div class="signature"><div class="signature-CS sig-block">
            <h2>Declaration</h2>public void <span>Rotate</span>(Vector3 eulers);
        </div></div></div>
        <div class="subsection"><h3>Parameters</h3><table class="list">
            <thead><tr><th>Parameter</th><th>Description</th></tr></thead>
            <tr><td>eulers</td><td>The rotation to apply in euler angles.</td></tr>
        </table></div>
        <div class="subsection"><h3>Returns</h3><p>void</p></div>
    </div></div></div>
</body></html>
"""

SCRIPTREF_CLASS_HTML = """\
<!DOCTYPE html>
<html><head><title>Unity - Scripting API: Rigidbody</title></head>
<body>
    <div id="DocsAnalyticsData" data-pagetype="scriptref"></div>
    <div id="content-wrap"><div class="section">
        <h1>Rigidbody</h1>
        <p class="cl mb0 left mr10">class in UnityEngine</p>
        <div class="subsection"><h3>Description</h3>
            <p>Control of an object's position through physics simulation.</p>
        </div>
    </div></div>
</body></html>
"""

SCRIPTREF_PROPERTY_HTML = """\
<!DOCTYPE html>
<html><head><title>Unity - Scripting API: Collider2D.isTrigger</title></head>
<body>
    <div id="DocsAnalyticsData" data-pagetype="scriptref"></div>
    <div id="content-wrap"><div class="section">
        <h1><a href="Collider2D.html">Collider2D</a>.isTrigger</h1>
        <div class="subsection"><h3>Description</h3>
            <p>Indicates whether the collider acts as a trigger.</p>
        </div>
        <div class="subsection"><div class="signature"><div class="sig-block">
            public bool <span>isTrigger</span>;
        </div></div></div>
    </div></div>
</body></html>
"""

MANUAL_HTML = """\
<!DOCTYPE html>
<html><head><title>Unity - Manual: Transforms</title></head>
<body>
    <div id="DocsAnalyticsData" data-pagetype="manual"></div>
    <div id="content-wrap"><div class="section">
        <h1>Transforms</h1>
        <p>The Transform stores a GameObject's Position, Rotation, Scale and parenting state.</p>
        <h2>The Transform Component</h2>
        <p>The Transform component determines the Position, Rotation, and Scale of each GameObject.</p>
        <h2>Parenting</h2>
        <p>Transforms can be parented to other Transforms.</p>
    </div></div>
</body></html>
"""


@pytest.fixture
def tmp_docs(tmp_path):
    sr = tmp_path / "en" / "ScriptReference"
    sr.mkdir(parents=True)
    (sr / "Transform.Rotate.html").write_text(SCRIPTREF_METHOD_HTML, encoding="utf-8")
    (sr / "Rigidbody.html").write_text(SCRIPTREF_CLASS_HTML, encoding="utf-8")
    (sr / "Collider2D-isTrigger.html").write_text(SCRIPTREF_PROPERTY_HTML, encoding="utf-8")

    manual = tmp_path / "en" / "Manual"
    manual.mkdir(parents=True)
    (manual / "class-Transform.html").write_text(MANUAL_HTML, encoding="utf-8")

    skipped = tmp_path / "en" / "StaticFiles"
    skipped.mkdir(parents=True)
    (skipped / "skip.html").write_text("<html><body>skip</body></html>", encoding="utf-8")
    return tmp_path


class TestDiscovery:
    def test_finds_indexable_files(self, tmp_docs):
        names = {p.name for p in discover_html_files(tmp_docs)}
        assert "Transform.Rotate.html" in names
        assert "Rigidbody.html" in names
        assert "class-Transform.html" in names
        assert "Collider2D-isTrigger.html" in names

    def test_skips_static(self, tmp_docs):
        names = {p.name for p in discover_html_files(tmp_docs)}
        assert "skip.html" not in names


class TestClassification:
    def test_scriptref_marker_wins(self):
        soup = BeautifulSoup('<div id="DocsAnalyticsData" data-pagetype="scriptref"></div>', "lxml")
        assert classify_page("en/Manual/foo.html", soup) == "api"

    def test_manual_marker_wins(self):
        soup = BeautifulSoup('<div id="DocsAnalyticsData" data-pagetype="manual"></div>', "lxml")
        assert classify_page("en/ScriptReference/foo.html", soup) == "guide"

    def test_path_fallback_scriptref(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        assert classify_page("en/ScriptReference/Foo.html", soup) == "api"

    def test_path_fallback_manual(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        assert classify_page("en/Manual/foo.html", soup) == "guide"

    def test_signature_signal(self):
        soup = BeautifulSoup('<html><body><div class="signature"></div></body></html>', "lxml")
        assert classify_page("en/Other/foo.html", soup) == "api"


class TestGuideType:
    def test_class_overview_in_manual(self):
        assert guide_type_for("en/Manual/class-Transform.html", "Transforms") == "reference"

    def test_tutorial_path(self):
        assert guide_type_for("en/Manual/tutorial-foo.html", "Foo") == "tutorial"

    def test_overview_title(self):
        assert guide_type_for("en/Manual/foo.html", "Animation Overview") == "overview"

    def test_default_manual(self):
        assert guide_type_for("en/Manual/foo.html", "Some Page") == "manual"


class TestParseHtmlFile:
    def test_method_page(self, tmp_docs):
        rec = parse_html_file(tmp_docs / "en" / "ScriptReference" / "Transform.Rotate.html", tmp_docs)
        assert isinstance(rec, ApiRecord)
        assert rec.symbol_name == "Transform.Rotate"
        assert rec.class_name == "Transform"
        assert rec.member_type == "method"
        assert "Rotate" in rec.signature
        assert rec.parameters_json
        assert "rotate" in rec.summary.lower()

    def test_class_page(self, tmp_docs):
        rec = parse_html_file(tmp_docs / "en" / "ScriptReference" / "Rigidbody.html", tmp_docs)
        assert isinstance(rec, ApiRecord)
        assert rec.symbol_name == "Rigidbody"
        assert rec.class_name == "Rigidbody"
        assert rec.namespace == "UnityEngine"
        assert rec.member_type == "class"

    def test_property_page(self, tmp_docs):
        rec = parse_html_file(
            tmp_docs / "en" / "ScriptReference" / "Collider2D-isTrigger.html", tmp_docs
        )
        assert isinstance(rec, ApiRecord)
        assert rec.symbol_name == "Collider2D.isTrigger"
        assert rec.class_name == "Collider2D"
        # The dash in the filename signals property/field/event.
        assert rec.member_type in {"property", "field", "event"}

    def test_manual_page(self, tmp_docs):
        rec = parse_html_file(tmp_docs / "en" / "Manual" / "class-Transform.html", tmp_docs)
        assert isinstance(rec, GuideRecord)
        assert "Transform" in rec.title
        assert rec.guide_type == "reference"
        assert rec.key_topics_json  # h2 headings should be picked up
        assert "transform" in rec.content_text.lower()

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.html"
        f.write_text("", encoding="utf-8")
        rec = parse_html_file(f, tmp_path)
        assert isinstance(rec, (ApiRecord, GuideRecord))

    def test_malformed_html(self, tmp_path):
        f = tmp_path / "bad.html"
        f.write_text("<html><body><div>unclosed", encoding="utf-8")
        rec = parse_html_file(f, tmp_path)
        assert isinstance(rec, (ApiRecord, GuideRecord))
