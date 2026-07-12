#!/usr/bin/env python3
"""SPIKE — minimal computer dropper + table view over the lake seam.

NOT a part build. This is a Phase-C (05_spec-stub) *stack de-risking spike*:
can a single stdlib-Python file + one HTML page cover the Excel's 3 jobs
(drop / whole-stream view / edit-older)? Evidence for the amb-#3 stack call
(local web vs Swift vs TUI). Throwaway by intent; no dependency beyond the
part-1 `collevity` package on PYTHONPATH.

Run (against a TEST lake — never point this at the live lake casually):
    COLLEVITY_LAKE=/tmp/test_lake.jsonl PYTHONPATH=../jsonl-schema \
        python3 server.py [port]

⚠ SPEC FINDING (the spike's main payoff): the seam has NO id-bearing read.
`read_day` returns {text, time, created_at} — fine for /checkin, useless for
an edit UI (edit_entry needs the id). This spike reads ids via the PRIVATE
`_read_all` as a documented violation. Part-4-new's /spec must settle the
seam-level answer (e.g. `read_day(..., with_ids=True)` or a `read_entries()`
returning full records).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from collevity.lake import append_entry, edit_entry, read_day, sync_sources
from collevity.lake import lake as _lake_mod  # SPIKE ONLY — see module docstring

SOURCE = "computer-dropper"  # proposed channel tag (05_ stub open point)

PAGE = """<!doctype html><meta charset="utf-8">
<title>dropper</title>
<style>
 body{font:14px -apple-system,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem}
 #drop{width:100%;font:inherit;padding:.5rem}
 table{border-collapse:collapse;width:100%;margin-top:1rem}
 td{border-top:1px solid #ddd;padding:.35rem .5rem;vertical-align:top}
 td.t{white-space:nowrap;color:#888}
 td.x{width:100%} td.x[contenteditable]:focus{outline:2px solid #59f}
 #status{color:#888;margin-left:.5rem}
</style>
<h3>dropper <small id="status"></small></h3>
<input id="drop" placeholder="drop a thing — enter to save" autofocus>
<table id="rows"></table>
<script>
const S=document.getElementById('status');
async function load(){
  const r=await fetch('/api/day');const rows=await r.json();
  const t=document.getElementById('rows');t.innerHTML='';
  for(const e of rows.reverse()){
    const tr=document.createElement('tr');
    const td1=document.createElement('td');td1.className='t';td1.textContent=e.time;
    const td2=document.createElement('td');td2.className='x';td2.textContent=e.text;
    td2.contentEditable=true;td2.dataset.id=e.id;td2.dataset.orig=e.text;
    td2.addEventListener('blur',async ev=>{
      const el=ev.target;if(el.textContent===el.dataset.orig)return;
      await fetch('/api/edit',{method:'POST',body:JSON.stringify({id:el.dataset.id,text:el.textContent})});
      el.dataset.orig=el.textContent;S.textContent='edited '+new Date().toLocaleTimeString();
    });
    tr.append(td1,td2);t.append(tr);
  }
}
document.getElementById('drop').addEventListener('keydown',async e=>{
  if(e.key!=='Enter'||!e.target.value.trim())return;
  await fetch('/api/drop',{method:'POST',body:JSON.stringify({text:e.target.value})});
  e.target.value='';S.textContent='dropped '+new Date().toLocaleTimeString();load();
});
load();
</script>"""


def _today_rows_with_ids() -> list[dict]:
    """read_day + ids — via the private layer (SPIKE ONLY; see spec finding)."""
    today = datetime.now().astimezone().date()
    pool = _lake_mod._resolve_pool(None)
    rows = []
    for e in _lake_mod._read_all(pool):
        if _lake_mod._local_day(e["created_at"]) == today:
            rows.append(
                {
                    "id": e["id"],
                    "time": _lake_mod._local_time_hm(e["created_at"]),
                    "text": e["text"],
                    "created_at": e["created_at"],
                }
            )
    rows.sort(key=lambda r: datetime.fromisoformat(r["created_at"]))
    return rows


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        if self.path == "/":
            sync_sources()  # checkin-style freshness composition (DEC-019)
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif self.path.startswith("/api/day"):
            self._json(_today_rows_with_ids())
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path == "/api/drop":
                eid = append_entry(
                    {
                        "text": body["text"],
                        "created_at": datetime.now().astimezone().isoformat(),
                        "source": SOURCE,
                        "author": "user",
                    }
                )
                self._json({"id": eid})
            elif self.path == "/api/edit":
                edit_entry(body["id"], {"text": body["text"]})
                self._json({"ok": True})
            else:
                self._send(404, b"not found", "text/plain")
        except Exception as exc:  # spike: surface, don't crash the server
            self._json({"error": f"{type(exc).__name__}: {exc}"}, code=500)

    def log_message(self, *a):  # quiet
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"dropper spike on http://localhost:{port}  (lake: "
          f"{_lake_mod._resolve_pool(None)})")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
