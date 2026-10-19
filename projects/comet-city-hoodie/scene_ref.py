"""Reference geometry for fidelity.py, written by scene.py (scene_ref.pkl): comet zone + star / meteor exclusions."""
import pickle
_d = pickle.load(open("scene_ref.pkl", "rb"))
ZONE = _d["zone"]; STREAK_U = _d["streak"]; LIM = _d["lim"]; GLOWS = _d["glows"]
