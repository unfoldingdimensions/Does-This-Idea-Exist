# IdeaExists backend — host-agnostic image (Fly / Railway / Render / any VPS).
#
# Requires a persistent writable volume mounted at /data: the archive is a
# SQLite file, not an external database. Without one, every deploy starts empty.
FROM python:3.11-slim

# Faster, quieter, no .pyc litter in the layer.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first so app edits don't invalidate the install layer.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Bundled seed sources. config.BASE_DIR resolves to /app, so the "famous" and
# "design_library" seeders look for these at /app/data/ — without them those two
# sources fail at runtime. Note this is NOT where the DB lives (that's /data).
COPY data/seed_famous.json data/seed_design_library.json ./data/

# Non-root. The volume mount point is created and chowned here so the container
# can write the DB even when the host mounts an empty named volume.
RUN useradd --create-home --uid 10001 ideasexist \
    && mkdir -p /data \
    && chown -R ideasexist:ideasexist /app /data
USER ideasexist

ENV DB_PATH=/data/ideasexist.db \
    LOG_LEVEL=INFO
EXPOSE 8020

# curl is not installed (slim, non-root) — use the stdlib so the healthcheck
# needs no extra package.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8020/api/health', timeout=4).status == 200 else 1)"]

# --workers 1 is a CORRECTNESS constraint, not a tuning knob. The job queue is
# in-process: worker threads start at module import and JOBS/QUEUES are
# per-process, so the "one verify pass at a time" guard only sees its own
# process. A second worker means two concurrent verify passes competing for the
# GitHub rate limit, two startup auto-verifies, and two writers on one SQLite
# file. Scale with more machines behind a load balancer, not more workers.
#
# --proxy-headers + --forwarded-allow-ips let uvicorn resolve the real client IP
# from the reverse proxy, which is what the per-IP rate limiter keys off.
# FORWARDED_ALLOW_IPS defaults to empty (trust nothing): set it to the proxy's
# address. Never "*" on a public host — that lets any caller spoof
# X-Forwarded-For and walk straight past the rate limits.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8020 --workers 1 --proxy-headers --forwarded-allow-ips=\"$FORWARDED_ALLOW_IPS\""]
