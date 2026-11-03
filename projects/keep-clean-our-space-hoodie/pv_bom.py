"""KCOS Rev M pullover BOM: the ONE place the Rev M fabric lines live. pv_pack.k1() prints them on K1 and the Haki
standard labels (engine/labels.py, care label by fibre) are picked from SELF, so the care label can never drift back to
the Rev J zip-jacket shell ("12 oz cotton duck canvas", no fibre % -> MISSING) that kcgtp.py still records for Rev J.

Founder 27 Oct 2026: same fabric + wash as the Hidden Inventory Hoodie; lines copied verbatim from that pack's BOM
(14/09/2025), which the factory wrote. Product lead 29 Oct 2026 (card standard-labels-fibre-pct): KCOS = Rev M
pullover, French Terry 350 GSM 100 % cotton, rib 95/5 -> the care label is the 100 % cotton art.
Rev N (product lead 3 Nov 2026): Mandy said on 30-31 Oct the fabric is 425 GSM, not the 350 GSM in the Hidden Inventory
BOM -> SELF says 425 and K1 / K7 mark the change (GSM_NOTE); the BOM line as written is kept in SELF_HI_BOM.
Light on imports on purpose (no out/ files needed), so tests can import it."""
import os, sys
_ENGINE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "engine"))
if _ENGINE not in sys.path: sys.path.insert(0, _ENGINE)
import labelsheet as LS

SELF_HI_BOM = "French Terry/Fleece. 350 GSM. 100% Cotton. Finishing: Brushed on reverse side. Colour: washed black."
SELF = SELF_HI_BOM.replace("350 GSM", "425 GSM")
GSM_NOTE = "Weight updated to 425 GSM, as you told us on 30-31 Oct (our Hidden Inventory BOM said 350 GSM)."
GSM_NOTE_SHORT = "425 GSM, as you told us on 30-31 Oct (Hidden Inventory BOM said 350 GSM)"
RIB = "Rib Knit 1x1. 380 GSM. 2 Way strechable. 95% Cotton 5% Elastane. Colour: washed black."
# the care label follows the shell (self) fabric; the rib is a trim and does not pick the label
CARE_SHELL = SELF
# the fibre % is the factory's own BOM wording (Hidden Inventory), not our proposal -> printed as confirmed
FIBRE_CONFIRMED = True

FABRIC_ROWS = (("Self", SELF), ("Rib (cuffs + body hem)", RIB))


def label_rows():
    """(item, text) for the pack: ONE K1 row (K1 has no room for two before the footer) = the Haki standard main
    label + the care label picked from SELF; the full spec is the labels page K7 (Rev N)."""
    fb = LS.care_fibre(CARE_SHELL)
    care = (f"Haki standard care label, {fb}" + ("" if FIBRE_CONFIRMED else " " + LS.unconfirmed(fb))) if fb else f"care label {LS.MISSING}"
    return (("Labels", f"Haki standard main label, woven 6.5 × 2 cm (centre back neck) + {care}, 3 × 6.5 cm printed satin. "
                       "Placement, artwork 1:1 and question 7 (rib on the care label): page K7. Art: zip labels/."),)


# K7 placement rows (item, where, proposed?). The pullover has no lining and no neck facing: the main label sits on the
# inside back neck under the seam where the hood joins the body. Founder 22 Oct standard: CB, flat, sewn down on 4 sides.
PLACEMENT = (("Main label", "inside back neck, centred at CB, flat, sewn down on all 4 sides (black thread)", False),
             ("Main label height", "top edge 1.5 cm below the neck seam (where the hood joins the body)", True),
             ("Size label", "with the main label: centred at CB, directly under it", True),
             ("Care label", "inside, wearer's left side seam, 10 cm above the top of the hem rib", True))
RIB_Q = ("The care label says 100 % cotton (the self fabric). The rib on the cuffs and body hem is 95 % cotton / 5 % "
         "elastane and is NOT on the label. Is that right for you, or must the label list the rib too?")


def export_labels(d):
    """write the label files the Rev M zip carries (labels/) into d; returns the file names."""
    return LS.export(d, CARE_SHELL)
