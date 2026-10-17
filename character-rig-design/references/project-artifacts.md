# 项目产物、网页调用与交接

首次为角色建立项目或交付任何阶段时读取。每阶段具体操作见其开头的“网页使用与交接卡”；本文件统一约定路径、权威数据与调用方式。

## 目录与命名

`S` 表示本skill的绝对路径，`P` 表示本次角色项目的绝对路径。下列路径是建议布局；已有项目沿用实际名称，不为了统一名字重建任务。命令中的 `S`、`P` 必须替换为实际绝对路径，包含空格时保留引号。原图扩展名按实际文件调整。

```text
P/
  input/
    character.png              用户原图，保留原件
    structure.json             AI提出的结构与节点，01生成输入
    split.json                 AI/设计者提供的拆分配置，02生成输入
    masks/                     split引用的前景、部件和五官蒙版
    repair-plan.json           AI逐部件处理建议，03生成输入
    eye-guides.json            可选：六点及闭眼贴图建议，05生成输入
  repair.assets/               AI按03确认实际制作的04修复源文件
    repair-manifest.json
    added/                     原图尺寸的新增像素标记
    removed/                   原图尺寸的移除像素标记
    repaired-materials.zip
    ...                        manifest引用的SVG及其他制作素材
  stage01-review.html          01生成网页
  stage01-review.workflow/     01的独立检查点目录
  stage02-review.html          02生成网页
  stage02-review.assets/       02最初生成的PNG、JSON和归属图
  stage02-review.workflow/
  stage03-review.html
  stage03-review.workflow/
  stage04-review.html
  stage04-review.workflow/
    edited-assets/             04网页实际保存像素编辑后生成
  stage05-review.html
  stage05-review.workflow/
  stage06-review.html
  stage06-review.workflow/
  history/                    各阶段只读版本快照
  review-history.html         历史导航页
  delivery/                   显式导出的动画交付版本
```

这是文件去向说明，不要求提前创建还没有用到的文件或空目录。生成器创建的workflow以 `--out` 文件名去掉扩展名后加 `.workflow` 命名，例如 `custom.html` 对应 `custom.workflow/`；01也支持显式 `--project`。实际路径以生成器返回和workflow记录为准。

## 每个workflow保存什么

| 文件／目录 | 用途 | 如何使用 |
| --- | --- | --- |
| `workflow.json` | 阶段、run_id、revision、状态、设计摘要、预览文件路径、上游依赖 | 恢复和版本校验入口；不能只看其中status就跳过check |
| `draft.json` | 用户最新已保存的设计及内嵌素材 | 继续编辑或AI返修的起点；未保存到服务的浏览器笔迹不在其中 |
| `confirmed.json` | 用户整阶段确认时的快照和确认范围；设计在 `design` 字段中 | 仅在check通过后作为下游输入；文件存在不等于当前仍有效 |
| `server.json` | 当前服务记录的URL、PID、run_id | 先核实服务仍可用，再复用或重新启动；端口不是永久地址 |
| `edited-assets/` | 04像素编辑后更新的PNG、坐标manifest和ZIP | 条件生成的便利导出；跨阶段仍读取有效确认快照 |

阶段06的最终手修放在 `draft.json → production.material_overrides`，层序放在 `production.layer_order`，面部转移底片放在 `production.face_underlay`；这些值不会自动回写04或05文件。本阶段导出的动画HTML／JSON使用这些覆盖。

## 新阶段如何直接调用

准备好对应输入并检查上游后，运行当前需要的一条生成命令，随后启动它的服务。下面是六条独立示例，不能一次运行完毕绕过中间的人工确认：

```text
python "S/scripts/build_rig_editor.py" --image "P/input/character.png" --config "P/input/structure.json" --out "P/stage01-review.html"
python "S/scripts/build_part_review.py" --upstream "P/stage01-review.workflow" --config "P/input/split.json" --out "P/stage02-review.html"
python "S/scripts/build_material_review.py" --upstream "P/stage02-review.workflow" --config "P/input/repair-plan.json" --out "P/stage03-review.html"
python "S/scripts/build_material_result.py" --upstream "P/stage03-review.workflow" --manifest "P/repair.assets/repair-manifest.json" --out "P/stage04-review.html"
python "S/scripts/build_animation_review.py" --upstream "P/stage04-review.workflow" --out "P/stage05-review.html"
python "S/scripts/build_motion_review.py" --upstream "P/stage05-review.workflow" --out "P/stage06-review.html"
```

05已有六点和闭眼资产建议时可附加 `--eye-guides "P/input/eye-guides.json"`。06的默认动作预设需先核对目标角色的节点语义和部件ID；具体适配遵循06说明。缺少当前角色的配置、边界或实际补全素材时先制作这些输入，模板不会代替分析和美术制作。

将下面的 `NN` 换成当前阶段号：

```text
python "S/scripts/review_checkpoint.py" serve --project "P/stageNN-review.workflow"
python "S/scripts/review_checkpoint.py" check --project "P/stageNN-review.workflow"
```

`serve` 是需保持运行的本地服务。打开它返回的 `/index.html` URL；网页调整、保存和确认连接该workflow。已有阶段只需恢复服务，不能用生成命令覆盖最新草稿。已连接服务时，服务器会在打开页面时注入最新draft和连接配置；磁盘上的初始HTML不保证包含之后的人工编辑。

## 保存、提交与下一步

1. **自动保存**：01节点与结构、02轮廓／层序、03勾选与备注、04检查状态、05绑定与六点、06层序与反馈等，按各页面实现写入draft。等待页面保存完成；有保存失败先处理，不把未落盘结果用于后续。
2. **显式保存像素**：04画笔／橡皮先点“保存像素修改”；06画笔／橡皮／双层像素转移先点“保存素材”。其他预览操作、缩放、播放和试动不会自动提交这些笔迹。
3. **整阶段提交**：用户点击当前阶段确认按钮，服务生成confirmed快照。AI执行check，退出码0且确认范围匹配才读取返回的 `confirmed_file`；从该文件的 `design` 提取输入。新修改会让原确认失效，重新交接前要再检查。
4. **生成下一步**：把当前workflow目录传给下一生成器的 `--upstream`；生成器读取并校验确认。02→03交付实际切片，03→04交付处理选择，04→05交付最终素材，05→06交付绑定和眼部资产；各阶段均保留节点与原图坐标。
5. **下载副本**：网页的导出JSON、PNG、ZIP和保存网页通常下载到浏览器指定的位置，不自动写入P。需要归档到项目时记录实际文件位置并保存副本。下载、单项已检查、关闭编辑窗口都不代替整阶段确认。

原始输入JSON、02初始assets和04初始修复源文件不会自动反映所有网页修改。返修读最新draft，正式进入下游读有效confirmed；离线展示使用网页导出或历史／交付脚本从最新数据生成的副本。

## 回看与最终产物

生成／交接阶段时保存只读回看：

```text
python "S/scripts/export_review_history.py" --project-root "P"
```

该命令导出项目已有的阶段workflow；每份快照在 `P/history/`，入口为 `P/review-history.html`。历史页与大肥鱼示例页用于回看／参考，不连接当前编辑服务，不能替代新项目确认。

保存当前可播放交付：

```text
python "S/scripts/export_motion_delivery.py" --project "P/stage06-review.workflow"
```

返回实际版本目录 `P/delivery/animation-<run前8位>-r<revision>-<数据摘要前10位>-<页面摘要前8位>/`，包括：

- `character-idle-run.html`：内嵌素材、人工覆盖、运行脚本的独立可播放网页。
- `character-idle-run.json`：同版本的完整设计、素材、绑定、动作与过渡。
- `release.json`：来源版本、依赖及真实确认状态。可交付待检查版本，不伪造最终确认。

AI每阶段交付至少报告：实际审阅URL、项目／workflow绝对路径、已保存revision和确认状态、主要产物路径、下游将读取哪个确认文件；不要要求用户自己在下载目录猜测哪个文件才是最新成果。
