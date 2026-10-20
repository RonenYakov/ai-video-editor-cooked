# python tools/beats.py <film-folder>/audio/track.wav > <film-folder>/audio/beats.json
#
# Writes the music grid. Every cut in the film lands on a timestamp from here.
#
# Downbeats are deliberately NOT inferred. Taking every fourth beat assumes 4/4
# and assumes beat one is a downbeat, and both are often wrong. Set barOne in
# film.config.json by ear once, and bars derive from it.
import sys, json
import numpy as np
import librosa

if len(sys.argv) < 2:
    sys.exit("usage: python tools/beats.py <audio file>")

y, sr = librosa.load(sys.argv[1], sr=None, mono=True)
tempo, frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
beats = librosa.frames_to_time(frames, sr=sr).round(3).tolist()

# Normalise onset strength so delta is a fraction of the loudest onset rather
# than an arbitrary absolute that changes with every track.
onset = librosa.onset.onset_strength(y=y, sr=sr)
peak = onset.max()
onset = onset / peak if peak else onset
hits = librosa.util.peak_pick(
    onset, pre_max=3, post_max=3, pre_avg=3, post_avg=5, delta=0.08, wait=10
)

json.dump({
    "source": sys.argv[1],
    "bpm": round(float(np.atleast_1d(tempo)[0]), 2),
    "duration": round(float(len(y) / sr), 3),
    "beats": beats,
    "hits": librosa.frames_to_time(hits, sr=sr).round(3).tolist(),
    "note": "downbeats are not inferred. set barOne in film.config.json by ear.",
}, sys.stdout, indent=1)
