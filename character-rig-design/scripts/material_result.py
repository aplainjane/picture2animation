"""Result-review validation, isolated from approval of the repair plan."""
import hashlib,json
from part_design import validate as validate_parts,confirm_design,is_confirmed

STAGE='04-material-result'
SCOPE='material-repair-result'


def validate(data):
    validate_parts(data)
    rows=data.get('repair_results',[])
    ids={p['id'] for p in data['parts']}
    if len(rows)!=len(ids) or {r.get('part_id') for r in rows}!=ids:
        raise ValueError('Result review needs one before/after record for every part')
    for row in rows:
        if row.get('before',{}).get('id')!=row['part_id']:
            raise ValueError('Before cutout must retain the same part ID')
        for flag in ('complete','svg','clean'):
            if type(row.get('actions',{}).get(flag)) is not bool:
                raise ValueError('Missing approved repair action')


def source_fingerprint(data):
    locked={k:data[k] for k in ('image','nodes','order','coordinate_system','upstream','repair_results','bundle','limitation')}
    locked['parts']=[{k:v for k,v in p.items() if k not in ('quality','review','note')} for p in data['parts']]
    locked['face']={k:v for k,v in data['face'].items() if k!='review'}
    return hashlib.sha256(json.dumps(locked,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
