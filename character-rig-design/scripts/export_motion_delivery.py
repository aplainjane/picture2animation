"""Export a playable motion version, whether approved or awaiting review."""
import argparse,hashlib,json
from pathlib import Path
from review_checkpoint import read,validate_for_run,checkpoint,digest,now
from export_review_history import embed,export_stage
from motion_design import STAGE


def export(project):
    state=read(project/'workflow.json')
    if state['stage']!=STAGE:raise ValueError('Expected motion-production project')
    data=validate_for_run(read(project/'draft.json'),state)
    if digest(data)!=state['design_sha256']:raise ValueError('Draft changed; retry export')
    page=Path(state['preview_path']).read_text(encoding='utf8')
    page=embed(embed(page,'rig-data',data),'checkpoint-config',None)
    view=hashlib.sha256(page.encode('utf8')).hexdigest()[:8]
    target=project.parent/'delivery'/f"animation-{state['run_id'][:8]}-r{state['revision']}-{digest(data)[:10]}-{view}"
    gate=checkpoint(project)
    metadata=dict(run_id=state['run_id'],revision=state['revision'],design_sha256=digest(data),
                  status=gate['status'],exported_at=now(),upstream=data['upstream'],
                  note='Playable delivery; approval status is recorded separately. Later revisions remain editable in the review service.')
    if read(project/'workflow.json')!=state:raise ValueError('Review changed during export; retry')
    target.mkdir(parents=True,exist_ok=True)
    (target/'character-idle-run.html').write_text(page,encoding='utf8')
    (target/'character-idle-run.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    (target/'release.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf8')
    export_stage(project)
    return dict(directory=str(target),status=gate['status'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True)
    print(json.dumps(export(p.parse_args().project.resolve()),ensure_ascii=False))
