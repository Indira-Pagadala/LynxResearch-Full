# app/services/qdrant_service.py

import logging
import uuid
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
)
from sentence_transformers import SentenceTransformer

from app.config import get_settings
from app.utils.text_cleaner import split_into_chunks

logger = logging.getLogger(__name__)
settings = get_settings()

_embedding_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading sentence-transformers model...")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("✅ Embedding model loaded")
    return _embedding_model


def get_qdrant_client() -> QdrantClient:
    """
    Returns a Qdrant client.
    Works for both local (no key) and Qdrant Cloud (requires api_key).
    """
    api_key = settings.QDRANT_API_KEY
    if api_key:
        # Qdrant Cloud — requires API key
        return QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
    else:
        # Local Qdrant — no auth needed
        return QdrantClient(url=settings.QDRANT_URL)


async def ensure_collection_exists():
    """
    Create Qdrant collection if it doesn't exist.
    Also creates a keyword payload index on 'run_id' —
    this is REQUIRED for filtered search to work.
    Without the index Qdrant returns 400 Bad Request.
    """
    client = get_qdrant_client()
    existing = [c.name for c in client.get_collections().collections]

    if settings.QDRANT_COLLECTION not in existing:
        # Create the collection
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"✅ Created Qdrant collection: {settings.QDRANT_COLLECTION}")

    # Always ensure the index exists — safe to call even if it already exists
    _ensure_run_id_index(client)


def _ensure_run_id_index(client: QdrantClient):
    """
    Creates a keyword payload index on 'run_id'.
    Qdrant requires this before you can use run_id in a Filter.
    Safe to call multiple times — won't error if index already exists.
    """
    try:
        client.create_payload_index(
            collection_name=settings.QDRANT_COLLECTION,
            field_name="run_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info("✅ Qdrant payload index on 'run_id' ensured")
    except Exception as e:
        # Qdrant raises if index already exists — that's fine, just log and continue
        logger.debug(f"[Qdrant] Index creation note (likely already exists): {e}")


async def embed_and_store_documents(
    run_id: str, docs: list[dict]
) -> list[dict]:
    """
    Chunk all documents, embed them, and store in Qdrant.
    Returns list of chunk dicts with qdrant_point_ids.
    """
    await ensure_collection_exists()
    model  = get_embedding_model()
    client = get_qdrant_client()

    all_chunks: list[dict] = []
    points_to_upsert: list[tuple] = []   # (point_id, text, payload)

    for doc in docs:
        text = doc.get("raw_text", "")
        url  = doc.get("url", "")
        if not text:
            continue

        chunks = split_into_chunks(
            text,
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP,
        )

        for i, chunk_text in enumerate(chunks):
            point_id = uuid.uuid4()
            all_chunks.append({
                "run_id":          run_id,
                "url":             url,
                "chunk_text":      chunk_text,
                "chunk_index":     i,
                "qdrant_point_id": str(point_id),
            })
            points_to_upsert.append((
                point_id,
                chunk_text,
                {
                    "run_id":     run_id,   # stored as string keyword
                    "url":        url,
                    "chunk_text": chunk_text,
                },
            ))

    if not points_to_upsert:
        logger.warning(f"[Qdrant] No chunks to embed for run {run_id}")
        return []

    # ── Batch embed ───────────────────────────────────────────
    texts      = [p[1] for p in points_to_upsert]
    logger.info(f"[Qdrant] Embedding {len(texts)} chunks for run {run_id}...")
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=False,
        normalize_embeddings=True,
    )

    # ── Build PointStructs ────────────────────────────────────
    qdrant_points = [
        PointStruct(
            id=str(points_to_upsert[i][0]),
            vector=embeddings[i].tolist(),
            payload=points_to_upsert[i][2],
        )
        for i in range(len(points_to_upsert))
    ]

    # ── Upsert in batches of 100 ──────────────────────────────
    batch_size = 100
    for i in range(0, len(qdrant_points), batch_size):
        batch = qdrant_points[i : i + batch_size]
        client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=batch,
            wait=True,
        )

    logger.info(
        f"[Qdrant] Stored {len(qdrant_points)} vectors for run {run_id}"
    )
    return all_chunks


async def similarity_search(
    run_id: str,
    query: str,
    top_k: int = 8,       # Increased from 6
) -> list[dict]:
    model  = get_embedding_model()
    client = get_qdrant_client()

    query_vector = model.encode(
        [query],
        normalize_embeddings=True,
    )[0].tolist()

    results = client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=query_vector,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="run_id",
                    match=MatchValue(value=run_id),
                )
            ]
        ),
        limit=top_k,
        with_payload=True,
        # NO score_threshold — MiniLM cosine scores are naturally 0.1–0.5
        # A threshold of 0.3 would filter out most valid results
    )

    chunks = [
        {
            "chunk_text": r.payload.get("chunk_text", ""),
            "url":        r.payload.get("url", ""),
            "score":      round(r.score, 4),
        }
        for r in results
        if r.payload.get("chunk_text", "").strip()  # skip empty chunks
    ]

    logger.info(
        f"[Qdrant] similarity_search: {len(chunks)} results for "
        f"run={run_id} query={query!r}"
    )
    return chunks


async def delete_run_vectors(run_id: str):
    """Delete all vectors for a specific run (cleanup)."""
    client = get_qdrant_client()
    try:
        client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="run_id",
                        match=MatchValue(value=run_id),
                    )
                ]
            ),
        )
        logger.info(f"[Qdrant] Deleted vectors for run {run_id}")
    except Exception as e:
        logger.error(f"[Qdrant] Failed to delete vectors for run {run_id}: {e}")