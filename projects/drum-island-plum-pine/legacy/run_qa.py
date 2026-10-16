import pickle, qa, json, sys, time
out={}
for tag in sys.argv[1:]:
    t0=time.time()
    d=pickle.load(open(f'back_{tag}.pkl','rb'))
    rows=qa.stitch_report(d["vis"])
    sil=qa.silhouette_check(d['vis'], d['W'], d['H'])
    out[tag]=dict(W=d['W'],H=d['H'],rows=rows,sil=sil)
    print('  silhouette', sil, flush=True)
    tot=sum(r["stitches"] for r in rows)
    print(f"== Option {tag}  {d['W']} x {d['H']} mm   est. stitches {tot:,.0f}   ({time.time()-t0:.0f}s)", flush=True)
    for r in rows:
        print(f"  {r['col']:<10}{r['cls']:<6} area {r['area']:8.0f}  thin {r['thin_pct']:5.1f}%  long-thin {r['long_pct']:4.1f}% (n={r['n_long']})  st {r['stitches']:8,.0f}", flush=True)
json.dump(out, open('qa_back.json','w'), default=float)
