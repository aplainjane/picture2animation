# 第一阶段网页数据格式

编写 `structure.json`、生成骨骼预览网页或读取设计者导出结果时使用本格式。坐标以方向正确的实际原图为准；示例只说明结构，不是可套用的角色节点。

```json
{
  "schema_version": 1,
  "title": "角色结构设计",
  "coordinate_system": {
    "origin": "top-left",
    "units": "px",
    "x": "right",
    "y": "down"
  },
  "image": {"name": "character.png", "width": 1000, "height": 1600},
  "nodes": [
    {
      "id": "root",
      "label": "根节点",
      "x": 500,
      "y": 1000,
      "parent": null,
      "type": "control",
      "placement": "inferred",
      "review": "proposed",
      "parts": ["torso"],
      "note": "位置待设计者复核"
    },
    {
      "id": "neck",
      "label": "颈部支点",
      "x": 500,
      "y": 550,
      "parent": "root",
      "type": "joint",
      "placement": "visible",
      "review": "proposed",
      "parts": ["head"],
      "note": "连接头部和躯干"
    }
  ],
  "parts": [
    {"id": "torso", "label": "躯干", "node_ids": ["root"], "material": "original-cutout"},
    {"id": "head", "label": "头部", "node_ids": ["neck"], "material": "original-cutout", "note": "保留原画细节"}
  ]
}
```

## 字段与约束

- `schema_version` 固定为 `1`，生成器可为省略值补齐。节点 ID、部件 ID 各自在其集合中唯一且非空。
- `image` 在生成器输入中可省略；若填写宽高，须匹配传入图片在 EXIF 转正后的尺寸。生成器写入实际文件名、宽高与 PNG data URL `src`。
- 网页导出的 JSON 含 `image.src`，因此可以独立导入恢复。手工 JSON 如果省略 `src`，必须提供 `image.name/width/height`，并先在编辑器打开同名同尺寸的正确图片；这只是匹配检查，需人工核对图片内容。通常直接用生成器内嵌原画更可靠。
- 坐标是原图像素，左上角为原点，x 向右、y 向下；x/y 必须是有限数字且在图片范围内。画布缩放和平移只影响预览。截图、浏览器 CSS 尺寸或归一化坐标不可直接填入。
- `parent` 为已有节点 ID 或 `null`，支持多个根节点，但不允许循环连接。
- `type`：`joint`（身体关节）、`anchor`（部件锚点）、`control`（变形控制点）。
- `placement`：`visible`（可见定位）、`inferred`（遮挡推测）。推测节点即使被设计者接受，也仍可保留推测依据。
- `review`：`proposed`（AI 建议）、`adjusted`（已调整）、`confirmed`（设计者已确认）。修改节点后状态变为 `adjusted`，需要设计者重新确认。
- `nodes[].parts` 是该节点关联的部件 ID 数组。`parts[].node_ids` 是可选的反向关联；若填写，应与节点关联一致。网页修改关联、重命名或删除节点时同步相关引用。尚未补全的部件 ID 可先记入节点，但应在配套部件方案中说明。
- `parts` 用于携带部件设计记录；`material`、补底、重绘说明、绘制顺序和边界等可作为部件或顶层扩展字段。当前网页保留这些字段，不提供部件轮廓编辑，也不将节点树作为绘制顺序。
- `note`（顶层）可用于说明素材来源或项目限制。网页用文本显示所有名称及备注；生成器对内嵌 JSON 的 `<` 转义，避免名称破坏 HTML。

## 设计者修改的交接

编辑网页后有两种保存方式：

1. 导出 JSON：包含原图、当前节点及原有扩展字段，供后续读取或再次导入。
2. 保存当前网页：将当前数据重新内嵌为独立 HTML，重新打开可继续编辑。AI 读取该 HTML 的 `script#rig-data` 中 JSON，即可恢复修改结果。

独立 HTML 不自动保存或回写原文件；“已导出”表示浏览器发起下载，设计者需保留下载文件。

上述两种方式是独立 HTML 的离线保存。通过本地审阅服务打开时，还提供以下检查点机制；阶段放行以本地项目的有效确认文件为准，离线副本不自动放行。

## 检查点项目与标识

```text
character-review.workflow/
├── workflow.json    # 当前任务、图片指纹、修订号、状态及设计摘要
├── draft.json       # 网页最近保存的设计
├── confirmed.json   # 人工点击整阶段确认后产生，含实际设计快照
└── server.json      # 本地服务 URL 与进程信息；不是放行标识
```

生成器给设计增加 `workflow: {run_id, stage}`；`stage` 为 `01-character-structure`。服务只接受同一任务、同一原图的修改；更换原图需新建审阅。重复生成会重置为 `awaiting_review`，旧确认即使仍存在也无效。

`confirmed.json` 包括 `run_id`、`stage`、`status: confirmed`、`revision`、`confirmed_at`、`approval_scope: skeleton-layout`、`design_sha256` 及 `design`。`design` 就是确认后的完整结构数据。`workflow.json`、草稿与确认快照必须匹配；不能只检查 `confirmed.json` 是否存在。

服务按顺序持久化网页修改，数据变动立即使已保存确认失效；重新点击确认才可放行。单节点的 `review: confirmed` 只是属性，不代表整阶段通过。两个网页同时编辑时，旧修订的提交会失败并提示重新加载，避免静默覆盖。

`review_checkpoint.py check/wait` 是主 skill 的实际放行入口。脚本退出 `0` 才可消费确认快照；返回 `2` 时仍等待。网页没有自动唤醒已结束 AI 会话的能力；活动会话可等待检查，恢复会话读取同一项目继续。
