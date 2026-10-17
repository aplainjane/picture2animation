<div align="center">

<img src="docs/media/icon.png" width="120" alt="picture2animation project icon">

# picture2animation

**Give an illustration its first steps.**

Let AI make a first pass. Move the joints, fix the edges, and make the character yours.

[中文](README.md) · **English**

[See the process](#how-dafeiyu-started-running) · [Get started](#get-started) · [Skill entry](character-rig-design/SKILL.md) · [Motion example](character-rig-design/references/dafeiyu-motion-example.md)

<img src="docs/media/dafeiyu-idle-run.gif" width="480" alt="Dafeiyu in the actual cutout player: idle, start running, run, stop, and return to idle">

*Dafeiyu goes for a little run. Captured from the actual cutout player, including both transitions.*

</div>

picture2animation is a staged AI skill for building editable 2D cutout characters from a single illustration. Work through skeleton layout, part separation, material repair, binding, and animation with a browser review page at every step.

Move a shoulder. Give a few sleeve pixels back to the arm. Fix a repair that changed the face too much. Once the character is running, you can still change the draw order or touch up a texture in the final player. Each stage keeps its own page and data, so there is a way back.

## How Dafeiyu started running

![The real workflow: source illustration, skeleton markers, colored parts, and the final run pose](docs/media/journey.jpg)

These are screenshots from the actual example. All six browser templates, their generators, and stage instructions are included. Reuse the tools for another character and prepare data for that character.

### 01 · Find the joints first

Place the head, neck, chest, shoulders, elbows, wrists, hips, knees, and ankles over the source image, then add anchors for hair and accessories. Hidden joints start as estimates you can drag into place. Names and parent relationships are editable too.

![Stage 01: skeleton placement on the original image, with a shoulder selected](docs/media/01-skeleton.png)

### 02 · Decide which pixels belong together

Colors follow each part's actual silhouette; numbers show its draw order. Select two neighboring layers and transfer pixels across their boundary. Eyes, brows, and the mouth become separate parts, with a blank face underneath for expression work.

![Stage 02: color-coded silhouettes and numbered layers](docs/media/02-separation.png)

<details>
<summary>A closer look at the blank face and separate expressions</summary>

![Separate face and expression previews, with the facial boundaries enlarged](docs/media/02-expressions.png)

</details>

### 03 · See what needs fixing before fixing it

Lay out every part. Decide which gaps need filling, which edges need cleaning, and where local SVG work makes sense. AI proposes a plan; you can select, deselect, and leave notes for each part. This stage approves the plan.

![Stage 03: an isolated-part gallery with completion, SVG, and cleanup checkboxes](docs/media/03-repair-plan.png)

### 04 · Fill the gaps, keep the character

Compare the before and after. Check new pixels, colors, and silhouettes. Dafeiyu's face went through several revisions here to keep the original chin and shading. A color picker, brush, and eraser let you make small fixes yourself and carry those changes forward.

![Stage 04: before-and-after comparisons of repaired transparent parts](docs/media/04-material-repair.png)

<details>
<summary>Make a small fix with the pixel tools</summary>

![An enlarged blank face with color picker, brush, and eraser controls](docs/media/04-pixel-tools.png)

</details>

### 05 · Even a blink deserves a closer look

Choose the driving node for each part and test small joint rotations. Six eye-guide points define the eyelid region; the upper and lower lids approach each other, then use the corresponding closed-eye texture at full closure. An enlarged preview helps catch stray skin or leftover lash pixels.

![Stage 05: the six-point eyelid guide and a live eye-opening preview](docs/media/05-eye-rig.png)

<details>
<summary>See full-body binding and expression previews</summary>

![Full-body binding, skeleton, and synchronized face preview](docs/media/05-binding.png)

</details>

### 06 · Keep editing after the first run

Try idle, start, run, and stop together. Pause, slow down, and scrub to inspect the arm swing and seams. Adjust draw order, select parts for pixel editing, or open a two-color editor to transfer pixels between two layers. Dafeiyu's final stop uses a small outward arm gesture, tuned down during review.

![Stage 06: final animation playback, clips, timeline, and draw-order controls](docs/media/06-animation.png)

**Want to try it?** Download the repository and open the [full interactive Dafeiyu example](character-rig-design/assets/examples/dafeiyu/index.html) in a browser. It embeds its assets and scripts, works offline, and lets you inspect the skeleton, play all four clips, and test live transitions. GitHub displays the HTML source; open the downloaded file locally to use the player.

## Get started

Use an AI environment that can inspect images, work with local files, and run Python. The browser templates provide the review tools; AI prepares the character's nodes, masks, repairs, and motion data. The review UI and detailed skill instructions are currently in Chinese.

```bash
git clone https://github.com/aplainjane/picture2animation.git
cd picture2animation
python -m pip install -r requirements.txt
```

Give your AI the illustration and this request:

```text
Use character-rig-design/SKILL.md in this repository.
Start with this character image and run stage 01.
Generate the editable skeleton review page using the existing template.
Wait for my confirmation in the browser before moving to the next stage.
```

To continue an existing project:

```text
Restore this character project and inspect its workflow and latest draft first.
Keep my edited textures, draw order, and bindings.
This time, only adjust the stop animation.
```

For repeated use, place `character-rig-design/` in your AI tool's skill directory, or keep invoking its `SKILL.md` by path. Stage documents are loaded as needed; there is no need to load every document and example into context at once.

**Environment:** Python 3, Pillow, NumPy, SciPy, and a modern browser. The optional SVG-to-PNG helper also uses Node.js, Playwright, and Chromium; see [stage 04](character-rig-design/stages/04-material-result.md).

## What moves from one stage to the next?

| Stage | What you review | What goes forward |
| --- | --- | --- |
| 01 Structure | Joint positions, left/right semantics, parents | Structure and skeleton coordinates |
| 02 Separation | Boundaries, draw order, blank face, expressions | Current cutouts and crop offsets |
| 03 Plan | Completion, local SVG work, cleanup selections | Your selected repair plan and notes |
| 04 Materials | Repairs, colors, seams | Final materials |
| 05 Binding | Driving nodes, joint tests, eye guides | Bindings and expression assets |
| 06 Motion | Loops, transitions, final textures and draw order | Animation HTML, complete JSON, version metadata |

Each stage starts with a handoff card covering inputs, browser actions, save and approval buttons, and output locations.

- **Save a draft** to keep working on the current design.
- **Approve a stage** in the browser to produce `confirmed.json`. AI checks that approval before using it downstream.
- **Export or download** a copy of the current result. A playable delivery can be exported before final approval, with its actual status recorded.

Downloads and individual “checked” flags do not stand in for stage approval. Your texture edits, guides, layer order, and bindings carry forward.

## Repository and project files

```text
picture2animation/
├── README.md                    Chinese home page
├── README.en.md                 English
├── docs/media/                  Real screenshots, GIF, and project icon
└── character-rig-design/
    ├── SKILL.md                 AI entry point
    ├── stages/                  Six stage guides and handoff cards
    ├── references/              Formats, reuse rules, and motion example guide
    ├── scripts/                 Generators, review service, checkpoints, exports
    └── assets/                  Six browser templates and runtime scripts
        └── examples/dafeiyu/    Complete, self-contained offline example
```

Each character gets a separate project directory:

```text
your-character-project/
├── input/                       Original image and generator inputs
├── stage01-review.html          Review pages, through stage06
├── stage01-review.workflow/     A separate workflow directory for each stage
│   ├── draft.json              Latest saved draft
│   ├── confirmed.json          Human-approved snapshot
│   └── workflow.json           Stage, revision, and dependencies
├── history/                     Read-only stage snapshots
├── review-history.html          History index
└── delivery/                    Playable HTML, complete JSON, release.json
```

See [project artifacts and handoff rules](character-rig-design/references/project-artifacts.md) for the commands and file locations. Resume from the latest draft, and use a valid approved snapshot downstream, so manual work does not get replaced by an older export.

## Where it fits

Use it for editable 2D cutout characters, gentle idle motion, blinks, in-place running, and transitions, with a designer reviewing each step.

The current renderer uses single-bone rigid cutouts and local strip deformation. Large turns, perspective changes, and newly exposed hidden regions need additional art or design work. There is no mesh skinning, IK solver, or Spine project export. New illustrations still need image-specific separation and repair decisions. The motion preset is a starting point to adapt to the character's proportions, rest directions, and requested movement.

## Keep exploring

- [Main skill](character-rig-design/SKILL.md): stage routing and shared rules.
- [Template reuse](character-rig-design/references/template-reuse.md): how another AI can call the existing tools.
- [Dafeiyu motion example](character-rig-design/references/dafeiyu-motion-example.md): four clips, live transitions, and the small stop gesture.
- [Motion JSON](character-rig-design/assets/examples/dafeiyu/motion.json): image-free data for studying individual node tracks.

Issues are welcome. A screenshot, a part name, and a timestamp—such as “left elbow seam at 0.2 seconds in run”—make a great starting point.

<sub>Screenshots and animation come from the included Dafeiyu example. The project icon was supplied by the project author. Inclusion of an example does not grant rights to reuse the underlying character or artwork.</sub>
