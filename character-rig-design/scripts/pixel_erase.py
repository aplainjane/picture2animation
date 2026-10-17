"""Explicit pixel editing for the stage04 result editor."""
import base64,copy,io,json,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter
from scipy import ndimage as ndi
from part_design import decode_png
from build_part_review import encode


def full(p,w,h):
    out=Image.new('RGBA',(w,h));out.paste(decode_png(p['src']),(p['x'],p['y']));return np.array(out)


def apply_erase(data,part_id,png):
    data=copy.deepcopy(data)
    p=next((p for p in data['parts'] if p['id']==part_id),None)
    if p is None:raise ValueError('Unknown part')
    old=np.array(decode_png(p['src']));candidate=np.array(decode_png(png))
    if candidate.shape!=old.shape:raise ValueError('Eraser cannot change image dimensions')
    if (candidate[:,:,3]>old[:,:,3]).any():raise ValueError('Eraser may only reduce alpha')
    count=int((candidate[:,:,3]<old[:,:,3]).sum())
    if not count:raise ValueError('没有擦到有效像素，无需保存')
    # RGB comes from the server's original pixels. Browser canvas rounding
    # cannot recolor any surviving part of the image.
    old[:,:,3]=candidate[:,:,3];im=Image.fromarray(old);box=im.getchannel('A').getbbox()
    if not box:raise ValueError('不能擦空整个部件；请撤销最后一笔')
    x,y,x1,y1=box;tile=im.crop(box);p.update(x=p['x']+x,y=p['y']+y,w=x1-x,h=y1-y,src=encode(tile),quality='pending',review='adjusted')
    alpha=tile.getchannel('A');binary=alpha.point(lambda v:255 if v else 0)
    edge=np.array(binary.filter(ImageFilter.MaxFilter(3))).astype(int)-np.array(binary.filter(ImageFilter.MinFilter(3))).astype(int)
    outline=Image.new('RGBA',tile.size,'white');outline.putalpha(Image.fromarray(np.clip(edge,0,255).astype('uint8')));p['outline_src']=encode(outline)
    dist=ndi.distance_transform_edt(np.pad(np.array(alpha)>0,1))[1:-1,1:-1];py,px=np.unravel_index(np.argmax(dist),dist.shape);p['label_point']=[int(p['x']+px),int(p['y']+py)]
    row=next(r for r in data['repair_results'] if r['part_id']==part_id)
    w,h=data['image']['width'],data['image']['height'];before=full(row['before'],w,h);after=full(p,w,h)
    added=(after[:,:,3]>0)&~(before[:,:,3]>0);removed=(before[:,:,3]>0)&~(after[:,:,3]>0)
    row.update(added_pixels=int(added.sum()),removed_pixels=int(removed.sum()),changed_pixels=int((np.any(before!=after,axis=2)&((before[:,:,3]>0)|(after[:,:,3]>0))).sum()))
    for label,mask,color in [('added',added,(33,157,132)),('removed',removed,(213,85,102))]:
        overlay=np.zeros((h,w,4),np.uint8);overlay[mask]=(*color,220);row[label+'_src']=encode(Image.fromarray(overlay))
    row['manual_erased_pixels']=row.get('manual_erased_pixels',0)+count
    row['svg_raster_edited']=bool(row.get('svg_source'))
    marker='；设计者网页橡皮擦修订PNG（保留原RGB，仅擦透明度）'
    if marker not in row['method']:row['method']+=marker
    data['face']['review']='adjusted'
    return data


def apply_paint(data,part_id,png,mask_png,paint_mask_png):
    """Full source-coordinate canvas; only touched pixels may change.

    Keep original RGB for alpha-only strokes, including browser round trips.
    A separate paint mask explicitly authorizes RGB changes for brush strokes.
    """
    data=copy.deepcopy(data)
    p=next((p for p in data['parts'] if p['id']==part_id),None)
    if p is None:raise ValueError('Unknown part')
    w,h=data['image']['width'],data['image']['height']
    candidate=np.array(decode_png(png))
    mask=np.array(decode_png(mask_png))
    paint_mask=np.array(decode_png(paint_mask_png))
    if any(a.shape!=(h,w,4) for a in (candidate,mask,paint_mask)):
        raise ValueError('Pixel edit canvases must use original image coordinates')
    touched=mask[:,:,3]>0;colored=paint_mask[:,:,3]>0
    if (colored&~touched).any():raise ValueError('Paint mask exceeds edited area')
    old=full(p,w,h);after=old.copy();after[touched]=candidate[touched]
    if (after[:,:,3][~colored]>old[:,:,3][~colored]).any():
        raise ValueError('Only brush strokes may add opacity')
    after[~colored,:3]=old[~colored,:3]
    changed=np.any(old!=after,axis=2)&((old[:,:,3]>0)|(after[:,:,3]>0))
    if not changed.any():raise ValueError('没有修改有效像素，无需保存')
    image=Image.fromarray(after);box=image.getchannel('A').getbbox()
    if not box:raise ValueError('不能清空整个部件；请撤销最后一笔')
    x,y,x1,y1=box;tile=image.crop(box)
    p.update(x=x,y=y,w=x1-x,h=y1-y,src=encode(tile),quality='pending',review='adjusted')
    alpha=tile.getchannel('A');binary=alpha.point(lambda v:255 if v else 0)
    edge=np.array(binary.filter(ImageFilter.MaxFilter(3))).astype(int)-np.array(binary.filter(ImageFilter.MinFilter(3))).astype(int)
    outline=Image.new('RGBA',tile.size,'white');outline.putalpha(Image.fromarray(np.clip(edge,0,255).astype('uint8')));p['outline_src']=encode(outline)
    dist=ndi.distance_transform_edt(np.pad(np.array(alpha)>0,1))[1:-1,1:-1];py,px=np.unravel_index(np.argmax(dist),dist.shape)
    p['label_point']=[int(x+px),int(y+py)]
    row=next(r for r in data['repair_results'] if r['part_id']==part_id)
    before=full(row['before'],w,h)
    added=(after[:,:,3]>0)&(before[:,:,3]==0);removed=(before[:,:,3]>0)&(after[:,:,3]==0)
    row.update(added_pixels=int(added.sum()),removed_pixels=int(removed.sum()),
               changed_pixels=int((np.any(before!=after,axis=2)&((before[:,:,3]>0)|(after[:,:,3]>0))).sum()),
               manual_painted_pixels=row.get('manual_painted_pixels',0)+int((changed&colored).sum()),
               manual_erased_pixels=row.get('manual_erased_pixels',0)+int((changed&~colored).sum()),
               svg_raster_edited=bool(row.get('svg_source')))
    for label,m,color in [('added',added,(33,157,132)),('removed',removed,(213,85,102))]:
        overlay=np.zeros((h,w,4),np.uint8);overlay[m]=(*color,220);row[label+'_src']=encode(Image.fromarray(overlay))
    marker='；设计者网页画笔／橡皮修订PNG'
    if marker not in row['method']:row['method']+=marker
    data['face']['review']='adjusted'
    return data


def persist_assets(data,project):
    folder=Path(project)/'edited-assets';folder.mkdir(exist_ok=True)
    records={r['part_id']:r for r in data['repair_results']}
    manifest={'coordinate_system':data['coordinate_system'],'order':data['order'],'parts':[],
              'note':'PNG包含网页像素编辑；svg-original为编辑前的SVG参考，不代表PNG当前内容。'}
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in data['parts']:
            r=records[p['id']];filename=p['id']+'.png'
            for label,src in [('after',p['src']),('before',r['before']['src'])]:
                payload=base64.b64decode(src.split(',',1)[1]);z.writestr(label+'/'+filename,payload)
                if label=='after':
                    (folder/'after').mkdir(exist_ok=True);(folder/'after'/filename).write_bytes(payload)
            if r.get('svg_source'):z.writestr(('svg-original' if r.get('svg_raster_edited') else 'svg')+'/'+p['id']+'.svg',r['svg_source'])
            manifest['parts'].append({**{k:v for k,v in p.items() if k not in ('src','outline_src')},
                'file':'after/'+filename,'manual_erased_pixels':r.get('manual_erased_pixels',0),
                'manual_painted_pixels':r.get('manual_painted_pixels',0),'svg_raster_edited':r.get('svg_raster_edited',False)})
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    payload=buffer.getvalue();(folder/'repaired-materials.zip').write_bytes(payload)
    (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    data['bundle']='data:application/zip;base64,'+base64.b64encode(payload).decode('ascii')
