"""Serve the course dashboard with this submission's latest dry-run state."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import tempfile

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1] / "week-03" / "code" / "lab-bot"
STATE = HERE / "dry_run_state.json"
WEBROOT = Path(tempfile.gettempdir()) / "zhenzhenfang_local_arena"
PORT = 8010


def main():
    if not STATE.is_file():
        raise SystemExit("dry_run_state.json is missing; run run_local_dry_run.py first")
    WEBROOT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(LAB / "dashboard.html", WEBROOT / "dashboard.html")
    shutil.copyfile(STATE, WEBROOT / "state.json")
    handler = partial(SimpleHTTPRequestHandler, directory=str(WEBROOT))
    server = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    print(f"Local Arena Dashboard: http://localhost:{PORT}/dashboard.html", flush=True)
    print("Read-only dry-run state only. Press Ctrl-C to stop this server.", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
