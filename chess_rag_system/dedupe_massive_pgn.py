"""Production-ready massive PGN deduplication with resumability."""

import chess.pgn
from chess_rag_system.deduplication import ChessDeduplicator
from chess_rag_system.db_config import DB_CONFIG
import os
import json
import time
import hashlib
import shutil
from io import StringIO
from datetime import datetime

class MassivePGNProcessor:
    def __init__(self, input_path, output_dir="deduplicated_chunks"):
        self.input_path = input_path
        self.output_dir = output_dir
        self.checkpoint_file = "dedup_checkpoint.json"
        self.manifest_file = "dedup_manifest.json"
        self.error_log = "dedup_errors.log"

        # Configurable parameters
        self.GAMES_PER_CHUNK = 10000
        self.CHECKPOINT_INTERVAL = 5000  # Save checkpoint every N games

        # Create directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs("quarantine", exist_ok=True)

        # Check disk space
        self._check_disk_space()

    def _check_disk_space(self):
        """Ensure sufficient disk space before starting."""
        stat = shutil.disk_usage(".")
        free_gb = stat.free / (1024**3)
        if free_gb < 30:
            raise Exception(f"Insufficient disk space: {free_gb:.1f}GB free, need 30GB minimum")

    def load_checkpoint(self):
        """Load checkpoint if exists."""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {
            'byte_offset': 0,
            'chunk_num': 0,
            'total_processed': 0,
            'total_unique': 0,
            'total_duplicates': 0,
            'total_errors': 0,
            'start_time': datetime.now().isoformat()
        }

    def save_checkpoint(self, checkpoint):
        """Save checkpoint atomically."""
        tmp = self.checkpoint_file + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        os.rename(tmp, self.checkpoint_file)

    def write_chunk(self, games, chunk_num):
        """Write chunk with checksum and atomic rename."""
        filename = f"chunk_{chunk_num:05d}.pgn"
        tmp_path = os.path.join(self.output_dir, filename + '.tmp')
        final_path = os.path.join(self.output_dir, filename)

        # Write to temp file
        with open(tmp_path, 'w', encoding='utf-8') as f:
            for game in games:
                f.write(game)
                if not game.endswith('\n\n'):
                    f.write('\n\n')
            f.flush()
            os.fsync(f.fileno())

        # Compute checksum
        with open(tmp_path, 'rb') as f:
            checksum = hashlib.sha256(f.read()).hexdigest()

        # Write checksum file
        with open(final_path + '.sha256', 'w') as f:
            json.dump({
                'filename': filename,
                'games': len(games),
                'sha256': checksum,
                'created': datetime.now().isoformat()
            }, f, indent=2)

        # Atomic rename
        os.rename(tmp_path, final_path)

        print(f"✓ Chunk {chunk_num:05d}: {len(games):,} games | SHA256: {checksum[:8]}...")

    def process(self):
        """Main processing loop."""
        checkpoint = self.load_checkpoint()
        dedup = ChessDeduplicator(DB_CONFIG)

        chunk_buffer = []
        start_time = time.time()
        last_checkpoint = checkpoint['total_processed']

        print(f"Starting deduplication of {self.input_path}")
        print(f"Output directory: {self.output_dir}")

        if checkpoint['byte_offset'] > 0:
            print(f"Resuming from byte {checkpoint['byte_offset']:,} (game {checkpoint['total_processed']:,})")

        try:
            with open(self.input_path, 'r', encoding='utf-8', errors='replace') as pgn_file:
                # Seek to checkpoint
                pgn_file.seek(checkpoint['byte_offset'])

                while True:
                    # Record position before reading
                    current_offset = pgn_file.tell()

                    # Read one game
                    try:
                        game = chess.pgn.read_game(pgn_file)
                        if game is None:
                            break

                        # Convert to string
                        exporter = StringIO()
                        print(game, file=exporter)
                        pgn_text = exporter.getvalue()

                    except Exception as e:
                        checkpoint['total_errors'] += 1
                        # Save malformed game to quarantine
                        with open(f"quarantine/error_{current_offset}.txt", 'w') as err_file:
                            err_file.write(f"Offset: {current_offset}\nError: {str(e)}\n")
                        # Log error
                        with open(self.error_log, 'a') as log:
                            log.write(f"{datetime.now().isoformat()} | Offset {current_offset}: {str(e)}\n")
                        continue

                    # Check for duplicate
                    game_hash, status = dedup.check_duplicate(pgn_text)
                    checkpoint['total_processed'] += 1

                    if status == 'new':
                        chunk_buffer.append(pgn_text)
                        checkpoint['total_unique'] += 1
                    elif status == 'duplicate':
                        checkpoint['total_duplicates'] += 1
                    elif status == 'error':
                        checkpoint['total_errors'] += 1

                    # Write chunk when full
                    if len(chunk_buffer) >= self.GAMES_PER_CHUNK:
                        self.write_chunk(chunk_buffer, checkpoint['chunk_num'])
                        checkpoint['chunk_num'] += 1
                        checkpoint['byte_offset'] = pgn_file.tell()
                        chunk_buffer = []

                    # Save checkpoint periodically
                    if checkpoint['total_processed'] - last_checkpoint >= self.CHECKPOINT_INTERVAL:
                        checkpoint['byte_offset'] = pgn_file.tell()
                        self.save_checkpoint(checkpoint)
                        last_checkpoint = checkpoint['total_processed']

                        # Progress report
                        elapsed = time.time() - start_time
                        rate = checkpoint['total_processed'] / elapsed if elapsed > 0 else 0
                        dup_rate = (checkpoint['total_duplicates'] / checkpoint['total_processed'] * 100) if checkpoint['total_processed'] > 0 else 0
                        eta_hours = (16000000 - checkpoint['total_processed']) / rate / 3600 if rate > 0 else 0

                        print(f"Progress: {checkpoint['total_processed']:,} / ~16M | "
                              f"Unique: {checkpoint['total_unique']:,} | "
                              f"Dup rate: {dup_rate:.1f}% | "
                              f"Speed: {rate:.0f} games/sec | "
                              f"ETA: {eta_hours:.1f} hours")

                # Write final chunk
                if chunk_buffer:
                    self.write_chunk(chunk_buffer, checkpoint['chunk_num'])
                    checkpoint['chunk_num'] += 1

                # Final checkpoint
                checkpoint['byte_offset'] = pgn_file.tell()
                checkpoint['completed'] = True
                checkpoint['end_time'] = datetime.now().isoformat()
                self.save_checkpoint(checkpoint)

                # Final report
                elapsed = time.time() - start_time
                print("\n" + "="*60)
                print("DEDUPLICATION COMPLETE")
                print("="*60)
                print(f"Total processed: {checkpoint['total_processed']:,}")
                print(f"Unique games: {checkpoint['total_unique']:,}")
                dup_percent = (checkpoint['total_duplicates']/checkpoint['total_processed']*100) if checkpoint['total_processed'] > 0 else 0
                print(f"Duplicates removed: {checkpoint['total_duplicates']:,} ({dup_percent:.1f}%)")
                print(f"Errors: {checkpoint['total_errors']:,}")
                print(f"Output chunks: {checkpoint['chunk_num']}")
                print(f"Total time: {elapsed/3600:.1f} hours")
                avg_speed = checkpoint['total_processed']/elapsed if elapsed > 0 else 0
                print(f"Average speed: {avg_speed:.0f} games/sec")

                # Write manifest
                with open(self.manifest_file, 'w') as f:
                    json.dump(checkpoint, f, indent=2)

        except KeyboardInterrupt:
            print("\n\nInterrupted! Saving checkpoint...")
            checkpoint['byte_offset'] = pgn_file.tell() if 'pgn_file' in locals() else checkpoint['byte_offset']
            self.save_checkpoint(checkpoint)
            print(f"Checkpoint saved at game {checkpoint['total_processed']:,}")
            print("Run again to resume from this point.")

        finally:
            dedup.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Deduplicate massive PGN file')
    parser.add_argument('input_pgn', help='Path to 30GB input PGN file')
    parser.add_argument('--output-dir', default='deduplicated_chunks',
                        help='Output directory for chunks')
    parser.add_argument('--games-per-chunk', type=int, default=10000,
                        help='Games per output chunk (default: 10000)')

    args = parser.parse_args()

    if not os.path.exists(args.input_pgn):
        print(f"Error: Input file {args.input_pgn} not found")
        return 1

    processor = MassivePGNProcessor(args.input_pgn, args.output_dir)
    if args.games_per_chunk:
        processor.GAMES_PER_CHUNK = args.games_per_chunk

    processor.process()
    return 0

if __name__ == "__main__":
    exit(main())