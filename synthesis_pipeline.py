"""
Synthesis Pipeline Module

Handles:
- 3-stage synthesis process (outline → expand → assemble)
- OpenAI GPT-5 integration
- Section generation with diagram markers
- Quality validation and assembly
"""

import re
import json
from openai import OpenAI

# Global variable to hold canonical library prompt
CANONICAL_POSITIONS_PROMPT = None

def build_canonical_positions_prompt():
    """
    Build a dynamic prompt section from canonical_positions.json.

    Returns:
        str: Formatted prompt section listing available canonical positions
    """
    try:
        with open('canonical_positions.json', 'r') as f:
            library = json.load(f)

        prompt_lines = [
            "",
            "CANONICAL POSITIONS LIBRARY:",
            "You can reference verified positions using @canonical/category/id format.",
            "",
            "Available positions:"
        ]

        # Build a compact listing
        for category, positions in library.items():
            prompt_lines.append(f"\n{category}:")
            for pos_id, pos_data in positions.items():
                caption = pos_data.get('caption', 'No caption')
                # Truncate long captions
                if len(caption) > 60:
                    caption = caption[:57] + "..."
                prompt_lines.append(f"  - @canonical/{category}/{pos_id}")
                prompt_lines.append(f"    {caption}")

        prompt_lines.append("")
        prompt_lines.append("USAGE EXAMPLES:")
        prompt_lines.append("- [DIAGRAM: @canonical/forks/knight_fork_queen_rook | Caption: Classic knight fork pattern]")
        prompt_lines.append("- [DIAGRAM: @canonical/pawn_structures/isolated_queen_pawn | Caption: The isolated queen pawn structure]")
        prompt_lines.append("")
        prompt_lines.append("ERROR HANDLING:")
        prompt_lines.append("- If specific ID not found → fallback to any position in that category")
        prompt_lines.append("- If category not found → silent skip (no diagram rendered)")
        prompt_lines.append("- Use canonical positions for tactical/structural concepts")
        prompt_lines.append("- Use move sequences (1.e4 e5...) for opening lines")
        prompt_lines.append("")

        return "\n".join(prompt_lines)

    except FileNotFoundError:
        return "\nCANONICAL POSITIONS LIBRARY: Not available\n"
    except Exception as e:
        return f"\nCANONICAL POSITIONS LIBRARY: Error loading ({str(e)})\n"

def initialize_canonical_prompt():
    """
    Initialize the global canonical positions prompt.
    Call this once at application startup.
    """
    global CANONICAL_POSITIONS_PROMPT
    CANONICAL_POSITIONS_PROMPT = build_canonical_positions_prompt()
    print(f"✓ Initialized canonical positions prompt ({len(CANONICAL_POSITIONS_PROMPT)} chars)")

def get_canonical_prompt():
    """Get the canonical positions prompt section."""
    global CANONICAL_POSITIONS_PROMPT
    if CANONICAL_POSITIONS_PROMPT is None:
        initialize_canonical_prompt()
    return CANONICAL_POSITIONS_PROMPT


def stage1_generate_outline(openai_client: OpenAI, query: str, context: str,
                            opening_name: str = None) -> dict:
    """
    Stage 1: Generate outline for the answer.

    Args:
        openai_client: OpenAI client instance
        query: User's question
        context: Retrieved context from RAG
        opening_name: Detected opening name (optional)

    Returns:
        dict with 'sections' list
    """
    system_prompt = """You are a chess expert creating structured outlines for chess opening explanations.

Your task: Create a clear outline with 3-5 main sections.

Output format (JSON):
{
  "sections": [
    {"title": "Introduction", "description": "Brief overview"},
    {"title": "Main Ideas", "description": "Key strategic concepts"},
    {"title": "Key Variations", "description": "Important lines"}
  ]
}

Guidelines:
- Use clear, descriptive section titles
- Each section should have a 1-sentence description
- 3-5 sections total
- Focus on answering the user's question"""

    user_prompt = f"""Question: {query}

Context from chess literature:
{context[:4000]}

Create an outline that directly answers this question."""

    if opening_name:
        user_prompt += f"\n\nNote: This is about the {opening_name} opening."

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_completion_tokens=2000
        )

        import json
        outline = json.loads(response.choices[0].message.content)
        return outline

    except Exception as e:
        print(f"Stage 1 error: {e}")
        return {
            "sections": [
                {"title": "Overview", "description": "Introduction to the topic"},
                {"title": "Key Concepts", "description": "Main ideas and strategies"},
                {"title": "Practical Application", "description": "How to use this knowledge"}
            ]
        }


def stage2_expand_sections(openai_client: OpenAI, sections: list, query: str,
                          context: str, opening_name: str = None,
                          expected_signature: str = None,
                          validate_stage2_diagrams_func = None,
                          generate_section_with_retry_func = None,
                          canonical_fen: str = None) -> list:
    """
    Stage 2: Expand each section with detailed content and diagram markers.

    Args:
        openai_client: OpenAI client instance
        sections: List of sections from stage 1
        query: User's question
        context: Retrieved context
        opening_name: Detected opening name
        expected_signature: Expected opening signature for validation
        validate_stage2_diagrams_func: Function for diagram validation (from opening_validator)
        generate_section_with_retry_func: Function for retry logic (from opening_validator)

    Returns:
        List of expanded sections with content
    """
    expanded = []

    # Get canonical positions listing
    canonical_prompt = get_canonical_prompt()

    system_prompt = f"""You are a chess expert writing detailed explanations with visual diagrams.

CRITICAL DIAGRAM RULES:
1. Include diagrams using [DIAGRAM: <position> | Caption: <description>] format
2. <position> can be: move sequence (1.e4 e5 2.Nf3 Nc6 3.Bc4) OR FEN string OR @canonical reference
3. <description> is a DESCRIPTIVE caption explaining what the position shows
4. For openings: diagrams show 3-6 moves from the starting position
5. For middlegame concepts: use @canonical/ references or provided canonical FEN
6. Diagrams must match the opening/concept being discussed
7. Include 2-4 diagrams per section to illustrate key positions

DIAGRAM FORMAT (with optional TACTIC field):
- [DIAGRAM: <position> | Caption: <description>]
- [DIAGRAM: <position> | Caption: <description> | TACTIC: <type>]
- [DIAGRAM: @canonical/category/id | Caption: <description>]

The TACTIC field is OPTIONAL but helpful for validation. Use it when diagrams illustrate tactical concepts:
- fork (piece attacks 2+ opponent pieces)
- pin (piece immobilized by line attack)
- skewer (like pin but more valuable piece in front)
- development (piece placement in opening)

EXAMPLES:
- [DIAGRAM: 1.e4 e5 2.Nf3 Nc6 3.Bc4 | Caption: Italian Game starting position with White's bishop on c4 | TACTIC: development]
- [DIAGRAM: 1.d4 d5 2.c4 | Caption: Queen's Gambit - White offers the c-pawn to gain central control | TACTIC: development]
- [DIAGRAM: @canonical/forks/knight_fork_queen_rook | Caption: Classic knight fork pattern | TACTIC: fork]
- [DIAGRAM: @canonical/pins/bishop_pin_knight | Caption: Bishop pins knight to king | TACTIC: pin]

CAPTION GUIDELINES:
- Be concise (5-15 words)
- Describe what's HAPPENING in the position (strategic ideas, piece placement, key moves)
- Do NOT just repeat the move notation
- Focus on WHY this position is important
- TACTIC field is optional - only include it for tactical positions

IMPORTANT: ALWAYS wrap diagrams in [DIAGRAM: ... | Caption: ...] brackets
NEVER output bare FEN strings directly in the text without brackets

{canonical_prompt}

CANONICAL POSITION USAGE:
If a [CANONICAL POSITION: FEN] is provided in the context below:
- You MUST generate diagrams based on this position
- Use [DIAGRAM: FEN_STRING] format with the canonical FEN or variations
- Do NOT use opening move sequences for middlegame concepts
- The canonical position represents the KEY position for this concept

Example (opening):
"The Italian Game begins with [DIAGRAM: 1.e4 e5 2.Nf3 Nc6 3.Bc4] where White develops quickly..."

Example (middlegame with canonical FEN):
"In this position [DIAGRAM: r1bq1rk1/pp2bppp/2n1pn2/2pp4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 9], White launches the minority attack..."

Example (using canonical reference):
"The knight fork is a powerful tactic [DIAGRAM: @canonical/forks/knight_fork_queen_rook] where the knight attacks multiple pieces..."

Write 2-3 detailed paragraphs per section with diagrams."""

    for i, section in enumerate(sections, 1):
        section_prompt = f"""Question: {query}

Section {i}/{len(sections)}: {section['title']}
Focus: {section['description']}

Context:
{context[:3000]}

Write detailed content for this section. Include 2-4 diagram markers showing key positions."""

        # Add canonical FEN context if provided (for middlegame concepts)
        if canonical_fen:
            section_prompt += f"""

[CANONICAL POSITION: {canonical_fen}]

CRITICAL: This is the KEY position for understanding this concept.

DIAGRAM GENERATION REQUIREMENTS:
1. Generate 3-5 DIFFERENT diagrams showing variations from this position
2. Show the canonical position ONCE as the main example
3. Then show VARIATIONS: positions 1-2 moves after this position
4. Each diagram must have a DIFFERENT FEN (not the same FEN repeated)
5. Variations should illustrate key ideas: pawn advances, piece repositioning, etc.

Example:
- Diagram 1: [DIAGRAM: {canonical_fen}] (canonical position)
- Diagram 2: [DIAGRAM: <fen after king move>] (showing king advance)
- Diagram 3: [DIAGRAM: <fen after pawn push>] (showing pawn breakthrough)

Do NOT repeat the same FEN multiple times. Show PROGRESSION and VARIATIONS."""

        if opening_name:
            section_prompt += f"\n\nNote: This is about the {opening_name} opening."

        if expected_signature:
            section_prompt += f"\n\nIMPORTANT: All diagrams must start with {expected_signature}"

        try:
            # Use retry logic if available (ITEM-008)
            if generate_section_with_retry_func and expected_signature:
                content, attempt_count = generate_section_with_retry_func(
                    openai_client,
                    section,
                    query,
                    context[:3000],
                    opening_name,
                    expected_signature
                )
                expanded.append({
                    "title": section["title"],
                    "content": content,
                    "attempts": attempt_count
                })
            else:
                # Standard generation without retry
                response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": section_prompt}
                    ],
                    max_completion_tokens=3000
                )

                content = response.choices[0].message.content
                expanded.append({
                    "title": section["title"],
                    "content": content,
                    "attempts": 1
                })

        except Exception as e:
            print(f"Stage 2 error on section {i}: {e}")
            expanded.append({
                "title": section["title"],
                "content": f"[Error generating content for this section: {str(e)}]",
                "attempts": 1
            })

    # Validate diagrams if validation function provided
    if validate_stage2_diagrams_func and expected_signature:
        expanded = validate_stage2_diagrams_func(expanded, opening_name)

    return expanded


def stage3_final_assembly(openai_client: OpenAI, expanded_sections: list,
                         query: str, opening_name: str = None) -> str:
    """
    Stage 3: Assemble final answer with smooth transitions.

    Args:
        openai_client: OpenAI client instance
        expanded_sections: List of expanded sections
        query: User's question
        opening_name: Detected opening name

    Returns:
        Final assembled answer as string
    """
    system_prompt = """You are a chess expert creating a cohesive, well-written article.

Your task: Combine the sections into a smooth, flowing article.

Guidelines:
- Write natural transitions between sections
- Maintain all [DIAGRAM: ...] markers exactly as provided
- Keep technical accuracy
- Use clear, engaging prose
- Ensure logical flow from introduction to conclusion"""

    sections_text = "\n\n".join([
        f"## {section['title']}\n{section['content']}"
        for section in expanded_sections
    ])

    assembly_prompt = f"""Question: {query}

Sections to assemble:
{sections_text}

Create a cohesive article that flows naturally. Maintain all diagram markers."""

    if opening_name:
        assembly_prompt += f"\n\nTitle: Understanding the {opening_name}"

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": assembly_prompt}
            ],
            max_completion_tokens=6000
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"Stage 3 error: {e}")
        # Fallback: just concatenate sections
        return "\n\n".join([
            f"## {section['title']}\n\n{section['content']}"
            for section in expanded_sections
        ])


def synthesize_answer(openai_client: OpenAI, query: str, context: str,
                     opening_name: str = None, expected_signature: str = None,
                     validate_stage2_diagrams_func = None,
                     generate_section_with_retry_func = None,
                     canonical_fen: str = None) -> str:
    """
    Main synthesis pipeline: orchestrates all 3 stages.

    Args:
        openai_client: OpenAI client instance
        query: User's question
        context: Retrieved context from RAG
        opening_name: Detected opening name
        expected_signature: Expected opening signature for ITEM-008 validation
        validate_stage2_diagrams_func: Validation function from opening_validator
        generate_section_with_retry_func: Retry function from opening_validator

    Returns:
        Final synthesized answer
    """
    print(f"🎯 Starting 3-stage synthesis for: {query}")

    # Stage 1: Generate outline
    print("  Stage 1: Generating outline...")
    outline = stage1_generate_outline(openai_client, query, context, opening_name)
    print(f"    ✓ Created {len(outline['sections'])} sections")

    # Stage 2: Expand sections
    print("  Stage 2: Expanding sections...")
    expanded = stage2_expand_sections(
        openai_client,
        outline['sections'],
        query,
        context,
        opening_name,
        expected_signature,
        validate_stage2_diagrams_func,
        generate_section_with_retry_func,
        canonical_fen
    )
    print(f"    ✓ Expanded {len(expanded)} sections")

    # Stage 3: Final assembly
    print("  Stage 3: Final assembly...")
    final_answer = stage3_final_assembly(openai_client, expanded, query, opening_name)
    print(f"    ✓ Assembled final answer ({len(final_answer)} chars)")

    return final_answer
