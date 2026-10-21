"""Voice to text for the pages: audio bytes in, text out, through a warm local Whisper worker.

home.py may run under any python, so the model lives in a worker subprocess that uses the editor
venv's python (the one setup.py builds). The worker loads WhisperModel once and answers JSON lines.

    python dictate.py <audio file>     prints the JSON result
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

HOME = Path(os.environ.get("AI_EDITOR_HOME", Path.home() / ".ai-video-editor"))
VPY = HOME / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
MODEL = os.environ.get("AI_EDITOR_WHISPER_MODEL", "small")
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_lock = threading.Lock()
_proc = None


class DictateError(Exception):
    def __init__(self, msg, code="failed"):
        super().__init__(msg)
        self.code = code


def _worker():
    """Runs inside the venv python: load the model once, then one JSON line in, one out."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    os.environ.setdefault("HF_HOME", str(HOME / "models"))
    try:
        from ai_editor import models
        from faster_whisper import WhisperModel
        path = models.whisper_dir(MODEL)
        if not path and MODEL not in models.WHISPER:
            from faster_whisper.utils import download_model
            path = download_model(MODEL, local_files_only=True, cache_dir=str(HOME / "models"))
        if not path:
            raise FileNotFoundError(MODEL)
        model = WhisperModel(str(path), device="cpu", compute_type="int8",
                             download_root=str(HOME / "models"), local_files_only=True)
    except FileNotFoundError:
        print(json.dumps({"fatal": "no_model", "msg": f"The {MODEL} transcription model is not installed."}), flush=True)
        return
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"fatal": "failed", "msg": f"Could not load the model: {e}"}), flush=True)
        return
    print(json.dumps({"ready": True}), flush=True)
    for line in sys.stdin:
        try:
            req = json.loads(line)
            t = time.time()
            # a known language skips detection, which costs as long as the transcription itself on a laptop CPU
            segs, info = model.transcribe(req["wav"], language=req.get("lang"), vad_filter=True, beam_size=1,
                                          without_timestamps=True, condition_on_previous_text=False)
            text = " ".join(s.text.strip() for s in segs).strip()
            out = {"text": text, "lang": info.language, "secs": round(time.time() - t, 2)}
        except Exception as e:  # noqa: BLE001
            out = {"error": str(e)}
        print(json.dumps(out), flush=True)


def _start():
    """Caller holds _lock. Returns a live, ready worker or raises DictateError."""
    global _proc
    if _proc and _proc.poll() is None:
        return _proc
    _proc = None
    if not VPY.exists():
        raise DictateError("The editor's Python environment is not set up. Run setup.", "no_venv")
    p = subprocess.Popen([str(VPY), str(Path(__file__).resolve()), "--worker"], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                         creationflags=NOWIN)
    first = p.stdout.readline()
    try:
        msg = json.loads(first)
    except ValueError:
        p.kill()
        raise DictateError("The transcription worker did not start. Run setup to repair the Python packages.",
                           "no_venv")
    if msg.get("fatal"):
        p.kill()
        raise DictateError(msg.get("msg", "Transcription is unavailable."), msg["fatal"])
    _proc = p
    return p


def warm():
    """Start the worker in the background so the first dictation is fast. Never raises."""
    def go():
        try:
            with _lock:
                _start()
        except Exception:  # noqa: BLE001
            pass
    threading.Thread(target=go, daemon=True).start()


def transcribe(audio_bytes, mime="audio/webm", lang=None):
    """-> {"text", "lang", "secs"}. lang ("he", "en", ...) or None to detect. Raises DictateError with code
    no_model, no_ffmpeg, no_venv or failed."""
    lang = lang if lang and lang.isalpha() and len(lang) <= 3 else None
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise DictateError("ffmpeg is not installed. Run setup.", "no_ffmpeg")
    if not audio_bytes:
        raise DictateError("No audio was recorded.", "failed")
    ext = "ogg" if "ogg" in mime else "mp4" if "mp4" in mime else "wav" if "wav" in mime else "webm"
    with tempfile.TemporaryDirectory(prefix="dictate-") as td:
        src, wav = Path(td) / f"in.{ext}", Path(td) / "out.wav"
        src.write_bytes(audio_bytes)
        r = subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "16000", str(wav)],
                           capture_output=True, text=True, creationflags=NOWIN)
        if r.returncode or not wav.exists():
            raise DictateError("Could not read that recording: " + (r.stderr.strip()[-200:] or "ffmpeg failed"), "failed")
        with _lock:
            for attempt in (0, 1):
                p = _start()
                try:
                    p.stdin.write(json.dumps({"wav": str(wav), "lang": lang}) + "\n")
                    p.stdin.flush()
                    line = p.stdout.readline()
                    if not line:
                        raise OSError("worker died")
                    out = json.loads(line)
                    break
                except (OSError, ValueError):
                    p.kill()
                    if attempt:
                        raise DictateError("The transcription worker stopped. Try again.", "failed")
    if out.get("error"):
        raise DictateError(out["error"], "failed")
    return {"text": out["text"], "lang": out["lang"], "secs": out["secs"]}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        _worker()
    elif len(sys.argv) > 1:
        t = time.time()
        try:
            res = transcribe(Path(sys.argv[1]).read_bytes(), "audio/" + Path(sys.argv[1]).suffix.lstrip(".").lower())
            res["total"] = round(time.time() - t, 2)
            print(json.dumps(res, ensure_ascii=False))
        except DictateError as e:
            print(json.dumps({"error": str(e), "code": e.code}))
            sys.exit(1)
        finally:
            if _proc:
                _proc.kill()
    else:
        sys.exit("usage: python dictate.py <audio file>")
