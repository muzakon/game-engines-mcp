"""Tests for multi-docset search and retrieval logic."""

from __future__ import annotations

import json

import pytest

from src.db import get_connection, init_db, upsert_api_record, upsert_guide_record
from src.docsets import clear_docset_cache, DocsetSpec
from src.models import ApiRecord, GuideRecord
from src.search import (
    IndexNotReadyError,
    answer_question,
    get_doc_page,
    get_stats,
    get_symbol_reference,
    search_api,
    search_guides,
)


@pytest.fixture
def registered_indexes(tmp_path, monkeypatch):
    unity_spec = DocsetSpec(
        engine="unity",
        version="current",
        docset="reference",
        label="Unity Reference",
        docs_root=tmp_path / "Documentation",
        db_path=tmp_path / "data" / "unity" / "current" / "reference.db",
        parser_kind="unity_html",
    )
    unreal_cpp_spec = DocsetSpec(
        engine="unreal",
        version="4.26",
        docset="cpp-api",
        label="Unreal Engine 4.26 C++ API",
        docs_root=tmp_path / "DocumentationUE" / "CppAPI-HTML",
        db_path=tmp_path / "data" / "unreal" / "4.26" / "cpp-api.db",
        parser_kind="unreal_cpp_html",
    )
    unreal_blueprint_spec = DocsetSpec(
        engine="unreal",
        version="4.26",
        docset="blueprint-api",
        label="Unreal Engine 4.26 Blueprint API",
        docs_root=tmp_path / "DocumentationUE" / "BlueprintAPI-HTML",
        db_path=tmp_path / "data" / "unreal" / "4.26" / "blueprint-api.db",
        parser_kind="unreal_blueprint_html",
    )
    godot_spec = DocsetSpec(
        engine="godot",
        version="4.6",
        docset="reference",
        label="Godot Engine 4.6 Documentation",
        docs_root=tmp_path / "DocumentationGodot",
        db_path=tmp_path / "data" / "godot" / "4.6" / "reference.db",
        parser_kind="godot_html",
    )

    manifest_path = tmp_path / "docsets.json"
    manifest_path.write_text(
        json.dumps(
            [
                {
                    "engine": unity_spec.engine,
                    "version": unity_spec.version,
                    "docset": unity_spec.docset,
                    "label": unity_spec.label,
                    "docs_root": str(unity_spec.docs_root),
                    "db_path": str(unity_spec.db_path),
                    "parser_kind": unity_spec.parser_kind,
                },
                {
                    "engine": unreal_cpp_spec.engine,
                    "version": unreal_cpp_spec.version,
                    "docset": unreal_cpp_spec.docset,
                    "label": unreal_cpp_spec.label,
                    "docs_root": str(unreal_cpp_spec.docs_root),
                    "db_path": str(unreal_cpp_spec.db_path),
                    "parser_kind": unreal_cpp_spec.parser_kind,
                },
                {
                    "engine": unreal_blueprint_spec.engine,
                    "version": unreal_blueprint_spec.version,
                    "docset": unreal_blueprint_spec.docset,
                    "label": unreal_blueprint_spec.label,
                    "docs_root": str(unreal_blueprint_spec.docs_root),
                    "db_path": str(unreal_blueprint_spec.db_path),
                    "parser_kind": unreal_blueprint_spec.parser_kind,
                },
                {
                    "engine": godot_spec.engine,
                    "version": godot_spec.version,
                    "docset": godot_spec.docset,
                    "label": godot_spec.label,
                    "docs_root": str(godot_spec.docs_root),
                    "db_path": str(godot_spec.db_path),
                    "parser_kind": godot_spec.parser_kind,
                },
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("UNITY_MCP_DOCSETS_MANIFEST", str(manifest_path))
    clear_docset_cache()

    for spec in (unity_spec, unreal_cpp_spec, unreal_blueprint_spec, godot_spec):
        spec.docs_root.mkdir(parents=True, exist_ok=True)
        conn = get_connection(spec.db_path)
        init_db(conn, spec)
        conn.close()

    conn = get_connection(unity_spec.db_path)
    for record in (
        ApiRecord(
            title="Transform",
            relative_path="en/ScriptReference/Transform.html",
            symbol_name="Transform",
            class_name="Transform",
            namespace="UnityEngine",
            member_type="class",
            summary="Position, rotation and scale of an object.",
            topic_path="ScriptReference",
            content_text="Position, rotation and scale of an object. Every object in a Scene has a Transform.",
        ),
        ApiRecord(
            title="Transform.Rotate",
            relative_path="en/ScriptReference/Transform.Rotate.html",
            symbol_name="Transform.Rotate",
            class_name="Transform",
            namespace="UnityEngine",
            member_type="method",
            signature="public void Rotate(Vector3 eulers);",
            parameters_json=json.dumps([{"name": "eulers", "description": "rotation"}]),
            returns_text="void",
            summary="Use Transform.Rotate to rotate GameObjects.",
            topic_path="ScriptReference",
            content_text="Use Transform.Rotate to rotate GameObjects in a variety of ways.",
        ),
    ):
        upsert_api_record(conn, record)
    for record in (
        GuideRecord(
            title="How to rotate objects",
            relative_path="en/Manual/rotate-objects.html",
            guide_type="manual",
            topic_path="Manual",
            summary="Rotate objects in the editor or via scripts.",
            content_text="You can rotate a cube using Transform.Rotate or by editing the rotation field.",
            key_topics_json=json.dumps(["Rotating in the editor", "Rotating via scripts"]),
        ),
    ):
        upsert_guide_record(conn, record)
    conn.commit()
    conn.close()

    conn = get_connection(unreal_cpp_spec.db_path)
    for record in (
        ApiRecord(
            title="UCableComponent",
            relative_path="en-US/API/Plugins/CableComponent/UCableComponent/index.html",
            symbol_name="UCableComponent",
            class_name="UCableComponent",
            module_name="CableComponent",
            member_type="class",
            signature="UCLASS() class UCableComponent : public UMeshComponent",
            summary="Component that allows you to specify custom triangle mesh geometry.",
            remarks="Component that allows you to specify custom triangle mesh geometry.",
            header_path="/Engine/Plugins/Runtime/CableComponent/Source/CableComponent/Classes/CableComponent.h",
            include_text='#include "CableComponent.h"',
            topic_path="Plugins/CableComponent",
            content_text="UCableComponent represents a cable rendering component.",
        ),
        ApiRecord(
            title="UCableComponent::SetAttachEndTo",
            relative_path="en-US/API/Plugins/CableComponent/UCableComponent/SetAttachEndTo/index.html",
            symbol_name="UCableComponent::SetAttachEndTo",
            class_name="UCableComponent",
            module_name="CableComponent",
            member_type="method",
            signature="void SetAttachEndTo ( AActor * Actor, FName ComponentProperty, FName SocketName )",
            parameters_json=json.dumps(
                [
                    {"name": "Actor", "description": "AActor *"},
                    {"name": "ComponentProperty", "description": "FName"},
                    {"name": "SocketName", "description": "FName"},
                ]
            ),
            returns_text="void",
            summary="Attaches the end of the cable to a specific Component within an Actor.",
            header_path="/Engine/Plugins/Runtime/CableComponent/Source/CableComponent/Classes/CableComponent.h",
            include_text='#include "CableComponent.h"',
            source_path="/Engine/Plugins/Runtime/CableComponent/Source/CableComponent/Private/CableComponent.cpp",
            topic_path="Plugins/CableComponent/UCableComponent",
            content_text="SetAttachEndTo attaches the end of the cable to a specific component.",
        ),
    ):
        upsert_api_record(conn, record)
    upsert_guide_record(
        conn,
        GuideRecord(
            title="Getting started with the Unreal Engine API",
            relative_path="en-US/API/QuickStart/index.html",
            guide_type="quickstart",
            summary="Getting started with the Unreal Engine API",
            topic_path="",
            content_text="Games, programs and the Unreal Editor are all targets built by UnrealBuildTool.",
            key_topics_json=json.dumps(["Orientation", "Core"]),
        ),
    )
    conn.commit()
    conn.close()

    conn = get_connection(unreal_blueprint_spec.db_path)
    upsert_api_record(
        conn,
        ApiRecord(
            title="Cast To MovieSceneActorReferenceSection",
            relative_path="en-US/BlueprintAPI/Utilities/Casting/CastToMovieSceneActorReferenceSe-/index.html",
            symbol_name="Cast To MovieSceneActorReferenceSection",
            module_name="Utilities",
            member_type="blueprint_node",
            signature="K2Node Dynamic Cast",
            topic_path="Utilities/Casting",
            inputs_json=json.dumps([{"name": "Object", "type": "Object Wildcard", "description": ""}]),
            outputs_json=json.dumps(
                [
                    {
                        "name": "As Movie Scene Actor Reference Section",
                        "type": "Movie Scene Actor Reference Section Object Reference",
                        "description": "",
                    }
                ]
            ),
            summary="Cast To MovieSceneActorReferenceSection",
            content_text="Blueprint node used to cast to MovieSceneActorReferenceSection.",
        ),
    )
    conn.commit()
    conn.close()

    conn = get_connection(godot_spec.db_path)
    for record in (
        ApiRecord(
            title="Node",
            relative_path="classes/class_node.html",
            symbol_name="Node",
            class_name="Node",
            member_type="class",
            signature="Inherits: Object",
            summary="Base class for all scene objects.",
            remarks="Nodes are Godot's building blocks.",
            topic_path="classes",
            inheritance_json=json.dumps(["Node", "Object"]),
            content_text="Node is the base class for all scene objects.",
        ),
        ApiRecord(
            title="Node.add_child",
            relative_path="classes/class_node.html#class-node-method-add-child",
            symbol_name="Node.add_child",
            class_name="Node",
            member_type="method",
            signature="void add_child(node: Node, force_readable_name: bool = false)",
            parameters_json=json.dumps(
                [
                    {"name": "node", "description": "Node"},
                    {"name": "force_readable_name", "description": "bool = false"},
                ]
            ),
            returns_text="void",
            summary="Adds a child node.",
            remarks="Adds a child node below this node in the scene tree.",
            topic_path="classes/Node",
            content_text="Adds a child node below this node in the scene tree.",
        ),
        ApiRecord(
            title="Node.ready",
            relative_path="classes/class_node.html#class-node-signal-ready",
            symbol_name="Node.ready",
            class_name="Node",
            member_type="signal",
            signature="ready()",
            summary="Emitted when the node is considered ready.",
            remarks="Emitted when the node is considered ready.",
            topic_path="classes/Node",
            content_text="Emitted when the node is considered ready.",
        ),
    ):
        upsert_api_record(conn, record)
    upsert_guide_record(
        conn,
        GuideRecord(
            title="Introduction to Godot",
            relative_path="getting_started/introduction/introduction_to_godot.html",
            guide_type="introduction",
            topic_path="getting_started/introduction",
            summary="This article helps you decide whether Godot is a good fit.",
            content_text="Godot is a general-purpose 2D and 3D game engine.",
            key_topics_json=json.dumps(["What is Godot?", "Programming languages"]),
        ),
    )
    conn.commit()
    conn.close()

    yield {
        "unity": unity_spec,
        "unreal_cpp": unreal_cpp_spec,
        "unreal_blueprint": unreal_blueprint_spec,
        "godot": godot_spec,
    }

    clear_docset_cache()


class TestSearchApi:
    def test_defaults_to_unity(self, registered_indexes):
        results = search_api("Transform")
        assert results
        assert results[0].engine == "unity"
        assert results[0].symbol_name == "Transform"

    def test_searches_unreal_cpp(self, registered_indexes):
        results = search_api(
            "UCableComponent::SetAttachEndTo",
            engine="unreal",
            version="4.26",
            docset="cpp-api",
        )
        assert results
        assert results[0].docset == "cpp-api"
        assert results[0].module_name == "CableComponent"

    def test_searches_across_unreal_docsets(self, registered_indexes):
        results = search_api("Cast To", engine="unreal", version="4.26")
        assert results
        assert any(result.docset == "blueprint-api" for result in results)

    def test_member_filter(self, registered_indexes):
        results = search_api("UCableComponent", engine="unreal", version="4.26", member_type="method")
        assert results
        assert all(result.member_type == "method" for result in results)

    def test_searches_godot_member(self, registered_indexes):
        results = search_api("Node.add_child", engine="godot", version="4.6")
        assert results
        assert results[0].symbol_name == "Node.add_child"

    def test_searches_godot_bare_member_name(self, registered_indexes):
        results = search_api("add_child", engine="godot", version="4.6")
        assert results
        assert any(result.symbol_name == "Node.add_child" for result in results)


class TestSearchGuides:
    def test_unity_guides(self, registered_indexes):
        results = search_guides("how to rotate")
        assert results
        assert results[0].engine == "unity"

    def test_unreal_quickstart(self, registered_indexes):
        results = search_guides("getting started", engine="unreal", version="4.26", docset="cpp-api")
        assert results
        assert results[0].guide_type == "quickstart"

    def test_godot_guides(self, registered_indexes):
        results = search_guides("introduction to godot", engine="godot", version="4.6")
        assert results
        assert results[0].guide_type == "introduction"


class TestGetSymbolReference:
    def test_unreal_cpp_symbol(self, registered_indexes):
        ref = get_symbol_reference(
            "UCableComponent::SetAttachEndTo",
            engine="unreal",
            version="4.26",
            docset="cpp-api",
        )
        assert ref is not None
        assert ref.docset == "cpp-api"
        assert ref.header_path.endswith("CableComponent.h")
        assert ref.module_name == "CableComponent"

    def test_blueprint_node(self, registered_indexes):
        ref = get_symbol_reference(
            "Cast To MovieSceneActorReferenceSection",
            engine="unreal",
            version="4.26",
            docset="blueprint-api",
        )
        assert ref is not None
        assert ref.member_type == "blueprint_node"
        assert json.loads(ref.inputs_json)[0]["name"] == "Object"

    def test_godot_member_symbol(self, registered_indexes):
        ref = get_symbol_reference(
            "Node.add_child",
            engine="godot",
            version="4.6",
            docset="reference",
        )
        assert ref is not None
        assert ref.member_type == "method"
        assert ref.returns_text == "void"
        assert json.loads(ref.parameters_json)[0]["name"] == "node"


class TestGetDocPage:
    def test_doc_page_lookup(self, registered_indexes):
        payload = get_doc_page("QuickStart/index.html", engine="unreal", version="4.26")
        assert payload is not None
        assert payload["category"] == "guide"
        assert payload["ref"].docset == "cpp-api"


class TestAnswerQuestion:
    def test_returns_both_sides(self, registered_indexes):
        bundle = answer_question("rotate", limit_per_index=5)
        assert "api" in bundle and "guide" in bundle
        assert any(result.category == "api" for result in bundle["api"])
        assert any(result.category == "guide" for result in bundle["guide"])


class TestStats:
    def test_unreal_stats(self, registered_indexes):
        stats = get_stats(engine="unreal", version="4.26")
        assert stats["api_pages"] == 3
        assert stats["guide_pages"] == 1
        assert len(stats["docsets"]) == 2
        assert stats["api_member_breakdown"].get("blueprint_node", 0) == 1

    def test_godot_stats(self, registered_indexes):
        stats = get_stats(engine="godot", version="4.6")
        assert stats["api_pages"] == 3
        assert stats["guide_pages"] == 1
        assert len(stats["docsets"]) == 1
        assert stats["api_member_breakdown"].get("method", 0) == 1


class TestErrors:
    def test_raises_when_index_missing(self, tmp_path, monkeypatch):
        manifest_path = tmp_path / "docsets.json"
        manifest_path.write_text(
            json.dumps(
                [
                    {
                        "engine": "unreal",
                        "version": "4.26",
                        "docset": "cpp-api",
                        "label": "Unreal Engine 4.26 C++ API",
                        "docs_root": str(tmp_path / "docs"),
                        "db_path": str(tmp_path / "missing.db"),
                        "parser_kind": "unreal_cpp_html",
                    }
                ]
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("UNITY_MCP_DOCSETS_MANIFEST", str(manifest_path))
        clear_docset_cache()

        with pytest.raises(IndexNotReadyError):
            search_api("UCableComponent", engine="unreal", version="4.26")

        clear_docset_cache()
