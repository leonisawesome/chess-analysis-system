# Chess Analysis System (Rebuild)

A high-performance AI Chess Coach designed to help a player move from 1300 to 2300 FIDE.

## 🚀 Vision
This system acts as a **Learning Management System**, not just a search tool. It connects engine analysis (Stockfish) to human-authored chess theory (EPUBs/PGNs) to provide deep, thematic coaching.

## 🛠 Tech Stack
- **Languages**: Python (Backend), Vanilla JS/HTML/CSS (Frontend)
- **Database**: SQLite FTS5 (Knowledge Bank)
- **AI Models**: 
  - **Primary**: Google Gemini 2.0 Flash
  - **Fallback**: OpenAI GPT-4o (Automatic 429 Resilience)
- **Chess Engine**: Stockfish 16.1

## 📁 Storage Strategy
- **Local**: `/Users/leon/Downloads/python/chess-analysis-system` (Code, Env, UI)
- **External (T7 Shield)**: `/Volumes/T7 Shield/rag/` (Databases, Books, Legacy Assets)

## 🏗 Phases
1.  **Phase 1: Project Reset & Infrastructure** (CURRENT: API Resilience complete)
2.  **Phase 2: Core Data Pipelines** (Next: EPUB Ingestion)
3.  **Phase 3: Diagram Generation**
4.  **Phase 4: Stockfish Agent Integration**
5.  **Phase 5: Statistical Analysis**

## 🚦 Verification Principles
- No phase begins until the previous phase is 100% verified.
- All ingestion requires human-in-the-loop search verification.
- Zero "textless" PGN games allowed in the corpus.
