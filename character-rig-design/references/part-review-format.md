# 第二阶段配置、素材与网页数据

## 生成器输入

```json
{
  "title": "角色切片检查",
  "foreground": {"mask": "masks/character.png"},
  "parts": [
    {"id": "torso", "label": "躯干", "mask": "masks/torso.png", "node_ids": ["root"]},
    {"id": "head", "label": "头部／空面部", "mask": "masks/head.png", "node_ids": ["neck"]}
  ],
  "order": ["torso", "head"],
  "face": {
    "base_part": "head",
    "node_id": "neck",
    "roi": [150, 100, 350, 300],
    "features": [
      {"id": "eye_near", "label": "近侧眼睛", "kind": "eye", "mask": "masks/eye-near.png"},
      {"id": "brow_near", "label": "近侧眉毛", "kind": "eyebrow", "mask": "masks/brow-near.png"},
      {"id": "mouth", "label": "嘴", "kind": "mouth", "mask": "masks/mouth.png"}
    ],
    "feather_px": 3
  }
}
```

示例只说明字段关系；节点、部件、五官数量与坐标必须来自实际角色。所有蒙版、坐标和可选空面部图都以阶段 01 原图的尺寸和方向为准。相对路径相对于配置 JSON 所在目录。

- 蒙版：全图尺寸的黑白图片，白色为选区。RGBA 蒙版使用 alpha；多边形可用 `poly: [[x,y],...]`，多个区域可用 `polygons`；椭圆可用 `ellipses: [[x0,y0,x1,y1],...]`。不要输入带不透明白底、意图靠 RGB 表示选区的 RGBA 蒙版。
- `foreground`：原图不透明、有背景时必须提供角色前景蒙版；透明底可省略。
- `parts` 按像素分配优先级排列；可选 `color_rule` 为 `light/not_light/white/red`。它只是 HSV 候选筛选，不是语义识别。
- 默认遇到未分配的前景像素就报错。`unclaimed: nearest` 可显式启用最近已分配区域填充，生成结果会记录填充的像素数。
- `order` 只列身体等基础部件，须完整且无重复；生成器把表情层依次插在 `base_part` 之后。网页最终的 `order` 则包括所有部件与表情。
- `node_ids` 引用上游真实节点。表情默认使用 `face.node_id`，可逐个覆盖。
- `face.features` 是要从底图移除的实际像素范围；各初始选区不应重叠。`feather_px` 可扩展少量边缘覆盖，范围 `0..20`，不是通用精细抠图算法。
- 默认使用邻域调和插值修补空面部。可提供 `skin_samples: [[x,y],...]` 用已知皮肤拟合平滑色面，至少三个不共线的原图点，采样点附近 5×5 区域必须在底图内且未被移除。肤色采样需实际查看图片，不从眼白、眉毛、头发取色。
- 如初步修补不自然，可提供 `face.clean_base`，指向设计者修好的全图尺寸 RGBA 图片；生成器取其 RGB 作为该底图颜色，alpha 仍沿用原部件。它不改变其他部件的几何范围。

## 输出

`parts-review.html` 内嵌原图与全部 PNG，可离线查看；`parts-review.assets/` 包含独立 PNG、初始 `parts.json`、基础归属图 `labels.npy`、其索引名称 `labels-order.json` 及面部移除范围 `face-erased-mask.png`。

PNG 文件中的前缀数字是生成时的序号；网页重新排序后以当前 JSON 的 `order` 为准，不把旧文件名前缀作为新的顺序。素材坐标为原图偏移，不能在改变尺寸后直接套用。

每个部件的数据包含：

- `id`、`label`、`node_ids`：稳定标识、名称和关联节点。
- `x/y/w/h`、`src`：原图偏移、裁剪尺寸与内嵌透明 PNG。
- `outline_src`：根据实际 alpha 提取的像素轮廓，而非包围框；`color` 是独立的展示颜色，不修改原 PNG 色彩。
- `label_point`：位于真实不透明像素内部的编号锚点。网页可用引线避开相邻编号。
- `category`：`body`、`face_base` 或 `expression`；`feature_kind` 记录表情种类。
- `quality`：`pending/accepted/needs_repair`；`review`：`proposed/adjusted/confirmed`。问题备注保存在 `note`。

`face` 包含 `base_part`、`feature_ids`、面部预览 `roi`、初步修补方法与检查状态。空面部保持实心底色；表情图层保留提取范围内的原画细节，可能包括少量皮肤边缘，需要检查。半透明 PNG 叠加可能有细微 alpha 舍入差异，不能仅以看起来一致断言逐字节无损。

## 确认与依赖

第二阶段复用检查点项目结构，但 `stage` 为 `02-part-separation`、`approval_scope` 为 `part-separation`。`upstream` 记录骨骼项目路径、任务 ID、修订号和确认设计摘要。后续检查会重新验证上游，防止使用已过期骨骼结果。

生成器不修改阶段 01。`--demo` 只生成明确标记的演示，不允许整阶段确认。单层标为已检查、导出 JSON 或截图都不是正式放行。

网页修改后的顺序、备注，以及画笔修改后的 PNG、轮廓、裁剪坐标和编号锚点保存在该阶段项目的 `draft.json`；只有人工整阶段确认后的 `confirmed.json` 是后续输入。网页“下载此层 PNG”、导出 JSON、保存网页均使用当前编辑结果。生成目录中的初始 PNG、`parts.json` 和 `labels.npy` 不会随网页修改自动覆盖，不能当作最新结果。

## 鼠标轮廓调整

基础部件画笔只处理指定两层，将已有像素从一层移交到另一层；两层合计的 alpha 保持不变，透明背景不会被涂成角色。面部 ROI 不作保护区；移动像素携带当前层颜色。空部件拒绝提交。

表情画笔默认且仅与 `face.base_part` 交换；面部层也可选择表情反向操作。缩小表情时，将删去区域的 RGBA 覆盖贴回面部，表情对应像素清空，不因面部原本已有底色而跳过。扩大表情时，从当前面部复制 RGBA 到表情透明区域，避免覆盖其他表情的非透明像素，面部仍保留完整底图。其 alpha 叠加关系与基础部件转移不同，不能用两层 alpha 求和不变检查表情操作。

首次有效表情编辑保存 `face.underlay: {src,x,y,w,h}`，记录该时刻的面部底色 PNG 与坐标；它是辅助素材，不占图层编号。表情扩入后，用备份中该位置的已有像素恢复面部底色；备份在该位置透明时保留当前面部像素，避免透明洞。这样可以把误退回面部的五官重新取回，并恢复下面原来的补底。备份随草稿、JSON 导出、独立网页及确认快照持久化；撤销/重做同步恢复。普通画笔操作不做新一轮 AI 补底。

每笔包含两层完整几何更新，统一进入撤销记录并触发一次草稿保存；指针取消或 Escape 放弃当前笔。撤销/重做必须同步重载 PNG 和面部底色缓存，不能只改 JSON 而仍显示旧轮廓。正在涂抹或恢复素材时禁止阶段确认。画笔调整后两层 `review=adjusted`、`quality=pending`，涉及表情时 `face.review=adjusted`，需要重新检查。

重建或接续流程时先读取最新快照。需要恢复全图蒙版时，将每层 PNG 的非零 alpha 按 `x/y` 粘回原图尺寸；表情与空面部有设计上的叠加关系，不可把所有层直接压成单一归属图。初始 `split.json` 不记录网页后来的修改。
