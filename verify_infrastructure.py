import os
import sys
from dotenv import load_dotenv
import chess

# Load local modules
sys.path.append(os.getcwd())
from content_surfacing_agent import ContentSurfacingAgent
from chess_coach import AnalysisEngine, RemediationAgent

def verify():
    load_dotenv()
    gemini_key = os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    stockfish_path = "/opt/homebrew/bin/stockfish"

    print("\n" + "="*40)
    print("CHESS SYSTEM INFRASTRUCTURE VERIFICATION")
    print("="*40)

    # 1. Verify Stockfish
    print("\n[1/4] Verifying Stockfish...")
    try:
        engine = AnalysisEngine(stockfish_path)
        board = chess.Board()
        info = engine.analyze_position(board)
        score = info.get("score")
        print(f"  ✅ Stockfish OK (Starting Eval: {score})")
        engine.close()
    except Exception as e:
        print(f"  ❌ Stockfish Failed: {e}")

    # 2. Verify External DB Path
    print("\n[2/4] Verifying External Knowledge Bank...")
    agent = ContentSurfacingAgent()
    db_exists = os.path.exists(agent.db_path)
    print(f"  Path: {agent.db_path}")
    if db_exists:
        print(f"  ✅ Knowledge Bank Accessible.")
        # Test a small search
        hits = agent.search_library("Sicilian Defense", limit=1)
        if hits:
            print(f"  ✅ FTS5 Search Working (Hit: {hits[0]['title']})")
        else:
            print(f"  ⚠️  Search returned 0 hits (Expected if DB empty).")
    else:
        print(f"  ⚠️  Knowledge Bank NOT FOUND at external path (Expected if not yet moved).")

    # 3. Verify Gemini connectivity
    print("\n[3/4] Verifying Gemini 2.0 API...")
    if gemini_key:
        try:
            coach = RemediationAgent(gemini_key, openai_key)
            explanation = coach.explain_error("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "h3", "e4", "0.0")
            print(f"  ✅ Gemini OK: \"{explanation[:60]}...\"")
        except Exception as e:
            print(f"  ❌ Gemini Failed: {e}")
    else:
        print("  ❌ Gemini Key Missing.")

    # 4. Verify OpenAI connectivity
    print("\n[4/4] Verifying OpenAI Fallback...")
    if openai_key:
        try:
            # Manually trigger fallback logic
            ans = coach._explain_error_openai("Explain why e4 is better than h3 in the starting position.")
            print(f"  ✅ OpenAI OK: \"{ans[:60]}...\"")
        except Exception as e:
            print(f"  ❌ OpenAI Failed: {e}")
    else:
        print("  ❌ OpenAI Key Missing.")

    print("\n" + "="*40)
    print("VERIFICATION COMPLETE")
    print("="*40)

if __name__ == "__main__":
    verify()
