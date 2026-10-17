"""cover_front.png / cover_back.png: the size-M flat lay (views.py) with the stitch preview of every piece in place."""
import wavecore as WC
import views as V
for v in ("front", "back"):
    im, bb, X = V.view_png(v, "M", 2.2); im.save(f"cover_{v}.png"); print(v, im.size)
