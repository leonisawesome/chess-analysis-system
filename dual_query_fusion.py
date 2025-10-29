#!/usr/bin/env python3
"""
Dual-Query Fusion + Domain Filter (ChatGPT's Approach)
Expected precision: 89-90%
"""

from openai import OpenAI
from qdrant_client import QdrantClient
import numpy as np
import re
from collections import OrderedDict
import json
import os

# Initialize clients
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
qdrant_client = QdrantClient(path="./qdrant_validation_db")

# --- CONFIG ---
EMBEDDING_MODEL = "text-embedding-3-small"
TOP_K = 40
M = 20    # after merge -> send to reranker
FINAL_TOP = 5
WEIGHTS = {'w1': 0.40, 'w2': 0.30, 'w3': 0.20, 'w4': 0.10}
COSINE_OVERLAP_THRESHOLD = 0.05  # fallback threshold for overlap

# Domain keywords for openings (expandable to other domains)
DOMAIN_KEYWORDS = {
    'openings': set([
        "opening", "openings", "repertoire", "lines", "main line", "sideline", "tabiya",
        "tabiyas", "transposition", "move-order", "move order", "ECO", "gambit",
        "novelty", "novelties", "model game", "theory", "variation", "variations",
        "pawn structure", "pawn structures", "trap", "traps", "debut", "debút"
    ]),
    'calculation': set([
        "calculation", "calculate", "calculating", "variation", "variations",
        "lookahead", "visualize", "visualization", "candidate move", "candidate moves",
        "tree", "branch", "branches", "forcing move", "forcing moves"
    ]),
    'tactics': set([
        "tactics", "tactical", "tactic", "combination", "combinations",
        "fork", "pin", "skewer", "discovered attack", "double attack",
        "motif", "motifs", "pattern", "patterns"
    ])
}

ECO_PATTERN = re.compile(r'\b[A-E][0-9]{2}\b', re.I)

# --- HELPER FUNCTIONS ---

def embed(text: str):
    """Return embedding vector using OpenAI."""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return np.array(response.data[0].embedding)


def semantic_search_vector(vec, top_k=40):
    """
    Return list of dicts: {'chunk_id','sim','text','meta':{'title','chapter','book_name'}}
    """
    results = qdrant_client.search(
        collection_name="chess_validation",
        query_vector=vec.tolist(),
        limit=top_k
    )

    output = []
    for result in results:
        output.append({
            'chunk_id': result.id,
            'sim': result.score,
            'text': result.payload['text'],
            'meta': {
                'title': result.payload.get('chapter_title', ''),
                'chapter': result.payload.get('chapter_title', ''),
                'book_name': result.payload.get('book_name', '')
            }
        })
    return output


def gpt5_expand_domain_preserving(query: str) -> dict:
    """
    Call GPT-5 with the domain-preserving expansion prompt and return JSON:
    {'paraphrase': '...', 'domain_focus': '...'}
    """

    prompt = f"""You are an assistant that expands user queries for retrieval. For queries of the form "How to [ACTION] [DOMAIN]" produce a short domain-preserving expansion that clarifies domain synonyms but preserves the ACTION intent. Do NOT add generic study verbs or broaden the topic to unrelated content. Keep the expansion concise.

INPUT:
Original query: "{query}"

INSTRUCTIONS:
1. Identify ACTION and DOMAIN in the query.
2. Produce two short strings as JSON:
  - "paraphrase": a short rewording that preserves original intent (<= 1.5× original length).
  - "domain_focus": expand the DOMAIN only (add synonyms, technical terms, typical phrases about the domain), do NOT add extra ACTION verbs. Limit to <= 3× original length.
3. For domain_focus, include domain tokens (e.g., for "openings": 'repertoire', 'lines', 'move-order', 'tabiya', 'transposition', 'ECO').
4. Do not include lists of unrelated training techniques or full catalogs of topics.
5. Output only valid JSON: {{"paraphrase": "...", "domain_focus": "..."}}

EXAMPLE:
Original: "How to study chess openings"
Output:
{{
  "paraphrase": "How should I study chess openings effectively?",
  "domain_focus": "study chess openings, repertoire building, main lines and sidelines, tabiyas and typical pawn structures, move-order and transpositions"
}}

Now expand: "{query}"

Output only valid JSON:"""

    response = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    result_text = response.choices[0].message.content.strip()

    # Parse JSON
    try:
        # Remove markdown code blocks if present
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]

        expansion = json.loads(result_text)
        return expansion
    except:
        # Fallback if JSON parsing fails
        return {'paraphrase': query, 'domain_focus': query}


def gpt5_rerank(query: str, candidates: list) -> list:
    """
    candidates: list of dicts {'chunk_id','text','meta','combined_score','domain_score'}
    Return list of dicts {'chunk_id','score':0-10,'justification','label'}
    """

    prompt = f"""You are a chess-aware relevance judge. Evaluate each candidate chunk for relevance to the user's query. Provide a score 0–10, a one-sentence justification, and a single label: method|theory|example|pgn.

INSTRUCTIONS:
- Consider the user's explicit intent (procedural "how to" vs conceptual).
- Prefer chunks that give **direct methods, steps, or examples** for HOW-TO queries.
- Penalize chunks that are only general background or tangential.
- Score 8-10: Directly addresses the query with actionable content
- Score 5-7: Related but tangential or too general
- Score 0-4: Irrelevant or wrong intent
- Output JSON list with entries: {{chunk_id, score, justification, label}}

USER_QUERY:
"{query}"

CANDIDATES:
"""

    for i, cand in enumerate(candidates, 1):
        meta_str = f"Book: {cand['meta'].get('book_name', 'unknown')}, Chapter: {cand['meta'].get('chapter', 'unknown')}"
        text_preview = cand['text'][:300].replace('\n', ' ')
        prompt += f"\n{i}) CHUNK_ID: {cand['chunk_id']}\nMETA: {meta_str}\nTEXT: {text_preview}...\n"

    prompt += """\nOUTPUT FORMAT (JSON list):
[
  {"chunk_id":"...","score":8.5,"justification":"This chunk lists stepwise drills for studying openings.","label":"method"},
  ...
]

Output only valid JSON:"""

    response = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    result_text = response.choices[0].message.content.strip()

    # Parse JSON
    try:
        # Remove markdown code blocks if present
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]

        rankings = json.loads(result_text)
        return rankings
    except Exception as e:
        print(f"Warning: Failed to parse GPT-5 reranking JSON: {e}")
        # Fallback: return candidates with default scores
        return [{'chunk_id': c['chunk_id'], 'score': 5, 'justification': 'Parse error', 'label': 'unknown'}
                for c in candidates]


def detect_domain(query: str) -> str:
    """Detect which domain the query is about."""
    query_lower = query.lower()

    if any(kw in query_lower for kw in ['opening', 'openings', 'repertoire', 'debut']):
        return 'openings'
    elif any(kw in query_lower for kw in ['calculation', 'calculate', 'visualize', 'lookahead']):
        return 'calculation'
    elif any(kw in query_lower for kw in ['tactics', 'tactical', 'combination']):
        return 'tactics'
    else:
        return 'general'


def compute_domain_score(chunk_text: str, meta: dict, domain: str = 'openings') -> float:
    """Compute domain presence score (0-1)."""

    keywords = DOMAIN_KEYWORDS.get(domain, set())

    text = (chunk_text + " " + meta.get('title', '') + " " + meta.get('chapter', '')).lower()

    count = 0
    for kw in keywords:
        count += text.count(kw)

    title_bonus = 1 if any(kw in (meta.get('title', '') or '').lower() for kw in keywords) else 0
    eco_bonus = 1 if domain == 'openings' and ECO_PATTERN.search(text) else 0

    raw = min(5, count + title_bonus + eco_bonus)
    domain_score = raw / 7.0

    return max(0.0, min(1.0, domain_score))


def union_dedupe(list_a, list_b):
    """Union two candidate lists and dedupe by chunk_id."""
    combined = OrderedDict()
    for item in list_a + list_b:
        cid = item['chunk_id']
        if cid not in combined:
            combined[cid] = item
    return list(combined.values())


def topk_overlap(list_a, list_b, k=10):
    """Calculate overlap ratio between top-k of two lists."""
    set_a = set(x['chunk_id'] for x in list_a[:k])
    set_b = set(x['chunk_id'] for x in list_b[:k])
    if not set_a:
        return 0.0
    overlap = len(set_a.intersection(set_b)) / len(set_a)
    return overlap


# --- MAIN FUNCTION ---

def dual_query_fusion_rerank(original_query: str, verbose=False):
    """
    Main dual-query fusion + domain filter pipeline.

    Returns: list of top 5 results with metadata
    """

    # 1) Check if HOW-TO query
    is_how_to = bool(re.search(r'^\s*(how|how to|best|improve|steps|practice|train|what.*way)\b',
                                original_query, re.I))

    if not is_how_to:
        if verbose:
            print("Not a HOW-TO query - using standard pipeline")
        # Fall back to standard pipeline
        vec = embed(original_query)
        orig_results = semantic_search_vector(vec, top_k=TOP_K)
        top_candidates = orig_results[:M]
        reranked = gpt5_rerank(original_query, top_candidates)
        final_ranked = sorted(reranked, key=lambda r: -r['score'])[:FINAL_TOP]

        # Add back full chunk data while preserving reranking fields
        chunk_map = {str(c['chunk_id']): c for c in top_candidates}
        final = []
        for item in final_ranked:
            chunk_id_str = str(item['chunk_id'])
            if chunk_id_str in chunk_map:
                result = chunk_map[chunk_id_str].copy()
                result['score'] = item.get('score')
                result['justification'] = item.get('justification')
                result['label'] = item.get('label')
                final.append(result)
            else:
                final.append(item)

        return final

    # 2) Detect domain
    domain = detect_domain(original_query)
    if verbose:
        print(f"Detected domain: {domain}")

    # 3) Domain-preserving expansion
    if verbose:
        print("Generating domain-preserving expansion...")
    expansion = gpt5_expand_domain_preserving(original_query)
    domain_focus = expansion.get('domain_focus') or expansion.get('paraphrase') or original_query

    if verbose:
        print(f"Original: {original_query}")
        print(f"Domain focus: {domain_focus}")

    # 4) Embed both queries
    v_orig = embed(original_query)
    v_dom = embed(domain_focus)

    # 5) Retrieve top-K for both
    orig_results = semantic_search_vector(v_orig, top_k=TOP_K)
    dom_results = semantic_search_vector(v_dom, top_k=TOP_K)

    # 6) Check overlap - fallback if too divergent
    overlap = topk_overlap(orig_results, dom_results, k=10)
    if verbose:
        print(f"Top-10 overlap: {overlap:.2%}")

    if overlap < COSINE_OVERLAP_THRESHOLD:
        if verbose:
            print(f"Overlap {overlap:.2%} < {COSINE_OVERLAP_THRESHOLD:.2%} - falling back to original only")
        top_candidates = orig_results[:M]
        reranked = gpt5_rerank(original_query, top_candidates)
        final_ranked = sorted(reranked, key=lambda r: -r['score'])[:FINAL_TOP]

        chunk_map = {str(c['chunk_id']): c for c in top_candidates}
        final = []
        for item in final_ranked:
            chunk_id_str = str(item['chunk_id'])
            if chunk_id_str in chunk_map:
                result = chunk_map[chunk_id_str].copy()
                result['score'] = item.get('score')
                result['justification'] = item.get('justification')
                result['label'] = item.get('label')
                final.append(result)
            else:
                final.append(item)

        return final

    # 7) Union & dedupe
    merged = union_dedupe(orig_results, dom_results)

    if verbose:
        print(f"Merged candidates: {len(merged)}")

    # 8) Compute features & combined_score
    sim_map_orig = {r['chunk_id']: r['sim'] for r in orig_results}
    sim_map_dom = {r['chunk_id']: r['sim'] for r in dom_results}
    orig_top10 = set(r['chunk_id'] for r in orig_results[:10])

    candidates = []
    for item in merged:
        cid = item['chunk_id']
        sim_orig = sim_map_orig.get(cid, 0.0)
        sim_dom = sim_map_dom.get(cid, 0.0)
        domain_score = compute_domain_score(item['text'], item.get('meta', {}), domain)
        in_orig_top10 = 1 if cid in orig_top10 else 0

        combined_score = (WEIGHTS['w1'] * sim_orig +
                          WEIGHTS['w2'] * sim_dom +
                          WEIGHTS['w3'] * domain_score +
                          WEIGHTS['w4'] * in_orig_top10)

        # Filter rule: for HOW-TO, drop purely generic chunks
        if domain_score == 0.0 and in_orig_top10 == 0:
            if verbose:
                print(f"Filtering out generic chunk: {item['text'][:100]}")
            continue

        item['sim_orig'] = sim_orig
        item['sim_dom'] = sim_dom
        item['domain_score'] = domain_score
        item['combined_score'] = combined_score
        candidates.append(item)

    # 9) Sort by combined_score and take top M
    candidates = sorted(candidates, key=lambda x: -x['combined_score'])[:M]

    if verbose:
        print(f"After filtering: {len(candidates)} candidates")
        print(f"Sending {len(candidates)} to GPT-5 reranker")

    # 10) Rerank with GPT-5
    reranked = gpt5_rerank(original_query, candidates)

    # 11) Final pick: sort by GPT score
    final_ranked = sorted(reranked, key=lambda r: -r['score'])[:FINAL_TOP]

    # Add back full chunk data while preserving reranking fields
    chunk_map = {str(c['chunk_id']): c for c in candidates}
    final = []
    for item in final_ranked:
        chunk_id_str = str(item['chunk_id'])
        if chunk_id_str in chunk_map:
            # Start with full chunk data
            result = chunk_map[chunk_id_str].copy()
            # Override with reranking fields
            result['score'] = item.get('score')
            result['justification'] = item.get('justification')
            result['label'] = item.get('label')
            final.append(result)
        else:
            # Fallback: just use the reranked item (missing chunk data)
            final.append(item)

    return final


if __name__ == "__main__":
    # Test on Query 5 (the critical regression case)
    test_query = "What is the best way to study chess openings?"

    print("="*80)
    print("DUAL-QUERY FUSION TEST")
    print("="*80)
    print(f"Query: {test_query}")
    print()

    results = dual_query_fusion_rerank(test_query, verbose=True)

    print("\n" + "="*80)
    print("TOP 5 RESULTS")
    print("="*80)

    for i, result in enumerate(results, 1):
        print(f"\n{i}. [Score: {result.get('score', 0)}/10] {result.get('label', 'unknown')}")
        meta = result.get('meta', {})
        print(f"   Book: {meta.get('book_name', 'unknown')}")
        print(f"   Chapter: {meta.get('chapter', 'unknown')}")
        print(f"   Domain score: {result.get('domain_score', 0):.3f}")
        print(f"   Justification: {result.get('justification', 'N/A')}")
        print(f"   Text: {result.get('text', '')[:200]}...")
