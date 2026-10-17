"""Build a per-part material repair-plan review from stage-02's confirmed PNGs.

--upstream parts.workflow --config repair-plan.json --out material-review.html
--draft-preview explicitly permits a non-approvable preview of an upstream draft.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy import ndimage

from material_plan import STAGE, validate
from part_design import decode_png
from review_checkpoint import checkpoint, digest, initialize, read


def alpha_metrics(part):
    tile = decode_png(part['src'])
    mask = np.asarray(tile)[:,:,3]>0
    labels, _ = ndimage.label(mask,np.ones((3,3),bool))
    sizes = np.bincount(labels.ravel())[1:]
    tiny = sizes[sizes<=12]
    boxes=[]
    for index, bounds in enumerate(ndimage.find_objects(labels),1):
        if bounds is not None and sizes[index-1]<=12:
            y,x=bounds
            boxes.append([x.start,y.start,x.stop,y.stop])
    return dict(width=tile.width,height=tile.height,opaque_pixels=int(mask.sum()),
        transparent_fraction=round(float(1-mask.mean()),5),
        components=int(len(sizes)),small_component_count=int(len(tiny)),
        small_component_pixels=int(tiny.sum()),threshold_px=12,
        small_component_boxes=boxes,
        tight_bbox=list(tile.getchannel('A').getbbox()))


def build(upstream,config_path,out_path,draft_preview=False):
    gate=checkpoint(upstream)
    approved=gate['status']=='confirmed' and gate.get('approval_scope')=='part-separation'
    if not approved and not draft_preview:
        raise ValueError('Stage 02 requires a valid human-confirmed part-separation checkpoint')
    state=read(upstream/'workflow.json')
    source=read(Path(gate['confirmed_file']))['design'] if approved else read(upstream/'draft.json')
    config=json.loads(config_path.read_text(encoding='utf-8-sig'))
    supplied={row['part_id']:row for row in config['repairs']}
    ids={part['id'] for part in source['parts']}
    if len(supplied)!=len(config['repairs']) or set(supplied)!=ids:
        raise ValueError('Supply one deliberate recommendation for every actual cutout')
    data={key:source[key] for key in ('schema_version','coordinate_system','image','nodes','parts','order','face')}
    data.update(title=config.get('title','部件补全与 SVG 重绘计划'),demo=not approved,
        plan_review='proposed',note=config.get('note',''),
        upstream=dict(project=str(upstream.resolve()),run_id=state['run_id'],revision=state['revision'],design_sha256=digest(source)),
        metrics={p['id']:alpha_metrics(p) for p in source['parts']},repair_plan=[])
    for key in source['order']:
        spec=supplied[key]
        suggestion={action:spec.get(action,False) for action in ('complete','svg','clean')}
        suggestion.update(priority=spec.get('priority','low'),reason=spec['reason'],regions=spec.get('regions',[]))
        data['repair_plan'].append(dict(part_id=key,suggestion=suggestion,
            **{action:suggestion[action] for action in ('complete','svg','clean')},note='',review='proposed'))
    validate(data)
    project=out_path.with_name(out_path.stem+'.workflow')
    data=initialize(project.resolve(),data,out_path,stage=STAGE)
    template=(Path(__file__).resolve().parent.parent/'assets/material-review.html').read_text(encoding='utf-8')
    opening='<script id="rig-data" type="application/json">'
    start=template.index(opening)+len(opening);end=template.index('</script>',start)
    page=template[:start]+json.dumps(data,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')+template[end:]
    out_path.parent.mkdir(parents=True,exist_ok=True)
    out_path.write_text(page,encoding='utf-8')
    print(json.dumps(dict(preview=str(out_path.resolve()),project=str(project.resolve()),
        parts=len(data['parts']),demo=data['demo']),ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream',type=Path,required=True)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--draft-preview',action='store_true')
    args=parser.parse_args()
    build(args.upstream.resolve(),args.config.resolve(),args.out.resolve(),args.draft_preview)
