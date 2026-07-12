#!/usr/bin/env python3
"""
NusaTool Web Dashboard — Browser-based Hacking UI
Run:  python webapp.py
Then open: http://localhost:5000
"""

import os, sys, json, subprocess, threading, time, queue, re, html
from flask import Flask, render_template, request, jsonify, Response, stream_with_context

sys.path.insert(0, os.path.dirname(__file__))
from nusatool import VERSION, COMMON_PORTS

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

JOBS = {}
JOB_COUNTER = 0
JOB_LOCK = threading.Lock()

NUSATOOL = os.path.join(os.path.dirname(__file__), "nusatool.py")
WORDLISTS = os.path.join(os.path.dirname(__file__), "wordlists")

# ── Helpers ──

def run_nusatool(cmd_parts, job_id):
    """Run nusatool command in thread, capture output."""
    output = []
    def _run():
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            p = subprocess.Popen(
                [sys.executable, NUSATOOL] + cmd_parts,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                env=env, bufsize=1, text=True
            )
            for line in p.stdout:
                clean = line.rstrip("\n\r")
                # Strip ANSI codes for web display
                clean_ansi = re.sub(r'\033\[[0-9;]*[a-zA-Z]', '', clean)
                output.append(clean_ansi)
                with JOB_LOCK:
                    if job_id in JOBS:
                        JOBS[job_id]["output"].append(clean_ansi)
            p.wait()
            with JOB_LOCK:
                if job_id in JOBS:
                    JOBS[job_id]["done"] = True
        except Exception as e:
            with JOB_LOCK:
                if job_id in JOBS:
                    JOBS[job_id]["output"].append(f"[ERROR] {e}")
                    JOBS[job_id]["done"] = True
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return output

@app.route("/")
def index():
    return render_template("index.html", version=VERSION, common_ports=COMMON_PORTS[:20])

@app.route("/api/run", methods=["POST"])
def api_run():
    global JOB_COUNTER
    data = request.json
    module = data.get("module", "")
    args = data.get("args", "").strip()

    if not module:
        return jsonify({"error": "No module specified"}), 400

    cmd_parts = [module]
    if args:
        cmd_parts.extend(args.split())

    with JOB_LOCK:
        JOB_COUNTER += 1
        job_id = f"job_{JOB_COUNTER}"
        JOBS[job_id] = {"output": [], "done": False, "module": module}

    run_nusatool(cmd_parts, job_id)

    return jsonify({"job_id": job_id})

@app.route("/api/stream/<job_id>")
def api_stream(job_id):
    def generate():
        last_len = 0
        while True:
            with JOB_LOCK:
                if job_id in JOBS:
                    job = JOBS[job_id]
                    new_lines = job["output"][last_len:]
                    last_len = len(job["output"])
                    done = job["done"]
                else:
                    new_lines = ["[JOB NOT FOUND]"]
                    done = True

            for line in new_lines:
                yield f"data: {html.escape(line)}\n\n"

            if done:
                yield "data: __DONE__\n\n"
                break
            time.sleep(0.1)
    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/api/jobs")
def api_jobs():
    with JOB_LOCK:
        active = [(jid, j["module"], j["done"]) for jid, j in JOBS.items()]
    return jsonify({"jobs": active})

@app.route("/api/jobs/<job_id>", methods=["DELETE"])
def api_delete_job(job_id):
    with JOB_LOCK:
        if job_id in JOBS:
            del JOBS[job_id]
    return jsonify({"status": "deleted"})

@app.route("/api/clear")
def api_clear():
    with JOB_LOCK:
        JOBS.clear()
    return jsonify({"status": "cleared"})

@app.route("/api/ports")
def api_common_ports():
    return jsonify({"ports": COMMON_PORTS})

@app.route("/api/wordlists")
def api_wordlists():
    files = []
    if os.path.isdir(WORDLISTS):
        for f in sorted(os.listdir(WORDLISTS)):
            fp = os.path.join(WORDLISTS, f)
            if os.path.isfile(fp):
                with open(fp) as fh:
                    count = sum(1 for _ in fh)
                files.append({"name": f, "path": fp, "lines": count})
    return jsonify({"wordlists": files})

if __name__ == "__main__":
    os.makedirs(os.path.join(os.path.dirname(__file__), "templates"), exist_ok=True)
    print(f"\n  \033[96mNusaTool Web Dashboard\033[0m v{VERSION}")
    print(f"  \033[90mOpen: \033[92mhttp://localhost:5000\033[0m\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
