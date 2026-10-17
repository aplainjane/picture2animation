"""--upstream stage03.workflow --manifest repairs/repair-manifest.json --out result.html"""
import argparse,base64,json
from pathlib import Path
from material_result import STAGE,validate
from review_checkpoint import checkpoint,read,initialize


def build(upstream,manifest,out,previous_review=None):
    gate=checkpoint(upstream)
    if gate['status']!='confirmed' or gate.get('approval_scope')!='material-repair-plan':
        raise ValueError('Human-confirmed material repair plan required')
    approved=read(Path(gate['confirmed_file']));source=approved['design'];report=read(manifest)
    expected=dict(project=str(upstream.resolve()),run_id=approved['run_id'],revision=approved['revision'],design_sha256=approved['design_sha256'])
    if report['upstream']!=expected:raise ValueError('Repair manifest does not match current confirmed plan')
    data={k:source[k] for k in ('schema_version','coordinate_system','image','nodes')}
    data.update(title=report['title'],parts=[r['part'] for r in report['rows']],order=report['order'],
        face={**source['face'],'review':'proposed'},repair_results=[],upstream=expected,demo=False,
        limitation=report['limitation']+' '+report.get('order_note',''),bundle='data:application/zip;base64,'+base64.b64encode((manifest.parent/'repaired-materials.zip').read_bytes()).decode('ascii'))
    decisions={r['part_id']:r for r in source['repair_plan']}
    originals={p['id']:p for p in source['parts']}
    for row in report['rows']:
        key=row['part']['id'];plan=decisions[key]
        if row['before']!=originals[key]:raise ValueError(f'Source cutout changed: {key}')
        if any(row['actions'][a]!=plan[a] for a in ('complete','svg','clean')):raise ValueError('Executed unapproved action')
        if not any(row['actions'].values()) and row['part']['src']!=row['before']['src']:
            raise ValueError(f'Unselected cutout changed: {key}')
        record={k:v for k,v in row.items() if k!='part'};record['part_id']=key
        for label in ('added','removed'):
            record[label+'_src']='data:image/png;base64,'+base64.b64encode((manifest.parent/label/f'{key}.png').read_bytes()).decode('ascii')
        record['svg_source']=(manifest.parent/row['svg_file']).read_text(encoding='utf-8') if row['svg_file'] else None
        data['repair_results'].append(record)
    if previous_review:
        previous=read(previous_review)
        if previous.get('upstream')!=expected or previous.get('workflow',{}).get('stage')!=STAGE:
            raise ValueError('Previous review must belong to the same approved input')
        previous_parts={p['id']:p for p in previous['parts']}
        for p in data['parts']:
            old=previous_parts.get(p['id'])
            if old:
                p['note']=old.get('note','')
                asset=lambda item:{k:v for k,v in item.items() if k not in ('quality','review','note')}
                if asset(p)==asset(old):
                    p.update(quality=old['quality'],review=old['review'])
                # Changed assets stay pending and require a fresh human check.
    validate(data)
    data=initialize(out.with_name(out.stem+'.workflow').resolve(),data,out,stage=STAGE)
    template=(Path(__file__).resolve().parent.parent/'assets/material-result.html').read_text(encoding='utf-8')
    opening='<script id="rig-data" type="application/json">';start=template.index(opening)+len(opening);end=template.index('</script>',start)
    out.write_text(template[:start]+json.dumps(data,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')+template[end:],encoding='utf-8')
    print(json.dumps(dict(preview=str(out.resolve()),project=str(out.with_name(out.stem+'.workflow').resolve()),parts=len(data['parts'])),ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream',type=Path,required=True);parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--previous-review',type=Path,help='Saved prior draft: retain notes and unchanged-part review states')
    args=parser.parse_args();build(args.upstream.resolve(),args.manifest.resolve(),args.out.resolve(),args.previous_review)
