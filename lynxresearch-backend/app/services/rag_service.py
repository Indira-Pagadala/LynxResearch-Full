# app/services/rag_service.py

import re
import logging

from app.services.qdrant_service import similarity_search
from app.utils.llm_factory import get_rag_llm
from app.utils.llm_limiter import groq_call_with_retry, trim_prompt_to_budget
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

logger = logging.getLogger(__name__)


async def chat_with_report(
    run_id: str,
    question: str,
    conversation_history: list[dict],
    report_markdown: str = "",
) -> str:
    """
    RAG chat using Groq — fast, free, no quota issues.

    Pipeline:
    1. Retrieve chunks from Qdrant
    2. If no chunks found, fall back to report markdown content
    3. Try Groq for a polished abstractive answer
    4. If Groq fails → extractive fallback from chunks
    """

    # ── Step 1: Retrieve from Qdrant ─────────────────────────
    chunks = await similarity_search(
        run_id=run_id,
        query=question,
        top_k=10,
    )

    logger.info(
        f"[RAG] {len(chunks)} chunks from Qdrant | "
        f"run={run_id[:8]} | "
        f"q={question!r}"
    )

    # ── Step 2: Fallback to report markdown if no chunks ─────
    if not chunks and report_markdown:
        logger.info("[RAG] No Qdrant chunks — using report markdown as context")
        chunks = _chunks_from_markdown(report_markdown, question)

    if not chunks:
        return (
            "I couldn't find relevant content in this report for your question. "
            "Try rephrasing or asking about a topic covered in the report."
        )
    if not _is_question_related_to_chunks(question, chunks):
        return "Sorry, I can only answer questions related to this report."

    # ── Step 3: Try Groq ─────────────────────────────────────
    groq_answer = await _call_groq(question, chunks, conversation_history)
    if groq_answer:
        return groq_answer

    # ── Step 4: Extractive fallback ──────────────────────────
    logger.info("[RAG] Groq unavailable — extractive fallback")
    return _extractive_answer(question, chunks)


def _chunks_from_markdown(markdown: str, question: str) -> list[dict]:
    """
    Split report markdown into chunks for RAG context.
    Splits on section headings to preserve logical grouping.
    Returns the most relevant chunks based on keyword overlap.
    """
    sections = re.split(r'\n(?=#{1,3}\s)', markdown)
    
    question_words = set(
        w.lower() for w in re.findall(r"\b\w{4,}\b", question)
    )
    
    scored_chunks = []
    for section in sections:
        section = section.strip()
        if not section or len(section) < 50:
            continue
        
        # Score by keyword overlap
        section_words = set(w.lower() for w in re.findall(r"\b\w{4,}\b", section))
        overlap = len(question_words & section_words)
        score = overlap / max(len(question_words), 1)
        
        scored_chunks.append({
            "chunk_text": section[:2000],  # Cap length
            "url": "report",
            "score": round(score, 4),
        })
    
    # Sort by relevance, take top chunks
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    result = scored_chunks[:8]
    
    # Always include at least some content even if scores are low
    if not result and sections:
        for s in sections[:4]:
            s = s.strip()
            if s and len(s) >= 50:
                result.append({
                    "chunk_text": s[:2000],
                    "url": "report",
                    "score": 0.1,
                })
    
    logger.info(f"[RAG] Built {len(result)} chunks from report markdown")
    return result


async def _call_groq(
    question: str,
    chunks: list[dict],
    conversation_history: list[dict],
) -> str | None:
    """Single Groq call. Returns None on any failure."""
    try:
        llm     = get_rag_llm(temperature=0.3)
        context = trim_prompt_to_budget(_build_context(chunks), max_tokens=2200)

        messages = [
            SystemMessage(content=(
                "You are a research assistant. Answer only using the "
                "provided research report excerpts.\n\n"
                "INSTRUCTIONS:\n"
                "- Be concise, clear, and directly relevant\n"
                "- Use specific data, statistics, and findings from excerpts\n"
                "- If excerpts contain relevant data, cite them by excerpt number [1], [2], etc.\n"
                "- If the excerpts don't fully answer the question, say what you can "
                "and note what information is missing\n"
                "- If question is unrelated to this report, respond exactly: "
                "'Sorry, I can only answer questions related to this report.'"
            ))
        ]

        # Keep only the latest turns to limit repeated context injection.
        for turn in conversation_history[-2:]:
            role    = turn.get("role", "")
            content = turn.get("content", "")
            if not content:
                continue
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=(
            f"Research report excerpts:\n\n{context}\n\n"
            f"---\n\n"
            f"Based on the above excerpts, please answer this question:\n"
            f"{question}"
        )))

        response = await groq_call_with_retry(
            llm,
            messages,
            max_retries=3,
            label=f"RAG run={question[:24]}",
        )
        answer   = response.content.strip()
        if answer:
            logger.info(f"[RAG] Groq answer: {len(answer)} chars")
        return answer if answer else None

    except Exception as e:
        logger.warning(f"[RAG] Groq failed: {e}")
        return None


def _extractive_answer(question: str, chunks: list[dict]) -> str:
    """
    Builds answer directly from chunks — no LLM needed.
    Scores sentences by keyword overlap with question.
    """
    question_words = set(
        w.lower() for w in re.findall(r"\b\w{4,}\b", question)
    )

    scored: list[tuple[float, str, str]] = []

    for chunk in chunks:
        text   = chunk.get("chunk_text", "")
        source = chunk.get("url", "")
        if not text:
            continue
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 40:
                continue
            s_words = set(w.lower() for w in re.findall(r"\b\w{4,}\b", sentence))
            overlap = len(question_words & s_words)
            boost   = 1.2 if any(
                w in sentence.lower()[:50] for w in question_words
            ) else 1.0
            score = (overlap / max(len(question_words), 1)) * boost
            scored.append((score, sentence, source))

    if not scored:
        return _top_chunks_fallback(chunks)

    scored.sort(key=lambda x: x[0], reverse=True)
    top = _deduplicate(scored[:12])[:5]

    if not top or top[0][0] < 0.1:
        return _top_chunks_fallback(chunks)

    lines         = ["**Based on the research report:**\n"]
    seen_sources: set[str] = set()

    for _, sentence, source in top:
        lines.append(f"- {sentence}")
        if source:
            seen_sources.add(source)

    if seen_sources:
        lines.append(
            f"\n*Sources: "
            f"{', '.join(_short_url(s) for s in seen_sources)}*"
        )

    lines.append(
        "\n*Note: This answer was assembled directly from report excerpts.*"
    )
    return "\n".join(lines)


def _top_chunks_fallback(chunks: list[dict]) -> str:
    parts = []
    for chunk in chunks[:2]:
        text = chunk.get("chunk_text", "").strip()
        if text:
            parts.append(text[:500])
    if not parts:
        return "No relevant content found in the report for this question."
    return (
        "**Most relevant section from the report:**\n\n"
        + "\n\n".join(parts)
    )


def _deduplicate(
    scored: list[tuple[float, str, str]]
) -> list[tuple[float, str, str]]:
    selected = []
    for item in scored:
        s = item[1].lower()
        if not any(_jaccard(s, x[1].lower()) > 0.6 for x in selected):
            selected.append(item)
    return selected


def _jaccard(a: str, b: str) -> float:
    wa = set(a.split())
    wb = set(b.split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks):
        text   = c.get("chunk_text", "").strip()
        source = c.get("url", "")
        score  = c.get("score", 0.0)
        if text:
            parts.append(
                f"[Excerpt {i+1} | relevance={score:.3f} | {source}]\n{text}"
            )
    return "\n\n---\n\n".join(parts)


def _short_url(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return url[:40]


def _is_question_related_to_chunks(question: str, chunks: list[dict]) -> bool:
    q_words = set(w.lower() for w in re.findall(r"\b\w{4,}\b", question))
    if not q_words:
        return False
    context_words: set[str] = set()
    for chunk in chunks[:6]:
        text = chunk.get("chunk_text", "")
        context_words.update(w.lower() for w in re.findall(r"\b\w{4,}\b", text[:1500]))
    overlap = len(q_words & context_words)
    return overlap >= 2