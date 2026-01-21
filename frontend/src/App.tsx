import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { BookOpen, Search, Layout, Settings, ChevronRight, Loader, ChevronLeft, FastForward, Rewind, Play, Image as ImageIcon, Copy, Wand2 } from 'lucide-react';
import { Chessboard } from 'react-chessboard';
import { Chess } from 'chess.js';
import { searchConcepts } from './api';
import type { Chunk } from './api';

// --- Types ---
interface Variation {
  moves: string[];
  fens: string[];
}

// --- Helper: Interactive Text Component ---
interface InteractiveTextProps {
  text: string;
  onMoveClick: (moveText: string, fullText: string) => void;
}

const InteractiveText: React.FC<InteractiveTextProps> = ({ text, onMoveClick }) => {
  const moveRegex = /((?:\d{1,3}(?:\.\.\.|\.)\s*)?[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:\=[QRBN])?[\+#]?|O-O(?:-O)?)/g;
  const parts = text.split(moveRegex);
  const matches = text.match(moveRegex) || [];

  let matchIndex = 0;
  return (
    <div className="leading-relaxed text-lg text-ink/90 whitespace-pre-wrap font-serif">
      {parts.map((part, i) => {
        if (matchIndex < matches.length && matches[matchIndex] === part) {
          const move = part;
          matchIndex++;
          return (
            <button
              key={i}
              onClick={(e) => {
                e.stopPropagation();
                onMoveClick(move, text);
              }}
              className="move-link inline-flex items-center px-1 py-0 bg-board-accent/10 text-board-accent font-bold rounded hover:bg-board-accent hover:text-white transition-colors cursor-pointer border-b border-board-accent/30 text-base align-baseline"
            >
              {move}
            </button>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </div>
  );
};

function App() {
  const [activeFen, setActiveFen] = useState<string>("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
  const [diagramFen, setDiagramFen] = useState<string>("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
  const [lessonChunks, setLessonChunks] = useState<Chunk[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("Isolated Queen Pawn");

  // Variation State
  const [currentVariation, setCurrentVariation] = useState<Variation | null>(null);
  const [currentMoveIdx, setCurrentMoveIdx] = useState(-1);

  // Generative State
  const [genInput, setGenInput] = useState("");

  // Panel Widths
  const [sidebarWidth, setSidebarWidth] = useState(256);
  const [boardWidth, setBoardWidth] = useState(500);
  const [isResizingSidebar, setIsResizingSidebar] = useState(false);
  const [isResizingBoard, setIsResizingBoard] = useState(false);

  const loadLesson = async (query: string) => {
    setLoading(true);
    console.log("[SYSTEM] Searching for:", query);
    try {
      const data = await searchConcepts(query);
      console.log("[SYSTEM] Data received:", data);
      if (data && data.results) {
        setLessonChunks(data.results);
        if (data.results.length > 0) {
          handleChunkClick(data.results[0].fen);
        }
      } else {
        console.warn("[SYSTEM] No results found or malformed response");
        setLessonChunks([]);
      }
    } catch (e) {
      console.error("[SYSTEM] API Error:", e);
      setLessonChunks([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLesson(searchQuery);
  }, []);

  // Resize Logic
  const startResizingSidebar = useCallback(() => setIsResizingSidebar(true), []);
  const startResizingBoard = useCallback(() => setIsResizingBoard(true), []);
  const stopResizing = useCallback(() => {
    setIsResizingSidebar(false);
    setIsResizingBoard(false);
  }, []);

  const resize = useCallback((e: MouseEvent) => {
    if (isResizingSidebar) setSidebarWidth(Math.max(160, Math.min(400, e.clientX)));
    if (isResizingBoard) setBoardWidth(Math.max(300, Math.min(800, window.innerWidth - e.clientX)));
  }, [isResizingSidebar, isResizingBoard]);

  useEffect(() => {
    if (isResizingSidebar || isResizingBoard) {
      window.addEventListener('mousemove', resize);
      window.addEventListener('mouseup', stopResizing);
    }
    return () => {
      window.removeEventListener('mousemove', resize);
      window.removeEventListener('mouseup', stopResizing);
    };
  }, [isResizingSidebar, isResizingBoard, resize, stopResizing]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadLesson(searchQuery);
  };

  const handleChunkClick = (fen: string) => {
    try {
      const chess = new Chess(fen);
      const normalized = chess.fen();
      setActiveFen(normalized);
      setDiagramFen(normalized);
      setCurrentVariation(null);
      setCurrentMoveIdx(-1);
    } catch (e) {
      setActiveFen(fen);
      setDiagramFen(fen);
    }
  };

  const handleMoveClick = (clickedMove: string, fullText: string) => {
    console.log("[PLAYER] Clicked:", clickedMove);
    const cleanMove = clickedMove.replace(/^\d+(\.\.\.|\.)\s*/, '').trim();

    // 1. Try to play from current
    try {
      const chess = new Chess(activeFen);
      if (chess.move(cleanMove)) {
        console.log("[PLAYER] Found legal move from current pos:", cleanMove);
        setActiveFen(chess.fen());
        return;
      }
    } catch (e) { }

    // 2. Sequence from diagram
    try {
      const moveRegex = /((?:\d{1,3}(?:\.\.\.|\.)\s*)?[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:\=[QRBN])?[\+#]?|O-O(?:-O)?)/g;
      const allMatches = fullText.match(moveRegex) || [];
      const chess = new Chess(diagramFen);
      let fens: string[] = [diagramFen];
      let targetIdx = -1;

      for (let i = 0; i < allMatches.length; i++) {
        const m = allMatches[i].replace(/^\d+(\.\.\.|\.)\s*/, '').trim();
        try {
          if (chess.move(m)) {
            fens.push(chess.fen());
            if (allMatches[i] === clickedMove) targetIdx = i;
          } else break;
        } catch (e) { break; }
      }

      if (targetIdx !== -1) {
        console.log("[PLAYER] Found sequence starting from diagram. Index:", targetIdx);
        setCurrentVariation({ moves: allMatches.slice(0, fens.length - 1), fens: fens.slice(1) });
        setCurrentMoveIdx(targetIdx);
        setActiveFen(fens[targetIdx + 1]);
      } else {
        console.warn("[PLAYER] Could not find logical branch for move:", cleanMove);
      }
    } catch (e) { }
  };

  const navigateMove = (direction: 'next' | 'prev' | 'start' | 'end') => {
    if (!currentVariation) return;
    let nextIdx = currentMoveIdx;
    if (direction === 'next') nextIdx = Math.min(currentVariation.fens.length - 1, currentMoveIdx + 1);
    if (direction === 'prev') nextIdx = Math.max(-1, currentMoveIdx - 1);
    if (direction === 'start') nextIdx = -1;
    if (direction === 'end') nextIdx = currentVariation.fens.length - 1;

    setCurrentMoveIdx(nextIdx);
    setActiveFen(nextIdx === -1 ? diagramFen : currentVariation.fens[nextIdx]);
  };

  const handleGenDiagram = (e: React.FormEvent) => {
    e.preventDefault();
    const input = genInput.toLowerCase();
    const chess = new Chess();
    chess.clear(); // Start empty

    // Basic heuristic parser for "knight fork of 2 rooks on d3"
    // Setting up the piece on d3 as requested
    if (input.includes("d3")) {
      chess.put({ type: 'n', color: 'w' }, 'd3');
      // Adding targets for the fork if it says "fork of 2 rooks"
      if (input.includes("rooks") || input.includes("rook")) {
        chess.put({ type: 'r', color: 'b' }, 'f2');
        chess.put({ type: 'r', color: 'b' }, 'b2');
      }
    }

    // Add kings to make it a legal FEN if possible, though Chessboard accepts partials
    if (!input.includes("king")) {
      chess.put({ type: 'k', color: 'w' }, 'e1');
      chess.put({ type: 'k', color: 'b' }, 'e8');
    }

    setActiveFen(chess.fen());
    setCurrentVariation(null);
    setGenInput("");
  };

  function onDrop({ sourceSquare, targetSquare }: any) {
    try {
      const chess = new Chess(activeFen);
      if (chess.move({ from: sourceSquare, to: targetSquare, promotion: 'q' })) {
        setActiveFen(chess.fen());
        setCurrentVariation(null);
        return true;
      }
    } catch (e) { }
    return false;
  }

  return (
    <div className={`flex h-screen bg-board-dark text-paper font-sans overflow-hidden ${isResizingSidebar || isResizingBoard ? 'select-none cursor-col-resize' : ''}`}>

      {/* 1. Sidebar */}
      <aside style={{ width: sidebarWidth }} className="bg-black/20 border-r border-white/10 flex flex-col shrink-0">
        <div className="p-6">
          <h1 className="text-xl font-serif font-bold text-board-accent tracking-wide">CHESS COACH</h1>
          <p className="text-xs text-ink-light mt-1 uppercase tracking-tighter">Knowledge Bank</p>
        </div>
        <nav className="flex-1 px-4 space-y-2">
          <NavItem icon={<BookOpen size={18} />} label="Lesson Synthesizer" active={!searchQuery.includes('vs')} onClick={() => { setSearchQuery("Isolated Queen Pawn"); loadLesson("Isolated Queen Pawn"); }} />
          <NavItem icon={<Search size={18} />} label="Concept Library" />
          <NavItem icon={<Layout size={18} />} label="My Repertoire" />
        </nav>
        <div className="p-4 border-t border-white/10">
          <NavItem icon={<Settings size={18} />} label="Settings" />
        </div>
      </aside>

      <div onMouseDown={startResizingSidebar} className="w-1 cursor-col-resize hover:bg-board-accent/50 transition-colors shrink-0 z-50"></div>

      {/* 2. Main Content */}
      <main className="flex-1 bg-paper text-ink flex flex-col relative min-w-0">
        <header className="h-20 border-b border-ink/10 flex items-center px-8 justify-between bg-paper z-20">
          <div className="flex-1 max-w-2xl px-4">
            <form onSubmit={handleSearch} className="relative group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-light group-focus-within:text-board-accent" size={20} />
              <input
                type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search chess concepts..."
                className="w-full bg-paper-dark/50 border border-ink/10 rounded-full py-3 pl-12 pr-6 focus:outline-none focus:ring-4 focus:ring-board-accent/10 focus:border-board-accent transition-all text-lg font-serif"
              />
            </form>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-12 py-10 space-y-12">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-96 text-ink-light"><Loader className="animate-spin mb-4" size={40} /><p className="text-xl font-serif">Consulting the Grandmasters...</p></div>
          ) : lessonChunks.length === 0 ? (
            <div className="max-w-4xl mx-auto flex flex-col items-center justify-center h-96 text-ink-light/50 border-2 border-dashed border-ink/5 rounded-3xl">
              <Search size={48} className="mb-4 opacity-20" />
              <p className="text-2xl font-serif">No insights found for "{searchQuery}"</p>
              <p className="text-sm mt-2">Try searching for concepts like "French Defense" or "King side attack"</p>
              <button onClick={() => loadLesson("Scandinavian")} className="mt-8 px-6 py-2 bg-board-accent/20 text-board-accent rounded-full hover:bg-board-accent/30 transition-all font-bold">Try "Scandinavian"</button>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto">
              {lessonChunks.map((chunk, i) => (
                <div key={chunk.chunk_id || i} className="group mb-16">
                  <article className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-board-accent font-bold mb-4">
                      <span className="w-8 h-px bg-board-accent/30"></span>
                      {chunk.book_title}
                    </div>
                    <h3 className="text-2xl font-bold font-serif mb-6 leading-tight">Positional Insight</h3>

                    {/* Diagram Rendering */}
                    {chunk.diagrams && chunk.diagrams.map((d, di) => (
                      <div key={di} className="float-right ml-8 mb-4 w-64 shadow-xl rounded-lg overflow-hidden border border-ink/10 group/img cursor-zoom-in" onClick={() => handleChunkClick(d.fen)}>
                        <img src={d.image_path} alt="Book Diagram" className="w-full h-auto bg-white" onError={(e) => (e.currentTarget.style.display = 'none')} />
                        <div className="p-2 bg-board-panel text-[10px] text-white/40 flex justify-between items-center">
                          <span>ORIGINAL DIAGRAM</span>
                          <ImageIcon size={12} />
                        </div>
                      </div>
                    ))}

                    <InteractiveText text={chunk.text} onMoveClick={handleMoveClick} />
                  </article>

                  <div className="clear-both mt-8">
                    <button onClick={() => handleChunkClick(chunk.fen)} className="w-full bg-board-accent/5 border border-board-accent/20 p-6 rounded-xl hover:bg-board-accent/10 hover:border-board-accent/40 transition-all flex items-center justify-between group">
                      <div className="min-w-0">
                        <span className="text-xs font-bold uppercase text-board-accent mb-1 block">Contextual Position</span>
                        <h4 className="font-bold text-lg text-board-dark">Reset Board to Chapter Position</h4>
                        <p className="text-sm text-ink-light font-mono truncate">{chunk.fen}</p>
                      </div>
                      <div className="bg-board-accent text-white p-3 rounded-full shadow-lg transform group-hover:scale-110 transition-transform"><ChevronRight size={24} /></div>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      <div onMouseDown={startResizingBoard} className="w-1 cursor-col-resize hover:bg-board-accent/50 transition-colors shrink-0 z-50"></div>

      {/* 3. Board Panel */}
      <aside style={{ width: boardWidth }} className="bg-board-dark/95 border-l border-white/10 p-8 flex flex-col shadow-2xl shrink-0">
        <div className="aspect-square w-full shadow-[0_0_50px_rgba(0,0,0,0.5)] rounded-lg overflow-hidden border-[12px] border-board-panel">
          <Chessboard
            key={activeFen}
            options={{
              position: activeFen,
              onPieceDrop: onDrop,
              boardOrientation: "white",
              darkSquareStyle: { backgroundColor: '#5ca1e6' },
              lightSquareStyle: { backgroundColor: '#f1f5f9' },
            }}
          />
        </div>

        <div className="mt-8 flex flex-col flex-1 min-h-0 bg-black/30 rounded-xl p-6 border border-white/5 shadow-inner">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs uppercase tracking-widest text-white/40 font-bold">{currentVariation ? "Active Sequence" : "Analysis Board"}</span>
            <div className="flex gap-2">
              <NavButton icon={<Rewind size={16} />} onClick={() => navigateMove('start')} disabled={!currentVariation} />
              <NavButton icon={<ChevronLeft size={16} />} onClick={() => navigateMove('prev')} disabled={!currentVariation} />
              <NavButton icon={<ChevronRight size={16} />} onClick={() => navigateMove('next')} disabled={!currentVariation} />
              <NavButton icon={<FastForward size={16} />} onClick={() => navigateMove('end')} disabled={!currentVariation} />
            </div>
          </div>

          {/* Variation History */}
          <div className="flex-1 overflow-y-auto mb-4">
            {currentVariation ? (
              <div className="flex flex-wrap gap-2 p-2 bg-black/20 rounded">
                <span onClick={() => navigateMove('start')} className={`cursor-pointer px-2 py-1 rounded text-xs transition-all ${currentMoveIdx === -1 ? 'bg-board-accent text-board-dark font-bold' : 'text-paper/40 hover:text-white'}`}>START</span>
                {currentVariation.moves.map((move, i) => (
                  <span key={i} onClick={() => { setCurrentMoveIdx(i); setActiveFen(currentVariation.fens[i]); }} className={`cursor-pointer px-2 py-1 rounded text-sm transition-all ${i === currentMoveIdx ? 'bg-board-accent text-board-dark font-bold' : 'text-paper/60 hover:text-paper hover:bg-white/5'}`}>{move}</span>
                ))}
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center px-4">
                <Play size={24} className="text-white/10 mb-2" />
                <p className="text-paper/30 text-sm font-serif italic">Select a move to start line analysis.</p>
              </div>
            )}
          </div>

          {/* Generative Diagram Tool */}
          <div className="mt-auto pt-4 border-t border-white/5">
            <form onSubmit={handleGenDiagram} className="relative group/gen">
              <Wand2 className="absolute left-3 top-1/2 -translate-y-1/2 text-white/20 group-focus-within/gen:text-board-accent transition-colors" size={14} />
              <input
                type="text"
                value={genInput}
                onChange={(e) => setGenInput(e.target.value)}
                placeholder="Generative Diagram: 'Knight fork on d3'..."
                className="w-full bg-black/20 border border-white/10 rounded-lg py-2 pl-9 pr-4 text-xs font-serif text-paper/80 focus:outline-none focus:border-board-accent/50 transition-all italic"
              />
            </form>
          </div>

          <div className="mt-4 flex items-center justify-between text-[10px] font-mono text-paper/40 truncate">
            <span className="truncate pr-4">FEN: {activeFen}</span>
            <button onClick={() => navigator.clipboard.writeText(activeFen)} className="hover:text-board-accent transition-colors"><Copy size={12} /></button>
          </div>
          <button className="mt-4 w-full bg-board-accent text-board-dark font-black tracking-tighter text-sm h-12 rounded-lg hover:brightness-110 active:scale-[0.98] transition-all uppercase shrink-0">Deep Analysis</button>
        </div>
      </aside>
    </div>
  );
}

const NavButton = ({ icon, onClick, disabled }: { icon: React.ReactNode, onClick: () => void, disabled?: boolean }) => (
  <button onClick={onClick} disabled={disabled} className={`p-2 rounded bg-white/5 hover:bg-white/10 transition-colors disabled:opacity-20 disabled:cursor-not-allowed text-paper`}>{icon}</button>
)

function NavItem({ icon, label, active = false, onClick }: { icon: React.ReactNode, label: string, active?: boolean, onClick?: () => void }) {
  return (
    <div onClick={onClick} className={`flex items-center gap-3 px-4 py-3 rounded-lg cursor-pointer transition-all ${active ? 'bg-board-accent text-board-dark font-black shadow-lg shadow-board-accent/20' : 'text-paper/40 hover:text-paper hover:bg-white/5 font-medium'}`}>{icon}<span className="text-sm tracking-tight">{label}</span></div>
  );
}

export default App;
