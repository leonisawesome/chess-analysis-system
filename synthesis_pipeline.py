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

print("\n*** [CANARY] synthesis_pipeline.py VERSION: 6.1a-2025-11-10 LOADED ***\n")

# Global variable to hold canonical library prompt
CANONICAL_POSITIONS_PROMPT = None

def build_canonical_positions_prompt():
    """
    Build a SIMPLIFIED prompt section from canonical_positions.json.
    
    Returns ~400 chars instead of 8,314 chars.
    Lists categories with counts, not all 73 positions.
    """
    try:
        with open('canonical_positions.json', 'r') as f:
            library = json.load(f)

        prompt_lines = [
            "",
            "CANONICAL POSITIONS LIBRARY:",
            "Use @canonical/{category}/{id} format for tactical/structural concepts.",
            "",
            "Available categories:"
        ]

        # Just list categories and counts with 1-2 example IDs
        for category, positions in library.items():
            count = len(positions)
            example_ids = list(positions.keys())[:2]
            examples = ', '.join(example_ids)
            if count > 2:
                examples += ', ...'
            prompt_lines.append(f"  - {category} ({count}): {examples}")

        prompt_lines.extend([
            "",
            "Format: [DIAGRAM: @canonical/{category}/{id} | Caption: description]",
            "Example: [DIAGRAM: @canonical/pins/bishop_pin_knight_king | Caption: Bishop pins knight]",
            ""
        ])

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

Context from chess sources (books and game files):
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

IMPORTANT: You will receive sources from two types of materials:
1. **Books** (labeled "[Source N: Book - ...]"): Prose explanations with strategic concepts,
   principles, and general understanding. Use these for explaining WHY and WHAT.
2. **PGN files** (labeled "[Source N: PGN - ...]"): Annotated game variations with move
   sequences and annotations. Use these for specific move sequences, concrete examples,
   and practical repertoire lines. Use these for showing HOW with specific moves.

When synthesizing your answer:
- Integrate book explanations with PGN examples
- Use book sources to explain strategic concepts and ideas
- Use PGN sources to show concrete move sequences and variations
- Reference both types naturally in your explanation
- Focus on clear explanations of strategic concepts and concrete variations
- CRITICAL: You MUST NOT write the text string "[DIAGRAM:" anywhere in your response. All chess diagrams will be provided separately via images. Writing [DIAGRAM: ...] will break the system.

Write 2-3 detailed paragraphs per section."""

    for i, section in enumerate(sections, 1):
        section_prompt = f"""Question: {query}

Section {i}/{len(sections)}: {section['title']}
Focus: {section['description']}

Context sources (Books provide concepts, PGN files provide concrete variations):
{context[:3000]}

Write detailed content for this section. Include 2-4 diagram markers showing key positions.
Synthesize information from both book sources (strategic ideas) and PGN sources (specific lines)."""

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

The sections synthesize information from both chess books (strategic concepts) and
PGN game files (concrete variations). Maintain this natural integration.

Guidelines:
- Write natural transitions between sections
- Maintain all [DIAGRAM: ...] markers exactly as provided
- Keep technical accuracy
- Use clear, engaging prose
- Ensure logical flow from introduction to conclusion
- Preserve the balance between conceptual explanations and concrete examples"""

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

        final_answer = response.choices[0].message.content

        # Strip any residual diagram markers (fallback safety)
        final_answer = re.sub(r'\[DIAGRAM:[^\]]+\]', '', final_answer)

        return final_answer

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
