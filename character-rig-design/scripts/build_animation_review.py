"""Build stage05 only from a valid, human-approved stage04 snapshot."""
import argparse,json
from pathlib import Path
from review_checkpoint import checkpoint,read,initialize
from animation_design import propose,validate,STAGE


def build(upstream,out,eye_guides=None):
    gate=checkpoint(upstream)
    if gate['status']!='confirmed' or gate.get('approval_scope')!='material-repair-result':
        raise ValueError('A current human-confirmed material-repair-result is required')
    approved=read(Path(gate['confirmed_file']));data=propose(approved['design'])
    data['upstream']=dict(project=str(upstream.resolve()),run_id=approved['run_id'],revision=approved['revision'],design_sha256=approved['design_sha256'])
    data['demo']=False;validate(data)
    template=(Path(__file__).resolve().parent.parent/'assets/animation-review.html').read_text(encoding='utf8')
    from export_review_history import embed
    if eye_guides:
        from review_checkpoint import image_digest
        from animation_design import validate_eye_guides
        proposed=read(eye_guides)
        if proposed['image_sha256']!=image_digest(data):raise ValueError('Eye guide proposals belong to another image')
        validate_eye_guides(data,proposed['eyes'])
        template=embed(template,'eye-guide-proposals',proposed['eyes'])
    out.parent.mkdir(parents=True,exist_ok=True)
    data=initialize(out.with_name(out.stem+'.workflow').resolve(),data,out,STAGE)
    out.write_text(embed(template,'rig-data',data),encoding='utf8')
    print(json.dumps(dict(preview=str(out),project=str(out.with_name(out.stem+'.workflow')),nodes=len(data['nodes']),parts=len(data['parts'])),ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--upstream',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--eye-guides',type=Path)
    args=parser.parse_args();build(args.upstream.resolve(),args.out.resolve(),args.eye_guides)
