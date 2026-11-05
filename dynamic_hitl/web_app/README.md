# Dynamic HITL Explainer

An interactive, static site that explains — to customers and technical stakeholders — how to turn **Azure AI Content Understanding** confidence scores into a defensible human-review policy, and how much review effort that saves.

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

`dist/` is plain static files with relative asset paths, so it can be dropped onto Azure Static Web Apps, GitHub Pages, a blob container, or any web server. **No backend, no API keys, no Python at page-view time.**

### Single-file build

```powershell
npm run build:single   # writes dist-standalone/dynamic-hitl-explainer.html (~630 kB)
```

This folds the JS, the CSS and the precomputed payload into one self-contained HTML file that makes **no network requests at all** — it opens by double-clicking it from disk, on a plane, with no server, no `npm` and no install. Email it, drop it in a Teams channel, or attach it to a wiki page. The build fails if any external or unbundled reference survives, so it cannot silently regress to needing the network.

It writes to its own folder, so `npm run build` and `npm run build:single` do not overwrite each other and both outputs can sit side by side.

### Fonts

The page uses the same font stack Microsoft Learn computes to — `Segoe UI`, falling back through `-apple-system` / `Helvetica Neue` / `Arial` — and `Consolas`/`SF Mono` for figures. These are all system fonts, so nothing is downloaded and the offline file matches the Azure documentation on Windows. Learn self-hosts *Segoe UI Variable* as a webfont, but that file is licensed to Microsoft's own properties and is not redistributable, so it is deliberately not embedded here.

## What the page walks through

| Section | Point it makes |
| --- | --- |
| 01 · The cost | Every extracted value is reviewed today, to find the ~18% that are wrong. |
| 02 · The tempting shortcut | One global confidence cutoff lands somewhere different in every field. |
| 03 · What to do instead | Two tracks per field, gated on whether that field's confidence carries real signal. |
| 04 · Your one dial | A single business target sets every cutoff; the savings composition moves with it. |
| 05 · Does it hold up? | The frozen policy, measured on 200 receipts it never saw. |
| 06 · Room to grow | Confidence cutoff vs. fitted `P(correct)` — identical today, extensible later. |
| Closing | Run the same method on your own documents via [`../calibration_lab/`](../calibration_lab/). |

Sections 4–6 are driven by one shared dial in the sticky bar at the bottom of the screen.

## How the numbers get here

Every figure on the page is precomputed. There is no live modelling in the browser.

```powershell
cd precompute
python build_payload.py     # writes ../src/data/payload.json
```

[`precompute/build_payload.py`](precompute/build_payload.py) imports the calibration code from the sibling [`../calibration_lab/`](../calibration_lab/) folder — the same code the customer-facing notebook runs — and sweeps it across:

- every coverage target from 50% to 99% in 1% steps,
- both scoring engines (raw confidence and fitted `P(correct)`),
- the training split (expected results) and the held-out test split (measured results).

`src/data/payload.json` (~240 KB) is **committed**, so the site builds and runs with Node alone. Regenerating it is only necessary after changing the dataset or the calibration logic, and takes the better part of an hour. The two folders ship together.

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
scripts/
  build-single-file.mjs  inlines the build output into one offline HTML file
```

No chart library — the charts are plain SVG so the animations and the visual language stay under our control.
