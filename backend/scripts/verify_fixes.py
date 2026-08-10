"""Fix verification for the :8021 isolated instance — SSRF guard, rate limit.
Runs with the venv python; reads ADMIN_TOKEN from backend/.env without echoing it.
"""
import os
import sys

sys.path.insert(0, r"E:\New-Personal-Projects\Does this Startup Exist\backend")
os.chdir(r"E:\New-Personal-Projects\Does this Startup Exist\backend")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.getcwd(), ".env"))
tok = os.environ["ADMIN_TOKEN"]
base = "http://localhost:8021"

import httpx  # noqa: E402

# 1. SSRF through the live API with a valid token (guard must fire before fetch)
for url in [
    "http://127.0.0.1:8021/api/nonexistent",
    "http://localhost:8021/x",
    "http://169.254.169.254/latest/meta-data/",
    "http://192.168.1.1/",
    "http://10.0.0.1/",
]:
    try:
        r = httpx.post(
            f"{base}/api/seed/website",
            json={"website_url": url},
            headers={"X-Admin-Token": tok},
            timeout=30,
        )
        print(f"SSRF {url:45s} -> {r.status_code} {str(r.json().get('detail', ''))[:70]}")
    except Exception as exc:
        print(f"SSRF {url:45s} -> EXC {type(exc).__name__}: {str(exc)[:70]}")

# 2. netguard unit checks (no LLM involved)
from app import netguard  # noqa: E402

for u in ["http://127.0.0.1:8021/x", "http://[::1]/", "http://169.254.169.254/", "http://192.168.0.5/", "https://example.com"]:
    try:
        netguard.check_target(u)
        print(f"check_target {u:32s} -> OK (public)")
    except netguard.BlockedAddressError as exc:
        print(f"check_target {u:32s} -> BLOCKED: {exc}")

r = netguard.safe_get("https://example.com", timeout=20)
print("safe_get https://example.com ->", r.status_code, len(r.content), "bytes")

# 3. rate limit: 25 rapid admin/check calls with valid token (limit 20/min)
codes = []
for _ in range(25):
    r = httpx.get(f"{base}/api/admin/check", headers={"X-Admin-Token": tok}, timeout=10)
    codes.append(r.status_code)
print("rate-limit codes (expect 20x 200 then 429s):", codes)
print("429 count:", codes.count(429))
