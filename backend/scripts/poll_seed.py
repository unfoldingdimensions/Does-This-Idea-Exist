"""Poll the design_library seed job until it finishes; print final summary."""
import json
import time
import urllib.request

JOB = "5012c44ba3fc"
tok = None
for line in open(".env", encoding="utf-8"):
    line = line.strip()
    if line.startswith("ADMIN_TOKEN="):
        tok = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
assert tok, "no ADMIN_TOKEN"

while True:
    with urllib.request.urlopen(
        urllib.request.Request(
            f"http://localhost:8020/api/admin/seed/status/{JOB}",
            headers={"X-Admin-Token": tok},
        )
    ) as r:
        j = json.loads(r.read())
    print(
        f"{time.strftime('%H:%M:%S')} {j['status']} {j['done']}/{j['total']} "
        f"ok={j['ok']} failed={j['failed']} current={j['current'][:70]}",
        flush=True,
    )
    if j["status"] in ("done", "failed"):
        print("ERRORS:", json.dumps(j["errors"], indent=1))
        break
    time.sleep(45)
