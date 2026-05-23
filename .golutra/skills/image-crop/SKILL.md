---
name: image-crop
description: 智能裁剪图片，支持多种比例和模式，可批量处理。当用户需要裁剪图片、调整图片比例、批量裁图、准备海报素材时使用。裁剪结果可直接配合 canvas-design skill 制作海报。触发词：裁剪图片、crop、图片裁剪、批量裁图、海报素材、1:1/16:9/4:3 裁剪。Use when: crop image, smart crop, batch crop, resize to ratio, prepare images for poster design.
---

# 图片裁剪 Skill

智能裁剪图片，支持多种比例、模式和批量处理。裁剪结果可无缝配合 canvas-design 制作海报。

## 快速开始

```bash
# 单图裁剪（默认 1:1 居中裁剪）
python ~/.claude/skills/image-crop/scripts/smart_crop.py photo.jpg

# 指定比例
python ~/.claude/skills/image-crop/scripts/smart_crop.py photo.jpg --ratio 16:9

# 批量裁剪整个文件夹
python ~/.claude/skills/image-crop/scripts/smart_crop.py ./photos/ --ratio 4:3 --output ./cropped/

# 智能模式（自动找内容最丰富的区域）
python ~/.claude/skills/image-crop/scripts/smart_crop.py photo.jpg --ratio 1:1 --mode smart
```

## 使用步骤

### 1. 分析用户需求

询问或从上下文判断：
- 图片路径（单张文件 或 整个文件夹）
- 目标比例或尺寸（如 1:1, 16:9, 9:16, 4:3，或精确像素如 1080x1080）
- 裁剪模式（center 居中 / top 顶部对齐 / smart 智能）
- 输出目录（默认在当前目录下创建 `cropped/`）

### 2. 执行裁剪命令

```bash
python ~/.claude/skills/image-crop/scripts/smart_crop.py \
  <输入路径> \
  --ratio <比例> \
  --mode <模式> \
  --output <输出目录>
```

**所有参数：**

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--ratio` | `-r` | 裁剪比例 | `1:1` |
| `--size` | `-s` | 精确尺寸如 `1080x1080`（覆盖 ratio）| 无 |
| `--mode` | `-m` | `center` / `top` / `smart` | `center` |
| `--output` | `-o` | 输出目录 | `./cropped` |
| `--quality` | `-q` | JPEG 质量 1-100 | `95` |

**支持的比例预设：**
`1:1`、`16:9`、`9:16`、`4:3`、`3:4`、`2:3`、`3:2`、`21:9`、`a4`（竖向）、`a4l`（横向）

### 3. 查看输出结果

脚本会在输出目录生成裁剪后的图片，文件名格式为 `原文件名_cropped.jpg`。

## 裁剪模式说明

| 模式 | 适用场景 |
|------|---------|
| `center`（居中）| 通用场景，取图片正中心区域 |
| `top`（顶部对齐）| 人像照片，保留上方头部区域，从底部裁剪 |
| `smart`（智能）| 自动检测边缘信息量，找到内容最丰富的区域 |

## 与 canvas-design 结合制作海报

裁剪完成后，可以结合 canvas-design skill 将图片嵌入海报。

**第一步：裁剪图片**
```bash
python ~/.claude/skills/image-crop/scripts/smart_crop.py ./my-photos/ --ratio 3:4 --output ./poster-assets/
```

**第二步：调用 canvas-design**

告诉 Claude：
```
用 canvas-design 制作一张海报，要求把以下本地图片作为视觉主体嵌入画布：
- ./poster-assets/photo1_cropped.jpg
- ./poster-assets/photo2_cropped.jpg
在 Python 代码里用 Image.open() 加载这些图片，paste 到画布合适位置。
```

canvas-design 的 Python 代码中嵌入图片的方式：
```python
from PIL import Image

# 加载裁剪好的图片
img = Image.open("./poster-assets/photo1_cropped.jpg").convert("RGBA")

# 调整到目标尺寸并粘贴到画布
img_resized = img.resize((target_w, target_h), Image.LANCZOS)
canvas.paste(img_resized, (x, y), img_resized)
```

## 常见场景

| 场景 | 命令示例 |
|------|---------|
| 社交媒体头像 | `--ratio 1:1 --size 800x800` |
| YouTube 封面 | `--ratio 16:9` |
| 竖版海报素材 | `--ratio 9:16` |
| Instagram 方图 | `--ratio 1:1 --size 1080x1080` |
| 证件照准备 | `--ratio 3:4 --mode top` |
| 批量统一规格 | `./images/ --ratio 4:3 --output ./output/` |

## 依赖安装

```bash
pip install Pillow
```
