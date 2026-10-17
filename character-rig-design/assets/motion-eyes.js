/* Preserve stage05 six-point masks and dedicated closed-eye attachments. */
window.createMotionEyes=async function(data,images){
const eyeRigs=new Map(),closedImages=new Map();
function makeCanvas(w,h){const c=document.createElement('canvas');c.width=w;c.height=h;return c;}
function smooth(v){v=Math.max(0,Math.min(1,v));return v*v*(3-2*v);}
function validGuide(g,p){const q=g.points;if(!Array.isArray(q)||q.length!==6||q.some(pt=>pt.length!==2||pt.some(v=>!Number.isFinite(v))||pt[0]<0||pt[0]>p.w||pt[1]<0||pt[1]>p.h))return false;const[a,b,c,d,e,f]=q;return a[0]<b[0]&&b[0]<c[0]&&c[0]<d[0]&&a[0]<f[0]&&f[0]<e[0]&&e[0]<d[0]&&b[1]<f[1]&&c[1]<e[1];}
function curveY(points,x){let i=0;while(i<points.length-2&&x>points[i+1][0])i++;const a=points[i],b=points[i+1],span=b[0]-a[0],t=Math.max(0,Math.min(1,(x-a[0])/span)),before=points[Math.max(0,i-1)],after=points[Math.min(points.length-1,i+2)],m0=(b[1]-before[1])/(b[0]-before[0]),m1=(after[1]-a[1])/(after[0]-a[0]);return(2*t**3-3*t*t+1)*a[1]+(t**3-2*t*t+t)*span*m0+(-2*t**3+3*t*t)*b[1]+(t**3-t*t)*span*m1;}
function guideRows(g,p){const[a,b,c,d,e,f]=g.points,left=Math.ceil(a[0]),right=Math.min(p.w-1,Math.floor(d[0])),outer=new Array(p.w).fill(null),inner=[...outer],lower=[...outer],closed=[...outer],lowerOuter=[...outer];for(let x=left;x<=right;x++){const u=(x-a[0])/(d[0]-a[0]),taper=Math.sin(Math.PI*u)**.5;outer[x]=Math.max(0,Math.min(p.h,curveY([a,b,c,d],x)));lowerOuter[x]=Math.max(outer[x],Math.min(p.h,curveY([a,f,e,d],x)));inner[x]=Math.min(lowerOuter[x],outer[x]+g.lash_band_px*taper);lower[x]=Math.max(inner[x],lowerOuter[x]-1.5*taper);closed[x]=a[1]*(1-u)+d[1]*u+p.h*.035*Math.sin(Math.PI*u);}return{left,right,top:outer,inner,lower,closed,lowerOuter};}
function pathBetween(r,top,bottom){const path=new Path2D();path.moveTo(r.left,top[r.left]);for(let x=r.left;x<=r.right;x++)path.lineTo(x,top[x]);for(let x=r.right;x>=r.left;x--)path.lineTo(x,bottom[x]);path.closePath();return path;}
function buildEyeRig(p){const guide=data.rig.eye_guides.find(g=>g.part_id===p.id);if(!guide||!validGuide(guide,p))return null;const rows=guideRows(guide,p),skin=makeCanvas(p.w,p.h),ctx=skin.getContext('2d');ctx.drawImage(images[p.id],0,0);ctx.globalCompositeOperation='destination-out';ctx.fill(pathBetween(rows,rows.top,rows.lowerOuter));return{w:p.w,h:p.h,...rows,skin,guide,closedImage:closedImages.get(p.id),layer:makeCanvas(p.w,p.h),lastOpen:null};}
function eyePath(r,open){const top=r.inner.map((v,x)=>v===null?null:r.closed[x]+(v-r.closed[x])*open),bottom=r.lower.map((v,x)=>v===null?null:r.closed[x]+(v-r.closed[x])*open);return pathBetween(r,top,bottom);}
function drawEye(ctx,p,open){const r=eyeRigs.get(p.id);if(!r||open>=1){ctx.drawImage(images[p.id],p.x,p.y,p.w,p.h);return;}open=Math.max(0,open);if(r.lastOpen!==open){const target=r.layer.getContext('2d');target.clearRect(0,0,r.w,r.h);target.drawImage(r.skin,0,0);target.save();target.clip(pathBetween(r,r.top,r.lowerOuter));if(open>0){target.save();target.clip(eyePath(r,open));target.drawImage(images[p.id],0,0);target.restore();}
 for(let x=r.left;x<=r.right;x++){const u=(x-r.left)/Math.max(1,r.right-r.left),taper=Math.sin(Math.PI*u)**.5,sy=Math.max(0,r.top[x]),sh=Math.max(.01,r.inner[x]-sy),bottom=r.closed[x]+(r.inner[x]-r.closed[x])*open,th=sh*(.8+.2*open);target.drawImage(images[p.id],x,sy,1,Math.min(sh,p.h-sy),x,bottom-th,1,th);const ly=r.lower[x],lh=Math.min(Math.max(.01,r.lowerOuter[x]-ly),p.h-ly);if(lh>0)target.drawImage(images[p.id],x,ly,1,lh,x,r.closed[x]+(ly-r.closed[x])*open,1,lh);}
 target.restore();
 // Blend to the dedicated closed-eye attachment over the last 12% of closing.
 // At zero, only that attachment is drawn inside the cage; exterior pixels
 // remain the original source. Premultiplied mixing avoids transparent halos.
 if(r.closedImage&&open<.12){const mix=smooth(1-open/.12),closedLayer=makeCanvas(r.w,r.h),cc=closedLayer.getContext('2d');cc.drawImage(r.skin,0,0);cc.save();cc.clip(pathBetween(r,r.top,r.lowerOuter));cc.drawImage(r.closedImage,0,0);cc.restore();target.save();target.globalCompositeOperation='destination-in';target.globalAlpha=1-mix;target.fillStyle='#000';target.fillRect(0,0,r.w,r.h);target.globalCompositeOperation='lighter';target.globalAlpha=mix;target.drawImage(closedLayer,0,0);target.restore();}
 if(open>.92){const mix=smooth((open-.92)/.08);target.save();target.globalCompositeOperation='destination-in';target.globalAlpha=1-mix;target.fillStyle='#000';target.fillRect(0,0,r.w,r.h);target.globalCompositeOperation='lighter';target.globalAlpha=mix;target.drawImage(images[p.id],0,0);target.restore();}r.lastOpen=open;}
 ctx.drawImage(r.layer,p.x,p.y);}

for(const g of data.rig.eye_guides||[]){if(g.closed_texture){const im=new Image();im.src=g.closed_texture.src;await im.decode();closedImages.set(g.part_id,im);}}
for(const p of data.parts)if(['eye_l','eye_r'].includes(p.id)){const r=buildEyeRig(p);if(r)eyeRigs.set(p.id,r);}
return {draw:drawEye};
};
