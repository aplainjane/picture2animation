"""Stage06 authored idle/run clips; preserve the entire approved stage05 rig."""
import base64,copy,hashlib,io,json,math
from PIL import Image
from animation_design import validate as validate_rig,number
from part_design import decode_png

STAGE='06-motion-production'
SCOPE='animation-clips'
IDS=('idle','run','idle_to_run','run_to_idle')

def source_fingerprint(data):
    locked={k:data[k] for k in ('image','nodes','parts','order','face','rig','coordinate_system','upstream','demo')}
    return hashlib.sha256(json.dumps(locked,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf8')).hexdigest()

def neutral(data):return {n['id']:[0.,0.,0.] for n in data['nodes']}
def smooth(t):return t*t*t*(t*(t*6-15)+10)

def foot_contact(part):
    im=Image.open(io.BytesIO(base64.b64decode(part['src'].split(',')[1]))).convert('RGBA')
    a=im.getchannel('A');box=a.point(lambda v:255 if v>100 else 0).getbbox()
    pixels=a.load();ys=range(max(0,box[3]-4),box[3]);xs=[x for y in ys for x in range(im.width) if pixels[x,y]>100]
    return [part['x']+sum(xs)/len(xs),part['y']+box[3]]

def sole_hull(part):
    im=Image.open(io.BytesIO(base64.b64decode(part['src'].split(',')[1]))).convert('RGBA');a=im.getchannel('A');pixels=a.load();pts=[]
    for y in range(im.height):
        row=[x for x in range(im.width) if pixels[x,y]>100]
        if row:pts.extend([(part['x']+row[0],part['y']+y+1),(part['x']+row[-1]+1,part['y']+y+1)])
    points=sorted(set(pts))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    def half(points):
        out=[]
        for p in points:
            while len(out)>=2 and cross(out[-2],out[-1],p)<=0:out.pop()
            out.append(p)
        return out
    return half(points)[:-1]+half(points[::-1])[:-1]

def propose(source):
    from witch_motion import propose_witch
    return propose_witch(source)


def validate(data):
    validate_rig(data)
    prod=data['production'];clips=prod['clips'];ids={n['id'] for n in data['nodes']}
    order=prod.get('layer_order',data['order'])
    if not isinstance(order,list) or len(order)!=len(data['order']) or set(order)!=set(data['order']):
        raise ValueError('Animation layer order must contain every part exactly once')
    overrides=prod.get('material_overrides',{})
    if not isinstance(overrides,dict) or not set(overrides).issubset(set(data['order'])):
        raise ValueError('Unknown material override')
    originals={p['id']:p for p in data['parts']}
    patches=dict(overrides)
    if 'face_underlay' in prod:patches['__face_underlay__']=prod['face_underlay']
    for key,p in patches.items():
        if not isinstance(p,dict) or set(p)!=set(('x','y','w','h','src')) or any(type(p.get(k)) is not int for k in ('x','y','w','h')):
            raise ValueError('Invalid material override')
        if not (0<=p['x']<p['x']+p['w']<=data['image']['width'] and 0<=p['y']<p['y']+p['h']<=data['image']['height']):
            raise ValueError('Material override exceeds source canvas')
        image=decode_png(p['src'])
        if image.size!=(p['w'],p['h']) or not image.getchannel('A').getbbox():raise ValueError('Invalid override PNG')
        if key in ('eye_l','eye_r') and any(p[k]!=originals[key][k] for k in ('x','y','w','h')):
            raise ValueError('Eye edits must retain the six-point texture canvas')
    if not isinstance(clips,list) or len(clips)!=4 or {c['id'] for c in clips}!=set(IDS):raise ValueError('Need idle, run and both transitions')
    for c in clips:
        duration=c['duration']
        if not number(duration,.1,30) or type(c['loop']) is not bool:raise ValueError('Invalid clip timing')
        tracks=c['tracks']
        if len(tracks)!=len(ids) or {t['node_id'] for t in tracks}!=ids:raise ValueError('Every clip needs every confirmed node')
        for t in tracks:
            keys=t['keys']
            if not 2<=len(keys)<=2000 or keys[0][0]!=0 or keys[-1][0]!=duration:raise ValueError('Incomplete keyframe range')
            previous=-1
            for k in keys:
                if len(k)!=4 or not number(k[0],0,duration) or k[0]<=previous or not number(k[1],-150,150) or any(not number(v,-data['image']['height']*.3,data['image']['height']*.3) for v in k[2:]):raise ValueError('Invalid animation keyframe')
                previous=k[0]
            if c['loop'] and any(abs(keys[0][j]-keys[-1][j])>1e-4 for j in (1,2,3)):raise ValueError('Loop endpoints differ')
        if not c['loop'] and (c.get('from_clip') not in ('idle','run') or c.get('to_clip') not in ('idle','run') or not number(c.get('target_phase'),0,30)):raise ValueError('Missing transition definition')
    b=prod['blink']
    if not number(b['period'],1,60) or any(not number(b[k],.01,1) for k in ('close','hold','open')) or not isinstance(b['events'],list):raise ValueError('Invalid blink timing')
    if any(not number(t,0,b['period']-b['close']-b['hold']-b['open']) for t in b['events']):raise ValueError('Blink exceeds period')
    if not number(prod['ground_y'],0,data['image']['height']) or prod.get('review') not in ('proposed','adjusted','confirmed') or prod.get('quality') not in ('pending','accepted','needs_repair') or not isinstance(prod.get('note'),str):raise ValueError('Invalid production review')
    if prod.get('choreography')=='witch-v1':
        effects=prod.get('effects',[])
        if len(effects)!=4 or {e['clip_id'] for e in effects}!=set(IDS):raise ValueError('Missing witch effect tracks')
        for effect in effects:
            clip=next(c for c in clips if c['id']==effect['clip_id']);keys=effect['keys'];previous=-1
            if len(keys)<2 or keys[0][0]!=0 or keys[-1][0]!=clip['duration']:raise ValueError('Incomplete effect range')
            for k in keys:
                if len(k)!=7 or not number(k[0],0,clip['duration']) or k[0]<=previous or any(not number(v,.7,1.3) for v in k[1:3]) or any(not number(v,-250,250) for v in k[3:5]) or not number(k[5],-.5,1.5) or not number(k[6],0,1):raise ValueError('Invalid witch effect key')
                previous=k[0]
            if clip['loop'] and any(abs(keys[0][j]-keys[-1][j])>1e-4 for j in range(1,7)):raise ValueError('Effect loop endpoints differ')
        for key in ('crouch','skid'):
            pose=prod['transition_poses'][key];fx=prod['transition_effects'][key]
            if set(pose)!=ids or any(len(v)!=3 or not number(v[0],-150,150) or any(not number(x,-data['image']['height']*.3,data['image']['height']*.3) for x in v[1:]) for v in pose.values()):raise ValueError('Invalid transition pose')
            if len(fx)!=6 or any(not number(v,-250,250) for v in fx):raise ValueError('Invalid transition effects')

def confirm_design(data):
    validate(data)
    if data.get('demo') or data['production']['quality']=='needs_repair':raise ValueError('Resolve motion issues before confirmation')
    data['production'].update(review='confirmed',quality='accepted')

def is_confirmed(data):return not data.get('demo') and data['production']['review']=='confirmed' and data['production']['quality']=='accepted'
