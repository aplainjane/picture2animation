"""Map the original witch run/start/stop choreography onto an approved rig.

Pose formulas and timings follow the workspace's original index.html. Original
art coordinates and procedural replacement arms are deliberately not copied.
"""
import copy,math
from motion_design import neutral,foot_contact,sole_hull

def ease_io(t):return 4*t*t*t if t<.5 else 1-(-2*t+2)**3/2
def ease_out(t):return 1-(1-t)**3
def back(t):return 1+2.70158*(t-1)**3+1.70158*(t-1)**2

def propose_witch(source):
    data={k:copy.deepcopy(source[k]) for k in ('schema_version','coordinate_system','image','nodes','parts','order','face','rig')}
    nodes={n['id']:n for n in data['nodes']};parts={p['id']:p for p in data['parts']}
    required=('root','pelvis','spine','chest','head','hip_l','knee_l','ankle_l','hip_r','knee_r','ankle_r','shoulder_l','elbow_l','wrist_l','shoulder_r','elbow_r','wrist_r')
    if any(k not in nodes for k in required):raise ValueError('Map confirmed humanoid IDs before using witch choreography')
    unit=data['image']['height']/1090;idle_duration=4.;run_duration=.5
    legs=[]
    for s in ('l','r'):
        h=nodes['hip_'+s];k=nodes['knee_'+s];a=nodes['ankle_'+s];legs.append(math.hypot(k['x']-h['x'],k['y']-h['y'])+math.hypot(a['x']-k['x'],a['y']-k['y']))
    leg=sum(legs)/2
    def plant(d):return math.degrees(math.acos(max(-1,min(1,(leg-d)/leg))))
    # The old runtime draws bent procedural arms. Here retain the confirmed
    # original arm/hand art and convert its segment directions to that pose.
    source_arm={}
    for s in ('l','r'):
        sh=nodes['shoulder_'+s];el=nodes['elbow_'+s];wr=nodes['wrist_'+s]
        up=math.degrees(math.atan2(el['y']-sh['y'],el['x']-sh['x']));lo=math.degrees(math.atan2(wr['y']-el['y'],wr['x']-el['x']))
        source_arm[s]=(up,lo-up)
    def base(**kw):
        p=dict(bob=0,lean=0,thighL=0,kneeL=0,thighR=0,kneeR=0,armL=0,armR=0,upL=52,upR=-43,elL=0,elR=0,swap=0,head=0,hat=0,hatTip=0,pend=0,potions=0,hair=0,skirt=0,sx=1,sy=1,squint=0,speed=0)
        p.update(kw);return p
    def mix(a,b,w):return {k:a[k]+(b[k]-a[k])*w for k in a}
    def idle(t):
        a=math.tau*t/idle_duration;br=(math.sin(2*a)+1)/2;d=br*4*unit;angle=plant(d)
        return base(bob=d,lean=math.sin(a)*1.2,thighL=angle,kneeL=-2*angle,thighR=angle,kneeR=-2*angle,armL=math.sin(2*a+.5)*2.5,armR=-math.sin(2*a+.8)*2.5,head=math.sin(a+.6)*2,hat=math.sin(a+.3)*1.2,pend=math.sin(a*2-.3)*5,hair=math.sin(a+1)*5,skirt=math.sin(a*2)*2,sx=1+br*.006,sy=1-br*.01)
    def run(t):
        p=math.tau*t/run_duration;s=math.sin(p);c=math.cos(p);s2=math.sin(2*p)
        return base(bob=(-8+38*s*s)*unit,lean=-9+1.5*math.cos(2*p),thighL=30*s,kneeL=-(8+58*max(0,c)),thighR=-30*s,kneeR=-(8+58*max(0,-c)),armL=-4-8*s,armR=4+8*s,upL=30-38*s,elL=70-20*s,upR=-20+38*s,elR=70+20*s,swap=1,head=4+1.5*s2,hat=1.5,hatTip=-14+5*math.sin(2*p+.5),pend=-28+8*math.sin(2*p+.3),potions=-22+8*s2,hair=38+8*math.sin(2*p+.6),skirt=12+6*s2,sx=1-.02*s*s,sy=1.02-.035*s*s,speed=1)
    crouch_angle=plant(24*unit)
    crouch=base(bob=24*unit,lean=4,thighL=crouch_angle,kneeL=-2*crouch_angle,thighR=crouch_angle,kneeR=-2*crouch_angle,armL=-6,armR=-6,upL=0,elL=45,upR=-50,elR=40,swap=1,head=3,hat=2,pend=10,hair=-4,skirt=-3,sx=1.03,sy=.95,squint=1)
    # Reference arms L/R mean screen left/right; this rig uses character sides.
    # Map the skid arms explicitly so both hands lift outward. Run has its own
    # contralateral gait mapping and must not be globally swapped with this pose.
    def skid(t):
        p=base(bob=(32+math.sin(t*70)*2)*unit,lean=12,thighL=28,kneeL=-2,thighR=-22,kneeR=-40,armL=-8,armR=8,upL=-105,elL=-15,upR=110,elR=20,swap=1,head=-4,hat=-1.5,pend=38,hair=-24,skirt=-16,sx=1.03,sy=.96,squint=1,speed=.35)
        # Keep only one third of the original outward gesture, measured from
        # each confirmed arm's rest direction rather than from absolute angles.
        for s,cap in [('l','L'),('r','R')]:
            rest_up,rest_bend=source_arm[s]
            p['arm'+cap]/=3
            p['up'+cap]=(rest_up-90)+(p['up'+cap]-(rest_up-90))/3
            p['el'+cap]=rest_bend+(p['el'+cap]-rest_bend)/3
        return p
    def mapped(p):
        pose=neutral(data);pose['pelvis'][2]=p['bob'];pose['spine'][0]=p['lean'];pose['head'][0]=p['head']
        for s,cap in [('l','L'),('r','R')]:
            pose['hip_'+s][0]=p['thigh'+cap];pose['knee_'+s][0]=p['knee'+cap]
            rest_up,rest_bend=source_arm[s];swap=max(0,min(1,p['swap']))
            desired_up=90+p['up'+cap]-rest_up+p['arm'+cap]
            desired_elbow=p['el'+cap]-rest_bend
            pose['shoulder_'+s][0]=p['arm'+cap]*(1-swap)+desired_up*swap
            pose['elbow_'+s][0]=desired_elbow*swap
            pose['wrist_'+s][0]=-3*math.sin(math.radians(p['up'+cap]))*swap
        for key,value in [('headpiece',p['hat']),('headpiece_dangle',p['pend']*.55),('rear_ornament',p['skirt']*.35),('hair_ahoge',p['hatTip']*.22)]:
            if key in pose:pose[key][0]=value
        return pose,[p['sx'],p['sy'],p['hair']*unit,p['skirt']*unit,p['speed'],max(0,min(1,p['squint']))]
    def clip(key,label,duration,loop,fn,count):
        samples=[(round(duration*i/count,7),mapped(fn(duration*i/count))) for i in range(count+1)]
        c=dict(id=key,label=label,duration=duration,loop=loop,tracks=[dict(node_id=n['id'],keys=[[t,*[round(v,6) for v in sample[0][n['id']]]] for t,sample in samples]) for n in data['nodes']])
        fx=dict(clip_id=key,keys=[[t,*[round(v,6) for v in sample[1]]] for t,sample in samples]);return c,fx
    clips=[];effects=[]
    for args in [('idle','待机 / idle',idle_duration,True,idle,96),('run','跑步 / run',run_duration,True,run,96)]:
        c,e=clip(*args);clips.append(c);effects.append(e)
    start_duration=.55;stop_duration=.85
    def start(t):
        u=t/start_duration
        if u<.35:return mix(idle(0),crouch,ease_io(u/.35))
        return mix(crouch,run(-run_duration/4+t-.35*start_duration),back((u-.35)/.65))
    def stop(t):
        u=t/stop_duration;sk=skid(t)
        if u<.14:return mix(run(0),sk,ease_out(u/.14))
        if u<.55:return sk
        return mix(sk,idle(t),back((u-.55)/.45))
    for key,label,dur,fn,fr,to,target in [('idle_to_run','蓄力 → 蹬地 → 跑步',start_duration,start,'idle','run',-run_duration/4+start_duration*.65),('run_to_idle','急刹 → 滑步 → 回弹',stop_duration,stop,'run','idle',stop_duration)]:
        c,e=clip(key,label,dur,False,fn,128);c.update(from_clip=fr,to_clip=to,target_phase=target);clips.append(c);effects.append(e)
    crouch_pose,crouch_fx=mapped(crouch);skid_pose,skid_fx=mapped(skid(0))
    feet={s:foot_contact(parts['boot_'+s]) for s in ('l','r')};soles={s:sole_hull(parts['boot_'+s]) for s in ('l','r')}
    data.update(title='角色动作 · Witch 跑步与起停衔接',limitation='采用原 Witch 的蓄力、蹬地、摆臂、急刹和回弹节奏；保留当前立绘视角、确认素材与绑定。')
    data['production']=dict(clips=clips,effects=effects,choreography='witch-v1',transition_poses=dict(crouch=crouch_pose,skid=skid_pose),transition_effects=dict(crouch=crouch_fx,skid=skid_fx),ground_y=max(v[1] for v in feet.values()),feet=feet,sole_points=soles,blink=dict(period=7,events=[2.1,5.4],close=.09,hold=.045,open=.16),review='proposed',quality='pending',note='',default_clip='idle',rendering='rigid-cutout-with-strip-warp',version=2)
    return data
