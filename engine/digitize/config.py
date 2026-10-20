"""Run configuration (ENGINE_PLAN M1): one run.yaml per digitizing run, with technique toggles, threads, budget, hoop
and gates. PyYAML reads it (requirements.txt); without PyYAML a JSON file (or YAML written as JSON, which is valid
YAML) still loads, and a real YAML file fails with a clear message instead of a traceback.

  cfg = config.load("projects/castle-falls-jacket/bench/run_bk_crop.yaml")
  cfg["techniques"]["satin"]   -> True / False
  config.path(cfg, cfg["zones"]) -> absolute path (relative paths resolve against cfg["project"])

Paths in the file are relative to `project` (itself relative to the yaml's folder; default: the folder above bench/)."""
import copy, json, os

DEFAULTS = {
    "techniques": {"tatami": True, "satin": True, "split_satin": True, "run": True, "bean": True,
                   "guided_fill": True, "contour_fill": True, "blend": True},                 # M2 plugins
    "rules": None,                         # None = engine/digitize/rules/house.yaml
    "rule_overrides": {},
    "threads": {"needles": "factory", "protected": [], "palette": {}},
    "evidence": {"ppm": 4.0, "smooth_mm": 0.35, "mode_mm": 0.6},
    "sequence": {"keep_mm": 1.0, "min_fragment_mm2": 2.0},
    "stub": {"min_part_mm2": 20.0, "min_protected_mm2": 4.0, "close_mm": 0.6},
    "direction": {"sigma_mm": 4.0, "fill_sigma_mm": 10.0, "min_coh": 0.25},     # M2: the reference-grain field
    "specks": {},                          # M2: merge_specks min_mm2 (default: stub.min_part_mm2)
    "budget": {"stitches_max": None},
    "hoop": None,
    "gates": {},
}


def _read(path):
    txt = open(path).read()
    try:
        import yaml
    except ImportError:
        try:
            return json.loads(txt)
        except ValueError:
            raise SystemExit(f"{path}: PyYAML is not installed and the file is not JSON. Install it "
                             f"(pip install -r requirements.txt) or pass the same config as .json.")
    return yaml.safe_load(txt) or {}


def merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def load(path, overrides=None):
    path = os.path.abspath(path); here = os.path.dirname(path)
    cfg = merge(DEFAULTS, _read(path))
    if overrides: cfg = merge(cfg, overrides)
    proj = cfg.get("project") or (os.path.dirname(here) if os.path.basename(here) == "bench" else here)
    cfg["project"] = os.path.abspath(os.path.join(here, proj))
    cfg["_path"] = path
    for k, v in cfg["techniques"].items():
        if not isinstance(v, bool): raise SystemExit(f"{path}: techniques.{k} must be true/false, got {v!r}")
    return cfg


def path(cfg, p):
    return p if os.path.isabs(p) else os.path.join(cfg["project"], p)


def needles(cfg):
    n = cfg["threads"].get("needles", "factory")
    if n == "factory":
        import factory
        return factory.max_threads()
    return int(n)
