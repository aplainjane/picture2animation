<div align="center">

<img src="docs/media/icon.png" width="120" alt="picture2animation 项目图标">

# picture2animation

**一张立绘，拆开、调好，让她跑起来。**

AI 起稿，你来调整。每一步都有网页可以看、有地方可以改。

**中文** · [English](README.en.md)

[看完整过程](#大肥鱼是怎么跑起来的) · [开始使用](#开始使用) · [Skill 入口](character-rig-design/SKILL.md) · [动作示例](character-rig-design/references/dafeiyu-motion-example.md)

<img src="docs/media/dafeiyu-idle-run.gif" width="480" alt="大肥鱼的实际动画：待机、起跑、跑步、收步后回到待机">

*大肥鱼先跑两步。上面录的是实际切片动画，包含 idle、run 和双向过渡。*

</div>

picture2animation 是一套分阶段的角色动画 Skill：从一张原图开始，和 AI 一起确定骨骼、拆分部件、补全素材，再做绑定和动画。

你可以把肩膀挪一点，把袖口多分给手臂一点；觉得补图改了脸，就回去修。跑起来以后发现层序不对、关节露缝，也能在最终页面继续调整。每个阶段都留下自己的网页和数据，随时能回头看。

## 大肥鱼是怎么跑起来的

![大肥鱼从原图、骨骼标注、彩色部件拆分到最终跑步姿势的完整过程](docs/media/journey.jpg)

下面都是这个案例的实际网页截图。六个阶段的前端模板、生成脚本和操作说明都在仓库里，换角色时复用工具，重新准备这个角色的数据。

### 01 · 先把关节找准

在原图上摆好头、颈、胸、肩、肘、腕、髋、膝、踝，再补头发和饰品的挂点。被衣服遮住的关节可以先估一个位置，由你拖动校准；节点名称和父子关系也能改。

![第一阶段：在原图上定位人体骨架，并调整肩部节点](docs/media/01-skeleton.png)

### 02 · 这块归谁，用鼠标说清楚

部件沿实际外形叠色，数字标出前后顺序。轮廓分错了，就选中相邻两层，把像素划过去。眼睛、眉毛、嘴单独拆，下面留一张没有五官的面部底图，给后面的表情动画留空间。

![第二阶段：按透明轮廓着色的切片与图层顺序](docs/media/02-separation.png)

<details>
<summary>放大看：面部和表情也能分开检查</summary>

![空面部与独立表情检查，以及放大后的面部轮廓](docs/media/02-expressions.png)

</details>

### 03 · 缺哪里，先看清再补

把所有部件摊开看：哪里会露洞，哪里只需要清理边缘，哪里适合局部 SVG。AI 给建议，你可以逐块勾选、取消和补充备注。这里确认的是处理计划。

![第三阶段：独立部件画廊、补全建议，以及可勾选的SVG和清理选项](docs/media/03-repair-plan.png)

### 04 · 补完整，也保留原来的味道

逐块看修复前后，检查新补的区域有没有跑出轮廓、有没有损失原来的颜色。大肥鱼的脸就在这里反复改过：下巴轮廓和原有明暗都要留住。小问题可以直接用取色、画笔和橡皮微调，保存后带着新素材继续走。

![第四阶段：透明部件的修复前后对照](docs/media/04-material-repair.png)

<details>
<summary>需要自己补两笔？打开像素工具</summary>

![放大的空面部与取色、画笔、橡皮工具](docs/media/04-pixel-tools.png)

</details>

### 05 · 眨一下眼，也要亲自过目

选部件、调驱动节点，试着转一转关节。眼睛用六点控制架校准，上下眼睑靠近闭合，完全闭合时切换对应的闭眼贴图。脸部放大窗口会同步预览，哪里夹带皮肤、哪里残留眼线，看得更清楚。

![第五阶段：眼部六点控制架，以及原眼贴图的开合预览](docs/media/05-eye-rig.png)

<details>
<summary>查看全身绑定与表情预览</summary>

![全身绑定检查、骨架和面部同步预览](docs/media/05-binding.png)

</details>

### 06 · 跑起来以后，照样能修

待机、起跑、跑步、收步，连起来试。暂停、慢放、拖时间轴，检查摆臂和接缝；图层可以直接调顺序，部件可以点选手修，还能选两块进入双色边界编辑。大肥鱼现在的收步，是双臂轻轻向外展开，幅度已经调小。

![第六阶段：最终动画、动作片段、时间轴和图层调整](docs/media/06-animation.png)

**想自己点一点？** 下载仓库后，用浏览器打开 [大肥鱼完整交互示例](character-rig-design/assets/examples/dafeiyu/index.html)。它内嵌素材和脚本，可以断网播放、查看骨架、切换四段动作，也可以测试实时起停。仓库文件页显示的是HTML源码，下载到本地打开即可。

## 开始使用

需要一个能读取图片、操作本地文件并运行 Python 的 AI 工作环境。网页模板负责展示和编辑，AI 负责为当前角色准备节点、边界、补图与动作数据。

```bash
git clone https://github.com/aplainjane/picture2animation.git
cd picture2animation
python -m pip install -r requirements.txt
```

然后把角色图交给 AI，告诉它：

```text
使用这个仓库的 character-rig-design/SKILL.md。
从这张角色图开始，先执行阶段01，生成可调整骨骼节点的网页。
沿用仓库里的网页模板，在网页中等我确认，再进入下一阶段。
```

已有进度也可以接着来：

```text
恢复这个角色项目，先检查已有 workflow 和最新草稿。
保留我改过的素材、层序和绑定，这次只调整收步动作。
```

长期使用时，可以把 `character-rig-design/` 放进 AI 工具的 Skill 目录。也可以一直按文件路径加载主 Skill。六个阶段按需读取，不必每次把所有文档和示例一起塞进上下文。

**运行环境：** Python 3，Pillow、NumPy、SciPy，现代浏览器。需要把 SVG 栅格化为 PNG 时，辅助脚本另外使用 Node.js、Playwright 和 Chromium；具体入口见[阶段04说明](character-rig-design/stages/04-material-result.md)。

## 每一步，交接什么

| 阶段 | 你检查什么 | 确认后交给下一步 |
| --- | --- | --- |
| 01 结构 | 节点位置、左右语义、父子关系 | 结构与骨骼坐标 |
| 02 拆图 | 轮廓、层序、空面部与独立表情 | 最新切片和裁切坐标 |
| 03 计划 | 补全、局部SVG、清理的勾选范围 | 实际处理计划与备注 |
| 04 素材 | 修复前后、颜色和接缝 | 最终素材 |
| 05 绑定 | 驱动节点、关节试动、眼部六点 | 绑定及表情资产 |
| 06 动作 | 循环、过渡、最终素材和层序 | 动画HTML、完整JSON、版本记录 |

每个阶段的说明开头都有一张**网页使用与交接卡**，写清输入、操作、保存按钮、确认按钮和产物位置。AI 知道怎么调用，你也知道自己交回去了什么。

- **保存草稿**：记录当前修改，方便继续做。
- **整阶段确认**：由你在网页点击，服务写出 `confirmed.json`；AI 检查有效后才进入依赖它的下一步。
- **导出／下载**：生成当前成果的副本。离线交付可随时导出，并记录真实确认状态。

网页下载和单项“已检查”不会冒充整阶段确认。人工改过的素材、六点、层序和绑定在后续继续沿用。

## 文件都放在哪里

```text
picture2animation/
├── README.md                    中文首页
├── README.en.md                 English
├── docs/media/                  实际流程截图、GIF和项目图标
└── character-rig-design/
    ├── SKILL.md                 AI从这里进入
    ├── stages/                  六阶段说明与网页交接卡
    ├── references/              格式、复用约定和大肥鱼动作说明
    ├── scripts/                 生成、审阅、检查点和导出工具
    └── assets/                  六个网页模板及运行脚本
        └── examples/dafeiyu/    内嵌素材的完整离线示例
```

每个新角色单独建项目目录，保存自己的原图、配置和成果：

```text
你的角色项目/
├── input/                       原图与生成输入
├── stage01-review.html          各阶段网页，依次到stage06
├── stage01-review.workflow/     每阶段各有一个workflow目录
│   ├── draft.json              最新已保存草稿
│   ├── confirmed.json          人工确认快照
│   └── workflow.json           阶段、修订和依赖
├── history/                     各阶段只读回看
├── review-history.html          回看入口
└── delivery/                    可播放HTML、完整JSON、release.json
```

完整的调用命令和文件去向见[项目产物与交接约定](character-rig-design/references/project-artifacts.md)。继续编辑时从最新草稿恢复；进入下游时读有效确认快照，避免把你手修的结果换回初始版本。

## 适合拿它做什么

适合把立绘做成可调整的 2D 切片角色，制作轻量待机、眨眼、原地跑步和动作过渡，也适合把制作过程留给设计者逐步检查。

目前使用单骨刚性切片和局部条带变形。复杂转身、透视变化、隐藏区域的大幅展开仍需要额外素材或设计；当前没有网格蒙皮、IK求解或Spine工程导出。新图的拆分和补全也需要结合原画判断。已有动作预设可作起点，再按角色体型、原始肢段方向和用户要求适配。

## 想继续折腾

- [主 Skill](character-rig-design/SKILL.md)：阶段路由与共同约定。
- [网页模板复用](character-rig-design/references/template-reuse.md)：后续AI如何直接调用已有工具。
- [大肥鱼动作示例](character-rig-design/references/dafeiyu-motion-example.md)：四段动作、实时衔接与小幅收步。
- [动作JSON](character-rig-design/assets/examples/dafeiyu/motion.json)：不含图片，方便按节点研究关键帧。

欢迎带着截图、具体部件和出问题的动作时刻提 Issue。比如“run 的 0.2 秒，左肘露了一条缝”，就很容易一起定位。

<sub>流程截图与动画来自仓库中的大肥鱼案例；项目图标由项目作者提供。示例图像的使用不代表获得相关角色或美术素材的再授权。</sub>
