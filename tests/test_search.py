"""Tests for the two-index search and retrieval logic."""

from __future__ import annotations

import json

import pytest

from unity_mcp.db import get_connection, init_db, upsert_api_record, upsert_guide_record
from unity_mcp.models import ApiRecord, GuideRecord
from unity_mcp.search import (
    answer_question,
    get_doc_page,
    get_stats,
    get_symbol_reference,
    search_api,
    search_guides,
)


@pytest.fixture
def indexed_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = get_connection(db_path)
    init_db(conn)

    api_records = [
        ApiRecord(
            title="Transform",
            relative_path="en/ScriptReference/Transform.html",
            symbol_name="Transform",
            class_name="Transform",
            namespace="UnityEngine",
            member_type="class",
            summary="Position, rotation and scale of an object.",
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
            content_text="Use Transform.Rotate to rotate GameObjects in a variety of ways.",
        ),
        ApiRecord(
            title="Rigidbody",
            relative_path="en/ScriptReference/Rigidbody.html",
            symbol_name="Rigidbody",
            class_name="Rigidbody",
            namespace="UnityEngine",
            member_type="class",
            summary="Control of an object's position through physics simulation.",
            content_text="Control of an object's position through physics simulation.",
        ),
        ApiRecord(
            title="Collider2D.isTrigger",
            relative_path="en/ScriptReference/Collider2D-isTrigger.html",
            symbol_name="Collider2D.isTrigger",
            class_name="Collider2D",
            namespace="UnityEngine",
            member_type="property",
            summary="Indicates whether the collider acts as a trigger.",
            content_text="Indicates whether the collider acts as a trigger.",
        ),
    ]
    for r in api_records:
        upsert_api_record(conn, r)

    guide_records = [
        GuideRecord(
            title="Transforms",
            relative_path="en/Manual/class-Transform.html",
            guide_type="reference",
            summary="The Transform component.",
            content_text="The Transform stores a GameObject's Position, Rotation, Scale.",
            key_topics_json=json.dumps(["The Transform Component", "Parenting"]),
        ),
        GuideRecord(
            title="How to rotate objects",
            relative_path="en/Manual/rotate-objects.html",
            guide_type="manual",
            summary="Rotate objects in the editor or via scripts.",
            content_text="You can rotate a cube using Transform.Rotate or by editing the rotation field.",
            key_topics_json=json.dumps(["Rotating in the editor", "Rotating via scripts"]),
        ),
        GuideRecord(
            title="Physics overview",
            relative_path="en/Manual/PhysicsSection.html",
            guide_type="overview",
            summary="An overview of Unity's physics systems.",
            content_text="Unity ships with two physics engines: 3D (PhysX) and 2D (Box2D).",
            key_topics_json=json.dumps(["Rigidbodies", "Colliders", "Joints"]),
        ),
    ]
    for r in guide_records:
        upsert_guide_record(conn, r)

    conn.commit()
    conn.close()
    return db_path


class TestSearchApi:
    def test_exact_class(self, indexed_db):
        results = search_api("Transform", db_path=indexed_db)
        assert results
        assert results[0].symbol_name == "Transform"
        assert results[0].category == "api"

    def test_exact_member(self, indexed_db):
        results = search_api("Transform.Rotate", db_path=indexed_db)
        assert results
        assert results[0].symbol_name == "Transform.Rotate"

    def test_member_filter(self, indexed_db):
        results = search_api("Transform", db_path=indexed_db, member_type="method")
        assert all(r.member_type == "method" for r in results)
        assert any(r.symbol_name == "Transform.Rotate" for r in results)

    def test_excludes_guides(self, indexed_db):
        # The guide titled "How to rotate objects" must NOT show up here.
        results = search_api("rotate", db_path=indexed_db)
        assert all(r.category == "api" for r in results)


class TestSearchGuides:
    def test_natural_language(self, indexed_db):
        results = search_guides("how to rotate", db_path=indexed_db)
        assert results
        assert results[0].category == "guide"
        assert "rotate" in results[0].title.lower() or "rotate" in results[0].snippet.lower()

    def test_excludes_api(self, indexed_db):
        results = search_guides("rigidbody", db_path=indexed_db)
        assert all(r.category == "guide" for r in results)

    def test_guide_type_filter(self, indexed_db):
        results = search_guides("physics", db_path=indexed_db, guide_type="overview")
        assert results
        assert all(r.guide_type == "overview" for r in results)


class TestGetSymbolReference:
    def test_exact_symbol(self, indexed_db):
        ref = get_symbol_reference("Transform.Rotate", db_path=indexed_db)
        assert ref is not None
        assert ref.symbol_name == "Transform.Rotate"
        assert ref.signature

    def test_bare_member(self, indexed_db):
        ref = get_symbol_reference("Rotate", db_path=indexed_db)
        assert ref is not None
        assert "Rotate" in ref.symbol_name

    def test_class_lookup(self, indexed_db):
        ref = get_symbol_reference("Rigidbody", db_path=indexed_db)
        assert ref is not None
        assert ref.class_name == "Rigidbody"

    def test_not_found(self, indexed_db):
        assert get_symbol_reference("NoSuchSymbolXYZ", db_path=indexed_db) is None


class TestGetDocPage:
    def test_api_path(self, indexed_db):
        payload = get_doc_page("ScriptReference/Transform.html", db_path=indexed_db)
        assert payload is not None
        assert payload["category"] == "api"

    def test_guide_path(self, indexed_db):
        payload = get_doc_page("Manual/PhysicsSection.html", db_path=indexed_db)
        assert payload is not None
        assert payload["category"] == "guide"

    def test_missing(self, indexed_db):
        assert get_doc_page("nope.html", db_path=indexed_db) is None


class TestAnswerQuestion:
    def test_returns_both_sides(self, indexed_db):
        bundle = answer_question("rotate", db_path=indexed_db, limit_per_index=5)
        assert "api" in bundle and "guide" in bundle
        assert any(r.category == "api" for r in bundle["api"])
        assert any(r.category == "guide" for r in bundle["guide"])


class TestStats:
    def test_breakdown(self, indexed_db):
        s = get_stats(db_path=indexed_db)
        assert s["api_pages"] == 4
        assert s["guide_pages"] == 3
        assert s["total_pages"] == 7
        assert s["unique_classes"] >= 3
        assert s["api_member_breakdown"].get("class", 0) >= 2
        assert s["guide_breakdown"].get("overview", 0) >= 1
