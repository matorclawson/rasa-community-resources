# Masterclass visual system

sow: software-factories-masterclass-SOW-02

The designer supplies `style.css`, `art/`, `visual-diagrams.mjs` and
`check-layout.mjs`. Rasa-ops owns the slide story and text in the single
offline `index.html`. Link the local `style.css` and inline the generated SVGs
from `art/` during generation so the reveal groups stay in the page DOM.
The deck directory needs no module loader,
package install, external font host or network connection.

The Architect's binding 04:31 partition makes `style.css` and `art/` the
canonical LOOK paths; it supersedes the earlier `pics/` receiving hook.
Rasa-ops owns `index.html`, including which art each slide consumes. This
contribution never writes the content owner's working index or generator.

The composition is a local adaptation of Rasa brand tokens v0.2.0, read from
`RasaHQ/brand` at the supplied checkout. Cream and ink carry the composition;
pink marks the focal action, mint a successful result, and orange a rejected
result. These diagrams are teaching illustrations, not product screenshots.
Use the existing embedded Newsreader, Inter and JetBrains Mono faces and keep
`FONT-LICENSES.txt`. Do not add Bureau binaries. Do not reconstruct the Rasa
logo; retain the supplied master when a logo is used.

## Composition contract

Each `.slide` has a `.crumb` navigation line, one `h1`, and one `.scene`.
The scene holds an SVG from the diagram helpers. At 1920 × 1080 the title is
80 px, navigation 32 px, diagram labels at least 32 px, and the designed scene
1680 × 660 px. All content stays inside a 6% safe area. Dimensions scale
together for 1280 × 720; text is never reduced to fit an overfull slide.

Use one sentence for the title and at most 12 visible instructional words in
the diagram and any body copy combined. Numbers, times, links and step labels
count; persistent breadcrumb navigation does not. Do not hide extra teaching
copy in notes, shrink it, clip it or move it off screen to make the gate pass.
An agenda or live-step instruction that cannot fit must be resolved with the
content owner, preserving the operator's required direction and narrative.

The primitives cover a traveller's disconnected sources and connected answer,
the factory sequence, builder versus protected tests, the two complementary
tools, three decision outcomes, chapter checkpoints, question/choice/briefing,
the eight-part roadmap and a capability hub. Labels are arguments
so the content owner can use the agreed vocabulary. Long labels or additional
nodes need a new measured composition rather than automatic font shrinking.

## Render every slide before updating the preview

Use an already installed Playwright Core; this adds no repository dependency:

```sh
node workshops/software-factories-masterclass/slides/check-layout.mjs \
  --playwright /path/to/installed/playwright-core \
  --deck workshops/software-factories-masterclass/slides/index.html \
  --out /path/to/rehearsal-evidence
```

The gate renders all slides at 1920 × 1080 and 1280 × 720, hashes every
screenshot, records its source hash, and exits nonzero for excessive slide or
word count, small text, thin margins, overlapping text, overflow, failed assets,
network fetches or a visual under half the slide area. The visual measurement
uses visible SVG marks, not an empty SVG container. Fixed deck chrome is also
measured. A background panel can be part of a designed scene; geometry alone
cannot prove that it communicates an idea. Inspect the screenshots and obtain
dt-proofreader's teaching/read-aloud review and Council review independently.

The 55-slide source at PR131 `4537736` is the recorded failure baseline.
The visual-system design review is a component demonstration, not a replacement
story, a completed deck or acceptance of the public preview.

`check-layout-controls.mjs` uses the same `--playwright` and `--out` arguments
to render one valid fixture and deliberately broken typography, margin,
overflow, visual-area, word-count, overlap, list, fixed-chrome and navigation
fixtures. It passes only when the gate rejects the expected defect at both
resolutions. These fixtures prove detection behavior, not the teaching quality
of the finished deck.

## Historical first 30-slide geometry bridge

`repair-v4-geometry.mjs` is a narrowly pinned bridge for the content owner's
first 30-slide preview (SHA-256 `658b68a130a06b5ad46c3d0eb596ff82dc72206ad04d3e3117dc5b978c3e5b52`).
It refuses other source bytes before launching a browser, writes to a separate
directory, and verifies that normalized title, body and diagram text is
unchanged across all 30 slides. It produces nine SVG drop-ins for the owner's
`pics/NN.svg` generation hook, a small margin override and a complete review
HTML file. The geometry changes separate labels and subtitles and wrap slide
7's overlong subtitle around its icon. No smaller font is used.

```sh
node workshops/software-factories-masterclass/slides/repair-v4-geometry.mjs \
  --playwright /path/to/installed/playwright-core \
  --deck /path/to/exact-v4-preview.html \
  --out /path/to/separate-geometry-review
```

That older bridge is retained for its exact failed source only. Current c268
content has superseded it. The receiver integrated the geometry and wording
changes into the same deck. New work uses the canonical paths above and runs
`check-layout.mjs` on the regenerated deck before any preview update.
The gate advances through the real keyboard reveal controls before measuring
each fully revealed slide, and checks that the expected slide actually showed.
The bridge does **not** resolve the remaining word-count failures: diagram
labels and body copy share the 12-word budget. Rasa-ops retains that content
decision and the final story; a geometry-only pass is not a finished deck pass.

## Thirty SVGs and teaching reveals

The content-owner partition is implemented by `art/01.svg` through
`art/30.svg`. Each uses `viewBox="0 0 1000 400"`, resolves its colours and
type into inline presentation styles, and has no external asset references.
The host keeps its existing embedded OFL font faces and licences. The drawings
adapt the larger composition without distorting its aspect ratio; their
smallest effective type is above 17 viewBox units.

These pictures preserve the complete title/body/diagram wording of PR131
`c268eccc`. Twenty-five teaching diagrams build in stages. Five orientation or
recap pictures stay complete. Structural panels remain visible as context;
icons, labels and connectors reveal in their teaching order. Hidden tests
appear before the builder works, and terminal commands appear in order.

Link the canonical `style.css` and inline `reveal-navigation.js` in the deck,
replacing its previous navigation handler. Do not install both handlers.
Arrow keys and clicks reveal the next stage; the press after the last stage
advances the slide. Back reverses the build, then returns to the completed
previous slide. Home and End show the cover and complete closing slide.
Without this controller the SVG content remains fully visible.

`export-slide-pictures.mjs` reproduces the pictures and a separate integrated
review HTML from the exact c268 input. It refuses a different revision rather
than silently replacing the content owner's newer words. That candidate also
retains the within-part breadcrumb counter. The content owner receives the
SVGs, controller and CSS and publishes through the same PR131. The candidate
links `style.css` as a local asset, and its gate records the stylesheet's exact
bytes and hash before rendering and verifies they did not change afterwards.
Other unbound local assets fail rather than silently escaping source binding.

Use `check-layout.mjs --capture-steps` for initial and intermediate reveal
screenshots in addition to every completed slide at both resolutions. The
report records the stage count and every frame's hash. Full layout checks
apply to completed compositions; stage screenshots require visual review.
`check-reveal-navigation.mjs` exercises actual keyboard/click behavior, source
ordering, the protected-test sequence, factory assembly, terminal commands,
reverse navigation and Home/End in the browser. Candidate evidence does not
qualify a subsequently changed head.
