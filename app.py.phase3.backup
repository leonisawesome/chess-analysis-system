#!/usr/bin/env python3
"""
System A Web UI
Flask web interface for chess knowledge retrieval with interactive diagrams
"""

import os
import re
import time
import json
import chess
import chess.pgn
import chess.svg
import spacy
from io import StringIO
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from qdrant_client import QdrantClient
from query_system_a import query_system_a, COLLECTION_NAME, QDRANT_PATH, embed_query, semantic_search, gpt5_rerank, TOP_K, TOP_N
from opening_data import detect_opening
import fen_validator
import query_classifier

from chess_positions import detect_fen, parse_moves_to_fen, extract_chess_positions, filter_relevant_positions, create_lichess_url
from diagram_processor import extract_moves_from_description, extract_diagram_markers, replace_markers_with_ids

# Feature flag for dynamic middlegame pipeline
USE_DYNAMIC_PIPELINE = True  # Set to False to disable middlegame handling

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Initialize clients at module level (created ONCE on startup)
print("Initializing clients...")
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set!")

OPENAI_CLIENT = OpenAI(api_key=api_key)
QDRANT_CLIENT = QdrantClient(path=QDRANT_PATH)
print(f"✓ Clients initialized (Qdrant: {QDRANT_CLIENT.count(COLLECTION_NAME).count} vectors)")

# Load spaCy model for smart caption extraction
print("Loading spaCy model...")
try:
    NLP = spacy.load("en_core_web_sm")
    print("✓ spaCy model loaded")
except OSError:
    print("⚠️  spaCy model not found. Run: python -m spacy download en_core_web_sm")
    NLP = None

# Load canonical FENs for middlegame concepts
print("Loading canonical FENs...")
CANONICAL_FENS = {}
try:
    with open('canonical_fens.json', 'r') as f:
        CANONICAL_FENS = json.load(f)
    print(f"✓ Loaded {len(CANONICAL_FENS)} canonical FEN concepts")
except FileNotFoundError:
    print("⚠️  canonical_fens.json not found - middlegame queries will use RAG only")


# ============================================================================
# MULTI-STAGE SYNTHESIS PIPELINE
# ============================================================================

import json

def stage1_generate_outline(openai_client, query: str, top_chunks: list) -> dict:
    """
    Stage 1: Generate structured outline from query and top chunks.

    Args:
        openai_client: OpenAI client instance
        query: User's query
        top_chunks: List of top 5 relevant text chunks

    Returns:
        dict with sections: {'sections': [{'title': ..., 'bullets': [...]}]}
    """
    # Combine top chunks into context
    context = "\n\n---\n\n".join([chunk[:800] for chunk in top_chunks[:5]])

    prompt = f"""You are a chess instructor creating a comprehensive guide. Based on the user's question and reference material, create a structured outline.

User Question: {query}

Reference Material:
{context}

Create a JSON outline with 5-7 sections. Each section should have:
- title: A clear section heading (e.g., "Overview", "Strategic Themes", "Main Variations", "Key Plans", "Common Tactics")
- bullets: 3-5 bullet points summarizing key information for that section
- diagram_anchor: A standard diagram position for this section (see templates below)

DIAGRAM ANCHOR TEMPLATES:
When creating the outline, specify which standard diagram position to use for each major section:

For Sicilian Defense queries, use these anchors:
- Introduction section: [ANCHOR: Basic Sicilian - 1.e4 c5]
- Najdorf section: [ANCHOR: Najdorf - 1.e4 c5 2.Nf3 d6 3.d4 cxd4 4.Nxd4 Nf6 5.Nc3 a6]
- Dragon section: [ANCHOR: Dragon - 1.e4 c5 2.Nf3 d6 3.d4 cxd4 4.Nxd4 Nf6 5.Nc3 g6]
- Sveshnikov section: [ANCHOR: Sveshnikov - 1.e4 c5 2.Nf3 Nc6 3.d4 cxd4 4.Nxd4 Nf6 5.Nc3 e5]
- Strategic themes section: [ANCHOR: Typical Sicilian pawn structure]

For each section in your JSON outline, include a "diagram_anchor" field with the appropriate anchor.

Return ONLY valid JSON in this exact format:
{{
  "sections": [
    {{"title": "Overview", "bullets": ["...", "...", "..."], "diagram_anchor": "[ANCHOR: Basic Sicilian - 1.e4 c5]"}},
    {{"title": "Strategic Themes", "bullets": ["...", "..."], "diagram_anchor": "[ANCHOR: Typical Sicilian pawn structure]"}},
    ...
  ]
}}"""

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=1500
    )

    try:
        raw_response = response.choices[0].message.content

        # Strip markdown code blocks if present
        if "```json" in raw_response:
            raw_response = raw_response.split("```json")[1].split("```")[0]
        elif "```" in raw_response:
            raw_response = raw_response.split("```")[1].split("```")[0]

        outline = json.loads(raw_response.strip())
        print(f"[Stage 1] ✅ Generated outline with {len(outline['sections'])} sections")
        return outline

    except json.JSONDecodeError as e:
        print(f"[Stage 1] ❌ JSON parse error: {e}")
        print(f"[Stage 1] Raw response: {response.choices[0].message.content[:500]}...")
        return {"sections": [{"title": "Overview", "bullets": ["General information about " + query]}]}
    except Exception as e:
        print(f"[Stage 1] ❌ Unexpected error: {e}")
        print(f"[Stage 1] Raw response: {response.choices[0].message.content[:500]}...")
        return {"sections": [{"title": "Overview", "bullets": ["General information about " + query]}]}


def extract_contamination_details(content: str, expected_signature: str) -> str:
    """
    ITEM-008: Extract details about diagram contamination for feedback.

    Args:
        content: Generated section content
        expected_signature: Expected opening signature (e.g., "1.e4 e5 2.Nf3 Nc6 3.Bc4")

    Returns:
        String with contamination details for regeneration feedback
    """
    import re

    diagrams = re.findall(r'\[DIAGRAM:\s*([^\]]+)\]', content)
    contamination_details = []

    expected_first_move = expected_signature.split()[0]  # e.g., "1.e4"

    for i, diagram_moves in enumerate(diagrams, 1):
        moves = diagram_moves.strip()
        # Check if diagram starts with correct opening moves
        if not moves.startswith(expected_signature[:10]):  # Check first 10 chars of signature
            contamination_details.append(
                f"  - Diagram {i}: {moves[:50]}... (WRONG - should start with {expected_signature})"
            )

    if contamination_details:
        return "\n".join(contamination_details)
    else:
        return "No specific contamination details available"


def generate_section_with_retry(openai_client, section: dict, query: str, context: str,
                                opening_name: str, expected_signature: str,
                                max_retries: int = 2) -> tuple:
    """
    ITEM-008: Generate section content with automatic retry on contamination detection.

    Args:
        openai_client: OpenAI client instance
        section: Section dict with title, bullets, diagram_anchor
        query: User's query
        context: Reference context
        opening_name: Name of the opening (e.g., "Italian Game")
        expected_signature: Expected opening signature for validation
        max_retries: Maximum number of retry attempts (default 2, total 3 attempts)

    Returns:
        Tuple of (generated_content: str, success: bool, attempts: int)
    """
    import re

    title = section['title']
    bullets = section['bullets']
    diagram_anchor = section.get('diagram_anchor', '')
    bullets_text = "\n".join([f"- {b}" for b in bullets])

    # Extract move sequence from diagram_anchor
    anchor_moves = ''
    if diagram_anchor and '-' in diagram_anchor:
        anchor_moves = diagram_anchor.split('-', 1)[1].strip().rstrip(']')

    # Opening signatures for context
    opening_signatures = {
        "Italian Game": "1.e4 e5 2.Nf3 Nc6 3.Bc4",
        "Sicilian Defense": "1.e4 c5",
        "French Defense": "1.e4 e6",
        "Caro-Kann Defense": "1.e4 c6",
        "Ruy Lopez": "1.e4 e5 2.Nf3 Nc6 3.Bb5",
        "Queen's Gambit": "1.d4 d5 2.c4",
        "King's Indian Defense": "1.d4 Nf6 2.c4 g6",
        "Nimzo-Indian Defense": "1.d4 Nf6 2.c4 e6 3.Nc3 Bb4",
        "English Opening": "1.c4",
        "Catalan Opening": "1.d4 Nf6 2.c4 e6 3.g3"
    }

    opening_context = ""
    if opening_name in opening_signatures:
        opening_context = f"\n\nOPENING SIGNATURE: {opening_name} = {opening_signatures[opening_name]}\nAll diagrams MUST start with these moves or be continuations of this sequence."

    # System message for generation
    system_message = """You are an expert chess instructor creating educational content.

<validation_rules>
CRITICAL: You MUST follow these diagram validation rules:
1. FIRST DIAGRAM: Must start from move 1 and match the opening signature exactly
2. SUBSEQUENT DIAGRAMS: May show continuations from later positions, but MUST be from the same opening family
3. PROHIBITED: Never include diagrams from unrelated openings
4. WHEN IN DOUBT: Omit a diagram rather than risk showing wrong opening
</validation_rules>

<reasoning_process>
Before generating each diagram, verify:
1. What opening am I writing about? (check section title)
2. Does this diagram start with the correct opening moves?
3. If it's a continuation, is it a valid variation of this specific opening?
4. Could this diagram be confused with a different opening family?
</reasoning_process>

<examples>
CORRECT - Italian Game First Diagram:
[DIAGRAM: 1.e4 e5 2.Nf3 Nc6 3.Bc4]
✓ Starts from move 1
✓ Matches Italian Game signature

WRONG - Sicilian in Italian Game Article:
[DIAGRAM: 1.e4 c5 2.Nf3 d6]
✗ This is Sicilian Defense (1.e4 c5)
✗ Completely different opening - NEVER do this
</examples>"""

    last_content = None

    for attempt in range(max_retries + 1):
        if attempt == 0:
            # First attempt - standard prompt
            prompt = f"""You are writing a section of a chess guide. Expand the following outline into 150-300 words.

Section Title: {title}
Key Points:
{bullets_text}

DIAGRAM ANCHOR FOR THIS SECTION: {diagram_anchor if diagram_anchor else 'No anchor - generate appropriate diagram'}
EXTRACTED MOVE SEQUENCE: {anchor_moves if anchor_moves else 'Generate move sequence based on content'}

Reference Context (if needed):
{context[:1500]}{opening_context}

Requirements:
- CRITICAL: All diagrams must show positions directly from the requested opening only. Do NOT include unrelated openings or comparisons (e.g., do not show Sicilian Defense positions when asked about Italian Game).
- Write 150-300 words in an educational, engaging style
- Include specific chess moves in algebraic notation (e.g., 1.e4 c5 2.Nf3)
- Be specific and practical
- Focus on understanding, not just memorization

DIAGRAM REQUIREMENTS (MANDATORY):
- Include exactly one [DIAGRAM: move sequence] marker per major variation discussed
- Place it IMMEDIATELY after introducing the key moves
- If EXTRACTED MOVE SEQUENCE is provided above, USE IT EXACTLY for your diagram marker
- Format: "The [variation] arises after [moves]. [DIAGRAM: moves] This position..."

EXAMPLE:
"The Najdorf Variation arises after 1.e4 c5 2.Nf3 d6 3.d4 cxd4 4.Nxd4 Nf6 5.Nc3 a6. [DIAGRAM: 1.e4 c5 2.Nf3 d6 3.d4 cxd4 4.Nxd4 Nf6 5.Nc3 a6] This flexible pawn structure allows Black to prepare queenside expansion."

MINIMUM: At least 1 diagram per major variation section (Najdorf, Dragon, etc.)

Write the expanded section now:"""
        else:
            # Regeneration attempt with feedback
            contamination_info = extract_contamination_details(last_content, expected_signature)
            prompt = f"""REGENERATION ATTEMPT {attempt}/{max_retries}

CRITICAL ISSUE DETECTED: Your previous response included diagrams from the WRONG opening.

CONTAMINATION FOUND:
{contamination_info}

THIS QUERY IS ABOUT: {opening_name}
REQUIRED OPENING MOVES: {expected_signature}

Section Title: {title}
Key Points:
{bullets_text}

Please regenerate this section with:
1. ONLY diagrams that start with: {expected_signature}
2. NO diagrams from other openings (especially Sicilian Defense with 1.e4 c5)
3. Ensure all diagrams are relevant to {opening_name}

Requirements:
- Write 150-300 words in an educational, engaging style
- Include specific chess moves in algebraic notation
- Include exactly one [DIAGRAM: move sequence] marker per major variation discussed
- Place it IMMEDIATELY after introducing the key moves
- ALL diagrams must start with the correct opening moves for {opening_name}

Write the corrected expanded section now:"""

        print(f"\n[ITEM-008] Section: {title} - Attempt {attempt + 1}/{max_retries + 1}")

        # Generate content
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=800
        )

        generated_content = response.choices[0].message.content.strip()
        last_content = generated_content

        # Validate the generated content
        diagrams = re.findall(r'\[DIAGRAM:\s*([^\]]+)\]', generated_content)
        is_valid = True

        if diagrams:
            for diagram_moves in diagrams:
                moves = diagram_moves.strip()
                # Check if diagram starts with expected signature
                if not moves.startswith(expected_signature[:10]):
                    is_valid = False
                    print(f"[ITEM-008]   ❌ Contamination detected: {moves[:50]}...")
                    break

        if is_valid:
            print(f"[ITEM-008]   ✅ Section validated successfully after {attempt + 1} attempt(s)")
            return (generated_content, True, attempt + 1)
        else:
            print(f"[ITEM-008]   ⚠️  Validation failed, will retry...")

    # Max retries exhausted
    print(f"[ITEM-008]   ❌ Failed after {max_retries + 1} attempts, using last generation")
    return (last_content, False, max_retries + 1)


def stage2_expand_sections(openai_client, query: str, sections: list, context: str) -> list:
    """
    Stage 2: Expand each section into 150-300 words with chess notation and diagram markers.

    Args:
        openai_client: OpenAI client instance
        query: User's query
        sections: List of section dicts from stage 1
        context: Combined reference text

    Returns:
        List of expanded section texts
    """
    # ITEM-008: Detect opening BEFORE loop to use in retry logic
    detected_opening, expected_signature, eco_code = detect_opening(query)

    if detected_opening:
        print(f"\n[ITEM-008] Detected opening: {detected_opening}")
        print(f"[ITEM-008] Expected signature: {expected_signature}")
        print(f"[ITEM-008] Regeneration feedback loop ENABLED")
    else:
        print(f"\n[ITEM-008] No opening detected - regeneration feedback loop DISABLED")

    expanded_sections = []

    # ITEM-008: Use regeneration feedback loop for each section
    for section in sections:
        title = section['title']

        if detected_opening:
            # Use retry logic with contamination detection
            print(f"\n[ITEM-008] Processing section '{title}' with retry logic")
            expanded_content, success, attempts = generate_section_with_retry(
                openai_client, section, query, context,
                detected_opening, expected_signature
            )

            if success:
                print(f"[ITEM-008] ✅ Section '{title}' generated successfully after {attempts} attempt(s)")
            else:
                print(f"[ITEM-008] ⚠️ Section '{title}' still contaminated after {attempts} attempts")

            expanded_sections.append(f"## {title}\n\n{expanded_content}")
            print(f"[Stage 2] Expanded section: {title} ({len(expanded_content.split())} words)")
        else:
            # No opening detected - use simplified generation without retry
            bullets = section['bullets']
            bullets_text = "\n".join([f"- {b}" for b in bullets])

            prompt = f"""You are writing a section of a chess guide. Expand the following outline into 150-300 words.

Section Title: {title}
Key Points:
{bullets_text}

Reference Context (if needed):
{context[:1500]}

Requirements:
- Write 150-300 words in an educational, engaging style
- Include specific chess moves in algebraic notation where appropriate
- Be specific and practical
- Focus on understanding, not just memorization

Write the expanded section now:"""

            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert chess instructor creating educational content."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=800
            )

            expanded = response.choices[0].message.content.strip()
            expanded_sections.append(f"## {title}\n\n{expanded}")
            print(f"[Stage 2] Expanded section: {title} ({len(expanded.split())} words)")

    # ITEM-008: Validation now happens during generation inside generate_section_with_retry()
    # Old post-loop validation removed since it's redundant
    return expanded_sections


def validate_stage2_diagrams(expanded_sections: list, opening_name: str) -> bool:
    """
    FIX 3: Validate that all diagram markers match the expected opening signature.

    Args:
        expanded_sections: List of expanded section texts from Stage 2
        opening_name: Name of the opening being discussed (e.g., "Italian Game")

    Returns:
        True if all diagrams match the opening signature, False otherwise
    """
    print(f"\n[Validation] validate_stage2_diagrams called for: {opening_name}")
    print(f"[Validation] Number of sections to validate: {len(expanded_sections)}")

    # Opening signatures for validation
    opening_signatures = {
        "Italian Game": "1.e4 e5 2.Nf3 Nc6 3.Bc4",
        "Sicilian Defense": "1.e4 c5",
        "French Defense": "1.e4 e6",
        "Caro-Kann Defense": "1.e4 c6",
        "Ruy Lopez": "1.e4 e5 2.Nf3 Nc6 3.Bb5",
        "Queen's Gambit": "1.d4 d5 2.c4",
        "King's Indian Defense": "1.d4 Nf6 2.c4 g6",
        "Nimzo-Indian Defense": "1.d4 Nf6 2.c4 e6 3.Nc3 Bb4",
        "English Opening": "1.c4",
        "Catalan Opening": "1.d4 Nf6 2.c4 e6 3.g3"
    }

    # Illegal moves for each opening (for continuation validation)
    illegal_starts = {
        "Sicilian Defense": ["1.d4", "1.c4", "1.Nf3"],
        "Italian Game": ["1.d4", "1.c4", "1.Nf3"],
        "French Defense": ["1.d4", "1.c4", "1.Nf3"],
        "Ruy Lopez": ["1.d4", "1.c4"],
        "King's Indian Defense": ["1.e4"],
        "Queen's Gambit": ["1.e4"],
    }

    if opening_name not in opening_signatures:
        print(f"[Validation] No signature found for opening: {opening_name}")
        return True  # Skip validation for unknown openings

    expected_signature = opening_signatures[opening_name]
    print(f"[Validation] Expected signature: {expected_signature}")
    all_valid = True

    # Extract all diagram markers from expanded sections
    import re
    total_diagrams = 0
    for i, section in enumerate(expanded_sections):
        diagrams = re.findall(r'\[DIAGRAM:\s*([^\]]+)\]', section)

        for diagram_moves in diagrams:
            total_diagrams += 1
            diagram_moves = diagram_moves.strip()

            if total_diagrams == 1:
                # First diagram: STRICT validation - must start from move 1 and match signature
                if not diagram_moves.startswith("1."):
                    print(f"[Validation]   ❌ First diagram must start from move 1!")
                    all_valid = False
                elif not diagram_moves.startswith(expected_signature):
                    print(f"[Validation]   ❌ First diagram doesn't match opening signature!")
                    print(f"[Validation]      Expected: {expected_signature}")
                    print(f"[Validation]      Got: {diagram_moves[:50]}...")
                    all_valid = False
                else:
                    print(f"[Validation]   ✅ First diagram valid - matches {opening_name}")
            else:
                # Subsequent diagrams: FLEXIBLE validation
                if diagram_moves.startswith("1."):
                    # If it starts from move 1, it must match the signature
                    if diagram_moves.startswith(expected_signature):
                        print(f"[Validation]   ✅ Valid - matches signature")
                    else:
                        print(f"[Validation]   ❌ Starts from move 1 but wrong opening!")
                        print(f"[Validation]      Expected: {expected_signature}")
                        print(f"[Validation]      Got: {diagram_moves[:50]}...")
                        all_valid = False
                else:
                    # Continuation diagram - check for contradictions
                    has_contradiction = False
                    for illegal in illegal_starts.get(opening_name, []):
                        if illegal in diagram_moves:
                            print(f"[Validation]   ❌ Continuation contains illegal moves: {illegal}")
                            has_contradiction = True
                            all_valid = False
                            break
                    if not has_contradiction:
                        print(f"[Validation]   ⚠️  Continuation (move {diagram_moves.split('.')[0]}+) - allowing")

    print(f"\n[Validation] Summary: {total_diagrams} total diagram(s) checked")
    if all_valid:
        print(f"[Validation] ✅ All diagrams match opening signature: {opening_name}")
    else:
        print(f"[Validation] ❌ Some diagrams do NOT match opening signature!")

    return all_valid


def stage3_final_assembly(openai_client, query: str, expanded_sections: list) -> str:
    """
    Stage 3: Assemble expanded sections into coherent 800-1500 word article.

    Args:
        openai_client: OpenAI client instance
        query: User's query
        expanded_sections: List of expanded section texts

    Returns:
        Final synthesized article text
    """
    sections_text = "\n\n".join(expanded_sections)

    # Count diagrams BEFORE Stage 3
    diagram_count = sections_text.count('[DIAGRAM:')
    print(f"[Stage 3] Input has {diagram_count} diagram markers")

    prompt = f"""You are combining multiple draft sections into a cohesive chess article.

CRITICAL STRUCTURE INTEGRITY REQUIREMENT:
- Input contains {diagram_count} diagram markers in the format [DIAGRAM: ...].
- Every diagram marker MUST appear in the final article exactly as written.
- These markers are structural and cannot be edited, merged, or deleted.
- You may move them for readability but not remove them.
- Output MUST contain exactly {diagram_count} markers.
- If any are missing, your answer is INVALID.

User Question: {query}

Input sections:
{sections_text}

Requirements:
- Add smooth transitions between sections
- Ensure logical flow from basics to advanced concepts
- Add a brief "Study Recommendations" section at the end
- Target length: 800-1500 words
- Preserve all {diagram_count} diagram markers exactly

Now produce the final integrated article:"""

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=2500
    )

    article = response.choices[0].message.content.strip()

    # POST-VALIDATION: Check diagram count
    output_diagram_count = article.count('[DIAGRAM:')
    print(f"[Stage 3] Output has {output_diagram_count}/{diagram_count} markers")

    if output_diagram_count < diagram_count:
        print(f"[Stage 3] ⚠️ VALIDATION FAILED: Missing {diagram_count - output_diagram_count} markers")
        print(f"[Stage 3] Attempting corrective retry...")

        correction_prompt = f"""You failed to preserve all diagram markers in your previous attempt.

ORIGINAL STAGE 3 INPUT (which had {diagram_count} markers):
{sections_text}

CRITICAL STRUCTURE INTEGRITY REQUIREMENT:
- Input contains {diagram_count} diagram markers in the format [DIAGRAM: ...].
- Every diagram marker MUST appear in the final article exactly as written.
- Output MUST contain exactly {diagram_count} markers.
- If any are missing, your answer is INVALID.

Your previous output had only {output_diagram_count} markers (INCORRECT).

Requirements:
- Add smooth transitions between sections
- Ensure logical flow from basics to advanced concepts
- Add a brief "Study Recommendations" section at the end
- Target length: 800-1500 words
- Preserve all {diagram_count} diagram markers exactly

Regenerate the complete article with ALL {diagram_count} markers preserved:"""

        retry_response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": correction_prompt}],
            max_completion_tokens=2500
        )

        article = retry_response.choices[0].message.content.strip()
        final_count = article.count('[DIAGRAM:')
        print(f"[Stage 3] Retry result: {final_count}/{diagram_count} markers")

    word_count = len(article.split())
    print(f"[Stage 3] Final article: {word_count} words")

    return article


def validate_and_fix_diagrams(openai_client, query: str, expanded_sections: list, context: str) -> list:
    """
    Validate that expanded sections contain [DIAGRAM: ...] markers.
    If missing, regenerate sections with stronger diagram enforcement.

    Args:
        openai_client: OpenAI client
        query: User's query
        expanded_sections: List of section texts
        context: Combined reference text

    Returns:
        List of validated section texts with diagrams
    """
    # Check if ANY diagrams exist in the expanded sections
    combined_text = "\n\n".join(expanded_sections)
    diagram_count = combined_text.count('[DIAGRAM:')

    print(f"\n[Validation] Checking diagram generation...")
    print(f"[Validation] Found {diagram_count} diagram markers in expanded sections")

    if diagram_count == 0:
        print(f"[Validation] ⚠️  NO DIAGRAMS FOUND! Attempting to add diagrams...")

        # Simple fallback: Add a basic diagram to the first section about the opening
        # Extract opening name from query
        query_lower = query.lower()

        # Try to add a relevant diagram based on the query
        if "italian" in query_lower:
            diagram_marker = "[DIAGRAM: 1.e4 e5 2.Nf3 Nc6 3.Bc4]"
            insert_text = f"\n\nThe Italian Game arises after 1.e4 e5 2.Nf3 Nc6 3.Bc4. {diagram_marker} This position is the starting point for many variations.\n"
        elif "sicilian" in query_lower:
            diagram_marker = "[DIAGRAM: 1.e4 c5]"
            insert_text = f"\n\nThe Sicilian Defence begins with 1.e4 c5. {diagram_marker} This is the fundamental position of the opening.\n"
        elif "french" in query_lower:
            diagram_marker = "[DIAGRAM: 1.e4 e6]"
            insert_text = f"\n\nThe French Defence starts with 1.e4 e6. {diagram_marker} This marks the beginning of this solid defensive system.\n"
        else:
            # Generic fallback
            diagram_marker = "[DIAGRAM: starting position]"
            insert_text = f"\n\n{diagram_marker} We'll examine the key positions that arise from this opening.\n"

        # Insert the diagram into the first section (after the title)
        if expanded_sections:
            first_section = expanded_sections[0]
            # Find the first paragraph break after the title
            lines = first_section.split('\n')
            if len(lines) >= 3:
                # Insert after title and first paragraph
                lines.insert(3, insert_text)
                expanded_sections[0] = '\n'.join(lines)
                print(f"[Validation] ✅ Added fallback diagram: {diagram_marker}")
            else:
                expanded_sections[0] = first_section + insert_text
                print(f"[Validation] ✅ Added fallback diagram at end: {diagram_marker}")

    return expanded_sections


def synthesize_answer(openai_client, query: str, top_chunks: list) -> str:
    """
    Complete 3-stage synthesis pipeline.

    Args:
        openai_client: OpenAI client instance
        query: User's query
        top_chunks: List of top ranked text chunks

    Returns:
        Synthesized answer text
    """
    print("\n" + "="*60)
    print("MULTI-STAGE SYNTHESIS PIPELINE")
    print("="*60)

    # Stage 1: Generate outline
    outline = stage1_generate_outline(openai_client, query, top_chunks)

    # Stage 2: Expand sections
    context = "\n\n".join([chunk[:1000] for chunk in top_chunks[:8]])
    expanded_sections = stage2_expand_sections(
        openai_client,
        query,
        outline['sections'],
        context
    )

    # Stage 2.5: Validate diagrams and fix if missing
    expanded_sections = validate_and_fix_diagrams(
        openai_client,
        query,
        expanded_sections,
        context
    )

    # Stage 3: Final assembly
    final_article = stage3_final_assembly(openai_client, query, expanded_sections)

    print("="*60 + "\n")

    return final_article




# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/test', methods=['POST'])
def test():
    """Test endpoint."""
    return jsonify({'status': 'ok', 'message': 'test works'})


@app.route('/query', methods=['POST'])
def query():
    """Handle query requests with detailed timing."""
    print("=" * 80)
    print("QUERY ENDPOINT CALLED")
    print("=" * 80)
    try:
        start = time.time()

        # Step 1: Parse request
        data = request.get_json()
        query_text = data.get('query', '').strip()
        t1 = time.time()
        print(f"⏱  Request parsing: {t1-start:.2f}s")

        if not query_text:
            return jsonify({'error': 'Query cannot be empty'}), 400

        # Step 1.5: Classify query and get canonical FEN if available
        query_type, concept_key, canonical_fen = query_classifier.get_canonical_fen_for_query(
            query_text,
            CANONICAL_FENS
        )
        print(f"📋 Query type: {query_type}")
        if concept_key:
            print(f"📋 Concept: {concept_key}")
        if canonical_fen:
            print(f"✓ Using canonical FEN: {canonical_fen}")

        # Step 2: Generate embedding
        query_vector = embed_query(OPENAI_CLIENT, query_text)
        t2 = time.time()
        print(f"⏱  Embedding: {t2-t1:.2f}s")

        # Step 3: Search Qdrant
        candidates = semantic_search(QDRANT_CLIENT, query_vector, top_k=TOP_K)
        t3 = time.time()
        print(f"⏱  Qdrant search: {t3-t2:.2f}s")

        # Step 4: Rerank with GPT-5
        ranked_results = gpt5_rerank(OPENAI_CLIENT, query_text, candidates, top_k=TOP_N)
        t4 = time.time()
        print(f"⏱  GPT-5 reranking: {t4-t3:.2f}s")

        # Step 5: Format results for web display
        results = []
        for candidate, score in ranked_results:
            payload = candidate.payload

            # Extract metadata
            book_name = payload.get('book_name', 'Unknown')
            if book_name.endswith('.epub') or book_name.endswith('.mobi'):
                book_name = book_name[:-5]

            text = payload.get('text', '')
            chapter = payload.get('chapter_title', '')

            # Extract chess positions from text (pass query for relevance filtering)
            positions = extract_chess_positions(text, query=query_text)

            # Format result
            result = {
                'score': round(score, 1),
                'book_name': book_name,
                'book': book_name,  # Keep for backwards compatibility
                'chapter_title': chapter,
                'chapter': chapter,  # Keep for backwards compatibility
                'text': text,
                'positions': positions,
                'has_positions': len(positions) > 0
            }
            results.append(result)

        t5 = time.time()
        print(f"⏱  Response formatting: {t5-t4:.2f}s")

        # DEBUG: Check position extraction
        print("\n=== POSITION EXTRACTION DEBUG ===")
        for i, result in enumerate(results[:5]):
            chunk_text = result.get('text', '')
            print(f"\nSource {i+1}:")
            print(f"  Book: {result.get('book_name', 'unknown')}")
            print(f"  Text preview: {chunk_text[:100]}...")

            # Check what position data exists
            if 'positions' in result:
                print(f"  ✅ Positions array length: {len(result['positions'])}")
                if len(result['positions']) > 0:
                    print(f"     First position: {result['positions'][0]}")
            else:
                print(f"  ❌ No 'positions' key")

            if 'has_positions' in result:
                print(f"  has_positions flag: {result['has_positions']}")
            else:
                print(f"  ❌ No 'has_positions' key")

            # Try to detect patterns in text
            import re
            fen_pattern = r'[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}'
            moves_pattern = r'1\.\s*e4\s+c5'

            if re.search(fen_pattern, chunk_text):
                print(f"  📋 FEN detected in text")
            if re.search(moves_pattern, chunk_text, re.IGNORECASE):
                print(f"  ♟ Moves '1.e4 c5' detected in text")
        print("=== END POSITION DEBUG ===\n")

        # Step 6: Synthesize coherent answer using 3-stage pipeline
        print(f"⏱  Starting 3-stage synthesis pipeline...")
        synthesis_start = time.time()

        # Prepare context with canonical FEN if available
        context_chunks = [r['text'] for r in results[:8]]
        if canonical_fen:
            context_chunks.insert(0, f"[CANONICAL POSITION: {canonical_fen}]")
            print(f"📋 Injected canonical FEN into synthesis context")

        # Call the new 3-stage synthesis function
        synthesized_answer = synthesize_answer(
            OPENAI_CLIENT,
            query_text,
            context_chunks
        )

        t6 = time.time()
        print(f"⏱  3-stage synthesis complete: {t6-synthesis_start:.2f}s")

        # Step 6.5: Extract and parse diagram markers from synthesized text
        print(f"\n⏱  Extracting diagram markers...")
        diagram_start = time.time()

        diagram_positions = extract_diagram_markers(synthesized_answer)
        synthesized_answer = replace_markers_with_ids(synthesized_answer, diagram_positions)

        diagram_time = time.time() - diagram_start
        print(f"⏱  Diagram extraction complete: {diagram_time:.2f}s")
        print(f"📋 Extracted {len(diagram_positions)} diagram positions from synthesis")

        total = time.time() - start
        print(f"🎯 TOTAL: {total:.2f}s")
        print("=" * 80)

        # DEBUG: Check what's actually being sent to frontend
        print("\n" + "="*60)
        print("FINAL RESPONSE TO FRONTEND - POSITION DEBUG")
        print("="*60)

        for i, source in enumerate(results[:5]):
            print(f"\nSource {i+1}:")
            print(f"  Book: {source.get('book_name', 'unknown')[:50]}")
            print(f"  Has 'positions' key: {'positions' in source}")
            print(f"  Has 'has_positions' key: {'has_positions' in source}")

            if 'positions' in source:
                positions = source['positions']
                print(f"  positions value: {positions}")
                print(f"  positions type: {type(positions)}")
                print(f"  positions length: {len(positions) if positions else 0}")

                if positions:
                    print(f"  First position: {positions[0]}")

            if 'has_positions' in source:
                print(f"  has_positions: {source['has_positions']}")

        print("\n" + "="*60)
        print("END POSITION DEBUG")
        print("="*60 + "\n")

        # Collect positions from top sources for answer section
        synthesized_positions = []
        for result in results[:5]:
            if result.get('has_positions') and result.get('positions'):
                for pos in result['positions']:
                    # Avoid duplicates (same FEN)
                    if not any(p['fen'] == pos['fen'] for p in synthesized_positions):
                        synthesized_positions.append(pos)
                        if len(synthesized_positions) >= 2:  # Max 2 boards in answer
                            break
            if len(synthesized_positions) >= 2:
                break

        print(f"📋 Collected {len(synthesized_positions)} positions for answer section")

        # Prepare response
        response_data = {
            'success': True,
            'query': query_text,
            'answer': synthesized_answer,
            'positions': synthesized_positions,  # Positions extracted from source chunks
            'diagram_positions': diagram_positions,  # NEW: Positions from [DIAGRAM: ...] markers in synthesis
            'sources': results[:5],
            'results': results,  # Keep for backwards compatibility
            'timing': {
                'embedding': round(t2 - t1, 2),
                'search': round(t3 - t2, 2),
                'reranking': round(t4 - t3, 2),
                'formatting': round(t5 - t4, 2),
                'synthesis': round(t6 - synthesis_start, 2),
                'diagrams': round(diagram_time, 2),
                'total': round(total, 2)
            }
        }

        # DEBUG: Log final response structure
        print("\n" + "="*80)
        print("=== FINAL RESPONSE STRUCTURE ===")
        print(f"Response keys: {list(response_data.keys())}")
        print(f"Has 'positions' key: {'positions' in response_data}")
        if 'positions' in response_data:
            print(f"Number of positions: {len(response_data['positions'])}")
            if len(response_data['positions']) > 0:
                print(f"First position keys: {list(response_data['positions'][0].keys())}")
                print(f"First position FEN: {response_data['positions'][0].get('fen', 'N/A')}")
                print(f"First position has SVG: {bool(response_data['positions'][0].get('svg'))}")
        print("="*80 + "\n")

        return jsonify(response_data)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR IN /query ENDPOINT:")
        print(error_details)
        return jsonify({'error': str(e), 'details': error_details}), 500


@app.route('/fen_to_lichess', methods=['POST'])
def fen_to_lichess():
    """Convert FEN to Lichess URL."""
    try:
        data = request.get_json()
        fen = data.get('fen', '')

        if not fen:
            return jsonify({'error': 'FEN cannot be empty'}), 400

        url = create_lichess_url(fen)
        return jsonify({'url': url})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set!")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        exit(1)

    print("=" * 80)
    print("SYSTEM A WEB UI")
    print("=" * 80)
    print(f"Corpus: 357,957 chunks from 1,052 books")
    print(f"Starting server at http://127.0.0.1:5001")
    print("=" * 80)

    app.run(debug=False, host='0.0.0.0', port=5001)
