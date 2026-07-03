# Zy 摄影作品集交接

## 当前入口

以 `index.html` 为主入口。它是一个纯静态页面，可以通过本地预览服务打开，也可以在多数浏览器里直接双击打开。

`ge-photo-archive-home.html` 是迁移前的原型备份，不再作为主入口维护。

## 当前结构

```text
index.html
assets/
  photo-data.js          <- 作品数据
  photos/                <- 网页展示图
    thumbs/              <- 缩略图
Photos/                  <- 原图和候选照片
tools/
  prepare-photos.py      <- 新增照片导入工具
  curate-photos.py       <- 本地选片工作台
```

## 页面数据

页面不再把作品数组写在 HTML 里，而是读取：

```text
assets/photo-data.js
```

每张作品包含：

- `id`
- `title`
- `series`
- `year`
- `image`
- `thumb`
- `alt`
- `orientation`
- `featured`
- `cameraMeta`

作品卡默认只显示标题、系列和年份；`cameraMeta` 暂时只在完整查看里显示。

## 新增照片流程

1. 先用 `tools/curate-photos.py` 从 Lightroom 文件夹筛选照片
2. 确认 `.curation/selection-draft.json` 里的入选项
3. 运行 `tools/prepare-photos.py --from-curation .curation/selection-draft.json` 生成网页图、缩略图和主站数据
4. 检查 `assets/photo-data.js` 里的草稿条目
5. 补齐标题、系列、年份和 `alt`
6. 打开 `index.html` 检查页面

示例：

```bash
python3 tools/curate-photos.py --source /Users/zy/Desktop/Lightroom
python3 tools/prepare-photos.py --from-curation .curation/selection-draft.json
```

选片工作台里，单击照片只会移动选框并在右侧预览；在当前照片上按空格会在“入选/未筛”之间切换。方向键可在网格里移动选框，数字键 `1`/`2`/`3`/`0` 分别设为入选/备选/淘汰/未筛。右上角“刷新”会重新加载本地工作台页面。

导入命令默认只导入草稿里状态为 `selected` 的照片；不会把本地原图路径写入公开的 `assets/photo-data.js`。如果不传 `--from-curation` 和文件名，工具会处理 `Photos/` 里的所有图片。

## 当前首轮作品

当前页面使用了 `Photos/` 中筛出的 14 张照片，并生成到 `assets/photos/zy-*.jpg` 和 `assets/photos/thumbs/zy-*.jpg`。

系列包括：

- 天象
- 边缘光
- 山线
- 水边
- 微观

## 注意

- 不要直接让页面引用 `Photos/` 里的原图，网页应使用 `assets/photos/` 下的压缩图。
- `Photos/` 作为候选库保留，新增或替换作品时只改数据文件和生成后的网页图。
- `.curation/` 是本地选片草稿和缩略图缓存，不进入 git。
- 如果正式发布到线上，建议再次检查数据文件中的 `cameraMeta`，只保留愿意公开的信息。
