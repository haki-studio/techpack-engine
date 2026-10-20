"""Product families: one reusable FAMILY (block, construction, trims, packing, page set) + data-only VARIANTS.
See docs/FAMILIES.md. Build a variant:  python3 scripts/family_build.py families/tee/variants/alabasta.yaml"""
import functools


@functools.lru_cache(maxsize=1)
def factory_profile():
    import factory
    return factory.load()
