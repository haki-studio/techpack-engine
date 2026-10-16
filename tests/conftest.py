import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "engine"), os.path.join(ROOT, "projects", "drum-island-plum-pine")]
os.chdir(os.path.join(ROOT, "projects", "drum-island-plum-pine"))
