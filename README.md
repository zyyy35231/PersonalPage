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

The page reads portfolio entries from `assets/photo-data.js` and web-ready images from `assets/photos/`.

## Local Curation Workbench

To review photos from the local Lightroom folder without changing the public site:

```bash
python3 tools/curate-photos.py --source /Users/zy/Desktop/Lightroom
```

Then open `http://127.0.0.1:8765/`.

The workbench saves review state to `.curation/selection-draft.json` and caches thumbnails in `.curation/thumbs/`. That folder stays local and is ignored by git.
