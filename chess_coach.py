import argparse
import sys
import chess
import chess.pgn
import chess.engine
import time
import os
from typing import Optional, List, Dict, Any

# Requirements:
# google-genai
# python-chess

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: google-genai library not found. Please install it via 'pip install google-genai'")
    sys.exit(1)

class RemediationAgent:
    """
    Handles communication with the Coach Agent (Gemini) and future RAG integration.
    """
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.system_prompt = (
            "You are a Grandmaster Chess Coach. The user played [Move] in position [FEN]. "
            "The engine recommends [Best Move]. "
            "Task 1: Explain why the played move is wrong (or inferior) in plain English. (e.g., 'This allows a fork', 'Leaves the king exposed'). "
            "Task 2: Explain why the best move is better. "
            "Format: One short sentence for the error, one short sentence for the best move. Be encouraging."
        )

    def explain_error(self, fen: str, played_move: str, best_move: str, score: str) -> str:
        prompt = f"Position FEN: {fen}\nPlayed Move: {played_move}\nBest Move: {best_move}\nEval: {score}\nExplain the error and the better alternative."
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=self.system_prompt,
                        temperature=0.7,
                    )
                )
                return response.text.strip()
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    if attempt < max_retries - 1:
                        sleep_time = 10 * (attempt + 1) # Increase wait: 10s, 20s, 30s
                        print(f"Rate limit hit. Retrying in {sleep_time} seconds...")
                        time.sleep(sleep_time)
                        continue
                print(f"Gemini API Error: {e}")
                return "Better was " + best_move
        return "Better was " + best_move

    def query_library(self, topic: str) -> None:
        """
        Stub for future local Qdrant/RAG query.
        TODO: Implement integration with local Qdrant instance containing chess books.
        """
        # Placeholder for future logic:
        # 1. Embed 'topic'
        # 2. Query Qdrant collection
        # 3. Return reading recommendations
        return None

class AnalysisEngine:
    """
    Wrapper for Local Stockfish Engine.
    """
    def __init__(self, stockfish_path: str, time_limit: float = 0.1, depth_limit: int = None):
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
            # Configure engine for analysis
        except FileNotFoundError:
            print(f"Error: Stockfish binary not found at {stockfish_path}")
            sys.exit(1)
        self.time_limit = time_limit
        self.depth_limit = depth_limit

    def close(self):
        self.engine.quit()

    def analyze_position(self, board: chess.Board) -> Dict[str, Any]:
        """
        Analyzes the current board position.
        """
        limit = chess.engine.Limit(time=self.time_limit, depth=self.depth_limit)
        info = self.engine.analyse(board, limit)
        return info

    def get_eval_score(self, info: Dict[str, Any], turn: bool) -> float:
        """
        Returns the score in centipawns from the perspective of White.
        """
        score = info["score"].white()
        if score.is_mate():
            return 99999 if score.mate() > 0 else -99999
        return score.score()

def get_nag(cp_score: float, is_mate: bool) -> int:
    """
    Returns the appropriate NAG integer based on centipawn score (white perspective).
    Ranges based on standard conventions.
    """
    # Mate
    if is_mate:
        return 18 if cp_score > 0 else 19 # +- or -+
    
    # Decisive (> 2.0)
    if cp_score > 200:
        return 18 # +-
    if cp_score < -200:
        return 19 # -+
        
    # Winning (> 1.0)
    if cp_score > 100:
        return 16 # +/-
    if cp_score < -100:
        return 17 # -/+
        
    # Better (> 0.5)
    if cp_score > 50:
        return 14 # +=
    if cp_score < -50:
        return 15 # =+
        
    # Equal
    return 11 # =

def process_game(input_pgn: str, output_pgn: str, engine: AnalysisEngine, coach: RemediationAgent, cp_threshold: float, side_filter: str):
    """
    Main loop to process the game PGN.
    """
    with open(input_pgn) as pgn_file:
        game = chess.pgn.read_game(pgn_file)
    
    if game is None:
        print(f"Error: Could not read PGN from {input_pgn}")
        return

    # Metadata
    game.headers["Annotator"] = "AI_Coach_Stockfish_Gemini"
    
    node = game
    board = game.board()
    
    print(f"Starting analysis of game...")

    # Initial analysis to establish baseline
    prev_info = engine.analyze_position(board)
    prev_score_val = engine.get_eval_score(prev_info, board.turn)
    
    move_count = 0
    
    while node.variations:
        next_node = node.variation(0)
        move = next_node.move
        
        # Determine if we should analyze this move (Side filter)
        is_white = board.turn
        should_analyze = False
        if side_filter == "both":
            should_analyze = True
        elif side_filter == "white" and is_white:
            should_analyze = True
        elif side_filter == "black" and not is_white:
            should_analyze = True
            
        current_fen = board.fen() # Position BEFORE the move
        
        board.push(move) # Make the move on the board
        
        if should_analyze:
            print(f"Analyzing move {move_count+1}... {'(White)' if is_white else '(Black)'}")
            
            # --- CALCULATE LOGIC TRIGGERS ---
            # 1. Previous evaluation (before move)
            prev_eval_white = engine.get_eval_score(prev_info, True)
            
            # 2. Current evaluation (after move)
            curr_info = engine.analyze_position(board)
            curr_eval_white = engine.get_eval_score(curr_info, True)
            
            # 3. Best Move Evaluation (Hypothetical best play from prev pos)
            # 'prev_info' contains the analysis of the board *before* the move.
            # Its 'score' is the eval of the best move.
            best_eval_white = prev_eval_white # Logic simplifies: prev_info score IS the best move score.
            
            # Calculate Scores in Pawns
            prev_score_pawn = prev_eval_white / 100.0
            curr_score_pawn = curr_eval_white / 100.0
            
            # Calculate Delta (from mover's perspective)
            if is_white:
                # White moved. 
                # Drop = Prev (Best) - Curr (Played)
                drop = prev_score_pawn - curr_score_pawn
            else:
                # Black moved.
                # Drop = Curr (Played) - Prev (Best) 
                # (Since lower is better for black, if played is higher, it's a drop)
                # Wait: Prev -2.0 (Black winning). Curr 0.0 (Equal). 
                # Drop: (-2.0) is better than (0.0). we lost advantage.
                # drop = Curr - Prev is correct?
                # Prev -2.0. Curr 0.0. -2.0 is better. 
                # Loss = How much worse is Curr than Prev?
                # Distance from -infinity.
                drop = curr_score_pawn - prev_score_pawn

            # Logic Triggers
            # 1. Bad Move (Drop > 0.3)
            is_bad_move = drop > 0.3
            
            # 2. Missed Opportunity (Missed > 0.75 gain)
            # This logic depends on 'prev_info' being accurate (depth sufficient).
            # If prev_info says +5.0 (Best), and we played a move resulting in +5.0 (Curr), drop is 0.
            # The User's definitions:
            # "decent move is made but there is a much stronger one"
            # This implies the played move might NOT drop 0.3 from the *current status quo*?
            # No, standard analysis compares against the BEST move.
            # If I have a mate in 1 (Eval +M1), and I play a quiet move (Eval +0.5).
            # Drop is HUGE. That is a Bad Move.
            # Maybe user means:
            # - Bad Move: I blundered something I HAD (My eval went down from 0 to -1).
            # - Missed Opp: I kept equality (0 to 0) but I COULD HAVE gone to +1.
            # But 'Prev_Eval' IS +1 (because engine sees the best move).
            # So standard "CP Loss" covers BOTH cases.
            # Users often confuse "Current Status" (static eval) with "Engine Eval" (dynamic).
            # We will treat any CP Loss > 0.75 as a "Missed Stronger Move" event, 
            # effectively treating it as a stronger category of error.
            
            trigger_bad = is_bad_move
            trigger_miss = drop > 0.75 # Overrides 'bad' if strictly larger, or just adds context?
            
            # Wait, user said: "we don't drop .3 but we miss a move that would have raised .75"
            # This implies 'Prev_Eval' considers the position 'before' finding the best move?
            # Impossible for an engine. The engine's evaluation OF the position IS the evaluation of the best move.
            # If the engine says "Position is +1.0", it means "There exists a move that gives +1.0".
            # If I play a move that gives +0.0, I lost 1.0.
            # So I will assume the user simply wants to distinguish SEVERITY.
            # "Drop > 0.3" -> Bad.
            # "Drop > 0.75" -> Missed Opportunity (Very Bad).
            
            should_comment = trigger_bad or trigger_miss
            
            current_fen = board.fen()
            best_move_uci = prev_info["pv"][0].uci() if "pv" in prev_info else None
            best_move_obj = prev_info["pv"][0] if "pv" in prev_info else None

            # --- NAG Annotation ---
            prev_is_mate = abs(prev_eval_white) > 90000
            curr_is_mate = abs(curr_eval_white) > 90000
            
            pos_nag = get_nag(curr_eval_white, curr_is_mate)
            next_node.nags.add(pos_nag)

            if should_comment:
                print(f"    ** Trigger: Drop {drop:.2f}")
                
                # 1. Add Move NAG
                if trigger_miss or drop > 1.0:
                     next_node.nags.add(4) # Blunder / Missed Win ??
                elif trigger_bad:
                     next_node.nags.add(2) # Mistake ?
                
                # 2. Add Refutation Line (Best Move)
                 # User wants "line to back it up" for BOTH wrong and right moves.
                 # The 'Right Move' line is the Best Move variation.
                if best_move_obj:
                    # Check if var exists
                    has_var = False
                    for var in node.variations:
                        if var.move == best_move_obj:
                            has_var = True
                            break
                    
                    if not has_var:
                        var_node = node.add_variation(best_move_obj)
                        var_node.nags.add(142) # Better move $142
                        # Add sub-variation (depth 3-4 moves) to show WHY it is better?
                        # Stockfish 'pv' usually has a line.
                        # We can try to extract more moves from PV? 
                        # 'prev_info' might have 'pv' list.
                        if "pv" in prev_info and len(prev_info["pv"]) > 1:
                            # Add the rest of the PV as comments or sub-moves? 
                            # python-chess variation is a linked list.
                            idx_node = var_node
                            for pv_move in prev_info["pv"][1:6]: # Add up to 5 moves of PV
                                idx_node = idx_node.add_main_variation(pv_move)

                # 3. Coach Explanation
                # "Why move was wrong" + "Why best move was better"
                score_str = f"{curr_info['score'].white()}"
                
                explanation = coach.explain_error(
                    fen=current_fen,
                    played_move=move.uci(),
                    best_move=best_move_uci,
                    score=score_str
                )
                
                # Format: "{Explanation} [%dia]"
                # Refutation of played move?? 
                # The 'played move' continuation is the main line. 
                # If the user wants a "line to back it up", the main line is usually it.
                
                comment_final = explanation
                comment_final += " [%dia]" 
                
                next_node.comment = comment_final
            
            # Update prev_info for next turn
            prev_info = curr_info
            
        else:
             # Even if we don't analyze, we need the eval for the next turn's baseline?
             # Yes, we need to know the 'before' state for the opponent's move next turn.
             # So we must analyze every move to track the evaluation graph, 
             # UNLESS we trust the evaluation from the opponent's 'after' state.
             # Ideally we analyze every position to keep the chain valid.
             # Optimization: We can just analyze the resulting position.
             prev_info = engine.analyze_position(board)

        node = next_node
        move_count += 1
        
    engine.close()
    
    print(f"Analysis complete. Writing to {output_pgn}")
    with open(output_pgn, "w") as f:
        exporter = chess.pgn.FileExporter(f)
        game.accept(exporter)

if __name__ == "__main__":
    import shutil

    parser = argparse.ArgumentParser(description="AI Chess Coach - Stockfish + Gemini")
    parser.add_argument("input_pgn", help="Path to input PGN file")
    parser.add_argument("output_pgn", help="Path to output PGN file")
    # Make stockfish_path optional
    parser.add_argument("stockfish_path", nargs="?", help="Path to local Stockfish binary (optional if in PATH)")
    
    parser.add_argument("--api_key", required=True, help="Google AISTUDIO API Key")
    parser.add_argument("--model", default="gemini-2.0-flash", help="Gemini Model Name (default: gemini-2.0-flash)")
    parser.add_argument("--cp_threshold", type=float, default=0.3, help="Centipawn loss threshold (default 0.3)")
    parser.add_argument("--side", choices=["white", "black", "both"], default="both", help="Side to analyze (default: both)")
    parser.add_argument("--depth", type=int, default=18, help="Stockfish analysis depth (default 18)")
    parser.add_argument("--time", type=float, default=0.1, help="Time per move in seconds (default 0.1)")
    
    args = parser.parse_args()

    # Resolve Stockfish Path
    binary_path = args.stockfish_path
    if not binary_path:
        binary_path = shutil.which("stockfish")
    
    if not binary_path:
        print("Error: Stockfish binary not found in PATH and not provided as argument.")
        print("Please install Stockfish or provide the path explicitly.")
        sys.exit(1)
        
    print(f"Using Stockfish at: {binary_path}")
    
    coach = RemediationAgent(api_key=args.api_key, model_name=args.model)
    engine = AnalysisEngine(stockfish_path=binary_path, time_limit=args.time, depth_limit=args.depth)
    
    process_game(args.input_pgn, args.output_pgn, engine, coach, args.cp_threshold, args.side)
