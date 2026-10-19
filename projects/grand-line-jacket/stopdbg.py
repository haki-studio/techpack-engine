import glcore, pickle, json
import pyembroidery as pe, readback
dst2 = glcore.patch_dst2()
import tech
r = json.load(open('out/01_front-scene/M/result_FR.json'))['full']
rb = readback.dst(r['file'] + '.dst')
print('DST', [(p['stop'], p['stitches']) for p in rb['per_stop']])
p = pe.read(r['file'] + '.dst')
cmds = [c & pe.COMMAND_MASK for x, y, c in p.stitches]
import collections; print(collections.Counter(cmds))
# first commands
print([pe.get_command_dictionary().get(c, c) if hasattr(pe,'get_command_dictionary') else c for c in cmds[:12]])
