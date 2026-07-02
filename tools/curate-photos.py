#!/usr/bin/env python3
"""Local photo curation workbench for the Zy portfolio."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import posixpath
import sys
import urllib.parse
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageOps


DEFAULT_SOURCE = Path("/Users/zy/Desktop/Lightroom")
CURATION_DIR = Path(".curation")
DRAFT_PATH = CURATION_DIR / "selection-draft.json"
THUMB_DIR = CURATION_DIR / "thumbs"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
SERIES = ["天象", "边缘光", "山线", "水边", "微观", "未分类"]
STATUSES = ["unreviewed", "selected", "maybe", "rejected"]


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Zy 选片工作台</title>
  <style>
    :root {
      --bg: #efede8;
      --panel: #fbfaf7;
      --ink: #171512;
      --muted: #6c675f;
      --line: rgba(23, 21, 18, 0.12);
      --accent: #8f4e36;
      --dark: #111417;
      --selected: #1f6f50;
      --maybe: #a86f1c;
      --rejected: #8f3530;
      --font-display: "Iowan Old Style", "Charter", Georgia, serif;
      --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      background: var(--bg);
      font-family: var(--font-body);
      -webkit-font-smoothing: antialiased;
    }

    button,
    select,
    textarea { font: inherit; }

    button {
      color: inherit;
      cursor: pointer;
    }

    img { display: block; max-width: 100%; }

    .app {
      min-height: 100vh;
      display: grid;
      grid-template-columns: minmax(280px, 340px) minmax(0, 1fr);
    }

    .sidebar {
      min-height: 100vh;
      border-right: 1px solid var(--line);
      background: rgba(251, 250, 247, 0.86);
      display: grid;
      grid-template-rows: auto auto minmax(0, 1fr);
    }

    .brand,
    .folder-list,
    .side-footer {
      padding: 18px;
    }

    .brand {
      border-bottom: 1px solid var(--line);
    }

    .brand h1 {
      margin: 0;
      font-family: var(--font-display);
      font-size: 36px;
      line-height: 1;
      letter-spacing: 0;
    }

    .source {
      margin-top: 10px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      word-break: break-all;
    }

    .totals {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1px;
      border-bottom: 1px solid var(--line);
      background: var(--line);
    }

    .total {
      padding: 12px 10px;
      background: rgba(255, 255, 255, 0.52);
    }

    .total span {
      display: block;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .total strong {
      display: block;
      margin-top: 4px;
      font-family: var(--font-display);
      font-size: 26px;
      line-height: 1;
      font-weight: 400;
    }

    .folder-list {
      overflow: auto;
      display: grid;
      align-content: start;
      gap: 8px;
    }

    .folder-button {
      width: 100%;
      min-height: 58px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.54);
      text-align: left;
      display: grid;
      gap: 6px;
    }

    .folder-button:hover,
    .folder-button:focus-visible,
    .folder-button.is-active {
      border-color: rgba(143, 78, 54, 0.42);
      outline: none;
    }

    .folder-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-weight: 650;
    }

    .folder-meta {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }

    .side-footer {
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }

    .main {
      min-width: 0;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
    }

    .topbar {
      min-height: 78px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 16px 22px;
      border-bottom: 1px solid var(--line);
      background: rgba(239, 237, 232, 0.9);
      position: sticky;
      top: 0;
      z-index: 10;
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
    }

    .current-title {
      min-width: 0;
    }

    .current-title h2 {
      margin: 0;
      font-family: var(--font-display);
      font-size: clamp(28px, 4vw, 48px);
      line-height: 1;
      letter-spacing: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .current-title p {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 13px;
    }

    .toolbar {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .toolbar select,
    .toolbar button {
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.7);
      padding: 0 13px;
    }

    .toolbar button:hover,
    .toolbar button:focus-visible,
    .toolbar select:focus-visible {
      border-color: rgba(143, 78, 54, 0.42);
      outline: none;
    }

    .workspace {
      min-height: 0;
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(320px, 420px);
    }

    .grid-wrap {
      min-width: 0;
      min-height: 0;
      overflow: auto;
      padding: 18px;
    }

    .photo-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(156px, 1fr));
      gap: 12px;
      align-content: start;
    }

    .photo-button {
      position: relative;
      border: 0;
      padding: 0;
      background: transparent;
      text-align: left;
      display: grid;
      gap: 7px;
    }

    .photo-button:focus-visible {
      outline: 2px solid rgba(143, 78, 54, 0.7);
      outline-offset: 4px;
    }

    .thumb {
      aspect-ratio: 1 / 1;
      background: #d6d1c8;
      overflow: hidden;
      border-radius: 7px;
      border: 2px solid transparent;
    }

    .photo-button.is-active .thumb {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(143, 78, 54, 0.18);
    }

    .thumb img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .photo-name {
      min-height: 30px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }

    .status-dot {
      position: absolute;
      top: 8px;
      left: 8px;
      width: 22px;
      height: 22px;
      display: grid;
      place-items: center;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.84);
      border: 1px solid rgba(0, 0, 0, 0.18);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
      color: white;
      font-size: 14px;
      line-height: 1;
    }

    .photo-button[data-status="selected"] .status-dot { background: var(--selected); }
    .photo-button[data-status="maybe"] .status-dot { background: var(--maybe); }
    .photo-button[data-status="rejected"] .status-dot { background: var(--rejected); }
    .photo-button[data-status="selected"] .status-dot::before { content: "✓"; }
    .photo-button[data-status="maybe"] .status-dot::before { content: "?"; }
    .photo-button[data-status="rejected"] .status-dot::before { content: "×"; }

    .detail {
      min-width: 0;
      min-height: 0;
      border-left: 1px solid var(--line);
      background: var(--panel);
      display: grid;
      grid-template-rows: minmax(260px, 1fr) auto;
    }

    .preview {
      min-height: 0;
      display: grid;
      place-items: center;
      padding: 18px;
      background:
        linear-gradient(135deg, rgba(255, 255, 255, 0.52), rgba(230, 225, 216, 0.72)),
        #e8e3da;
    }

    .preview img {
      width: 100%;
      height: 100%;
      max-height: calc(100vh - 250px);
      object-fit: contain;
    }

    .empty {
      color: var(--muted);
      font-size: 14px;
    }

    .editor {
      border-top: 1px solid var(--line);
      padding: 16px;
      display: grid;
      gap: 14px;
    }

    .filename {
      font-weight: 700;
      overflow-wrap: anywhere;
    }

    .filemeta {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      overflow-wrap: anywhere;
    }

    .segmented {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 6px;
    }

    .segmented button {
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.74);
      font-size: 13px;
    }

    .segmented button.is-active {
      color: white;
      border-color: transparent;
    }

    .segmented button[data-status="unreviewed"].is-active { background: var(--muted); }
    .segmented button[data-status="selected"].is-active { background: var(--selected); }
    .segmented button[data-status="maybe"].is-active { background: var(--maybe); }
    .segmented button[data-status="rejected"].is-active { background: var(--rejected); }

    .field {
      display: grid;
      gap: 6px;
    }

    .field label {
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .field select,
    .field textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: white;
      padding: 10px;
      color: var(--ink);
    }

    .field textarea {
      min-height: 88px;
      resize: vertical;
      line-height: 1.5;
    }

    .save-state {
      min-height: 18px;
      color: var(--muted);
      font-size: 12px;
    }

    @media (max-width: 1120px) {
      .app,
      .workspace {
        grid-template-columns: 1fr;
      }

      .sidebar {
        min-height: auto;
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }

      .folder-list {
        max-height: 280px;
      }

      .detail {
        border-left: 0;
        border-top: 1px solid var(--line);
      }

      .preview img {
        max-height: 58vh;
      }
    }

    @media (max-width: 640px) {
      .totals,
      .segmented {
        grid-template-columns: repeat(2, 1fr);
      }

      .topbar {
        align-items: stretch;
        flex-direction: column;
      }

      .toolbar {
        width: 100%;
      }

      .toolbar select,
      .toolbar button {
        flex: 1;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <header class="brand">
        <h1>Zy Curation</h1>
        <div class="source" id="sourcePath"></div>
      </header>
      <section class="totals" aria-label="整体统计">
        <div class="total"><span>All</span><strong id="totalAll">0</strong></div>
        <div class="total"><span>In</span><strong id="totalSelected">0</strong></div>
        <div class="total"><span>Maybe</span><strong id="totalMaybe">0</strong></div>
        <div class="total"><span>Out</span><strong id="totalRejected">0</strong></div>
      </section>
      <nav class="folder-list" id="folderList" aria-label="照片文件夹"></nav>
      <footer class="side-footer" id="draftPath"></footer>
    </aside>

    <main class="main">
      <header class="topbar">
        <div class="current-title">
          <h2 id="folderTitle">选择文件夹</h2>
          <p id="folderMeta">0 张</p>
        </div>
        <div class="toolbar">
          <select id="statusFilter" aria-label="按状态筛选">
            <option value="all">全部状态</option>
            <option value="unreviewed">未筛</option>
            <option value="selected">入选</option>
            <option value="maybe">备选</option>
            <option value="rejected">淘汰</option>
          </select>
          <button id="refreshButton" type="button">刷新</button>
        </div>
      </header>

      <section class="workspace">
        <div class="grid-wrap">
          <div class="photo-grid" id="photoGrid"></div>
        </div>
        <aside class="detail">
          <div class="preview" id="preview">
            <div class="empty">No photo selected</div>
          </div>
          <form class="editor" id="editor">
            <div>
              <div class="filename" id="photoName">未选择</div>
              <div class="filemeta" id="photoMeta"></div>
            </div>
            <div class="segmented" aria-label="筛选状态">
              <button type="button" data-status="unreviewed">未筛</button>
              <button type="button" data-status="selected">入选</button>
              <button type="button" data-status="maybe">备选</button>
              <button type="button" data-status="rejected">淘汰</button>
            </div>
            <div class="field">
              <label for="seriesSelect">Series</label>
              <select id="seriesSelect"></select>
            </div>
            <div class="field">
              <label for="noteInput">Note</label>
              <textarea id="noteInput" placeholder="构图、颜色、入站理由或后续处理想法"></textarea>
            </div>
            <div class="save-state" id="saveState"></div>
          </form>
        </aside>
      </section>
    </main>
  </div>

  <script>
    const STATUS_LABELS = {
      unreviewed: "未筛",
      selected: "入选",
      maybe: "备选",
      rejected: "淘汰"
    };

    let appState = null;
    let activeFolder = null;
    let photos = [];
    let activeIndex = -1;
    let saveTimer = null;

    const sourcePath = document.getElementById("sourcePath");
    const draftPath = document.getElementById("draftPath");
    const totalAll = document.getElementById("totalAll");
    const totalSelected = document.getElementById("totalSelected");
    const totalMaybe = document.getElementById("totalMaybe");
    const totalRejected = document.getElementById("totalRejected");
    const folderList = document.getElementById("folderList");
    const folderTitle = document.getElementById("folderTitle");
    const folderMeta = document.getElementById("folderMeta");
    const statusFilter = document.getElementById("statusFilter");
    const refreshButton = document.getElementById("refreshButton");
    const photoGrid = document.getElementById("photoGrid");
    const preview = document.getElementById("preview");
    const editor = document.getElementById("editor");
    const photoName = document.getElementById("photoName");
    const photoMeta = document.getElementById("photoMeta");
    const seriesSelect = document.getElementById("seriesSelect");
    const noteInput = document.getElementById("noteInput");
    const saveState = document.getElementById("saveState");
    const statusButtons = [...document.querySelectorAll("[data-status]")];

    function api(path, options) {
      return fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options
      }).then(async (response) => {
        if (!response.ok) {
          const text = await response.text();
          throw new Error(text || response.statusText);
        }
        return response.json();
      });
    }

    function formatCount(stats) {
      return `${stats.total} 张 · ${stats.unreviewed} 未筛 · ${stats.selected} 入选 · ${stats.maybe} 备选 · ${stats.rejected} 淘汰`;
    }

    function renderSummary() {
      sourcePath.textContent = appState.source;
      draftPath.textContent = `Draft: ${appState.draftPath}`;
      totalAll.textContent = appState.totals.total;
      totalSelected.textContent = appState.totals.selected;
      totalMaybe.textContent = appState.totals.maybe;
      totalRejected.textContent = appState.totals.rejected;

      folderList.innerHTML = appState.folders.map((folder) => `
        <button class="folder-button ${folder.key === activeFolder ? "is-active" : ""}" type="button" data-folder="${folder.key}">
          <span class="folder-name">${folder.label}</span>
          <span class="folder-meta">
            <span>${folder.stats.total} 张</span>
            <span>${folder.stats.selected} 入选</span>
            <span>${folder.stats.maybe} 备选</span>
          </span>
        </button>
      `).join("");
    }

    function visiblePhotos() {
      const filter = statusFilter.value;
      return photos.filter((photo) => filter === "all" || photo.status === filter);
    }

    function activePhoto() {
      const visible = visiblePhotos();
      return visible[activeIndex] || null;
    }

    function renderPhotos() {
      const visible = visiblePhotos();
      photoGrid.innerHTML = visible.map((photo, index) => `
        <button class="photo-button ${index === activeIndex ? "is-active" : ""}" type="button" data-index="${index}" data-status="${photo.status}">
          <span class="status-dot" aria-hidden="true"></span>
          <span class="thumb"><img src="/api/thumb/${photo.id}.jpg" alt="${photo.fileName}" loading="lazy"></span>
          <span class="photo-name">${photo.fileName}</span>
        </button>
      `).join("");

      if (!visible.length) {
        activeIndex = -1;
      } else if (activeIndex < 0 || activeIndex >= visible.length) {
        activeIndex = 0;
      }
      renderDetail();
    }

    function setActiveIndex(index, shouldFocus = false) {
      const visible = visiblePhotos();
      if (!visible.length) {
        activeIndex = -1;
        renderDetail();
        return;
      }
      activeIndex = Math.max(0, Math.min(visible.length - 1, index));
      renderDetail();
      const button = document.querySelector(`.photo-button[data-index="${activeIndex}"]`);
      if (button) {
        button.scrollIntoView({ block: "nearest", inline: "nearest" });
        if (shouldFocus) button.focus({ preventScroll: true });
      }
    }

    function renderDetail() {
      const photo = activePhoto();
      statusButtons.forEach((button) => button.classList.remove("is-active"));
      if (!photo) {
        preview.innerHTML = '<div class="empty">No photo selected</div>';
        photoName.textContent = "未选择";
        photoMeta.textContent = "";
        noteInput.value = "";
        seriesSelect.value = "未分类";
        return;
      }

      preview.innerHTML = `<img src="/api/image/${photo.id}" alt="${photo.fileName}">`;
      photoName.textContent = photo.fileName;
      photoMeta.textContent = `${photo.width || "?"} x ${photo.height || "?"} · ${photo.orientation} · ${photo.relativePath}`;
      noteInput.value = photo.note || "";
      seriesSelect.value = photo.series || "未分类";
      const activeButton = statusButtons.find((button) => button.dataset.status === photo.status);
      if (activeButton) activeButton.classList.add("is-active");

      document.querySelectorAll(".photo-button").forEach((button) => {
        button.classList.toggle("is-active", Number(button.dataset.index) === activeIndex);
      });
    }

    function moveSelection(step) {
      const visible = visiblePhotos();
      if (!visible.length) return;
      setActiveIndex(activeIndex + step, true);
    }

    function gridColumnCount() {
      const columns = window.getComputedStyle(photoGrid).gridTemplateColumns;
      return Math.max(1, columns.split(" ").filter(Boolean).length);
    }

    async function loadSummary() {
      appState = await api("/api/summary");
      if (!activeFolder && appState.folders.length) {
        activeFolder = appState.folders[0].key;
      }
      renderSummary();
    }

    async function loadFolder(key) {
      activeFolder = key;
      activeIndex = 0;
      const data = await api(`/api/photos?folder=${encodeURIComponent(key)}`);
      photos = data.photos;
      folderTitle.textContent = data.label;
      folderMeta.textContent = formatCount(data.stats);
      renderSummary();
      renderPhotos();
    }

    async function refreshAll() {
      await loadSummary();
      if (activeFolder) {
        await loadFolder(activeFolder);
      }
    }

    function queueSave(patch) {
      const photo = activePhoto();
      if (!photo) return;
      const statusChanged = Object.prototype.hasOwnProperty.call(patch, "status");
      const seriesChanged = Object.prototype.hasOwnProperty.call(patch, "series");
      Object.assign(photo, patch);
      saveState.textContent = "Saving...";
      if (statusChanged) {
        renderPhotos();
      } else if (seriesChanged) {
        renderDetail();
      }
      clearTimeout(saveTimer);
      saveTimer = setTimeout(async () => {
        try {
          const updated = await api(`/api/photo/${photo.id}`, {
            method: "POST",
            body: JSON.stringify({
              status: photo.status,
              series: photo.series,
              note: photo.note
            })
          });
          Object.assign(photo, updated.photo);
          saveState.textContent = `Saved ${new Date().toLocaleTimeString()}`;
          await loadSummary();
          const current = appState.folders.find((folder) => folder.key === activeFolder);
          if (current) folderMeta.textContent = formatCount(current.stats);
          if (statusChanged) {
            renderPhotos();
          }
        } catch (error) {
          saveState.textContent = error.message;
        }
      }, 220);
    }

    function toggleSelected() {
      const photo = activePhoto();
      if (!photo) return;
      queueSave({ status: photo.status === "selected" ? "unreviewed" : "selected" });
    }

    folderList.addEventListener("click", (event) => {
      const target = event.target.closest("[data-folder]");
      if (target) loadFolder(target.dataset.folder);
    });

    photoGrid.addEventListener("click", (event) => {
      const target = event.target.closest("[data-index]");
      if (!target) return;
      setActiveIndex(Number(target.dataset.index), true);
    });

    statusButtons.forEach((button) => {
      button.addEventListener("click", () => queueSave({ status: button.dataset.status }));
    });

    seriesSelect.innerHTML = %SERIES_OPTIONS%;
    seriesSelect.addEventListener("change", () => queueSave({ series: seriesSelect.value }));
    noteInput.addEventListener("input", () => queueSave({ note: noteInput.value }));
    statusFilter.addEventListener("change", renderPhotos);
    refreshButton.addEventListener("click", () => window.location.reload());

    document.addEventListener("keydown", (event) => {
      if (event.target === noteInput) return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        moveSelection(-1);
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        moveSelection(1);
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        moveSelection(-gridColumnCount());
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        moveSelection(gridColumnCount());
      }
      if (event.key === " ") {
        event.preventDefault();
        toggleSelected();
      }
      if (event.key === "1") queueSave({ status: "selected" });
      if (event.key === "2") queueSave({ status: "maybe" });
      if (event.key === "3") queueSave({ status: "rejected" });
      if (event.key === "0") queueSave({ status: "unreviewed" });
    });

    refreshAll().catch((error) => {
      folderTitle.textContent = "启动失败";
      folderMeta.textContent = error.message;
    });
  </script>
</body>
</html>
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def image_orientation(width: int, height: int) -> str:
    if not width or not height:
        return "unknown"
    ratio = width / height
    if ratio > 2:
        return "panorama"
    if ratio > 1.08:
        return "landscape"
    if ratio < 0.92:
        return "portrait"
    return "square"


def is_ignored(path: Path, source: Path) -> bool:
    try:
        rel = path.relative_to(source)
    except ValueError:
        return True
    if any(part == "视频素材" for part in rel.parts):
        return True
    lowered = path.name.lower()
    return "联系表" in path.name or "contactsheet" in lowered or "contact sheet" in lowered


def stable_id(path: Path) -> str:
    return hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:16]


class CurationStore:
    def __init__(self, source: Path, curation_dir: Path = CURATION_DIR) -> None:
        self.source = source.expanduser().resolve()
        self.curation_dir = curation_dir
        self.draft_path = curation_dir / "selection-draft.json"
        self.thumb_dir = curation_dir / "thumbs"
        self.entries: dict[str, dict] = {}
        self.photos_by_id: dict[str, dict] = {}
        self.folders: dict[str, list[dict]] = {}
        self.load_draft()
        self.scan()

    def load_draft(self) -> None:
        if not self.draft_path.exists():
            self.entries = {}
            return
        payload = json.loads(self.draft_path.read_text(encoding="utf-8"))
        items = payload.get("photos", []) if isinstance(payload, dict) else []
        self.entries = {item["sourcePath"]: item for item in items if item.get("sourcePath")}

    def save_draft(self) -> None:
        self.curation_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "source": str(self.source),
            "updatedAt": now_iso(),
            "photos": sorted(self.entries.values(), key=lambda item: item["sourcePath"]),
        }
        self.draft_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def scan(self) -> None:
        if not self.source.exists():
            raise FileNotFoundError(f"Source folder does not exist: {self.source}")

        photos: list[dict] = []
        for path in sorted(self.source.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            if is_ignored(path, self.source):
                continue
            photo = self.photo_record(path)
            photos.append(photo)

        self.photos_by_id = {photo["id"]: photo for photo in photos}
        self.folders = {}
        for photo in photos:
            self.folders.setdefault(photo["folderKey"], []).append(photo)

    def photo_record(self, path: Path) -> dict:
        source_path = str(path)
        entry = self.entries.get(source_path, {})
        width = entry.get("width", 0)
        height = entry.get("height", 0)
        rel = path.relative_to(self.source)
        parent = rel.parent.as_posix()
        folder_key = "." if parent == "." else parent
        status = entry.get("status", "unreviewed")
        if status not in STATUSES:
            status = "unreviewed"
        series = entry.get("series", "未分类")
        if series not in SERIES:
            series = "未分类"
        return {
            "id": stable_id(path),
            "sourcePath": source_path,
            "relativePath": rel.as_posix(),
            "fileName": path.name,
            "folderKey": folder_key,
            "width": width,
            "height": height,
            "orientation": image_orientation(width, height),
            "status": status,
            "series": series,
            "note": entry.get("note", ""),
            "updatedAt": entry.get("updatedAt", ""),
        }

    @staticmethod
    def read_size(path: Path) -> tuple[int, int]:
        try:
            with Image.open(path) as image:
                image = ImageOps.exif_transpose(image)
                return image.size
        except Exception:
            return 0, 0

    def folder_label(self, key: str) -> str:
        return "根目录" if key == "." else key

    def stats(self, photos: list[dict]) -> dict:
        result = {status: 0 for status in STATUSES}
        for photo in photos:
            result[photo["status"]] += 1
        result["total"] = len(photos)
        return result

    def summary(self) -> dict:
        all_photos = list(self.photos_by_id.values())
        folder_items = []
        for key, photos in sorted(self.folders.items(), key=lambda item: (item[0] != ".", item[0].lower())):
            folder_items.append({
                "key": key,
                "label": self.folder_label(key),
                "stats": self.stats(photos),
            })
        return {
            "source": str(self.source),
            "draftPath": str(self.draft_path),
            "totals": self.stats(all_photos),
            "folders": folder_items,
            "series": SERIES,
            "statuses": STATUSES,
        }

    def photos_for_folder(self, key: str) -> dict:
        photos = self.folders.get(key, [])
        return {
            "key": key,
            "label": self.folder_label(key),
            "stats": self.stats(photos),
            "photos": photos,
        }

    def update_photo(self, photo_id: str, patch: dict) -> dict:
        if photo_id not in self.photos_by_id:
            raise KeyError(photo_id)
        photo = self.photos_by_id[photo_id]
        status = patch.get("status", photo["status"])
        series = patch.get("series", photo["series"])
        if status not in STATUSES:
            status = "unreviewed"
        if series not in SERIES:
            series = "未分类"
        note = str(patch.get("note", photo.get("note", "")))

        photo.update({
            "status": status,
            "series": series,
            "note": note,
            "updatedAt": now_iso(),
        })
        self.entries[photo["sourcePath"]] = {
            "sourcePath": photo["sourcePath"],
            "fileName": photo["fileName"],
            "relativePath": photo["relativePath"],
            "width": photo["width"],
            "height": photo["height"],
            "orientation": photo["orientation"],
            "status": photo["status"],
            "series": photo["series"],
            "note": photo["note"],
            "updatedAt": photo["updatedAt"],
        }
        self.save_draft()
        return photo

    def thumbnail_path(self, photo_id: str) -> Path:
        return self.thumb_dir / f"{photo_id}.jpg"

    def ensure_thumbnail(self, photo_id: str) -> Path:
        if photo_id not in self.photos_by_id:
            raise KeyError(photo_id)
        target = self.thumbnail_path(photo_id)
        if target.exists():
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        photo = self.photos_by_id[photo_id]
        source = Path(photo["sourcePath"])
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            photo["width"], photo["height"] = image.size
            photo["orientation"] = image_orientation(photo["width"], photo["height"])
            image.thumbnail((720, 720), Image.Resampling.LANCZOS)
            image.save(target, "JPEG", quality=82, optimize=True, progressive=True)
        return target


class CurationHandler(BaseHTTPRequestHandler):
    store: CurationStore

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_text(self, text: str, content_type: str = "text/html; charset=utf-8") -> None:
        data = text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path: Path, content_type: str | None = None) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = posixpath.normpath(parsed.path)
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if path == "/" or path == "/index.html":
                options = "\n".join(f'<option value="{item}">{item}</option>' for item in SERIES)
                self.send_text(HTML.replace("%SERIES_OPTIONS%", json.dumps(options)))
            elif path == "/api/summary":
                self.send_json(self.store.summary())
            elif path == "/api/photos":
                key = query.get("folder", ["."])[0]
                self.send_json(self.store.photos_for_folder(key))
            elif path.startswith("/api/thumb/"):
                photo_id = Path(path).stem
                self.send_file(self.store.ensure_thumbnail(photo_id), "image/jpeg")
            elif path.startswith("/api/image/"):
                photo_id = path.rsplit("/", 1)[-1]
                photo = self.store.photos_by_id.get(photo_id)
                if not photo:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self.send_file(Path(photo["sourcePath"]))
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as error:
            self.send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_HEAD(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = posixpath.normpath(parsed.path)
        if path == "/" or path == "/index.html":
            data = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = posixpath.normpath(parsed.path)
        if not path.startswith("/api/photo/"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(raw or "{}")
            photo_id = path.rsplit("/", 1)[-1]
            photo = self.store.update_photo(photo_id, payload)
            self.send_json({"photo": photo})
        except Exception as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)


def run(source: Path, curation_dir: Path, host: str, port: int) -> None:
    store = CurationStore(source, curation_dir)
    CurationHandler.store = store
    server = ThreadingHTTPServer((host, port), CurationHandler)
    url = f"http://{host}:{port}/"
    print(f"Zy curation workbench")
    print(f"Source: {store.source}")
    print(f"Draft:  {store.draft_path}")
    print(f"Open:   {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the local Zy photo curation workbench.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="Photo folder to scan.")
    parser.add_argument("--curation-dir", default=str(CURATION_DIR), help="Folder for local draft and thumbnail cache.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind.")
    args = parser.parse_args()
    run(Path(args.source), Path(args.curation_dir), args.host, args.port)


if __name__ == "__main__":
    main()
