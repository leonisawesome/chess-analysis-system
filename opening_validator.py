"""
Opening Validation Module

Handles:
- ITEM-008: Opening contamination detection and prevention  
- Diagram validation against opening signatures
- Section regeneration with feedback loop
- Opening-specific validation rules
"""

import re


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


def validate_stage2_diagrams(expanded_sections: list, opening_name: str) -> list:
    """
    FIX 3: Validate that all diagram markers match the expected opening signature.

    Args:
        expanded_sections: List of expanded section texts from Stage 2
        opening_name: Name of the opening being discussed (e.g., "Italian Game")

    Returns:
        expanded_sections list (unchanged - validation prints warnings only)
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
        return expanded_sections  # Skip validation for unknown openings

    expected_signature = opening_signatures[opening_name]
    print(f"[Validation] Expected signature: {expected_signature}")
    all_valid = True

    # Extract all diagram markers from expanded sections
    import re
    total_diagrams = 0
    for i, section in enumerate(expanded_sections):
        section_content = section.get('content', '') if isinstance(section, dict) else section
        diagrams = re.findall(r'\[DIAGRAM:\s*([^\]]+)\]', section_content)

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

    print(f"[DEBUG] About to return expanded_sections (type: {type(expanded_sections)}, len: {len(expanded_sections)})")
    return expanded_sections


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


