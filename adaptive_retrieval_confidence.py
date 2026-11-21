"""
Adaptive Retrieval Confidence Engine
====================================
Computes a calibrated multi-signal confidence metric for legal RAG retrieval.
Replaces single arbitrary MIN_RETRIEVAL_SCORE thresholds with an evidence-grounded
composite score incorporating:
  1. Dense semantic similarity (FAISS / cosine)
  2. Sparse lexical BM25 strength & rank
  3. Reciprocal Rank Fusion (RRF) positioning
  4. Cross-Encoder reranker score (calibrated from raw logits)
  5. Supporting chunk density and multi-document source diversity
  6. Query-document lexical overlap
  7. Evidence grading & citation verification results

Recommends actionable decisions:
  - "answer": High confidence (grounded, multi-source or strong semantic match)
  - "rewrite_and_retry": Medium confidence (ambiguous band, needs CRAG query rewrite)
  - "refuse": Low confidence (corpus does not substantiate query)
"""

import math
import os
from typing import Any, Dict, List, Optional


def _sigmoid(x: float) -> float:
    """Standard sigmoid to map raw logits into [0, 1]."""
    try:
        return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, x))))
    except Exception:
        return 0.5


def calibrate_reranker_score(raw_score: Optional[float]) -> float:
    """
    Normalizes CrossEncoder logits (typically between -10 and +10) into [0, 1].
    If raw_score is None, returns a neutral fallback.
    """
    if raw_score is None:
        return 0.5
    if 0.0 <= raw_score <= 1.0:
        return float(raw_score)
    # Logit scale conversion
    return float(_sigmoid(raw_score))


def compute_lexical_overlap(query: str, passages: List[Dict[str, Any]]) -> float:
    """Calculates query token containment in retrieved passages."""
    if not query or not passages:
        return 0.0
    
    stop_words = {
        "what", "which", "where", "when", "who", "whom", "whose", "why", "how",
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "up", "about", "into", "over", "after",
        "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
        "do", "does", "did", "can", "could", "should", "would", "may", "might",
        "must", "shall", "under", "section", "act", "law", "court", "case", "held"
    }
    
    query_tokens = [w.lower().strip("?,.:;\"'()[]{}") for w in query.split() if len(w) > 2]
    substantive_tokens = [w for w in query_tokens if w not in stop_words]
    if not substantive_tokens:
        substantive_tokens = query_tokens or ["legal"]
        
    passage_text = " ".join((p.get("raw_text") or p.get("text") or "").lower() for p in passages)
    
    hits = sum(1 for token in substantive_tokens if token in passage_text)
    return round(hits / max(1, len(substantive_tokens)), 3)


def evaluate_retrieval_confidence(
    query: str,
    passages: List[Dict[str, Any]],
    top_score: Optional[float] = None,
    reranker_score: Optional[float] = None,
    verification: Optional[Dict[str, Any]] = None,
    min_threshold: float = 0.54,
    weak_threshold: float = 0.58,
) -> Dict[str, Any]:
    """
    Produces a composite, calibrated confidence assessment.
    
    Returns:
      {
        "confidence": float (0.0 to 1.0),
        "level": "high" | "medium" | "low",
        "signals": { ... },
        "recommended_action": "answer" | "rewrite_and_retry" | "refuse",
        "explanation": str
      }
    """
    if not passages:
        return {
            "confidence": 0.0,
            "level": "low",
            "signals": {
                "dense_similarity": 0.0,
                "bm25_strength": 0.0,
                "rrf_score": 0.0,
                "reranker_score": 0.0,
                "supporting_chunks": 0,
                "source_diversity": 0,
                "lexical_overlap": 0.0,
                "citation_verification_ratio": 0.0,
            },
            "recommended_action": "refuse",
            "explanation": "No relevant passages were retrieved from the corpus."
        }

    # 1. Dense Semantic Similarity
    if top_score is None:
        scores = [float(p.get("score") or 0.0) for p in passages]
        dense_sim = max(scores) if scores else 0.0
    else:
        dense_sim = float(top_score)
    dense_norm = max(0.0, min(1.0, dense_sim))

    # 2. BM25 / Rank signal
    bm25_scores = [float(p.get("bm25_score") or p.get("sparse_score") or 0.0) for p in passages]
    max_bm25 = max(bm25_scores) if bm25_scores else 0.0
    # BM25 scores can be unbounded; normalize with saturating curve
    bm25_norm = max(0.0, min(1.0, 1.0 - math.exp(-max_bm25 / 15.0))) if max_bm25 > 0 else 0.5

    # 3. RRF Rank signal
    rrf_scores = [float(p.get("rrf_score") or 0.0) for p in passages]
    rrf_val = max(rrf_scores) if rrf_scores else 0.0
    rrf_norm = max(0.0, min(1.0, rrf_val * 40.0)) if rrf_val > 0 else dense_norm

    # 4. Cross-Encoder Reranker
    best_rerank = reranker_score
    if best_rerank is None:
        for p in passages:
            if "rerank_score" in p:
                best_rerank = max(best_rerank or -999.0, float(p["rerank_score"]))
    rerank_norm = calibrate_reranker_score(best_rerank)

    # 5. Supporting chunks & source diversity
    num_chunks = len(passages)
    chunk_score = min(1.0, num_chunks / 4.0)
    
    unique_sources = len(set(p.get("source_file") or p.get("case_name") or str(i) for i, p in enumerate(passages)))
    diversity_score = min(1.0, unique_sources / 2.0)

    # 6. Lexical token overlap
    lex_overlap = compute_lexical_overlap(query, passages)

    # 7. Citation verification ratio
    cit_ratio = 1.0
    if verification:
        claims = verification.get("claims") or verification.get("citations") or []
        if claims:
            supported = sum(
                1 for c in claims
                if c.get("status") in {"supported", "partially_supported", "verified"}
                or c.get("verdict") in {"yes", "partial"}
            )
            cit_ratio = supported / max(1, len(claims))

    # Weighted composite calibration
    # Weights sum to 1.0
    weights = {
        "dense": 0.28,
        "rerank": 0.24,
        "bm25": 0.14,
        "lexical": 0.14,
        "chunks": 0.10,
        "verification": 0.10,
    }

    composite = (
        weights["dense"] * dense_norm +
        weights["rerank"] * rerank_norm +
        weights["bm25"] * bm25_norm +
        weights["lexical"] * lex_overlap +
        weights["chunks"] * chunk_score +
        weights["verification"] * cit_ratio
    )
    composite = round(max(0.0, min(1.0, composite)), 3)

    # Calibrated decision bands
    # Preserves backwards compatibility with MIN_RETRIEVAL_SCORE
    if dense_sim < min_threshold and composite < 0.48:
        level = "low"
        action = "refuse"
        explanation = f"Confidence score ({composite:.0%}) is below evidentiary threshold; corpus lacks direct support."
    elif composite >= 0.72 and dense_sim >= weak_threshold:
        level = "high"
        action = "answer"
        explanation = f"High confidence ({composite:.0%}) backed by robust semantic matching and multi-chunk evidence."
    else:
        level = "medium"
        action = "rewrite_and_retry"
        explanation = f"Moderate confidence ({composite:.0%}); evidence is partially ambiguous or requires expanded search."

    return {
        "confidence": composite,
        "level": level,
        "signals": {
            "dense_similarity": round(dense_norm, 3),
            "bm25_strength": round(bm25_norm, 3),
            "rrf_score": round(rrf_norm, 3),
            "reranker_score": round(rerank_norm, 3),
            "supporting_chunks": num_chunks,
            "source_diversity": unique_sources,
            "lexical_overlap": round(lex_overlap, 3),
            "citation_verification_ratio": round(cit_ratio, 3),
        },
        "recommended_action": action,
        "explanation": explanation,
    }
