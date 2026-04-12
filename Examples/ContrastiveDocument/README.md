# ContrastiveDocument Example

This is an example configuration for the Contrastive 3-way document evaluation task type.

## Task Type

`ContrastiveDocument` shows three system translations side-by-side for the same source
segment, allowing annotators to score all three in a single view.

## Usage

1. Place `manifest.json` and `batches.json` in this directory.
2. Run `python manage.py init_campaign Examples/ContrastiveDocument/manifest.json`
3. Import batches: upload `batches.json` via the Dashboard or use `ProcessCampaignData`.

## Batch Format

Each item in `batches.json` has a `targets` array with **3 entries** (one per system).
Each target has `targetID`, `targetText`, `targetContextLeft`, and `_target` (0, 1, or 2).
Set `targetsSize: 3`.

## Supported Options

- `ESA` — Enable error span annotation (MQM-style) on each translation
- `SQM` — Scalar quality metric mode
- `ScalarSlider` — Use the ScalarSlider widget
- `Scale100` — Use 0-100 scale instead of 1-10
- `CommentsSeg` — Per-segment comments
- `CommentsDo` — Per-document comments (required before submit)
- `DisableMobile` — Block narrow viewports
- `Monolingual` — Hide source text
- `SkipDocumentScores` — Skip document-level scoring
- `SliderBubble` — Show value bubble on slider handle
