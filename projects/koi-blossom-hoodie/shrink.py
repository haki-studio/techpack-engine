import sys
from pypdf import PdfReader, PdfWriter
src, dst, maxpx, q = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
w = PdfWriter(clone_from=src)
for page in w.pages:
    for img in page.images:
        im = img.image
        if im.mode in ("RGBA", "LA", "PA") or "/SMask" in img.indirect_reference.get_object():
            continue                    # transparent art on the flats: re-encoding as RGB would turn the background black
        if max(im.size) > maxpx:
            im.thumbnail((maxpx, maxpx))
        img.replace(im.convert("RGB"), quality=q)
w.compress_identical_objects(remove_identicals=True, remove_orphans=True)
w.write(dst)
