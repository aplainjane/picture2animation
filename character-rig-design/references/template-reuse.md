# 网页模板对应关系与复用规则

本 skill 同时包含阶段说明、完整前端和配套生成／审阅脚本。新角色复用工具，另建角色项目保存输入、草稿、素材、确认与交付。不要把某个角色已经生成的 HTML 当作空模板：它含有角色数据，可能还绑定有效服务配置。

## 按阶段调用

下列路径相对本 skill 根目录。具体输入格式和命令参数以对应 `stages/` 子文档为准。

| 阶段 | 保留的前端模板 | 生成脚本 | AI 需准备的角色数据 |
| --- | --- | --- | --- |
| 01 结构与节点 | `assets/rig-editor.html` | `scripts/build_rig_editor.py` | 原图、部件规划、节点及父子关系 JSON |
| 02 拆图与表情分离 | `assets/part-review.html` | `scripts/build_part_review.py` | 01确认、前景与部件边界配置、独立五官和空面部方案 |
| 03 补全计划 | `assets/material-review.html` | `scripts/build_material_review.py` | 02确认、逐块检查与补全／SVG／清理建议 |
| 04 修复结果与手修 | `assets/material-result.html` | `scripts/build_material_result.py` | 03确认、实际修复素材及 repair-manifest.json |
| 05 绑定与表情校准 | `assets/animation-review.html` | `scripts/build_animation_review.py` | 04确认、驱动节点、眼部六点建议与闭眼贴图 |
| 06 动作与最终编辑 | `assets/motion-review.html` | `scripts/build_motion_review.py` | 05确认、适配当前角色的动作轨道及过渡 |

阶段06生成器还会内嵌 `motion-runtime.js`、`motion-eyes.js`、`motion-material-editor.js`；必须连同 HTML 模板保留，才能保留实时过渡、眼部效果、点选、画笔／橡皮／取色和双层像素转移。其他阶段的交互逻辑位于各自 HTML 中。

共同服务为 `scripts/review_checkpoint.py`，负责草稿、版本校验和人工确认。`scripts/export_review_history.py` 保存逐阶段只读快照；`scripts/export_motion_delivery.py` 保存含实际确认状态的动画 HTML 与 JSON。

各网页的输入、操作、提交和下游交接见对应阶段开头的“网页使用与交接卡”；统一目录、完整调用示例和权威产物说明见[项目产物与交接约定](project-artifacts.md)。

## 新项目与恢复

1. 实际读取新原图，在独立角色项目目录准备当前阶段的数据；复用模板和生成器，只向项目输出文件注入角色数据。先读阶段文档，检查上游确认后执行。
2. 生成器建立 `<网页名>.workflow/`。启动 `review_checkpoint.py serve --project <workflow目录>`，打开服务实际返回的 URL，不复用历史端口。网页可离线查看，但持久保存草稿和人工确认需要配套本地服务。
3. 人工完成当前阶段确认后执行 `check`，只将返回的有效确认快照传给下一阶段。AI 不替人确认。
4. 恢复已有角色先读取其 workflow 与最新 draft，复用可用服务。不要重新运行初始化生成器覆盖人工调整。局部更新应使用服务草稿接口的 run_id／revision 校验，并保留未涉及的字段；发生版本冲突时重新读取最新草稿再合并。
5. 最终页返修保留 `production.material_overrides`、`layer_order`、`face_underlay`、绑定、眼部参数及反馈。先存历史，再修受影响内容，更新后续内嵌数据；不要从上游旧素材覆盖人工手修。

## 复用范围与环境

- 使用 Python 3，图片／分割脚本需要 Pillow、NumPy、SciPy。SVG栅格化辅助脚本另外需要 Node.js、Playwright 和 Chromium；使用目标环境已有的路径或脚本参数，不依赖开发机器的盘符。
- 模板不是图像识别模型。AI／设计者仍需提供节点、前景和语义部件边界，审阅需要补全的隐藏区域，并制作实际补片、SVG或闭眼素材；本次角色的专用处理脚本与分析记录留在角色项目，不是其他角色的必需输入。
- 当前表情工具采用 `eye_l/eye_r/brow_l/brow_r/mouth` 等语义ID。阶段06默认提供 Witch 人形动作预设，依赖其人体节点和 `boot_l/boot_r` 等部件ID；新角色须核对左右语义、ID映射、体型与原始肢段方向，再适配动作。用户自定的命名不能不经检查直接套用。
- 网页交互与检查点流程可以复用；对新图的美术判断和最终动作质量仍需人工检查。保留完整 skill 文件夹即可保留这些工具；要自动发现此 skill，还需在目标环境安装或按路径明确加载主 `SKILL.md`。
- 迁移已经制作好的角色时，另带完整角色项目及上游 workflow；依赖链包含绝对路径，换目录后需重新映射并校验，不能仅复制最终 HTML 就声称恢复了可编辑的完整流程。
