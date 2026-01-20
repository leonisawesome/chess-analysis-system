import sys
import chess.pgn
import io
from pathlib import Path
from pgn_quality_analyzer import PGNQualityAnalyzer, GameScore

def verify_game_score(pgn_text: str):
    """
    Runs the quality analyzer on a single PGN string and prints the breakdown.
    """
    analyzer = PGNQualityAnalyzer(Path("test_db.sqlite"))
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    
    if game is None:
        print("❌ Could not parse PGN.")
        return

    score = analyzer.score_game(game, raw_text=pgn_text)
    
    print("\n" + "="*50)
    print(f"♟️  GAME ANALYSIS: {game.headers.get('White')} vs {game.headers.get('Black')}")
    print("="*50)
    
    if score is None:
        print("❌ RESULT: REJECTED (Score = None)")
        # Manually debug why
        print("   Reason: Likely failed Language Check or WPM Gate.")
        return

    print(f"📊 FINAL SCORE (EVS): {score.evs:.1f} / 100")
    print("-" * 30)
    print(f"   • Structure Score:   {score.structure:.1f}")
    print(f"   • Annotation Score:  {score.annotations:.1f}")
    print(f"   • Humanness Score:   {score.humanness:.1f}")
    print(f"   • Educational Score: {score.educational:.1f}")
    print("-" * 30)
    print(f"📝 METRICS:")
    print(f"   • Total Moves:       {score.total_moves}")
    print(f"   • Comment Words:     {score.comment_words}")
    print(f"   • Words Per Move:    {score.comment_words / max(score.total_moves, 1):.2f} (Must be > 1.5)")
    print(f"   • Density:           {score.annotation_density:.2f}")
    
    if score.dropped_reason:
        print(f"\n⚠️  DROPPED REASON: {score.dropped_reason}")
    elif score.evs < 50:
         print(f"\n⚠️  STATUS: LOW QUALITY (EVS < 50)")
    else:
         print(f"\n✅ STATUS: ACCEPTED")

if __name__ == "__main__":
    print("Paste your PGN below (press Ctrl+D or Ctrl+Z when done):")
    lines = sys.stdin.readlines()
    pgn_input = "".join(lines)
    verify_game_score(pgn_input)
