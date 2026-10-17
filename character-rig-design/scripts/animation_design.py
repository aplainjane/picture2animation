"""Stage05 rigid cutout binding and conservative motion-preview schema."""
import base64,copy,hashlib,json,math,struct
from part_design import validate as validate_parts,decode_png

STAGE='05-skeleton-animation'
SCOPE='skeleton-animation-rig'


def propose(source):
    data={k:copy.deepcopy(source[k]) for k in ('schema_version','coordinate_system','image','nodes','parts','order','face')}
    nodes={n['id']:n for n in data['nodes']}
    bindings=[]
    for p in data['parts']:
        ids=p.get('node_ids',[])
        if not ids:raise ValueError('Assign an explicit node to '+p['id']+' before binding')
        # In a two-joint segment, the proximal (parent-side) joint drives the
        # rigid image; the distal joint is its endpoint, not a second weight.
        candidates=[key for key in ids if nodes[key].get('parent') not in ids]
        bindings.append(dict(part_id=p['id'],node_id=(candidates or ids)[0],note=''))
    motion=[]
    for i,n in enumerate(data['nodes']):
        key=n['id'];amp=0
        if key=='chest':amp=.22
        elif key=='head':amp=.4
        elif key.startswith('hair_') and key!='hair_fringe':amp=.65
        elif n['type']=='anchor' and 'dangle' in key:amp=.8
        # Legs remain fixed in the initial idle so there is no foot sliding.
        motion.append(dict(node_id=key,amplitude_deg=amp,phase=(i%5)*.32,note=''))
    data['rig']=dict(bindings=bindings,motion=motion,period_seconds=4.0,review='proposed',quality='pending',note='')
    data['title']='骨骼绑定与轻量待机 · 动作检查'
    data['limitation']='单骨刚性切片预览；尚未配置网格蒙皮、IK或Spine导出。大角度试动只用于找露缝，不能当作已完成的成品动作。'
    return data


def number(value,low,high):
    return type(value) in (int,float) and math.isfinite(value) and low<=value<=high


def validate(data):
    validate_parts(data)
    rig=data['rig'];parts={p['id'] for p in data['parts']};nodes={n['id'] for n in data['nodes']}
    bindings=rig['bindings'];motion=rig['motion']
    if len(bindings)!=len(parts) or {b['part_id'] for b in bindings}!=parts:raise ValueError('Every part needs exactly one binding')
    if any(b['node_id'] not in nodes or not isinstance(b.get('note'),str) for b in bindings):raise ValueError('Invalid binding node or note')
    if len(motion)!=len(nodes) or {m['node_id'] for m in motion}!=nodes:raise ValueError('Every node needs one motion setting')
    for m in motion:
        if not number(m['amplitude_deg'],0,15) or not number(m['phase'],-math.tau,math.tau) or not isinstance(m.get('note'),str):raise ValueError('Invalid motion range')
    if not number(rig['period_seconds'],1,20) or rig['review'] not in ('proposed','adjusted','confirmed') or not isinstance(rig['note'],str):raise ValueError('Invalid rig review')
    if rig.get('quality') not in ('pending','accepted','needs_repair'):raise ValueError('Invalid rig quality')
    validate_eye_guides(data,rig.get('eye_guides',[]))


def validate_eye_guides(data,guides):
    if not isinstance(guides,list):raise ValueError('Eye guides must be a list')
    parts={p['id']:p for p in data['parts']};seen=set()
    for guide in guides:
        if not isinstance(guide,dict):raise ValueError('Invalid eye guide')
        key=guide.get('part_id');points=guide.get('points')
        if key in seen or key not in data['face']['feature_ids']:raise ValueError('Invalid eye-guide part')
        seen.add(key);p=parts[key]
        if not isinstance(points,list) or len(points)!=6:raise ValueError('An eye guide needs six points')
        if any(not isinstance(pt,list) or len(pt)!=2 or not number(pt[0],0,p['w']) or not number(pt[1],0,p['h']) for pt in points):raise ValueError('Eye guide exceeds source bounds')
        a,b,c,d,e,f=points
        if not (a[0]<b[0]<c[0]<d[0] and a[0]<f[0]<e[0]<d[0] and b[1]<f[1] and c[1]<e[1]):raise ValueError('Eye points must follow left, upper-left, upper-right, right, lower-right, lower-left')
        if not number(guide.get('lash_band_px'),1,p['h']*.3):raise ValueError('Invalid lash band width')
        if 'closed_texture' in guide:
            texture=guide['closed_texture']
            if not isinstance(texture,dict) or texture.get('w')!=p['w'] or texture.get('h')!=p['h']:
                raise ValueError('Closed-eye texture must match the source eye canvas')
            src=texture.get('src','');prefix='data:image/png;base64,'
            if not isinstance(src,str) or not src.startswith(prefix) or len(src)>16*1024*1024:
                raise ValueError('Closed-eye texture must be an embedded PNG')
            try:raw=base64.b64decode(src[len(prefix):],validate=True)
            except ValueError:raise ValueError('Invalid closed-eye PNG encoding')
            if len(raw)<33 or raw[:8]!=b'\x89PNG\r\n\x1a\n' or raw[12:16]!=b'IHDR' or struct.unpack('>II',raw[16:24])!=(p['w'],p['h']):
                raise ValueError('Invalid closed-eye PNG dimensions')
            image=decode_png(src)
            if not image.getchannel('A').getbbox():raise ValueError('Closed-eye texture is empty')


def source_fingerprint(data):
    # Only rig bindings, motion settings and review note may change here.
    locked={k:data[k] for k in ('image','nodes','parts','order','face','coordinate_system','upstream','demo')}
    return hashlib.sha256(json.dumps(locked,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf8')).hexdigest()


def confirm_design(data):
    if data.get('demo'):raise ValueError('Draft preview cannot approve an animation rig')
    validate(data)
    if data['rig']['quality']=='needs_repair':raise ValueError('Resolve rig issues before confirming')
    data['rig'].update(review='confirmed',quality='accepted')


def is_confirmed(data):
    return not data.get('demo') and data['rig']['review']=='confirmed' and data['rig']['quality']=='accepted'
