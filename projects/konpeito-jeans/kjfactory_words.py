"""Konpeito factory-copy wording (kjfactory.py): leak patterns + scrub rules. No build data needed to import."""
from kjcore import KJ_PAL

# Konpeito-only leaks: pointers to internal pages, decision ids, people
EXTRA = [r"\bG6b?\b", r"_image\.png|back_pocket_haki\.png", r"\b\d+ px\b", r"\bmoved \d+ mm\b", r"\bthread added\b", r"\bthe trace\b", r"\bC[1-7]\b", r"\bQ1\b", r"\bJ[1-5]\b", r"\bQ-[ab]\b", r"Mandy", r"\bNick\b", r"\bSteph\b", r"\bDevin\b",
         r"per px\b", r"median of the", r"\bclient\b", r"mockup pixels", r"traced (?:bodies|per sprite)", r"reads cream", r"\bdropped\b"]   # how we digitised, not what to sew

# Konpeito wording -> factory wording (applied after factory_copy.BASE_SCRUB); None = drop the line
KJ_SCRUB = [
    (r"^Check — 07 trail map vs mockup$|^Compare — .*|^Founder decisions.*", None),
    (r"F · NOTES", "D · NOTES"),
    (r"; check vs mockup on C5, compare C7", ""),
    (r"\s*\(check on C5\)", ""), (r", compare on C7", ""), (r" \(C5, red X\)", ""), (r"\s*\(C5\)", ""),
    (r"; compare sheet in the pack", ""),
    (r"\s*\(07 front-leg trail included from Rev B6[^)]*\)", ""),
    (r"Size 24 is DROPPED: it was in the Rev A run and the brief, but has no row on the HI chart and no label\.", "No size 24 (not on the HI chart)."),
    (r"^Gates per sprite.*", None),
    (r"\(licen[cs]e risk accepted[^)]*\)", ""),
    (r"\s*— founder \d{1,2} Oct$", ""),
    (r"\bfounder change \d{1,2} Oct: ", ""), (r"\(founder change[^)]*\)", ""),
    (r"Founder \d{1,2} Oct \(J\d\): ", ""), (r"\s*\(J\d\)", ""),
    (r"Founder: scale up so the konpeito match\. ", ""),
    (r"\bfounder's vector art\b", "Haki vector art"), (r"\bFOUNDER'S VECTOR ART\b", "HAKI VECTOR ART"),
    (r"\s*\(inputs/svg, 16 Oct clean art, true size\)", " (true size)"),
    (r"\s*\(inputs/svg\)", ""), (r"inputs/svg/", ""), (r"inputs/", ""),
    (r"\bread back\b", "counted"),
    (r"No pants block in our engine: we do not draft a pattern\. ", ""),
    (r" / C5\)", ")"), (r", C5\)", ")"),
    (r"\s*Replaces the Rev [A-Z]\d* [^.]*\.", ""),
    (r"\s*\(PLM pipeline\.size_charts [0-9a-f-]+, published on Shopify, updated [\d-]+\)", ""),
    (r"HK code from PLM: to follow", "HK code: to follow"),
    (r"'haki' is not in the SVGs: traced from back_pocket_haki\.png \(as before\)\.", "'haki' traced from the mockup."),
    (r"^Mockup candies \d+ px .*", None), (r"^mockup shows them at \d+ px\)$", None),     # 2nd line of a wrapped "Generated" note
    (r"\(mockup ~\d+ mm in; moved \d+ mm inward to clear the outer topstitch\)", "(clears the outer topstitch)"),
    (r"\(mockup ~\d+ mm in; moved \d+ mm inward to clear the outer topstitch;$", "(clears the outer topstitch)."),
    (r"^move (?:CONFIRMED|confirmed)\)\.\s*", ""),
    (r" — KEPT, confirmed\.", "."),
    (r"\s*\(white thread added\)", ""),
    (r"^(?:move CONFIRMED|kept: confirmed|kept as the mockup)$", None),        # T8 note column: decision history
    (r"The trail on the garment mockup is the artwork \([^)]*\)\.", "The trail on the garment mockup is the artwork."),
    (r"^the (\d+) konpeito clipped", r"The \1 konpeito clipped"), (r"\s*The trace still finds them; this product excludes them\.", ""),
    (r"^the soot-sprite characters are KEPT as on the mockup\s*\.\s*Sewn first", "Soot sprites as on the mockup: sewn first"),
    # PR #57 review: say what to sew, not how we got there (B8 rewrites G7: the EXTRA patterns catch new wording)
    (r"^Edge red, as in the SVG \(shared with patch 03\): confirmed.*\(the mockup edge reads cream\)\.$", f"Edge: red {KJ_PAL['kj_red'][0]} (shared with patch 03)."),
    (r"Silhouette traced from the client flat lay; construction lines placed from it;", "Silhouette and construction lines from the flat lay;"),
    (r"\s*\(read from the mockup pixels\)", ""),
    (r"one width: art [\d.]+ mm -[>›] ([\d.]+ mm needle span)", r"one width, \1"),
    (r"\s*\(size 24 dropped: not on the HI chart, no label\)", ""),
    (r" = median of the \d+ traced bodies;", ";"),
    (r"\s*Redrawn from the low-res mockup \(~1 mm per px\):$", ""),
    (r"^eye \+ pupil positions traced per sprite; uniform body size, the fuzz length", "Eye + pupil positions as on the mockup; one body size; the fuzz length"),
    # B8 G7 (#58): most legs are inferred, so the factory copy must not claim "as on the mockup"
    (r"^Rev B8\s*: limbs, eye size and gaze from a hand-read art table of the low-res mockup \(~1 mm per px\)",
     "Limbs, eye size and gaze as drawn on this page and in the stitch file"),
]
