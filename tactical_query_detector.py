"""
Tactical Query Detection and Canonical Diagram Injection
Purpose: Bypass GPT-5 diagram generation for tactical queries
"""
import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Tactical keywords that trigger canonical injection
TACTICAL_KEYWORDS = {
    'pin', 'pins', 'pinned', 'pinning',
    'fork', 'forks', 'forking',
    'skewer', 'skewers', 'skewering',
    'discovered', 'discovered attack', 'discovered check',
    'deflection', 'deflect',
    'decoy',
    'clearance',
    'interference',
    'removal', 'remove defender',
    'x-ray', 'xray',
    'windmill',
    'smothered mate',
    'zugzwang',
    'zwischenzug'
}

def is_tactical_query(query: str) -> bool:
    """
    Detect if user query is asking about tactical concepts.

    Args:
        query: User's search query

    Returns:
        bool: True if tactical query detected
    """
    query_lower = query.lower()

    # Check for tactical keywords
    for keyword in TACTICAL_KEYWORDS:
        if keyword in query_lower:
            logger.info(f"Tactical query detected: keyword '{keyword}' found in query")
            return True

    return False

def infer_tactical_category(query: str) -> Optional[str]:
    """
    Infer canonical category from query.

    Args:
        query: User's search query

    Returns:
        str: Category name or None
    """
    query_lower = query.lower()

    # Map keywords to categories
    if any(k in query_lower for k in ['pin', 'pins', 'pinned', 'pinning']):
        return 'pins'
    elif any(k in query_lower for k in ['fork', 'forks', 'forking']):
        return 'forks'
    elif any(k in query_lower for k in ['skewer', 'skewers', 'skewering']):
        return 'skewers'
    elif any(k in query_lower for k in ['discovered']):
        return 'discovered_attacks'
    elif any(k in query_lower for k in ['deflection', 'deflect']):
        return 'deflection'
    elif 'decoy' in query_lower:
        return 'decoy'
    elif 'clearance' in query_lower:
        return 'clearance'
    elif 'interference' in query_lower:
        return 'interference'
    elif any(k in query_lower for k in ['removal', 'remove']):
        return 'removal_of_defender'

    return None

def inject_canonical_diagrams(query: str, canonical_positions: Dict) -> List[Dict]:
    """
    Inject canonical diagrams for tactical query.

    Args:
        query: User's search query
        canonical_positions: Canonical positions library

    Returns:
        List of diagram objects
    """
    category = infer_tactical_category(query)

    if not category or category not in canonical_positions:
        logger.warning(f"Could not infer category or category not found: {category}")
        return []

    positions = canonical_positions[category]
    diagrams = []

    # Inject up to 5 canonical positions
    for i, (pos_id, pos_data) in enumerate(list(positions.items())[:5]):
        diagram = {
            'id': f'@canonical/{category}/{pos_id}',
            'fen': pos_data.get('fen'),
            'caption': pos_data.get('default_caption', f'{category} example'),
            'tactic': pos_data.get('tactic'),
            'source': 'canonical',
            'injected': True,
            'category': category
        }
        diagrams.append(diagram)
        logger.info(f"Injected canonical diagram: {category}/{pos_id}")

    logger.info(f"Injected {len(diagrams)} canonical diagrams for category '{category}'")
    return diagrams

def strip_diagram_markers(text: str) -> str:
    """
    Remove all [DIAGRAM: ...] markers from text.

    Args:
        text: GPT-5 generated text

    Returns:
        Text with diagram markers removed
    """
    # Remove [DIAGRAM: ...] markers
    cleaned = re.sub(r'\[DIAGRAM:.*?\]', '', text, flags=re.DOTALL)
    return cleaned
