# System A Web UI

Interactive web interface for querying the chess knowledge corpus with dynamic diagram generation.

## Features

- **Query Interface**: Ask chess questions in natural language
- **Smart Results**: Top 5 results ranked by GPT-5
- **Chess Diagrams**: Automatic detection and rendering of chess positions
- **Interactive Boards**: Powered by chessboard.js
- **Lichess Integration**: One-click analysis links for any position
- **Metadata Display**: Book names, scores, and context

## Quick Start

### Start the Web Server

```bash
source .venv/bin/activate
export OPENAI_API_KEY='your-key-here'
python app.py
```

### Access the Interface

Open your browser to: **http://127.0.0.1:5000**

## Usage

1. **Enter a Question**: Type your chess question in the search box
   - Example: "How do I improve my calculation in the middlegame?"
   - Example: "What are the main ideas in the French Defense?"

2. **View Results**: Top 5 results appear with:
   - Relevance score (0-10)
   - Book name and chapter
   - Text excerpt
   - Detected chess positions (if any)

3. **Explore Positions**:
   - View positions on interactive boards
   - Click "Analyze on Lichess" to open in Lichess

## Chess Position Detection

The system automatically detects:

1. **FEN Strings**: Standard chess position notation
   - Example: `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`

2. **Move Sequences**: Algebraic notation
   - Example: `1.e4 e5 2.Nf3 Nc6`
   - Parses up to 20 moves and displays the resulting position

## Architecture

### Backend (`app.py`)
- **Flask**: Web server
- **python-chess**: Position parsing and validation
- **Query System**: Reuses `query_system_a.py` logic

### Frontend (`templates/index.html`)
- **chessboard.js**: Interactive board rendering
- **chess.js**: Position validation
- **Vanilla JavaScript**: No heavy frameworks

## Performance

- **Initial load**: Instant
- **Query latency**: 10-15 seconds (semantic search + GPT-5 reranking)
- **Board rendering**: Instant (client-side)

## Troubleshooting

### Server won't start
```bash
# Check if OPENAI_API_KEY is set
echo $OPENAI_API_KEY

# Check if virtual environment is activated
which python  # Should show .venv path

# Check if port 5000 is available
lsof -i :5000
```

### Queries timeout
- Expected for complex queries (GPT-5 reranking takes 8-12s)
- Check console for errors
- Verify Qdrant database exists: `ls -lh qdrant_production_db/`

### No chess diagrams appear
- Positions are only shown when detected in text
- Not all results will have diagrams
- Check browser console for JavaScript errors

## CLI Still Available

The command-line interface remains functional:

```bash
# Single query
python query_system_a.py "How do I improve my calculation?"

# Interactive mode
python query_system_a.py
```

## Technical Details

### Dependencies
- Flask 3.1.2
- python-chess (latest)
- chessboard.js 1.0.0 (CDN)
- chess.js 0.10.3 (CDN)

### Corpus
- 357,957 chunks
- 1,052 books
- 5.6GB database

### API Endpoints

**POST /query**
- Input: `{"query": "your question"}`
- Output: `{"success": true, "results": [...]}`

**POST /fen_to_lichess**
- Input: `{"fen": "position FEN"}`
- Output: `{"url": "https://lichess.org/analysis/..."}`

## Future Enhancements

Possible improvements:
- User authentication
- Query history
- Favorite results
- Export to PGN
- Multiple board themes
- Mobile responsive design

## System A Status

✅ **FULLY OPERATIONAL**

- Corpus: Complete (1,052 books, 357,957 chunks)
- Precision: 86-87% baseline
- Interface: Web UI + CLI
- Diagrams: Automatic detection and rendering
- Integration: Lichess analysis links
