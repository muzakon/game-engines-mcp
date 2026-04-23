"""Tests for vector search, navigation, and cross-engine translation."""

from __future__ import annotations

import json
import shutil

import pytest

from src.db import get_connection, init_db, upsert_api_record, upsert_guide_record
from src.docsets import clear_docset_cache, DocsetSpec
from src.models import ApiRecord, GuideRecord
from src.embedding import get_embedding_model
from src.vecsearch import build_vector_index, vector_search_single, _rrf_merge
from src.navigation import (
    browse_class,
    list_class_members,
    browse_inheritance,
    list_classes,
    browse_module,
    get_related_symbols,
)
from src.crossengine import translate_symbol
from src.search import SearchResult


@pytest.fixture
def nav_indexes(tmp_path, monkeypatch):
    """Set up test indexes with richer data for navigation/translation tests."""
    unity_spec = DocsetSpec(
        engine="unity",
        version="6000.4",
        docset="reference",
        label="Unity 6000.4 Reference",
        docs_root=tmp_path / "docs" / "unity",
        db_path=tmp_path / "data" / "unity" / "6000.4" / "reference.db",
        parser_kind="unity_html",
    )
    godot_spec = DocsetSpec(
        engine="godot",
        version="4.6",
        docset="reference",
        label="Godot 4.6 Reference",
        docs_root=tmp_path / "docs" / "godot",
        db_path=tmp_path / "data" / "godot" / "4.6" / "reference.db",
        parser_kind="godot_html",
    )

    manifest_path = tmp_path / "docsets.json"
    manifest_path.write_text(
        json.dumps([
            {
                "engine": unity_spec.engine, "version": unity_spec.version,
                "docset": unity_spec.docset, "label": unity_spec.label,
                "docs_root": str(unity_spec.docs_root), "db_path": str(unity_spec.db_path),
                "parser_kind": unity_spec.parser_kind,
            },
            {
                "engine": godot_spec.engine, "version": godot_spec.version,
                "docset": godot_spec.docset, "label": godot_spec.label,
                "docs_root": str(godot_spec.docs_root), "db_path": str(godot_spec.db_path),
                "parser_kind": godot_spec.parser_kind,
            },
        ]),
        encoding="utf-8",
    )

    monkeypatch.setenv("UNITY_MCP_DOCSETS_MANIFEST", str(manifest_path))
    clear_docset_cache()

    for spec in (unity_spec, godot_spec):
        spec.docs_root.mkdir(parents=True, exist_ok=True)
        conn = get_connection(spec.db_path)
        init_db(conn, spec)
        conn.close()

    # Unity records
    conn = get_connection(unity_spec.db_path)
    upsert_api_record(conn, ApiRecord(
        title="Transform", relative_path="Transform.html",
        symbol_name="Transform", class_name="Transform",
        member_type="class", namespace="UnityEngine",
        summary="Position rotation and scale",
        inheritance_json='["Transform", "Component", "Object"]',
    ))
    upsert_api_record(conn, ApiRecord(
        title="Transform.Rotate", relative_path="Transform.Rotate.html",
        symbol_name="Transform.Rotate", class_name="Transform",
        member_type="method", namespace="UnityEngine",
        summary="Rotates the transform",
        signature="void Rotate(Vector3 eulers)",
    ))
    upsert_api_record(conn, ApiRecord(
        title="Transform.position", relative_path="Transform.position.html",
        symbol_name="Transform.position", class_name="Transform",
        member_type="property", namespace="UnityEngine",
        summary="The position of the transform",
    ))
    upsert_api_record(conn, ApiRecord(
        title="Rigidbody", relative_path="Rigidbody.html",
        symbol_name="Rigidbody", class_name="Rigidbody",
        member_type="class", module_name="Physics",
        summary="Rigidbody for physics simulation",
        inheritance_json='["Rigidbody", "Component", "Object"]',
    ))
    conn.commit()
    conn.close()

    # Godot records
    conn = get_connection(godot_spec.db_path)
    upsert_api_record(conn, ApiRecord(
        title="Node3D", relative_path="class_node3d.html",
        symbol_name="Node3D", class_name="Node3D",
        member_type="class",
        summary="3D game object node",
        inheritance_json='["Node3D", "Node", "Object"]',
    ))
    upsert_api_record(conn, ApiRecord(
        title="Node3D.rotate", relative_path="class_node3d.html#rotate",
        symbol_name="Node3D.rotate", class_name="Node3D",
        member_type="method",
        summary="Rotates the node",
    ))
    upsert_api_record(conn, ApiRecord(
        title="RigidBody3D", relative_path="class_rigidbody3d.html",
        symbol_name="RigidBody3D", class_name="RigidBody3D",
        member_type="class",
        summary="Physics body for 3D",
        inheritance_json='["RigidBody3D", "PhysicsBody3D", "CollisionObject3D", "Node3D", "Node", "Object"]',
    ))
    conn.commit()
    conn.close()

    yield {"unity": unity_spec, "godot": godot_spec}
    clear_docset_cache()


class TestBrowseClass:
    def test_browse_transform(self, nav_indexes):
        info = browse_class("Transform", engine="unity")
        assert info is not None
        assert info.symbol_name == "Transform"
        assert info.inheritance == ["Transform", "Component", "Object"]
        assert len(info.methods) == 1
        assert info.methods[0]["symbol_name"] == "Transform.Rotate"
        assert len(info.properties) == 1
        assert info.properties[0]["symbol_name"] == "Transform.position"

    def test_browse_nonexistent_class(self, nav_indexes):
        info = browse_class("DoesNotExist", engine="unity")
        assert info is None


class TestListClassMembers:
    def test_list_all_members(self, nav_indexes):
        members = list_class_members("Transform", engine="unity")
        assert len(members) == 2
        symbols = [m["symbol_name"] for m in members]
        assert "Transform.Rotate" in symbols
        assert "Transform.position" in symbols

    def test_filter_by_type(self, nav_indexes):
        members = list_class_members("Transform", member_type="method", engine="unity")
        assert len(members) == 1
        assert members[0]["symbol_name"] == "Transform.Rotate"


class TestBrowseInheritance:
    def test_godot_inheritance_chain(self, nav_indexes):
        chain = browse_inheritance("RigidBody3D", engine="godot")
        names = [c["symbol_name"] for c in chain]
        assert "RigidBody3D" in names
        # Parents may not be in the index (only RigidBody3D was added),
        # but the chain should at least contain the class itself
        assert len(chain) >= 1


class TestListClasses:
    def test_unity_classes(self, nav_indexes):
        classes = list_classes(engine="unity")
        symbols = [c["symbol_name"] for c in classes]
        assert "Transform" in symbols
        assert "Rigidbody" in symbols

    def test_prefix_filter(self, nav_indexes):
        classes = list_classes(engine="unity", prefix="Trans")
        assert len(classes) >= 1
        assert classes[0]["symbol_name"] == "Transform"


class TestBrowseModule:
    def test_physics_module(self, nav_indexes):
        info = browse_module("Physics", engine="unity")
        assert info is not None
        assert "Rigidbody" in info.classes

    def test_nonexistent_module(self, nav_indexes):
        info = browse_module("DoesNotExist", engine="unity")
        assert info is None


class TestGetRelatedSymbols:
    def test_related_to_rotate(self, nav_indexes):
        results = get_related_symbols("Transform.Rotate", engine="unity")
        symbols = [r["symbol_name"] for r in results]
        assert "Transform.position" in symbols


class TestCrossEngineTranslation:
    def test_rigidbody_unity_to_godot(self, nav_indexes):
        results = translate_symbol("Rigidbody", "unity", "godot")
        symbols = [r.target_symbol for r in results]
        assert any("RigidBody" in s for s in symbols)

    def test_same_engine_returns_empty(self, nav_indexes):
        results = translate_symbol("Transform", "unity", "unity")
        assert results == []


class TestVectorSearch:
    def test_vector_search_single(self, nav_indexes):
        spec = nav_indexes["unity"]
        model = get_embedding_model()
        build_vector_index(spec, model)
        hits = vector_search_single("rotate transform", spec)
        assert len(hits) > 0
        rowids = [h[0] for h in hits]
        # All hits should be valid records in the db
        conn = get_connection(spec.db_path, readonly=True)
        for rid in rowids:
            row = conn.execute("SELECT symbol_name FROM api_records WHERE id=?", (rid,)).fetchone()
            assert row is not None
        conn.close()

    def test_rrf_merge(self):
        r1 = SearchResult(id=1, category="api", title="A", relative_path="a", snippet="", score=0.1)
        r2 = SearchResult(id=2, category="api", title="B", relative_path="b", snippet="", score=0.2)
        r3 = SearchResult(id=1, category="api", title="A", relative_path="a", snippet="", score=0.05)

        merged = _rrf_merge([r1, r2], [r3])
        assert len(merged) == 2
        # r1 (id=1) should rank highest because it appears in both lists
        assert merged[0].id == 1

    def test_rrf_empty_lists(self):
        assert _rrf_merge([], []) == []
