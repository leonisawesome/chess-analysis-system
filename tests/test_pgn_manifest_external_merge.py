import os, subprocess, sys
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parents[1] / "scripts" / "pgn_manifest.py")


def _mk_files(root: Path, names):
    root.mkdir(parents=True, exist_ok=True)
    for n in names:
        p = root / n
        p.write_text("", encoding="utf-8")


def _run(args):
    proc = subprocess.run([sys.executable, SCRIPT] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    return proc.stdout


def _read_manifest(out_dir: Path):
    with open(out_dir / "pgn_manifest.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f]


def test_numeric_external_merge_correctness(tmp_path: Path):
    # The chunk-size hint here may still keep everything in a single chunk depending
    # on path lengths, but correctness must hold in both single- and multi-chunk cases.
    src = tmp_path / "src"
    names = ["game1.pgn", "game10.pgn", "game2.pgn", "game20.pgn"]
    _mk_files(src, names)
    out = tmp_path / "out"
    out.mkdir()
    _run(["--src", str(src), "--out", str(out), "--mode", "numeric", "--external", "--chunk-size-mb", "1"])
    manifest = [Path(p).name for p in _read_manifest(out)]
    assert manifest == ["game1.pgn", "game2.pgn", "game10.pgn", "game20.pgn"]


def test_shuffle_external_determinism(tmp_path: Path):
    src = tmp_path / "src"
    names = [f"game{i}.pgn" for i in range(1, 8)]
    _mk_files(src, names)
    out1 = tmp_path / "o1"; out1.mkdir()
    out2 = tmp_path / "o2"; out2.mkdir()
    # Same seed → identical order
    _run(["--src", str(src), "--out", str(out1), "--mode", "shuffle", "--seed", "42", "--external", "--chunk-size-mb", "1"])
    _run(["--src", str(src), "--out", str(out2), "--mode", "shuffle", "--seed", "42", "--external", "--chunk-size-mb", "1"])
    m1 = _read_manifest(out1); m2 = _read_manifest(out2)
    assert m1 == m2
    # Different seed → different order (very high probability)
    out3 = tmp_path / "o3"; out3.mkdir()
    _run(["--src", str(src), "--out", str(out3), "--mode", "shuffle", "--seed", "43", "--external", "--chunk-size-mb", "1"])
    m3 = _read_manifest(out3)
    assert m1 != m3

