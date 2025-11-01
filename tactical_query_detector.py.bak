"""
Tactical Query Detector (Option D - Emergency Fix)
FIXED: Multi-category detection using SET instead of if/elif chain
"""
import re
import json
import logging
from typing import List, Dict, Optional, Set
import uuid

logger = logging.getLogger(__name__)

# Tactical keywords mapped to categories
TACTICAL_KEYWORDS = {
    'pins': ['pin', 'pins', 'pinned', 'pinning'],
    'forks': ['fork', 'forks', 'forked', 'forking', 'knight fork', 'double attack'],
    'skewers': ['skewer', 'skewers', 'skewering', 'x-ray', 'x-ray attack'],
    'discovered_attacks': ['discovered attack', 'discovered', 'discovery', 'discovered check'],
    'deflection': ['deflection', 'deflect', 'deflecting'],
    'decoy': ['decoy', 'lure'],
    'clearance': ['clearance', 'line clearance'],
    'interference': ['interference', 'interpose'],
    'removal_of_defender': ['removal', 'remove defender', 'removing defender'],
}

def is_tactical_query(query: str) -> bool:
    """Checks if query contains any tactical keywords."""
    query_lower = query.lower()
    for keywords in TACTICAL_KEYWORDS.values():
        for keyword in keywords:
            if keyword in query_lower:
                return True
    return False

def infer_tactical_categories(query: str) -> Set[str]:
    """
    Infers ALL tactical categories mentioned in query.
    Returns SET of category names (e.g., {'pins', 'forks'}).
    
    FIXED: Was if/elif chain that only returned first match.
    Now returns all matching categories.
    """
    query_lower = query.lower()
    found_categories = set()
    
    for category, keywords in TACTICAL_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query_lower:
                found_categories.add(category)
                break  # Found this category, check next
    
    return found_categories

def inject_canonical_diagrams(query: str, canonical_positions: Dict) -> List[Dict]:
    """
    Injects canonical diagrams for ALL inferred categories.
    
    FIXED: Now handles multi-category queries properly.
    
    Returns list of diagram objects with FEN, caption, id.
    """
    inferred_categories = infer_tactical_categories(query)
    all_diagrams = []
    
    logger.info(f"[Detector] Query: {query}")
    logger.info(f"[Detector] Inferred categories: {inferred_categories}")
    
    if not inferred_categories:
        logger.warning("[Detector] No tactical categories inferred")
        return []
    
    for category in inferred_categories:
        if category not in canonical_positions:
            logger.warning(f"[Detector] Category '{category}' not in canonical library")
            continue
        
        category_data = canonical_positions[category]
        logger.info(f"[Detector] Found {len(category_data)} positions in '{category}'")
        
        # Add diagrams from this category
        for pos_id, pos_data in list(category_data.items())[:3]:  # Max 3 per category
            diagram = {
                'id': str(uuid.uuid4()),
                'fen': pos_data.get('fen'),
                'caption': pos_data.get('default_caption', f'{category} example'),
                'source': 'canonical',
                'category': category,
                'canonical_id': f'{category}/{pos_id}',
                'tactic': pos_data.get('tactic', category)
            }
            all_diagrams.append(diagram)
    
    # Limit total diagrams to reasonable number
    MAX_DIAGRAMS = 6
    if len(all_diagrams) > MAX_DIAGRAMS:
        logger.info(f"[Detector] Limiting {len(all_diagrams)} diagrams to {MAX_DIAGRAMS}")
        all_diagrams = all_diagrams[:MAX_DIAGRAMS]
    
    logger.info(f"[Detector] Returning {len(all_diagrams)} total diagrams")
    return all_diagrams

def strip_diagram_markers(text: str) -> str:
    """Remove all [DIAGRAM: ...] markers from text."""
    cleaned = re.sub(r'\[DIAGRAM(?:_ID)?:.*?\]', '', text, flags=re.IGNORECASE | re.DOTALL)
    return cleaned
