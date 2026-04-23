"""Cross-engine API translation and concept mapping.

Enables looking up the equivalent of a symbol or concept in a different
game engine.  For example, finding the Godot equivalent of Unity's
``Rigidbody``.

The mapping is built dynamically from indexed documentation by matching
class-level API records with similar names, member types, and descriptions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .db import get_connection
from .docsets import select_docsets
from .search import IndexNotReadyError

logger = logging.getLogger(__name__)


@dataclass
class TranslationResult:
    """A single cross-engine translation hit."""

    source_engine: str
    source_symbol: str
    source_title: str
    source_member_type: str
    target_engine: str
    target_symbol: str
    target_title: str
    target_member_type: str
    target_summary: str
    target_relative_path: str
    target_docset: str
    target_docset_label: str
    confidence: str  # "high", "medium", "low"


# ---------------------------------------------------------------------------
# Concept keyword map (common game-dev terms across engines)
# ---------------------------------------------------------------------------

_CONCEPT_MAP: dict[str, dict[str, list[str]]] = {
    "physics_body": {
        "unity": ["Rigidbody", "Rigidbody2D"],
        "godot": ["RigidBody3D", "RigidBody2D", "PhysicsBody3D"],
        "unreal": ["UBodyInstance", "FBodyInstance"],
    },
    "transform": {
        "unity": ["Transform"],
        "godot": ["Node3D", "Node2D", "Transform3D"],
        "unreal": ["FTransform", "USceneComponent"],
    },
    "collision": {
        "unity": ["Collider", "Collision", "Physics"],
        "godot": ["CollisionShape3D", "CollisionShape2D", "PhysicsBody3D"],
        "unreal": ["UCollisionProfile", "UPrimitiveComponent"],
    },
    "input": {
        "unity": ["Input", "InputSystem"],
        "godot": ["Input", "InputEvent", "InputMap"],
        "unreal": ["UInputComponent", "UEnhancedInputComponent"],
    },
    "animation": {
        "unity": ["Animator", "Animation", "AnimationClip"],
        "godot": ["AnimationPlayer", "AnimationTree", "AnimatedSprite2D"],
        "unreal": ["UAnimInstance", "UAnimMontage", "UAnimSequence"],
    },
    "camera": {
        "unity": ["Camera", "Camera.main"],
        "godot": ["Camera3D", "Camera2D"],
        "unreal": ["UCameraComponent", "APlayerCameraManager"],
    },
    "character": {
        "unity": ["CharacterController", "CharacterController2D"],
        "godot": ["CharacterBody3D", "CharacterBody2D"],
        "unreal": ["ACharacter", "UCharacterMovementComponent"],
    },
    "node_actor": {
        "unity": ["GameObject"],
        "godot": ["Node"],
        "unreal": ["AActor"],
    },
    "scene_level": {
        "unity": ["Scene", "SceneManager"],
        "godot": ["SceneTree", "PackedScene"],
        "unreal": ["UWorld", "ULevel"],
    },
    "audio": {
        "unity": ["AudioSource", "AudioListener", "AudioClip"],
        "godot": ["AudioStreamPlayer", "AudioStream", "AudioListener3D"],
        "unreal": ["UAudioComponent", "USoundBase", "USoundWave"],
    },
    "raycast": {
        "unity": ["Physics.Raycast", "Physics2D.Raycast"],
        "godot": ["PhysicsRayQueryParameters3D", "DirectSpaceState3D"],
        "unreal": ["LineTrace", "UWorld::LineTraceSingle"],
    },
    "material": {
        "unity": ["Material", "Renderer"],
        "godot": ["Material", "ShaderMaterial", "MeshInstance3D"],
        "unreal": ["UMaterialInterface", "UMaterialInstanceDynamic", "UMeshComponent"],
    },
    "timer": {
        "unity": ["Invoke", "Coroutine", "Time"],
        "godot": ["Timer", "SceneTreeTimer", "Tween"],
        "unreal": ["FTimerHandle", "GetWorldTimerManager"],
    },
    "spawn": {
        "unity": ["Instantiate", "Object.Instantiate"],
        "godot": ["add_child", "instantiate", "PackedScene.instantiate"],
        "unreal": ["SpawnActor", "UWorld::SpawnActor"],
    },
    "navigation": {
        "unity": ["NavMeshAgent", "AI nav"],
        "godot": ["NavigationRegion3D", "NavigationAgent3D", "AStarGrid2D"],
        "unreal": ["UNavMovementComponent", "AAIController", "UNavigationSystemV1"],
    },
}

_MEMBER_TYPE_EQUIV: dict[str, list[str]] = {
    "class": ["class"],
    "method": ["method", "function"],
    "property": ["property", "variable", "field"],
    "signal": ["signal", "event", "delegate"],
}


# ---------------------------------------------------------------------------
# Translation API
# ---------------------------------------------------------------------------


def translate_symbol(
    symbol: str,
    source_engine: str,
    target_engine: str,
    *,
    limit: int = 5,
) -> list[TranslationResult]:
    """Find the equivalent of *symbol* from *source_engine* in *target_engine*.

    Uses a combination of concept mapping and fuzzy name matching.
    """
    source_engine = source_engine.strip().lower()
    target_engine = target_engine.strip().lower()

    if source_engine == target_engine:
        return []

    results: list[TranslationResult] = []
    seen_symbols: set[str] = set()

    # Step 1: Look up source symbol in the index
    source_info = _lookup_source_symbol(symbol, source_engine)

    # Step 2: Try concept-map translation
    concept_hits = _translate_via_concepts(
        symbol, source_info, source_engine, target_engine
    )
    for hit in concept_hits:
        key = hit.target_symbol.lower()
        if key not in seen_symbols:
            seen_symbols.add(key)
            results.append(hit)

    # Step 3: Try name-based fuzzy matching in target engine
    name_hits = _translate_via_name(
        symbol, source_info, source_engine, target_engine, limit=limit
    )
    for hit in name_hits:
        key = hit.target_symbol.lower()
        if key not in seen_symbols:
            seen_symbols.add(key)
            results.append(hit)

    return results[:limit]


def compare_symbol_across_engines(
    symbol: str,
    *,
    engines: list[str] | None = None,
) -> dict[str, list[TranslationResult]]:
    """Look up *symbol* across multiple engines and return equivalents."""
    if engines is None:
        engines = ["unity", "godot", "unreal"]

    # Find which engine this symbol belongs to
    source_engine = _detect_symbol_engine(symbol)
    if not source_engine:
        source_engine = engines[0] if engines else "unity"

    results: dict[str, list[TranslationResult]] = {}
    for target in engines:
        if target == source_engine:
            continue
        results[target] = translate_symbol(symbol, source_engine, target, limit=3)
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _detect_symbol_engine(symbol: str) -> str | None:
    """Heuristic to guess which engine a symbol belongs to."""
    if (
        "::" in symbol
        or symbol.startswith("U")
        or symbol.startswith("A")
        or symbol.startswith("F")
    ):
        if any(c == "::" for c in symbol) or symbol[0] in "UAF":
            return "unreal"
    if "." in symbol and not symbol.startswith("U"):
        parts = symbol.split(".")
        if parts[0].startswith("@") or parts[0][0].isupper():
            return "godot"
    return None


def _lookup_source_symbol(symbol: str, engine: str) -> dict | None:
    """Look up the source symbol in the index to get metadata."""
    try:
        specs = select_docsets(engine=engine)
        indexed = [s for s in specs if s.indexed]
        if not indexed:
            return None
    except (ValueError, IndexNotReadyError):
        return None

    for spec in indexed:
        conn = get_connection(spec.db_path, readonly=True)
        try:
            row = conn.execute(
                """
                SELECT symbol_name, title, class_name, member_type, summary
                FROM api_records
                WHERE symbol_name = ? COLLATE NOCASE
                   OR title = ? COLLATE NOCASE
                LIMIT 1
                """,
                (symbol, symbol),
            ).fetchone()
            if row:
                return dict(row)
        finally:
            conn.close()
    return None


def _translate_via_concepts(
    symbol: str,
    source_info: dict | None,
    source_engine: str,
    target_engine: str,
) -> list[TranslationResult]:
    """Match via the concept keyword map."""
    results: list[TranslationResult] = []

    # Find matching concepts
    matched_concepts: list[str] = []
    symbol_lower = symbol.lower()
    for concept, engines in _CONCEPT_MAP.items():
        source_keywords = engines.get(source_engine, [])
        for kw in source_keywords:
            if kw.lower() in symbol_lower or symbol_lower in kw.lower():
                matched_concepts.append(concept)
                break

    if not matched_concepts:
        return []

    # Look up target engine keywords in the index
    target_symbols: set[str] = set()
    for concept in matched_concepts:
        target_keywords = _CONCEPT_MAP.get(concept, {}).get(target_engine, [])
        target_symbols.update(kw.lower() for kw in target_keywords)

    if not target_symbols:
        return []

    try:
        target_specs = select_docsets(engine=target_engine)
        indexed = [s for s in target_specs if s.indexed]
    except (ValueError, IndexNotReadyError):
        return []

    for spec in indexed:
        conn = get_connection(spec.db_path, readonly=True)
        try:
            placeholders = " OR ".join(
                ["LOWER(symbol_name) LIKE ?"] * len(target_symbols)
            )
            args = [f"%{kw}%" for kw in target_symbols]
            rows = conn.execute(
                f"""
                SELECT symbol_name, title, class_name, member_type, summary, relative_path
                FROM api_records
                WHERE ({placeholders})
                LIMIT 10
                """,
                args,
            ).fetchall()
            for row in rows:
                confidence = (
                    "high" if row["symbol_name"].lower() in target_symbols else "medium"
                )
                results.append(
                    TranslationResult(
                        source_engine=source_engine,
                        source_symbol=symbol,
                        source_title=source_info.get("title", symbol)
                        if source_info
                        else symbol,
                        source_member_type=source_info.get("member_type", "")
                        if source_info
                        else "",
                        target_engine=target_engine,
                        target_symbol=row["symbol_name"],
                        target_title=row["title"],
                        target_member_type=row["member_type"] or "",
                        target_summary=row["summary"] or "",
                        target_relative_path=row["relative_path"],
                        target_docset=spec.docset,
                        target_docset_label=spec.label,
                        confidence=confidence,
                    )
                )
        finally:
            conn.close()

    return results


def _translate_via_name(
    symbol: str,
    source_info: dict | None,
    source_engine: str,
    target_engine: str,
    *,
    limit: int = 5,
) -> list[TranslationResult]:
    """Fuzzy name-based matching across engines."""
    # Extract the base name (e.g. "Transform.Rotate" -> "Rotate", "Rigidbody" -> "Rigidbody")
    base_name = symbol
    for sep in (".", "::"):
        if sep in symbol:
            base_name = symbol.split(sep)[-1]
            break

    try:
        target_specs = select_docsets(engine=target_engine)
        indexed = [s for s in target_specs if s.indexed]
    except (ValueError, IndexNotReadyError):
        return []

    results: list[TranslationResult] = []
    for spec in indexed:
        conn = get_connection(spec.db_path, readonly=True)
        try:
            # Match on symbol name or title containing the base name
            rows = conn.execute(
                """
                SELECT symbol_name, title, class_name, member_type, summary, relative_path
                FROM api_records
                WHERE symbol_name LIKE ? COLLATE NOCASE
                   OR title LIKE ? COLLATE NOCASE
                ORDER BY
                    CASE WHEN symbol_name = ? COLLATE NOCASE THEN 0 ELSE 1 END,
                    CASE WHEN member_type = 'class' THEN 0 ELSE 1 END
                LIMIT ?
                """,
                (f"%{base_name}%", f"%{base_name}%", base_name, limit),
            ).fetchall()
            for row in rows:
                results.append(
                    TranslationResult(
                        source_engine=source_engine,
                        source_symbol=symbol,
                        source_title=source_info.get("title", symbol)
                        if source_info
                        else symbol,
                        source_member_type=source_info.get("member_type", "")
                        if source_info
                        else "",
                        target_engine=target_engine,
                        target_symbol=row["symbol_name"],
                        target_title=row["title"],
                        target_member_type=row["member_type"] or "",
                        target_summary=row["summary"] or "",
                        target_relative_path=row["relative_path"],
                        target_docset=spec.docset,
                        target_docset_label=spec.label,
                        confidence="low",
                    )
                )
        finally:
            conn.close()

    return results[:limit]
