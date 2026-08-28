# Dynamic HITL Explainer

An interactive, static site that explains — to a non-technical audience — how to turn
**Azure AI Content Understanding** confidence scores into a defensible human-review
policy, and how much review effort that saves.

Built for the Content Understanding product group to share with customers.

## Run it

```powershell
npm install
npm run dev      # http://localhost:5173
```

To produce a deployable folder:

```powershell
npm run build    # writes dist/
npm run preview  # serve dist/ locally
```

`dist/` is plain static files with relative asset paths, so it can be dropped onto Azure
Static Web Apps, GitHub Pages, a blob container, or any web server. **No backend, no API
keys, no Python at page-view time.**

## What the page walks through

| Section | Point it makes |
| --- | --- |
| 01 · The cost | Every extracted value is reviewed today, to find the ~18% that are wrong. |
| 02 · The tempting shortcut | One global confidence cutoff lands somewhere different in every field. |
| 03 · What to do instead | Two tracks per field, gated on whether that field's confidence carries real signal. |
| 04 · Your one dial | A single business target sets every cutoff; the savings composition moves with it. |
| 05 · Does it hold up? | The frozen policy, measured on 100 receipts it never saw. |
| 06 · Room to grow | Confidence cutoff vs. fitted `P(correct)` — identical today, extensible later. |
| Closing | Run the same method on your own documents via [`../calibration_lab/`](../calibration_lab/). |

Sections 4–6 are driven by one shared dial in the sticky bar at the bottom of the screen.

## How the numbers get here

Every figure on the page is precomputed. There is no live modelling in the browser.

```powershell
cd precompute
python build_payload.py     # writes ../src/data/payload.json
```

[`precompute/build_payload.py`](precompute/build_payload.py) imports the calibration code
from the sibling [`../calibration_lab/`](../calibration_lab/) folder — the same code the
customer-facing notebook runs — and sweeps it across:

- every coverage target from 50% to 99% in 1% steps,
- both scoring engines (raw confidence and fitted `P(correct)`),
- the training split (expected results) and the held-out test split (measured results).

`src/data/payload.json` (~220 KB) is **committed**, so the site builds and runs with Node
alone. Regenerating it is only necessary after changing the dataset or the calibration
logic. The two folders ship together.

## Layout

```
src/
  App.tsx            slider + engine state, sticky dial bar
  sections/          one file per scroll section
  charts/            hand-drawn SVG charts (d3-scale for maths, framer-motion for transitions)
  components/ui.tsx  section shell, cards, metrics, slider, toggle, legend
  lib/               typed payload accessors, formatting, colour tokens
  data/payload.json  precomputed results (committed)
precompute/
  build_payload.py   regenerates the payload from ../calibration_lab
```

No chart library — the charts are plain SVG so the animations and the visual language stay
under our control.
