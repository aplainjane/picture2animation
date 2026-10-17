# 补全与SVG计划数据

运行阶段03时读取。配置是AI基于实际切片写出的建议，不是分割或自动重绘模型。

```json
{
  "title": "角色 · 独立部件与补全重绘计划",
  "repairs": [
    {
      "part_id": "head_base",
      "complete": true,
      "svg": true,
      "clean": false,
      "priority": "high",
      "reason": "空面部在刘海下有缺口，局部重建肤色底形。",
      "regions": [
        {"kind":"svg", "label":"额头搭接与肤色底形", "points":[[100,100],[200,100],[190,180],[110,180]]}
      ]
    }
  ]
}
```

`repairs` 必须覆盖实际所有部件，ID不重复。未处理项三个布尔值均为false，仍需给出保留理由。`priority` 为high/medium/low；`regions` 可省略，多边形坐标为原图px，`kind` 为complete/svg/clean。示例坐标仅用于说明格式。

生成器读取有效阶段02确认中的PNG，逐部件计算alpha有效像素、透明占比、8连通块和≤12px小块的数量／位置。12px只是显示候选的统计口径，不是删除规则。所有推荐坐标来自AI实际观察，不从这些统计量直接推导。

网页快照在阶段02数据之外新增：

- `metrics`：逐部件alpha统计，只读。
- `repair_plan`：每行含 `part_id`、只读 `suggestion`（AI建议与区域），可编辑 `complete/svg/clean/note`，以及 `review`。
- `plan_review`：proposed/adjusted/confirmed。
- `upstream`：阶段02确认的目录、run、revision、design SHA256。

后端将原切片、节点、层序、面部、统计及AI建议作为只读输入做指纹绑定，只允许选择与备注改变。`confirmed.json` 的 `approval_scope=material-repair-plan`，表明计划已确认；其中的原始PNG仍是修复前切片。

生产命令：

```bash
python scripts/build_material_review.py --upstream stage02.workflow --config repair-plan.json --out stage03-review.html
python scripts/review_checkpoint.py serve --project stage03-review.workflow
python scripts/review_checkpoint.py check --project stage03-review.workflow
```

重新生成会建立新run。需要恢复时直接启动已有workflow的服务，不重新生成覆盖用户选择。未确认上游的开发预览可显式加 `--draft-preview`，不得用来放行。
