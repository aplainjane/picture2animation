"""Build motion production only from the valid human-approved stage05 rig."""
import argparse,json
from pathlib import Path
from review_checkpoint import checkpoint,read,initialize
from motion_design import propose,validate,STAGE
from export_review_history import embed

def build(upstream,out):
    gate=checkpoint(upstream)
    if gate['status']!='confirmed' or gate.get('approval_scope')!='skeleton-animation-rig':raise ValueError('A current human-confirmed skeleton-animation-rig is required')
    approved=read(Path(gate['confirmed_file']));data=propose(approved['design'])
    data['upstream']=dict(project=str(upstream.resolve()),run_id=approved['run_id'],revision=approved['revision'],design_sha256=approved['design_sha256']);data['demo']=False;validate(data)
    assets=Path(__file__).resolve().parent.parent/'assets';page=(assets/'motion-review.html').read_text(encoding='utf8')
    for file in ('motion-runtime.js','motion-eyes.js','motion-material-editor.js'):page=page.replace('/* EMBED '+file+' */',(assets/file).read_text(encoding='utf8'))
    out.parent.mkdir(parents=True,exist_ok=True)
    data=initialize(out.with_name(out.stem+'.workflow').resolve(),data,out,STAGE)
    out.write_text(embed(page,'rig-data',data),encoding='utf8')
    print(json.dumps(dict(preview=str(out),project=str(out.with_name(out.stem+'.workflow')),clips=[c['id'] for c in data['production']['clips']]),ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--upstream',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.upstream.resolve(),a.out.resolve())
