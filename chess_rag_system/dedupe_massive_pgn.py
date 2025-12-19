"""Production-ready massive PGN deduplication with resumability."""

from chess_rag_system.deduplication import ChessDeduplicator
from chess_rag_system.db_config import DB_CONFIG
import os
import json
import time
import hashlib
import shutil
from datetime import datetime

class MassivePGNProcessor:
    def __init__(
        self,
        input_path,
        output_dir="deduplicated_chunks",
        *,
        total_games_hint: int | None = None,
        duplicates_out: str | None = None,
        duplicates_limit: int = 0,
    ):
        self.input_path = input_path
        self.output_dir = output_dir
        self.checkpoint_file = "dedup_checkpoint.json"
        self.manifest_file = "dedup_manifest.json"
        self.error_log = "dedup_errors.log"
        self._total_bytes = os.path.getsize(input_path) if os.path.exists(input_path) else 0
        self._total_games_hint = total_games_hint
        self._duplicates_out = duplicates_out
        self._duplicates_limit = max(int(duplicates_limit), 0)

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

    def iter_raw_games(self, handle, *, resume: bool):
        """
        Stream raw PGN blocks split on an [Event ...] header.

        This avoids dropping games that python-chess can't parse (e.g. "illegal san")
        while still allowing exact-text dedupe.

        Yields:
            (raw_game_text, game_start_offset, next_game_offset)
        """
        buffer = []
        buffer_start = None
        saw_first_event = not resume

        while True:
            line_offset = handle.tell()
            line = handle.readline()
            if not line:
                break

            stripped = line.lstrip()
            if stripped.startswith("[Event "):
                if not saw_first_event:
                    saw_first_event = True
                if buffer:
                    yield "".join(buffer).strip(), buffer_start, line_offset
                buffer = [line]
                buffer_start = line_offset
            else:
                if not saw_first_event:
                    continue
                buffer.append(line)

        if buffer:
            yield "".join(buffer).strip(), buffer_start, handle.tell()

    def count_games(self) -> int:
        """
        Count games by scanning for an [Event ...] header line.

        This is a full-file pass (I/O bound) but gives an exact denominator for progress/ETA.
        """
        total = 0
        with open(self.input_path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if line.lstrip().startswith("[Event "):
                    total += 1
        return total

    def process(self):
        """Main processing loop."""
        checkpoint = self.load_checkpoint()
        dedup = ChessDeduplicator(DB_CONFIG)

        chunk_buffer = []
        start_time = time.time()
        last_checkpoint = checkpoint['total_processed']
        last_safe_offset = checkpoint['byte_offset']
        total_games_hint = checkpoint.get("total_games_hint") or self._total_games_hint
        duplicates_written = int(checkpoint.get("duplicates_written", 0) or 0)
        dup_handle = None

        print(f"Starting deduplication of {self.input_path}")
        print(f"Output directory: {self.output_dir}")

        if checkpoint['byte_offset'] > 0:
            print(f"Resuming from byte {checkpoint['byte_offset']:,} (game {checkpoint['total_processed']:,})")

        try:
            if self._duplicates_out:
                if checkpoint["byte_offset"] == 0 and os.path.exists(self._duplicates_out):
                    os.remove(self._duplicates_out)
                dup_handle = open(self._duplicates_out, "a", encoding="utf-8")

            with open(self.input_path, 'r', encoding='utf-8', errors='replace') as pgn_file:
                # Seek to checkpoint
                pgn_file.seek(checkpoint['byte_offset'])
                resume = checkpoint['byte_offset'] > 0
                for raw_game, game_start, next_offset in self.iter_raw_games(pgn_file, resume=resume):
                    last_safe_offset = next_offset

                    if not raw_game:
                        continue

                    # Check for duplicate (exact-text, whitespace-normalized)
                    _, status = dedup.check_duplicate(raw_game)
                    checkpoint['total_processed'] += 1

                    if status == 'new':
                        chunk_buffer.append(raw_game)
                        checkpoint['total_unique'] += 1
                    elif status == 'duplicate':
                        checkpoint['total_duplicates'] += 1
                        if dup_handle and (self._duplicates_limit == 0 or duplicates_written < self._duplicates_limit):
                            if duplicates_written > 0:
                                dup_handle.write("\n\n")
                            dup_handle.write(raw_game.strip())
                            duplicates_written += 1
                    else:
                        # Keep unrecognized/unparseable games; don't drop content.
                        checkpoint['total_errors'] += 1
                        chunk_buffer.append(raw_game)
                        checkpoint['total_unique'] += 1
                        with open(self.error_log, 'a') as log:
                            log.write(
                                f"{datetime.now().isoformat()} | "
                                f"Dedup normalize error at offset {game_start}\n"
                            )

                    # Write chunk when full
                    if len(chunk_buffer) >= self.GAMES_PER_CHUNK:
                        self.write_chunk(chunk_buffer, checkpoint['chunk_num'])
                        checkpoint['chunk_num'] += 1
                        checkpoint['byte_offset'] = last_safe_offset
                        chunk_buffer = []

                    # Save checkpoint periodically
                    if checkpoint['total_processed'] - last_checkpoint >= self.CHECKPOINT_INTERVAL:
                        checkpoint['byte_offset'] = last_safe_offset
                        if total_games_hint:
                            checkpoint["total_games_hint"] = int(total_games_hint)
                        if dup_handle:
                            checkpoint["duplicates_written"] = duplicates_written
                        self.save_checkpoint(checkpoint)
                        last_checkpoint = checkpoint['total_processed']

                        # Progress report
                        elapsed = time.time() - start_time
                        rate = checkpoint['total_processed'] / elapsed if elapsed > 0 else 0
                        dup_rate = (checkpoint['total_duplicates'] / checkpoint['total_processed'] * 100) if checkpoint['total_processed'] else 0

                        denom = "~?"
                        eta_hours = 0
                        if total_games_hint:
                            remaining = max(int(total_games_hint) - checkpoint["total_processed"], 0)
                            eta_hours = (remaining / rate / 3600) if rate > 0 else 0
                            denom = f"{int(total_games_hint):,}"
                        elif self._total_bytes and last_safe_offset:
                            frac = min(max(last_safe_offset / self._total_bytes, 0.0), 1.0)
                            est_total = int(checkpoint['total_processed'] / frac) if frac > 0 else 0
                            remaining = max(est_total - checkpoint['total_processed'], 0)
                            eta_hours = (remaining / rate / 3600) if rate > 0 else 0
                            denom = f"~{est_total:,}"

                        print(
                            f"Progress: {checkpoint['total_processed']:,} / {denom} | "
                            f"Unique: {checkpoint['total_unique']:,} | "
                            f"Dup rate: {dup_rate:.2f}% | "
                            f"Speed: {rate:.0f} games/sec | "
                            f"ETA: {eta_hours:.1f} hours"
                        )

                # Write final chunk
                if chunk_buffer:
                    self.write_chunk(chunk_buffer, checkpoint['chunk_num'])
                    checkpoint['chunk_num'] += 1

                # Final checkpoint
                checkpoint['byte_offset'] = last_safe_offset
                checkpoint['completed'] = True
                checkpoint['end_time'] = datetime.now().isoformat()
                if total_games_hint:
                    checkpoint["total_games_hint"] = int(total_games_hint)
                if dup_handle:
                    checkpoint["duplicates_written"] = duplicates_written
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
            checkpoint['byte_offset'] = last_safe_offset
            if total_games_hint:
                checkpoint["total_games_hint"] = int(total_games_hint)
            if dup_handle:
                checkpoint["duplicates_written"] = duplicates_written
            self.save_checkpoint(checkpoint)
            print(f"Checkpoint saved at game {checkpoint['total_processed']:,}")
            print("Run again to resume from this point.")

        finally:
            if dup_handle:
                try:
                    dup_handle.flush()
                    dup_handle.close()
                except Exception:
                    pass
            dedup.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Deduplicate massive PGN file')
    parser.add_argument('input_pgn', help='Path to 30GB input PGN file')
    parser.add_argument('--output-dir', default='deduplicated_chunks',
                        help='Output directory for chunks')
    parser.add_argument('--games-per-chunk', type=int, default=10000,
                        help='Games per output chunk (default: 10000)')
    parser.add_argument(
        '--count-games-first',
        action='store_true',
        help='Do a full pre-scan to count games (exact denominator for progress/ETA; adds one extra read pass).',
    )
    parser.add_argument(
        '--total-games',
        type=int,
        default=0,
        help='Provide a known total game count (skips pre-scan; improves ETA).',
    )
    parser.add_argument(
        '--duplicates-out',
        default='',
        help='Optional path to write duplicate games as a PGN (can be very large).',
    )
    parser.add_argument(
        '--duplicates-limit',
        type=int,
        default=0,
        help='Optional max number of duplicates to write (0 = unlimited).',
    )

    args = parser.parse_args()

    if not os.path.exists(args.input_pgn):
        print(f"Error: Input file {args.input_pgn} not found")
        return 1

    total_games_hint = args.total_games if args.total_games else None
    duplicates_out = args.duplicates_out.strip() or None
    processor = MassivePGNProcessor(
        args.input_pgn,
        args.output_dir,
        total_games_hint=total_games_hint,
        duplicates_out=duplicates_out,
        duplicates_limit=args.duplicates_limit,
    )
    if args.games_per_chunk:
        processor.GAMES_PER_CHUNK = args.games_per_chunk

    if args.count_games_first and not total_games_hint:
        t0 = time.time()
        print("Counting games (pre-scan)...")
        total_games_hint = processor.count_games()
        processor._total_games_hint = total_games_hint
        print(f"Counted {total_games_hint:,} games in {time.time() - t0:.1f}s")

    processor.process()
    return 0

if __name__ == "__main__":
    exit(main())
