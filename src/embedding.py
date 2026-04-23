"""Embedding model wrapper for semantic search.

Provides a singleton :class:`EmbeddingModel` that lazily loads a
``fastembed`` ONNX model and exposes batch-encode helpers.  Falls back
to a hash-based fake embedding when the model cannot be loaded (e.g. in
constrained environments without disk space for the model weights).
"""

from __future__ import annotations

import hashlib
import logging
import struct
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from .config import EMBEDDING_BATCH_SIZE, VECTOR_DIM, VECTOR_MODEL_NAME

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Lazy-loading wrapper around a fastembed ONNX model.

    If the model cannot be loaded (missing weights, no onnxruntime, etc.),
    a deterministic hash-based fake embedding is used so that the rest
    of the vector search pipeline still functions for testing.
    """

    def __init__(self) -> None:
        self._model = None
        self._loaded = False
        self._fallback = False

    @property
    def dim(self) -> int:
        return VECTOR_DIM

    @property
    def is_available(self) -> bool:
        """True when a real embedding model has been loaded."""
        if not self._loaded:
            self._try_load()
        return not self._fallback

    def _try_load(self) -> None:
        if self._loaded:
            return
        try:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(VECTOR_MODEL_NAME)
            # Warm up: encode a dummy text to trigger model download
            list(self._model.embed(["warmup"]))
            self._loaded = True
            logger.info("Loaded embedding model: %s", VECTOR_MODEL_NAME)
        except Exception as exc:
            logger.warning(
                "Could not load embedding model (%s). "
                "Vector search will use hash-based fallback embeddings.",
                exc,
            )
            self._loaded = True
            self._fallback = True

    def encode(self, texts: list[str]) -> NDArray[np.float32]:
        """Encode a list of texts into float32 embedding vectors.

        Returns an array of shape ``(len(texts), VECTOR_DIM)``.
        """
        if not self._loaded:
            self._try_load()

        if self._fallback:
            return self._hash_encode(texts)

        embeddings = list(self._model.embed(texts, batch_size=EMBEDDING_BATCH_SIZE))
        return np.array(embeddings, dtype=np.float32)

    def encode_single(self, text: str) -> NDArray[np.float32]:
        """Encode a single text string into a float32 embedding vector."""
        return self.encode([text])[0]

    def _hash_encode(self, texts: list[str]) -> NDArray[np.float32]:
        """Deterministic hash-based pseudo-embeddings for fallback/testing."""
        out = np.zeros((len(texts), VECTOR_DIM), dtype=np.float32)
        for i, text in enumerate(texts):
            h = hashlib.sha256(text.encode("utf-8")).digest()
            values = struct.unpack(f"{VECTOR_DIM // 2}H", h * (VECTOR_DIM // 32 + 1))
            out[i, : len(values)] = np.array(values, dtype=np.float32) / 65535.0
            norm = np.linalg.norm(out[i])
            if norm > 0:
                out[i] /= norm
        return out


_model: Optional[EmbeddingModel] = None


def get_embedding_model() -> EmbeddingModel:
    """Return the shared :class:`EmbeddingModel` singleton."""
    global _model
    if _model is None:
        _model = EmbeddingModel()
    return _model
