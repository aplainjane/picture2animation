# 阶段04：按确认计划修复素材并检查结果

输入：阶段03有效人工确认 `material-repair-plan`。输出：所有部件的透明PNG、局部真实SVG、修复前后网页、原位合成、新增／移除像素标记、素材包和独立结果checkpoint。

## 网页使用与交接卡

路径中的 `P` 为当前角色项目绝对路径；见[统一目录与调用](../references/project-artifacts.md)。

- **调用工具**：`scripts/build_material_result.py` 复用 `assets/material-result.html`，建议输出 `P/stage04-review.html`。
- **AI准备／提交**：检查03确认后实际制作已勾选的修复，放在 `P/repair.assets/`；准备 `repair-manifest.json`、原图尺寸的 `added/<id>.png` 和 `removed/<id>.png`、引用的真实SVG及 `repaired-materials.zip`。生成器只包装和校验这些成果，不自动画出补全内容。
- **用户怎么用**：逐块比较修复前后，查看原位合成、新增／移除像素、空面部与独立表情；标记检查结果并备注。放大窗口可取色、画笔补画、橡皮擦、撤销和取消。
- **保存与整阶段提交**：备注和检查状态自动保存；像素笔迹先点“保存像素修改”才提交。解决需修项并等待保存完成后，点“确认补全与重绘结果”。下载素材包不等于确认。
- **产出在哪里**：网页在 `P/stage04-review.html`；权威草稿与确认在 `P/stage04-review.workflow/draft.json` 和 `confirmed.json`。网页保存像素后，最新独立PNG在同workflow的 `edited-assets/after/`，坐标清单与ZIP在 `edited-assets/manifest.json` 和 `edited-assets/repaired-materials.zip`。初始修复源文件仍在 `P/repair.assets/`；未进行网页像素编辑时不保证存在edited-assets。
- **下一阶段拿什么**：阶段05检查04的有效确认，只用确认快照中的最终PNG、裁切坐标、节点和层序；手修PNG不自动回写SVG路径，不能拿旧SVG栅格化覆盖用户成果。

## 执行与核对

先运行 `scripts/review_checkpoint.py check --project <阶段03目录>`，检查成功后只读返回确认文件的 `design`。逐项读取 `repair_plan` 的 `complete/svg/clean` 与设计者备注，动作范围不得超出用户确认的选择。不覆盖原图、上游切片或确认文件。

根据当前角色绘制实际补全范围，不复用其他案例坐标。保留复杂发纹、虹膜、衣褶和宝石的可见原画；只补缺口和动作可能露出的隐藏底片。简单皮肤、眉线、红晕或链环可用真实SVG路径与渐变。可采用局部像素延展或绘制简化位图底片，但须明确其是隐藏结构估计；不要将拉伸宝石、衣边的条纹当作完整衣褶。不以透明包围盒大小为填色依据。

生成工具可用时按其自身要求执行；不可用时不要声称使用过生成模型。SVG必须可独立打开且没有嵌入位图冒充矢量。`scripts/rasterize_svg.cjs` 可使用可用的 Playwright/Chromium 将自包含SVG渲染成透明PNG，供合成审阅。

逐块保留原图坐标，收紧有效alpha裁切并同步 x/y/w/h。新增底片应位于应遮挡它的前层后面，避免静态外轮廓向背景漏出。独立表情与空面部仍分层；检查发肤交界、眼尾、眉线底色、虹膜高光及嘴边接缝，不把表情重新烘焙进脸底。需要调整层序时说明具体原因并记录结果顺序。

修脸以原有可见皮肤和脸缘为依据，只填表情移走后的缺口或必要隐藏底片；不要为了补额头而用整脸椭圆与统一渐变覆盖原肤色、腮部明暗和下巴轮廓。用户要求保持原貌时，将下半脸alpha及原皮肤颜色列为保留区域，逐像素核对；需要改动的局部单独说明。

核对未选部件与源图逐像素相同；选中但无实际改动的项目如实记录零改动。重新裁切的PNG必须非空，编号点位于有效alpha内。小碎片不能仅凭面积删除，特别是鼻点、发丝与坠饰。实际检查独立切片、空面部及全角色合成；静态合成通过只表示当前姿势可检查，不等于已做动画验证。

## 结果网页

按 `scripts/build_material_result.py` 的输入约定生成当前项目的 `repair-manifest.json`：

- `upstream` 为阶段03的 project绝对路径、run_id、revision、design_sha256。
- `rows` 每部件一项：`before` 为确认快照中的完整原part，`part` 为修复后part；`actions` 必须精确等于确认选择。其余包括 `added_pixels/removed_pixels/changed_pixels`、处理说明 `method`、设计者备注 `designer_note`、可选相对路径 `svg_file`。
- `order` 为完整结果层序；`title` 与 `limitation` 说明当前交付及局限。文件旁提供 `added/<id>.png`、`removed/<id>.png` 原图大小透明标记，以及 `repaired-materials.zip`，包内包含PNG、SVG、裁切坐标和处理记录。

```bash
python scripts/build_material_result.py --upstream plan.workflow --manifest repair.assets/repair-manifest.json --out result.html
python scripts/review_checkpoint.py serve --project result.workflow
python scripts/export_review_history.py --project-root <角色项目目录>
```

打开服务返回URL。网页逐块展示修复前后，详情页使用同一原图坐标，可高亮新增／移除、叠加其他部件、缩放和下载单独PNG或SVG。原位合成可切换前后、隐藏表情检查空面部。用户能写备注、选择待检查／已检查／需要修订，下载素材包或导出检查JSON。网页像素工具可直接修订当前结果；AI重新制作素材时先保存历史，建立新的结果run，沿用最新人工修改及备注。

修订时可传 `--previous-review <已归档的上一版draft.json>`，保留设计者备注及素材未变的部件检查状态。发生资产改动的部件回到待检查；旧版“需要修订”记录应留在历史快照中，不能覆盖掉反馈。

### 网页取色、画笔与橡皮擦

部件放大窗口提供平移、取色、画笔、橡皮擦、颜色、直径、撤销、取消修改与“保存像素修改”。取色可选当前层、原图或合成；透明处不取色，成功后切换画笔。画笔可在原图画布内向部件透明边缘补画，不受旧裁切边界限制，只绘制当前层。Alt或中键平移，滚轮缩放。先本地预览，保存才持久化；未保存时阻止阶段确认和切换部件。历史快照只读。

`/api/paint` 提交原图大小RGBA、笔迹遮罩及画笔授权遮罩，服务端仅替换笔迹范围；仅擦除处保留原RGB，画笔处才允许改色和增添alpha，笔迹外逐像素保留。旧 `/api/erase` 仍支持仅降低alpha。保存更新裁切、偏移、轮廓、像素统计、PNG与ZIP。最新独立素材在workflow的 `edited-assets/`，权威数据仍为 `draft.json`。保存前后追加历史快照；当前部件回到待检查、阶段确认失效。普通备注接口不能替换素材。

编辑的是PNG，没有自动修改SVG路径。受影响层禁止下载成“修改后的SVG”，原SVG留在包内 `svg-original/`。不能保存空部件。后续AI修订须沿用最新草稿的人工编辑，不能从初始脚本覆盖。用户在最终页要求局部微调时，优先使用[阶段06的最终页编辑](06-motion-production.md#最终页图层与素材微调)，不强制返回本阶段。

## Checkpoint

阶段ID `04-material-result`，范围 `material-repair-result`，依赖阶段03及其整个上游链。用户点击“确认补全与重绘结果”才写出结果 `confirmed.json`；AI不得代点。任何部件标记 `needs_repair` 时禁止确认，整阶段按钮明确表示用户检查后接受全部结果。图片、SVG、层序、节点与处理记录绑定当前run，不允许通过保存备注悄悄替换资产。

有界等待人工确认，恢复任务时重新 `check`。尚未确认则停在结果检查；已确认可按用户授权进入[阶段05骨骼绑定与动作检查](05-skeleton-animation.md)。每次生成与阶段交接导出离线流程回看，服务端确认后自动保存该次快照。
