# Phase 1: Project Reset and Archiving

The goal of this phase is to create a clean slate for the "Chess Analysis System" by archiving legacy code and technical debt into a `legacy/` directory. This will allow us to rebuild the core functionalities (ingestions, diagrams, LLM integration) from a verified and reliable foundation.

## Proposed Changes

### [Component] File Archiving and Organization

We will move almost all top-level files and legacy directories into the external legacy storage, except for the explicitly preserved assets.

#### [NEW] [/Volumes/T7 Shield/rag/legacy/](file:///Volumes/T7%20Shield/rag/legacy/)
An external directory created on the T7 Shield to house all previous iterations and experimental scripts.


#### [PRESERVE] Root Level Files
- `chess_coach.py`: The verified Stockfish wrapper.
- `analyze_pgn_games.py`: The PGN **Ingester** (turns files into RAG chunks).
- `pgn_quality_analyzer.py`: The PGN **Scorer/Filter** (calculates EVS to decide what to keep).
- `verify_system_stats.py`: For system monitoring.
- `.env`: Environment variables.
- `.gitignore`: Git configuration.

> [!NOTE]
> `the_evaluator.py` has been identified as legacy script for data management/renaming and will be archived.


#### [PRESERVE] Directories
- `data/`: Contains SQLite databases and persistent data.
- `static/`: Frontend assets.
- `templates/`: HTML templates.

### [Component] Cleanup

- **Database Health**: We will verify the integrity of the existing `data/chess_text.db` (or equivalent) and decide whether to clear it for a "clean" re-ingestion or keep existing valid data.
- **Environment**: Ensure all required dependencies in `requirements.txt` are current and valid for the new architecture.

## Verification Plan

### Automated Tests
- Run `verify_system_stats.py` before and after archiving to ensure no data loss in the `data/` directory.
- Execute a basic test with `chess_coach.py` to confirm the Stockfish integration still works after the move.

### Manual Verification
- Inspections of the root directory to ensure it is minimal and organized.
- Verify that the web server (when re-implemented) can still access the `static/` and `templates/` folders.
