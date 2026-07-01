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

1. 把原图放入 `Photos/`
2. 运行 `tools/prepare-photos.py` 生成网页图和缩略图
3. 检查 `assets/photo-data.js` 里的草稿条目
4. 补齐标题、系列、年份和 `alt`
5. 打开 `index.html` 检查页面

示例：

```bash
python3 tools/prepare-photos.py your-photo.jpg
```

如果不传文件名，工具会处理 `Photos/` 里的所有图片。

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
- 如果正式发布到线上，建议再次检查数据文件中的 `cameraMeta`，只保留愿意公开的信息。
