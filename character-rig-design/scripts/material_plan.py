"""Validation for stage-03 repair selections; this checkpoint approves a plan."""
import hashlib
import json
import math

from part_design import validate as validate_parts

STAGE = '03-material-completion'
SCOPE = 'material-repair-plan'


def source_fingerprint(data):
    # These fields are evidence, not editable choices. Bind to the exact cutouts
    # and AI proposal so a plan edit cannot silently replace the approved input.
    fields = {k:data[k] for k in ('image','coordinate_system','nodes','parts','order','face','upstream','metrics')}
    fields['suggestions'] = {r['part_id']:r['suggestion'] for r in data['repair_plan']}
    return hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(',',':'),
        ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()


def validate(data):
    validate_parts(data)
    plans = data.get('repair_plan')
    ids = {p['id'] for p in data['parts']}
    if not isinstance(plans,list) or len(plans)!=len(ids) or {r.get('part_id') for r in plans}!=ids:
        raise ValueError('Every cutout needs exactly one repair-plan row')
    if data.get('plan_review') not in ('proposed','adjusted','confirmed'):
        raise ValueError('Invalid material plan review state')
    if set(data.get('metrics',{}))!=ids:
        raise ValueError('Missing alpha metrics')
    w,h=data['image']['width'],data['image']['height']
    for row in plans:
        for action in ('complete','svg','clean'):
            if type(row.get(action)) is not bool:
                raise ValueError('Repair choices must be booleans')
        if not isinstance(row.get('note'),str) or len(row['note'])>4000:
            raise ValueError('Invalid repair note')
        if row.get('review') not in ('proposed','adjusted','confirmed'):
            raise ValueError('Invalid repair review state')
        proposal=row.get('suggestion',{})
        if any(type(proposal.get(action)) is not bool for action in ('complete','svg','clean')):
            raise ValueError('Missing AI suggestion flags')
        if proposal.get('priority') not in ('high','medium','low') or not isinstance(proposal.get('reason'),str):
            raise ValueError('Invalid AI suggestion')
        for region in proposal.get('regions',[]):
            if region.get('kind') not in ('complete','svg','clean') or not isinstance(region.get('label'),str):
                raise ValueError('Invalid suggested region')
            points=region.get('points',[])
            if len(points)<3:
                raise ValueError('Suggested region needs at least three points')
            for point in points:
                if (not isinstance(point,list) or len(point)!=2
                    or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in point)
                    or not (0<=point[0]<=w and 0<=point[1]<=h)):
                    raise ValueError('Suggested region exceeds original image')


def confirm_design(data):
    if data.get('demo'):
        raise ValueError('A draft preview cannot approve a production plan')
    for row in data['repair_plan']:
        row['review']='confirmed'
    data['plan_review']='confirmed'


def is_confirmed(data):
    return (not data.get('demo') and data['plan_review']=='confirmed'
            and all(row['review']=='confirmed' for row in data['repair_plan']))
