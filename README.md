# Zy Photography Portfolio

Static photography portfolio for Zy.

## Local Preview

```bash
python3 -m http.server 8080
```

Then open `http://127.0.0.1:8080/index.html`.

## Photo Workflow

Original and candidate photos stay local in `Photos/`.

To prepare web images and draft photo data:

```bash
python3 tools/prepare-photos.py your-photo.jpg
```

To import photos marked as selected in the local curation workbench:

```bash
python3 tools/prepare-photos.py --from-curation .curation/selection-draft.json
```

The page reads portfolio entries from `assets/photo-data.js` and web-ready images from `assets/photos/`.
Preview images and published images both use `tools/photo_processing.py`; the workbench writes preview cache files to `.curation/previews/`, while the public site uses `assets/photos/`.

## Local Curation Workbench

To review photos from the local Lightroom folder without changing the public site:

```bash
python3 tools/curate-photos.py --source /Users/zy/Desktop/Lightroom
```

Then open `http://127.0.0.1:8765/`.

In the workbench, click a photo to preview it and move the active frame. Press Space on the active photo to toggle selected/unreviewed, use arrow keys to move through the grid, and use 1/2/3/0 for selected/maybe/rejected/unreviewed. Changes auto-save, and the Save button writes the current photo state, series, homepage order, color-group cover flag, and note immediately. Homepage order starts at `1`; leave it blank for automatic placement.

The workbench saves review state to `.curation/selection-draft.json` and caches thumbnails in `.curation/thumbs/`. That folder stays local and is ignored by git.
