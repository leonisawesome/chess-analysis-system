"""
Diagnostic Logging for Debugging Stage 1 Failure
"""
import logging

logger = logging.getLogger(__name__)

def log_enforcement_attempt(diagram_positions, is_tactical, enforcement_triggered):
    """Log enforcement attempt for debugging."""
    logger.info("="*60)
    logger.info("ENFORCEMENT DIAGNOSTIC")
    logger.info(f"  Diagram count: {len(diagram_positions)}")
    logger.info(f"  Is tactical: {is_tactical}")
    logger.info(f"  Enforcement triggered: {enforcement_triggered}")

    for i, diag in enumerate(diagram_positions[:3]):
        logger.info(f"  Diagram {i}: caption='{diag.get('caption', '')}', source='{diag.get('source', '')}'")

    logger.info("="*60)
