"""Rulebook v0 (ENGINE_PLAN M1): kind -> technique + direction + stitch numbers, read from rules/house.yaml.

  rb = Rulebook(toggles=cfg["techniques"])
  rb.technique_for("fall_cord")          -> "split_satin" (first ENABLED technique in the kind's list)
  rb.stitch_spec("fall_cord")            -> StitchSpec(technique="split_satin", spacing=0.42, ...)
  rb.direction("sky_band")               -> DirSpec(0, source="rule")
  rb.direction("zone_stub", field=37.5)  -> DirSpec(37.5, source="field-mean")

A kind whose techniques are ALL disabled raises RulebookError: the engine never falls back to something the run did not
allow (a toggle is a promise to the founder, e.g. "no satin on this garment"). A kind with no rule raises too."""
import os
from digitize.schema import DirSpec, StitchSpec

HERE = os.path.dirname(os.path.abspath(__file__))
HOUSE = os.path.join(HERE, "rules", "house.yaml")


class RulebookError(ValueError):
    pass


def _load(path):
    from digitize import config
    return config._read(path)


class Rulebook:
    def __init__(self, path=None, toggles=None, overrides=None):
        from digitize import config
        self.path = path or HOUSE
        self.data = config.merge(_load(self.path), overrides or {})
        self.principles = self.data["principles"]
        self.toggles = dict(toggles or {})

    def enabled(self, tech):
        return bool(self.toggles.get(tech, True))

    def rule(self, kind):
        k = self.data["kinds"].get(kind)
        if k is None: raise RulebookError(f"rulebook {os.path.basename(self.path)}: no rule for kind {kind!r}")
        return k

    def technique_for(self, kind):
        opts = self.rule(kind)["techniques"]
        for t in opts:
            if self.enabled(t): return t
        raise RulebookError(f"kind {kind!r}: every technique it may use {opts} is disabled in this run "
                            f"({ {t: self.toggles.get(t) for t in opts} }). Enable one in run.yaml `techniques:` or "
                            f"add a technique to the kind in {os.path.basename(self.path)}; the engine never substitutes.")

    def stitch_spec(self, kind, technique=None):
        t = technique or self.technique_for(kind); k = self.rule(kind)
        base = dict(self.data["techniques"].get(t, {}))
        for key in ("spacing", "stitch_len", "underlay", "pull_comp"):
            if key in k: base[key] = k[key]
        params = {key: v for key, v in base.items() if key not in ("spacing", "stitch_len", "underlay", "pull_comp")}
        return StitchSpec(technique=t, spacing=float(base.get("spacing", 0.45)), stitch_len=float(base.get("stitch_len", 3.5)),
                          underlay=list(base.get("underlay", [])), pull_comp=float(base.get("pull_comp", 0.2)), params=params)

    def direction(self, kind, field=None):
        d = self.rule(kind)["dir"]
        if d == "field-mean":
            if field is None: raise RulebookError(f"kind {kind!r} takes the field-mean angle: pass field=<deg>")
            return DirSpec(float(field), source="field-mean")
        return DirSpec(float(d), source="rule")

    def z(self, kind, default=None):
        z = self.rule(kind).get("z", default)
        if z is None: raise RulebookError(f"kind {kind!r} has no z in the rulebook: give it from the zone")
        return float(z)
