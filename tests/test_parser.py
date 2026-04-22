"""Tests for parser dispatch across Unity and Unreal docsets."""

from __future__ import annotations

import json

import pytest
from bs4 import BeautifulSoup

from server.docsets import DocsetSpec
from server.models import ApiRecord, GuideRecord
from server.parser import classify_page, discover_html_files, guide_type_for, parse_html_file


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

UNREAL_CPP_CLASS_HTML = """\
<!DOCTYPE html>
<html>
<head>
    <title>UCableComponent | Unreal Engine Documentation</title>
    <meta name="description" content="Component that allows you to specify custom triangle mesh geometry" />
</head>
<body>
    <div id="pagecontainer">
        <div class="hero">
            <div class="info">
                <div id="pageTitle"><h1 id="H1TitleId">UCableComponent</h1></div>
                <h2>Component that allows you to specify custom triangle mesh geometry</h2>
            </div>
        </div>
        <div id="maincol">
            <div class="heading expanded"><p>Inheritance Hierarchy</p></div>
            <div id="hierarchy">
                <div class="hierarchy">
                    <div class="hierarchy-label-cell"><p>UObject</p></div>
                    <div class="hierarchy-label-cell"><p>USceneComponent</p></div>
                    <div class="hierarchy-label-cell"><p>UCableComponent</p></div>
                </div>
            </div>
            <div class="heading expanded"><p>References</p></div>
            <div id="references">
                <div class="member-list">
                    <table cellspacing="0">
                        <tr class="normal-row"><td class="name-cell"><p>Module</p></td><td class="desc-cell"><p>CableComponent</p></td></tr>
                        <tr class="normal-row"><td class="name-cell"><p>Header</p></td><td class="desc-cell"><p>/Engine/Plugins/Runtime/CableComponent/Source/CableComponent/Classes/CableComponent.h</p></td></tr>
                        <tr class="normal-row"><td class="name-cell"><p>Include</p></td><td class="desc-cell"><p>#include "CableComponent.h"</p></td></tr>
                    </table>
                </div>
            </div>
            <div class="heading expanded"><p>Syntax</p></div>
            <div id="syntax">
                <div class="simplecode_api"><p>UCLASS() class UCableComponent : public UMeshComponent</p></div>
            </div>
            <div class="heading expanded"><p>Remarks</p></div>
            <div id="description">
                <p>Component that allows you to specify custom triangle mesh geometry</p>
            </div>
            <div class="heading expanded"><p>Variables</p></div>
            <div id="variables"></div>
            <div class="heading expanded"><p>Functions</p></div>
            <div id="functions_0"></div>
        </div>
    </div>
</body>
</html>
"""

UNREAL_CPP_METHOD_HTML = """\
<!DOCTYPE html>
<html>
<head>
    <title>UCableComponent::SetAttachEndTo | Unreal Engine Documentation</title>
    <meta name="description" content="Attaches the end of the cable to a specific Component within an Actor" />
</head>
<body>
    <div id="pagecontainer">
        <div class="hero">
            <div class="info">
                <div id="pageTitle"><h1 id="H1TitleId">UCableComponent::SetAttachEndTo</h1></div>
                <h2>Attaches the end of the cable to a specific Component within an Actor</h2>
            </div>
        </div>
        <div id="maincol">
            <div class="heading expanded"><p>References</p></div>
            <div id="references">
                <div class="member-list">
                    <table cellspacing="0">
                        <tr class="normal-row"><td class="name-cell"><p>Module</p></td><td class="desc-cell"><p>CableComponent</p></td></tr>
                        <tr class="normal-row"><td class="name-cell"><p>Header</p></td><td class="desc-cell"><p>/Engine/Plugins/Runtime/CableComponent/Source/CableComponent/Classes/CableComponent.h</p></td></tr>
                        <tr class="normal-row"><td class="name-cell"><p>Include</p></td><td class="desc-cell"><p>#include "CableComponent.h"</p></td></tr>
                        <tr class="normal-row"><td class="name-cell"><p>Source</p></td><td class="desc-cell"><p>/Engine/Plugins/Runtime/CableComponent/Source/CableComponent/Private/CableComponent.cpp</p></td></tr>
                    </table>
                </div>
            </div>
            <div class="heading expanded"><p>Syntax</p></div>
            <div id="syntax">
                <div class="simplecode_api">
                    <p>UFUNCTION(BlueprintCallable, Category="Cable") void SetAttachEndTo ( AActor * Actor, FName ComponentProperty, FName SocketName )</p>
                </div>
            </div>
            <div class="heading expanded"><p>Remarks</p></div>
            <div id="description">
                <p>Attaches the end of the cable to a specific Component within an Actor</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

UNREAL_CPP_GUIDE_HTML = """\
<!DOCTYPE html>
<html>
<head>
    <title>Getting started with the Unreal Engine API | Unreal Engine Documentation</title>
    <meta name="description" content="Getting started with the Unreal Engine API" />
</head>
<body>
    <div id="pagecontainer">
        <div class="hero">
            <div class="info">
                <div id="pageTitle"><h1 id="H1TitleId">Getting started with the Unreal Engine API</h1></div>
                <h2>Getting started with the Unreal Engine API</h2>
            </div>
        </div>
        <div id="maincol">
            <h2 id="orientation">Orientation</h2>
            <p>Games and tools are targets built by UnrealBuildTool.</p>
            <h2 id="core">Core</h2>
            <p>The Core module provides common framework features.</p>
        </div>
    </div>
</body>
</html>
"""

UNREAL_BLUEPRINT_HTML = """\
<!DOCTYPE html>
<html>
<head>
    <title>Cast To MovieSceneActorReferenceSection | Unreal Engine Documentation</title>
    <meta name="description" content="Cast To MovieSceneActorReferenceSection" />
</head>
<body>
    <div id="pagecontainer">
        <div class="hero">
            <div class="info">
                <div id="pageTitle"><h1 id="H1TitleId">Cast To MovieSceneActorReferenceSection</h1></div>
                <h2>Cast To MovieSceneActorReferenceSection</h2>
            </div>
        </div>
        <div id="maincol">
            <p>K2Node Dynamic Cast</p>
            <div class="heading expanded"><p>Inputs</p></div>
            <div id="inputs">
                <div class="member-list">
                    <table cellspacing="0">
                        <tr id="Object" class="normal-row">
                            <td class="icon-cell"></td>
                            <td class="name-cell"><a>Object</a><div class="name-cell-arguments">Object Wildcard</div></td>
                            <td class="desc-cell"></td>
                        </tr>
                    </table>
                </div>
            </div>
            <div class="heading expanded"><p>Outputs</p></div>
            <div id="outputs">
                <div class="member-list">
                    <table cellspacing="0">
                        <tr id="As_Movie" class="normal-row">
                            <td class="icon-cell"></td>
                            <td class="name-cell"><a>As Movie Scene Actor Reference Section</a><div class="name-cell-arguments">Movie Scene Actor Reference Section Object Reference</div></td>
                            <td class="desc-cell"></td>
                        </tr>
                    </table>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


@pytest.fixture
def unity_docset(tmp_path) -> DocsetSpec:
    return DocsetSpec(
        engine="unity",
        version="current",
        docset="reference",
        label="Unity Reference",
        docs_root=tmp_path,
        db_path=tmp_path / "unity.db",
        parser_kind="unity_html",
        skip_dirs=("StaticFiles",),
    )


@pytest.fixture
def unreal_cpp_docset(tmp_path) -> DocsetSpec:
    root = tmp_path / "cpp"
    root.mkdir()
    return DocsetSpec(
        engine="unreal",
        version="4.26",
        docset="cpp-api",
        label="Unreal C++ API",
        docs_root=root,
        db_path=tmp_path / "cpp.db",
        parser_kind="unreal_cpp_html",
    )


@pytest.fixture
def unreal_blueprint_docset(tmp_path) -> DocsetSpec:
    root = tmp_path / "blueprint"
    root.mkdir()
    return DocsetSpec(
        engine="unreal",
        version="4.26",
        docset="blueprint-api",
        label="Unreal Blueprint API",
        docs_root=root,
        db_path=tmp_path / "blueprint.db",
        parser_kind="unreal_blueprint_html",
    )


class TestUnityHelpers:
    def test_scriptref_marker_wins(self):
        soup = BeautifulSoup('<div id="DocsAnalyticsData" data-pagetype="scriptref"></div>', "lxml")
        assert classify_page("en/Manual/foo.html", soup) == "api"

    def test_manual_marker_wins(self):
        soup = BeautifulSoup('<div id="DocsAnalyticsData" data-pagetype="manual"></div>', "lxml")
        assert classify_page("en/ScriptReference/foo.html", soup) == "guide"

    def test_guide_type(self):
        assert guide_type_for("en/Manual/class-Transform.html", "Transforms") == "reference"
        assert guide_type_for("en/Manual/tutorial-foo.html", "Foo") == "tutorial"


class TestDiscovery:
    def test_unity_discovery_skips_static(self, unity_docset):
        sr = unity_docset.docs_root / "en" / "ScriptReference"
        sr.mkdir(parents=True)
        (sr / "Transform.Rotate.html").write_text(SCRIPTREF_METHOD_HTML, encoding="utf-8")

        manual = unity_docset.docs_root / "en" / "Manual"
        manual.mkdir(parents=True)
        (manual / "class-Transform.html").write_text(MANUAL_HTML, encoding="utf-8")

        skipped = unity_docset.docs_root / "en" / "StaticFiles"
        skipped.mkdir(parents=True)
        (skipped / "skip.html").write_text("<html><body>skip</body></html>", encoding="utf-8")

        names = {path.name for path in discover_html_files(unity_docset)}
        assert names == {"Transform.Rotate.html", "class-Transform.html"}


class TestUnityParser:
    def test_scriptref_method_page(self, unity_docset):
        target = unity_docset.docs_root / "en" / "ScriptReference"
        target.mkdir(parents=True)
        html_path = target / "Transform.Rotate.html"
        html_path.write_text(SCRIPTREF_METHOD_HTML, encoding="utf-8")

        record = parse_html_file(html_path, unity_docset)
        assert isinstance(record, ApiRecord)
        assert record.symbol_name == "Transform.Rotate"
        assert record.class_name == "Transform"
        assert record.member_type == "method"
        assert json.loads(record.parameters_json)[0]["name"] == "eulers"

    def test_manual_page(self, unity_docset):
        target = unity_docset.docs_root / "en" / "Manual"
        target.mkdir(parents=True)
        html_path = target / "class-Transform.html"
        html_path.write_text(MANUAL_HTML, encoding="utf-8")

        record = parse_html_file(html_path, unity_docset)
        assert isinstance(record, GuideRecord)
        assert record.guide_type == "reference"
        assert record.topic_path == "Manual"
        assert json.loads(record.key_topics_json) == ["The Transform Component", "Parenting"]


class TestUnrealCppParser:
    def test_class_page(self, unreal_cpp_docset):
        target = unreal_cpp_docset.docs_root / "en-US" / "API" / "Plugins" / "CableComponent" / "UCableComponent"
        target.mkdir(parents=True)
        html_path = target / "index.html"
        html_path.write_text(UNREAL_CPP_CLASS_HTML, encoding="utf-8")

        record = parse_html_file(html_path, unreal_cpp_docset)
        assert isinstance(record, ApiRecord)
        assert record.symbol_name == "UCableComponent"
        assert record.member_type == "class"
        assert record.module_name == "CableComponent"
        assert record.header_path.endswith("CableComponent.h")
        assert json.loads(record.inheritance_json)[-1] == "UCableComponent"

    def test_method_page(self, unreal_cpp_docset):
        target = (
            unreal_cpp_docset.docs_root
            / "en-US"
            / "API"
            / "Plugins"
            / "CableComponent"
            / "UCableComponent"
            / "SetAttachEndTo"
        )
        target.mkdir(parents=True)
        html_path = target / "index.html"
        html_path.write_text(UNREAL_CPP_METHOD_HTML, encoding="utf-8")

        record = parse_html_file(html_path, unreal_cpp_docset)
        assert isinstance(record, ApiRecord)
        assert record.symbol_name == "UCableComponent::SetAttachEndTo"
        assert record.class_name == "UCableComponent"
        assert record.member_type == "method"
        assert record.source_path.endswith("CableComponent.cpp")
        params = json.loads(record.parameters_json)
        assert [item["name"] for item in params] == ["Actor", "ComponentProperty", "SocketName"]
        assert record.returns_text == "void"

    def test_quickstart_page(self, unreal_cpp_docset):
        target = unreal_cpp_docset.docs_root / "en-US" / "API" / "QuickStart"
        target.mkdir(parents=True)
        html_path = target / "index.html"
        html_path.write_text(UNREAL_CPP_GUIDE_HTML, encoding="utf-8")

        record = parse_html_file(html_path, unreal_cpp_docset)
        assert isinstance(record, GuideRecord)
        assert record.guide_type == "quickstart"
        assert "Orientation" in json.loads(record.key_topics_json)


class TestUnrealBlueprintParser:
    def test_blueprint_node_page(self, unreal_blueprint_docset):
        target = (
            unreal_blueprint_docset.docs_root
            / "en-US"
            / "BlueprintAPI"
            / "Utilities"
            / "Casting"
            / "CastToMovieSceneActorReferenceSe-"
        )
        target.mkdir(parents=True)
        html_path = target / "index.html"
        html_path.write_text(UNREAL_BLUEPRINT_HTML, encoding="utf-8")

        record = parse_html_file(html_path, unreal_blueprint_docset)
        assert isinstance(record, ApiRecord)
        assert record.member_type == "blueprint_node"
        assert record.topic_path == "Utilities/Casting"
        assert record.signature == "K2Node Dynamic Cast"
        assert json.loads(record.inputs_json)[0]["name"] == "Object"
        assert "Movie Scene Actor Reference Section" in json.loads(record.outputs_json)[0]["name"]
