import os
import uuid
import tempfile
import threading
import subprocess
import json
import time

from flask import Flask, request, jsonify, send_file, Response, render_template

app = Flask(__name__)

# Stockage en mémoire des jobs
# Structure : {job_id: {status, logs, file, filename}}
# status : "running" | "done" | "error"
JOBS = {}
JOBS_LOCK = threading.Lock()


def build_yt_dlp_cmd(url, quality, fmt, audio_only, output_dir, audio_quality="192"):
    cmd = ["yt-dlp", "--no-playlist", "--no-check-certificates"]

    if audio_only == "true":
        # audio_quality = bitrate en kbps (128, 192, 320)
        cmd += ["-x", "--audio-format", "mp3", "--audio-quality", audio_quality + "K"]
    else:
        # Construction du format string yt-dlp selon qualité + conteneur
        if quality == "best":
            format_str = f"bestvideo[ext={fmt}]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
        else:
            # Ex: "720p" → height=720
            height = quality.replace("p", "")
            format_str = (
                f"bestvideo[height<={height}][ext={fmt}]+bestaudio[ext=m4a]"
                f"/bestvideo[height<={height}]+bestaudio"
                f"/best[height<={height}]/best"
            )
        cmd += ["-f", format_str, "--merge-output-format", fmt]

    # Sortie dans le dossier du job, nom de fichier auto
    cmd += ["-o", os.path.join(output_dir, "%(title)s.%(ext)s")]
    cmd.append(url)
    return cmd


def run_download(job_id, url, quality, fmt, audio_only, audio_quality="192"):
    # Dossier temporaire propre à ce job
    tmp_base = tempfile.mkdtemp()
    output_dir = os.path.join(tmp_base, job_id)
    os.makedirs(output_dir, exist_ok=True)

    cmd = build_yt_dlp_cmd(url, quality, fmt, audio_only, output_dir, audio_quality)

    with JOBS_LOCK:
        JOBS[job_id]["logs"].append(f"$ {' '.join(cmd)}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        # Streamer chaque ligne de yt-dlp dans les logs du job
        for line in proc.stdout:
            line = line.rstrip("\n")
            if line:
                with JOBS_LOCK:
                    JOBS[job_id]["logs"].append(line)

        proc.wait()

        if proc.returncode != 0:
            raise RuntimeError(f"yt-dlp exited with code {proc.returncode}")

        # Trouver le fichier produit dans le dossier de sortie
        files = [f for f in os.listdir(output_dir) if not f.startswith(".")]
        if not files:
            raise RuntimeError("No file produced by yt-dlp")

        downloaded_file = os.path.join(output_dir, files[0])

        with JOBS_LOCK:
            JOBS[job_id]["status"] = "done"
            JOBS[job_id]["file"] = downloaded_file
            JOBS[job_id]["filename"] = files[0]
            JOBS[job_id]["tmp_base"] = tmp_base

    except Exception as exc:
        with JOBS_LOCK:
            JOBS[job_id]["logs"].append(f"ERROR: {exc}")
            JOBS[job_id]["status"] = "error"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
def download():
    url = request.form.get("url", "").strip()
    quality = request.form.get("quality", "best")
    fmt = request.form.get("format", "mp4")
    audio_only = request.form.get("audio_only", "false")
    audio_quality = request.form.get("audio_quality", "192")

    if not url:
        return jsonify({"error": "url is required"}), 400

    job_id = str(uuid.uuid4())
    with JOBS_LOCK:
        JOBS[job_id] = {
            "status": "running",
            "logs": [],
            "file": None,
            "filename": None,
            "tmp_base": None,
        }

    # Lancer le téléchargement dans un thread daemon pour ne pas bloquer Flask
    t = threading.Thread(
        target=run_download,
        args=(job_id, url, quality, fmt, audio_only, audio_quality),
        daemon=True,
    )
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/progress/<job_id>")
def progress(job_id):
    if job_id not in JOBS:
        return jsonify({"error": "unknown job"}), 404

    def generate():
        sent_lines = 0  # index dans la liste des logs déjà streamés

        while True:
            with JOBS_LOCK:
                job = JOBS[job_id]
                new_lines = job["logs"][sent_lines:]
                status = job["status"]
                filename = job["filename"]

            # Envoyer les nouvelles lignes de log au client
            for line in new_lines:
                payload = json.dumps({"log": line})
                yield f"data: {payload}\n\n"
            sent_lines += len(new_lines)

            if status == "done":
                payload = json.dumps({"done": True, "filename": filename})
                yield f"data: {payload}\n\n"
                break
            elif status == "error":
                payload = json.dumps({"error": True})
                yield f"data: {payload}\n\n"
                break

            time.sleep(0.3)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/file/<job_id>")
def serve_file(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)

    if not job:
        return jsonify({"error": "unknown job"}), 404
    if job["status"] != "done" or not job["file"]:
        return jsonify({"error": "file not ready"}), 404

    file_path = job["file"]
    filename = job["filename"]
    tmp_base = job["tmp_base"]

    @app.after_request
    def cleanup_after(response):
        # Nettoyage du dossier temp après envoi de la réponse
        import shutil
        try:
            shutil.rmtree(tmp_base, ignore_errors=True)
        except Exception:
            pass
        return response

    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
