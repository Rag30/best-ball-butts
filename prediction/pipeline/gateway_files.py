"""Move the weekly run's files through the gateway's /files lane, and nothing else.

.claude/settings.json allows exactly `python3 ../../pipeline/gateway_files.py *`, so a
cloud session can run this without an auto-mode permission check. Because the rule
skips that check, this script is the guard: the host is fixed, and it only downloads
a league snapshot into the current run dir or uploads a brief PDF from a run dir.

Run from the run dir (prediction/runs/<date>/):
  python3 ../../pipeline/gateway_files.py get <token> bbb_snapshot_w<N>.json
  python3 ../../pipeline/gateway_files.py put <token> "<brief>.pdf" bbb_week<N>_brief.pdf

get writes ./snapshot.json and prints its sha256. put prints the gateway's reply and
exits 1 if the gateway's sha256 differs from the local file's.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

BASE = "https://mcp.rrr-projects.com/files/"
RUNS = (Path(__file__).resolve().parent.parent / "runs").resolve()
TOKEN_RE = re.compile(r"[0-9a-f]{64}")
SNAPSHOT_RE = re.compile(r"bbb_snapshot_w\d{1,2}\.json")
BRIEF_RE = re.compile(r"bbb_week\d{1,2}_brief\.pdf")
MAX_PDF_BYTES = 20 * 1024 * 1024


def fail(msg):
    print(f"gateway_files: {msg}", file=sys.stderr)
    sys.exit(2)


def in_runs(path):
    p = path.resolve()
    return p.parent.parent == RUNS and p.parent.is_dir()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def curl(token, *args):
    cmd = ["curl", "-sS", "--proto", "=https", "--max-redirs", "0",
           "-H", f"Authorization: Bearer {token}", *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def main(argv):
    if len(argv) < 3:
        fail(__doc__)
    op, token = argv[0], argv[1]
    if not TOKEN_RE.fullmatch(token):
        fail("token must be the 64-hex upload token from gateway__upload_direct_lane")

    if op == "get" and len(argv) == 3:
        name = argv[2]
        if not SNAPSHOT_RE.fullmatch(name):
            fail("get only fetches bbb_snapshot_w<N>.json")
        out = Path("snapshot.json")
        if not in_runs(out):
            fail(f"run this from a run dir under {RUNS}")
        r = curl(token, "--fail-with-body", "-o", str(out), BASE + name)
        if r.returncode:
            out.unlink(missing_ok=True)
            fail(f"download failed ({r.returncode}): {r.stderr.strip()}")
        print(f"{sha256(out)}  snapshot.json")
        return

    if op == "put" and len(argv) == 4:
        local, name = Path(argv[2]), argv[3]
        if not BRIEF_RE.fullmatch(name):
            fail("put only uploads to bbb_week<N>_brief.pdf")
        if local.suffix.lower() != ".pdf" or not local.is_file() or not in_runs(local):
            fail(f"put only uploads a .pdf that sits in a run dir under {RUNS}")
        if local.stat().st_size > MAX_PDF_BYTES:
            fail("PDF is larger than 20 MB")
        with open(local, "rb") as f:
            if f.read(5) != b"%PDF-":
                fail("file is not a PDF")
        r = curl(token, "-T", str(local), BASE + name)
        print(r.stdout.strip())
        if r.returncode:
            fail(f"upload failed ({r.returncode}): {r.stderr.strip()}")
        try:
            remote = json.loads(r.stdout).get("sha256")
        except ValueError:
            remote = None
        local_hash = sha256(local)
        if remote != local_hash:
            print(f"sha256 mismatch: gateway {remote}, local {local_hash}", file=sys.stderr)
            sys.exit(1)
        print(f"sha256 matches: {local_hash}")
        return

    fail(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
