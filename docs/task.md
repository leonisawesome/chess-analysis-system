# Chess Analysis System - Rebuild Task List

## [x] Phase 1: Project Reset and Archiving
- [x] Create legacy storage at `/Volumes/T7 Shield/rag/legacy`
- [x] Archive all non-essential files and directories
- [x] Verify preserved assets
- [x] **Infrastructure Checkpoint: Documentation & API Resilience**
    - [x] Rebuild OpenAI (GPT-4o) fallback logic in the agent
    - [x] Update `README.md` and `ARCHITECTURE.md` with the new lean structure
    - [x] **Verification**: Confirm Stockfish wrapper works and API fallback triggers successfully.

## [/] Phase 2: Core Data Pipelines
- [/] **EPUB Ingestion Pipeline (Rigorous Verification Required)**
    - [/] Design robust EPUB parsing and chunking strategy
    - [ ] Implement SQLite-based storage for text and metadata
    - [ ] Documentation: `docs/DATABASE_SCHEMA.md`
    - [ ] **Verification**: Manually test search results for 5 diverse chess topics.
- [/] **PGN Ingestion Pipeline (Rigorous Verification Required)**
    - [ ] Integrate and verify preserved PGN ingestion script
    - [ ] Ensure deduplication and filtering (remove games with no text)
    - [x] Documentation: `docs/PGN_INGEST.md`
    - [ ] Implement SQLite-based storage for PGN games
    - [ ] **Verification**: Confirm zero "textless" games remain and deduplication is 100% accurate.


## [ ] Phase 3: Diagram Generation
- [ ] Implement static diagram generation (FTS to Image)
- [ ] Implement dynamic board rendering in UI
- [ ] Integrate opening interactive diagrams with LLM
- [ ] Verify end-to-end rendering in the web interface

## [ ] Phase 4: Stockfish Agent Integration
- [ ] Integrate preserved Stockfish wrapper (`chess_coach.py`)
- [ ] Development of an agent to analyze games and identify weaknesses
- [ ] Connect agent to RAG system to retrieve relevant content
- [ ] Verify analysis and recommendation quality

## [ ] Phase 5: Statistical Analysis and Enhancements
- [ ] Implement statistical analysis features
- [ ] Add further enhancements as identified during development
- [ ] Final system-wide verification
