# System Architecture

## Overview
The system follows a **Modular RAG (Retrieval-Augmented Generation)** architecture, split between high-performance local execution and high-capacity external storage.

```mermaid
graph TD
    User((User)) <--> WebUI[Web Interface]
    WebUI <--> Server[App Lite / Flask]
    Server <--> Agent[Content Surfacing Agent]
    
    subgraph Local [Local Disk: MacBook M4]
        Agent
        Server
        Logic[Chess Positions / Diagrams]
    end
    
    subgraph External [External Disk: T7 Shield]
        DB[(SQLite FTS5: Knowledge Bank)]
        Books[Raw EPUBs & PGNs]
        Legacy[Archived Assets]
    end
    
    subgraph Cloud [AI Models]
        Agent -- Primary --> Gemini[Gemini 2.0 Flash]
        Agent -- Fallback --> GPT[GPT-4o]
    end
    
    Agent <--> DB
```

## Component Breakdown

### 1. The Knowledge Bank (External)
- **Schema**: `knowledge_docs` table in SQLite.
- **Search**: FTS5 virtual table for full-text search.
- **Deduplication**: Content fingerprinting (ignoring PGN move variations) to ensure unique results.

### 2. The Surfacing Agent (Local)
- **Retrieval**: Multi-stage FTS5 search (Phrase -> AND -> OR).
- **Synthesis**: Multi-provider logic.
- **Resilience**: If Gemini hits a `RESOURCE_EXHAUSTED` (429) error, the agent automatically retries with GPT-4o.

### 3. Diagram Engine (Local)
- **Extraction**: Regex-based FEN and Move sequence detection.
- **Rendering**: `chess.svg` and interactive JS boards.

## Database Schema
Wait for `docs/DATABASE_SCHEMA.md` in Phase 2 for details.
