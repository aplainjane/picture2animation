"""Export current stage snapshots and an offline, read-only review history hub."""
import argparse,hashlib,html,json
from pathlib import Path
from review_checkpoint import read,digest,checkpoint,validate_for_run,atomic_write,now

TITLES={'01-character-structure':'01 · 骨骼与结构','02-part-separation':'02 · 拆图与表情',
        '03-material-completion':'03 · 补全与 SVG 计划','04-material-result':'04 · 补全结果','05-skeleton-animation':'05 · 骨骼与动作检查','06-motion-production':'06 · Idle / Run 动作制作'}
MUTATIONS='#openImage,#import,#savePage,#addMode,#confirm,#delete,#undo,#redo,#confirmStage,#editMask,#forward,#backward,#resetAll,#resetOne,#retry,#historyLink,#eraseTools,#layerTools,#editMaterial,#materialEditor,#pickMode,#pickPair,#editPair,#pairDialog,#bindNode,#boneAmplitude,#period,#rigQuality,#rigNote,#resetEyeGuide,#motionQuality,#motionNote'
FIELDS='#inspector input,#inspector select,#inspector textarea,#label,#color,#quality,#partNote,#note,.choices input,.detail-choices input,select[data-part],#bindNode,#boneAmplitude,#period,#rigQuality,#rigNote,#eyeGuideBand,#motionQuality,#motionNote'


def embed(page,ident,value):
    opening=f'<script id="{ident}" type="application/json">'
    start=page.index(opening)+len(opening);end=page.index('</script>',start)
    return page[:start]+json.dumps(value,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')+page[end:]


def export_stage(project):
    project=Path(project).resolve();root=project.parent;history=root/'history';history.mkdir(exist_ok=True)
    state=read(project/'workflow.json');data=validate_for_run(read(project/'draft.json'),state)
    if digest(data)!=state['design_sha256']:raise ValueError('Draft changed while exporting; retry')
    gate=checkpoint(project);status='已确认' if gate['status']=='confirmed' else '待确认草稿'
    title=TITLES[state['stage']]
    page=Path(state['preview_path']).read_text(encoding='utf-8')
    view_hash=hashlib.sha256(page.encode('utf8')).hexdigest()
    slug=f"{project.stem}-{state['run_id']}-r{state['revision']}-{digest(data)[:10]}-view-{view_hash[:8]}"
    filename=slug+'.html';target=history/filename
    metadata=dict(stage=state['stage'],title=title,status=status,run_id=state['run_id'],revision=state['revision'],
                  design_sha256=digest(data),view_sha256=view_hash,saved_at=now(),file=filename,checkpoint_reason=gate.get('reason',''))
    if not target.exists():
        page=embed(embed(page,'rig-data',data),'checkpoint-config',None)
        banner=f'''<div id="historyBanner"><a href="../review-history.html">← 流程回看</a><b>{html.escape(title)} · {status}</b><span>只读快照 · 修订 {state['revision']} · {state['run_id'][:8]}</span></div>'''
        style='''<style>body{padding-top:46px!important}#historyBanner{position:fixed;top:0;left:0;right:0;z-index:9999;min-height:46px;background:#203f34;color:#fff;display:flex;align-items:center;gap:18px;padding:10px 20px;font:12px "Microsoft YaHei",sans-serif}#historyBanner a{color:#d1f4dd}#historyBanner span{margin-left:auto}#checkpointBar{display:none!important}svg [data-node]{pointer-events:none!important}'''+MUTATIONS+'{display:none!important}</style>'
        # Capture before editor handlers. Read-only inputs remain inspectable,
        # while search, zoom, layer selection and image downloads still work.
        readonly='''<script>(()=>{const fields='''+json.dumps(FIELDS)+''';function lock(){for(const n of document.querySelectorAll(fields))if(!n.disabled)n.disabled=true;}new MutationObserver(lock).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['disabled']});document.addEventListener('keydown',e=>{if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Delete','Backspace'].includes(e.key)||((e.ctrlKey||e.metaKey)&&['z','y'].includes(e.key.toLowerCase()))){if(!e.target.matches('#search')){e.preventDefault();e.stopImmediatePropagation();}}},true);document.addEventListener('input',e=>{if(e.target.matches(fields)){e.preventDefault();e.stopImmediatePropagation();}},true);document.addEventListener('change',e=>{if(e.target.matches(fields)){e.preventDefault();e.stopImmediatePropagation();}},true);document.addEventListener('DOMContentLoaded',lock);})();</script>'''
        page=page.replace('</head>',style+readonly+'</head>',1).replace('<body>','<body>'+banner,1)
        if read(project/'workflow.json')!=state:raise ValueError('Review changed while exporting; retry')
        target.write_text(page,encoding='utf-8');atomic_write(history/(slug+'.json'),metadata)
    build_hub(root)
    return metadata


def build_hub(root):
    history=root/'history';rows=[read(p) for p in history.glob('*.json')]
    rows.sort(key=lambda r:(r['stage'],r['saved_at']),reverse=True)
    grouped={key:[] for key in TITLES}
    for row in rows:grouped[row['stage']].append(row)
    cards=[]
    for stage,items in grouped.items():
        if not items:continue
        latest=items[0]
        links=''.join(f'<li><a href="history/{html.escape(r["file"])}">{html.escape(r["status"])} · 修订 {r["revision"]}</a><small>{html.escape(r["saved_at"][:19].replace("T"," "))} UTC · {r["run_id"][:8]}</small></li>' for r in items)
        cards.append(f'<article><div class="num">{stage[:2]}</div><h2>{html.escape(TITLES[stage][5:])}</h2><p>{html.escape(latest["status"])} · {len(items)} 份保存记录</p><a class="button" href="history/{html.escape(latest["file"])}">查看最新快照 ↗</a><details><summary>所有保存记录</summary><ul>{links}</ul></details></article>')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>角色制作 · 流程回看</title><style>*{box-sizing:border-box}body{font:14px/1.8 "Microsoft YaHei",sans-serif;margin:0;background:#f1f4ef;color:#233f33}main{max-width:1180px;margin:auto;padding:55px 28px}h1{font-size:30px;margin:8px 0}p,small{color:#6b7b6b}a{color:#226b53}header{max-width:800px;margin-bottom:32px}.eyebrow{font-size:11px;letter-spacing:.15em;color:#718273}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}article{background:#fff;border:1px solid #dce4d8;border-radius:12px;padding:24px}.num{font-size:32px;color:#78a88b}h2{font-size:18px}.button{display:inline-block;padding:9px 14px;border-radius:6px;background:#246b54;color:white;text-decoration:none;margin:8px 0 20px}details{font-size:12px}ul{padding-left:18px}li{margin:12px 0}small{display:block;font-size:10px;overflow-wrap:anywhere}footer{margin-top:30px;border-top:1px solid #dce4d8;padding-top:20px;font-size:12px}</style><main><header><div class="eyebrow">CHARACTER LAB / REVIEW HISTORY</div><h1>角色制作 · 流程回看</h1><p>每一步的原图、节点、切片、处理选择和检查状态，保存在对应的独立网页里。点击即可离线查看、放大和切换视图。</p></header><section class="grid">'''+''.join(cards)+'''</section><footer>这些是保存时的只读快照，不会更改检查点。阶段确认后会自动追加快照；中间每次鼠标操作不逐条录像。若要继续编辑，运行本目录的 open-review.ps1，或让 AI 重新打开对应阶段；本地服务端口可能变化。素材与数据请连同整个项目文件夹一起保留。</footer></main></html>'''
    (root/'review-history.html').write_text(page,encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project-root',type=Path,required=True);args=parser.parse_args()
    for project in sorted(args.project_root.resolve().glob('stage*-review.workflow')):export_stage(project)
    print(json.dumps({'history':str((args.project_root/'review-history.html').resolve())},ensure_ascii=False))
