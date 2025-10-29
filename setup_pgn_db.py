#!/usr/bin/env python3
"""
Setup PGN Database for Validation
Uses SQLite for easier validation (can migrate to PostgreSQL for production).
"""

import sqlite3
import json
import chess.pgn
from pathlib import Path


DATABASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename VARCHAR(255),
    white VARCHAR(255),
    black VARCHAR(255),
    event VARCHAR(255),
    site VARCHAR(255),
    date VARCHAR(50),
    round VARCHAR(50),
    result VARCHAR(10),
    eco VARCHAR(10),
    opening VARCHAR(255),
    plycount INTEGER,
    move_count INTEGER,
    pgn_text TEXT
);

CREATE INDEX IF NOT EXISTS idx_white ON games(white);
CREATE INDEX IF NOT EXISTS idx_black ON games(black);
CREATE INDEX IF NOT EXISTS idx_opening ON games(opening);
CREATE INDEX IF NOT EXISTS idx_eco ON games(eco);
CREATE INDEX IF NOT EXISTS idx_result ON games(result);
CREATE INDEX IF NOT EXISTS idx_event ON games(event);
"""


def setup_database(db_path: str = "pgn_validation.db",
                   games_dir: str = "validation_games",
                   metadata_file: str = "validation_games_metadata.json"):
    """
    Create database and load all validation games.
    """
    print("="* 80)
    print("SETTING UP PGN VALIDATION DATABASE")
    print("="* 80)
    print(f"Database: {db_path}")
    print(f"Games directory: {games_dir}\n")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create schema
    print("Creating database schema...")
    cursor.executescript(DATABASE_SCHEMA)
    conn.commit()
    print("✓ Schema created\n")

    # Load metadata
    with open(metadata_file, 'r', encoding='utf-8') as f:
        all_metadata = json.load(f)

    print(f"Loading {len(all_metadata)} games...")

    # Load each game
    games_loaded = 0
    for metadata in all_metadata:
        game_file = Path(games_dir) / metadata['filename']

        if not game_file.exists():
            print(f"⚠️  File not found: {metadata['filename']}")
            continue

        # Read PGN text
        with open(game_file, 'r', encoding='utf-8') as f:
            pgn_text = f.read()

        # Parse game to get move text
        with open(game_file, 'r', encoding='utf-8') as f:
            game = chess.pgn.read_game(f)

        # Insert into database
        cursor.execute("""
            INSERT INTO games (
                filename, white, black, event, site, date, round,
                result, eco, opening, plycount, move_count, pgn_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata['filename'],
            metadata['white'],
            metadata['black'],
            metadata['event'],
            metadata.get('site', 'Unknown'),
            metadata['date'],
            metadata.get('round', 'Unknown'),
            metadata['result'],
            metadata['eco'],
            metadata['opening'],
            metadata.get('plycount', 0),
            metadata['move_count'],
            pgn_text
        ))

        games_loaded += 1

        if games_loaded % 10 == 0:
            print(f"  Loaded {games_loaded}/{len(all_metadata)} games...")

    conn.commit()

    print(f"\n✅ Database setup complete: {games_loaded} games loaded\n")

    # Show summary statistics
    print("="* 80)
    print("DATABASE STATISTICS")
    print("="* 80)

    cursor.execute("SELECT COUNT(*) FROM games")
    total = cursor.fetchone()[0]
    print(f"\nTotal games: {total}")

    # ECO codes
    cursor.execute("SELECT COUNT(DISTINCT eco) FROM games WHERE eco != 'Unknown'")
    eco_count = cursor.fetchone()[0]
    print(f"Unique ECO codes: {eco_count}")

    # Results
    cursor.execute("""
        SELECT result, COUNT(*) as count
        FROM games
        GROUP BY result
        ORDER BY count DESC
    """)
    print(f"\nResults distribution:")
    for result, count in cursor.fetchall():
        print(f"  {result}: {count} games")

    # Top ECO codes
    cursor.execute("""
        SELECT eco, COUNT(*) as count
        FROM games
        WHERE eco != 'Unknown'
        GROUP BY eco
        ORDER BY count DESC
        LIMIT 5
    """)
    print(f"\nTop 5 ECO codes:")
    for eco, count in cursor.fetchall():
        print(f"  {eco}: {count} games")

    # Sample games
    cursor.execute("""
        SELECT white, black, eco, result
        FROM games
        WHERE white != 'Unknown' AND black NOT IN ('?', 'Unknown')
        LIMIT 5
    """)
    print(f"\nSample games:")
    for white, black, eco, result in cursor.fetchall():
        print(f"  {white} vs {black} ({eco}) - {result}")

    print("="* 80)

    conn.close()

    return games_loaded


if __name__ == '__main__':
    games_loaded = setup_database()
