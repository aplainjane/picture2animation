/* Native cutout animation format: seconds, degrees, original-image pixels. */
window.CharacterMotion=(()=>{
const smooth=x=>{x=Math.max(0,Math.min(1,x));return x*x*x*(x*(x*6-15)+10);};
const copy=p=>Object.fromEntries(Object.entries(p).map(([id,v])=>[id,[...v]]));
const easeIO=t=>t<.5?4*t*t*t:1-(-2*t+2)**3/2,easeOut=t=>1-(1-t)**3,back=t=>1+2.70158*(t-1)**3+1.70158*(t-1)**2;
function sample(clip,time){
 const t=clip.loop?((time%clip.duration)+clip.duration)%clip.duration:Math.max(0,Math.min(clip.duration,time)),pose={};
 for(const track of clip.tracks){const keys=track.keys;let i=0;while(i<keys.length-2&&keys[i+1][0]<t)i++;const a=keys[i],b=keys[i+1],dt=b[0]-a[0],u=(t-a[0])/dt;
  // Cubic interpolation uses neighboring keys; repeated loop endpoints share
  // the same tangent so playback is continuous at the wrap.
  let prev=i?keys[i-1]:clip.loop?[keys[keys.length-2][0]-clip.duration,...keys[keys.length-2].slice(1)]:a;
  let next=i+2<keys.length?keys[i+2]:clip.loop?[keys[1][0]+clip.duration,...keys[1].slice(1)]:b;
  pose[track.node_id]=Array.from({length:a.length-1},(_,index)=>{const j=index+1,m0=(b[j]-prev[j])/(b[0]-prev[0]),m1=(next[j]-a[j])/(next[0]-a[0]);return(2*u**3-3*u*u+1)*a[j]+(u**3-2*u*u+u)*dt*m0+(-2*u**3+3*u*u)*b[j]+(u**3-u*u)*dt*m1;});
 }return pose;
}
function blend(a,b,w){return Object.fromEntries(Object.keys(a).map(id=>[id,a[id].map((v,j)=>v*(1-w)+b[id][j]*w)]));}
function effects(data,id,time){const clip=data.production.clips.find(c=>c.id===id),fx=data.production.effects?.find(e=>e.clip_id===id);return fx?sample({duration:clip.duration,loop:clip.loop,tracks:[{node_id:'fx',keys:fx.keys}]},time).fx:[1,1,0,0,0,0];}
function blink(settings,time){const t=((time%settings.period)+settings.period)%settings.period;for(const at of settings.events){const dt=t-at;if(dt<0)continue;if(dt<settings.close)return 1-smooth(dt/settings.close);if(dt<settings.close+settings.hold)return 0;if(dt<settings.close+settings.hold+settings.open)return smooth((dt-settings.close-settings.hold)/settings.open);}return 1;}
class Player{
 constructor(data){this.data=data;this.clips=new Map(data.production.clips.map(c=>[c.id,c]));this.clock=0;this.state='idle';this.phase=0;this.transition=null;this.rest=false;}
 pose(){if(this.rest)return Object.fromEntries(this.data.nodes.map(n=>[n.id,[0,0,0]]));if(!this.transition)return sample(this.clips.get(this.state),this.phase);
  if(this.data.production.choreography==='witch-v1')return this.witchBlend(false);
  const tr=this.transition,u=Math.min(1,tr.elapsed/tr.duration),target=sample(this.clips.get(tr.to),tr.elapsed),p=blend(tr.source,target,smooth(u)),accent=Math.sin(Math.PI*u)**2;
  p.spine[0]+=(tr.to==='run'?-1.4:1.8)*accent;p.pelvis[2]+=4*(this.data.image.height/1448)*accent;return p;
 }
 fx(){return this.transition&&this.data.production.choreography==='witch-v1'?this.witchBlend(true):effects(this.data,this.state,this.phase);}
 witchBlend(isFx){const tr=this.transition,u=Math.min(1,tr.elapsed/tr.duration),data=this.data.production,mix=isFx?(a,b,w)=>a.map((v,j)=>v+(b[j]-v)*w):blend,source=isFx?tr.sourceFx:tr.source;
  if(tr.to==='run'){const crouch=isFx?data.transition_effects.crouch:data.transition_poses.crouch;if(u<.35)return mix(source,crouch,easeIO(u/.35));const phase=-this.clips.get('run').duration/4+tr.elapsed-tr.duration*.35,target=isFx?effects(this.data,'run',phase):sample(this.clips.get('run'),phase);return mix(crouch,target,back((u-.35)/.65));}
  const skid=isFx?data.transition_effects.skid:data.transition_poses.skid;if(u<.14)return mix(source,skid,easeOut(u/.14));if(u<.55)return isFx?[...skid]:copy(skid);const target=isFx?effects(this.data,'idle',tr.elapsed):sample(this.clips.get('idle'),tr.elapsed);return mix(skid,target,back((u-.55)/.45));
 }
 request(to,override,overrideFx){if(!['idle','run'].includes(to))return;if(!override&&!this.transition&&this.state===to&&!this.rest)return;if(!override&&this.transition?.to===to)return;const source=copy(override||this.pose()),sourceFx=[...(overrideFx||this.fx())];this.rest=false;const key=to==='run'?'idle_to_run':'run_to_idle';this.transition={from:this.state,to,source,sourceFx,elapsed:0,duration:this.clips.get(key).duration};this.state=key;}
 update(dt){this.clock+=dt;if(this.transition){this.transition.elapsed+=dt;if(this.transition.elapsed>=this.transition.duration){const tr=this.transition;this.state=tr.to;this.phase=this.data.production.choreography==='witch-v1'&&tr.to==='run'?-this.clips.get('run').duration/4+tr.elapsed-tr.duration*.35:tr.elapsed;this.transition=null;}}else this.phase+=dt;}
 reset(){this.state='idle';this.phase=0;this.clock=0;this.transition=null;this.rest=false;}
}
return{sample,blend,blink,smooth,effects,Player};
})();
