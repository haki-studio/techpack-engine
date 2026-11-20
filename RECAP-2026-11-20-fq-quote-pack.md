# RECAP 2026-11-20: fq-quote-pack (quote pack vs award pack spec)

## What
- `docs/QUOTE_PACK_SPEC.md`: design-phase spec (due 24 Nov; build 2-18 Dec). Tiers quote/award/internal, placeholder
  decoration box, per-factory mark + copy code + harmless variation + register, gates G1-G8 with red-then-green proofs,
  DoD test `tests/test_quote_pack.py`.
- Decision: supplier names for G5/footer come from the existing `factory.json` `suppliers` map (read by
  `engine/supplier_gate.py`), not a new `engine/suppliers.json`: one supplier list.

## Caveat
- First lead (dd31034b) wrote the spec, hit the 5-h limit before committing; respawned lead e91bf9bb committed + opened PR #67.

## Next
- Reviewer verdict on PR #67 → fix or CTO sign + release:ready.
- Build phase 2 Dec: `engine/quote_pack.py`, `engine/trace_mark.py`, tier tags in `factory_copy.py`; first adopter Pixel Sky.
