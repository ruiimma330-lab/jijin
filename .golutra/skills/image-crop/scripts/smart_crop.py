#!/usr/bin/env python3
"""
smart_crop.py - 智能图片裁剪工具
支持单图/批量裁剪，多种比例和裁剪模式

用法：
  python smart_crop.py photo.jpg --ratio 1:1
  python smart_crop.py ./photos/ --ratio 16:9 --mode smart --output ./cropped/
"""

import sys
import argparse
from pathlib import Path

try:
    from PIL import Image, ImageFilter, ImageOps
except ImportError:
    print("❌ 缺少依赖，请运行：pip install Pillow")
    sys.exit(1)

SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}

PRESET_RATIOS = {
    '1:1':  (1, 1),
    '16:9': (16, 9),
    '9:16': (9, 16),
    '4:3':  (4, 3),
    '3:4':  (3, 4),
    '2:3':  (2, 3),
    '3:2':  (3, 2),
    '21:9': (21, 9),
    'a4':   (210, 297),   # 竖向 A4
    'a4l':  (297, 210),   # 横向 A4
}


def parse_ratio(ratio_str):
    """解析比例字符串，返回 (w, h)"""
    s = ratio_str.lower().strip()
    if s in PRESET_RATIOS:
        return PRESET_RATIOS[s]
    if ':' in s:
        parts = s.split(':')
        return (float(parts[0]), float(parts[1]))
    raise ValueError(f"无法识别的比例：{ratio_str}，支持格式如 16:9 或预设值 {list(PRESET_RATIOS)}")


def parse_size(size_str):
    """解析尺寸字符串 'WxH'，返回 (w, h)"""
    s = size_str.lower().strip()
    if 'x' in s:
        w, h = s.split('x', 1)
        return (int(w), int(h))
    raise ValueError(f"无法识别的尺寸：{size_str}，请使用 800x600 格式")


def center_crop_box(img_w, img_h, ratio_w, ratio_h):
    """居中裁剪框"""
    if (img_w / img_h) > (ratio_w / ratio_h):
        # 图片更宽，裁左右
        new_w = int(img_h * ratio_w / ratio_h)
        left = (img_w - new_w) // 2
        return (left, 0, left + new_w, img_h)
    else:
        # 图片更高，裁上下
        new_h = int(img_w * ratio_h / ratio_w)
        top = (img_h - new_h) // 2
        return (0, top, img_w, top + new_h)


def top_crop_box(img_w, img_h, ratio_w, ratio_h):
    """顶部对齐裁剪框（适合人像，保留头部）"""
    if (img_w / img_h) > (ratio_w / ratio_h):
        new_w = int(img_h * ratio_w / ratio_h)
        left = (img_w - new_w) // 2
        return (left, 0, left + new_w, img_h)
    else:
        new_h = int(img_w * ratio_h / ratio_w)
        return (0, 0, img_w, new_h)


def smart_crop_box(img, ratio_w, ratio_h):
    """
    基于边缘信息量的智能裁剪框。
    在滑动窗口中找到边缘像素总和最大的区域。
    """
    img_w, img_h = img.size
    gray = img.convert('L')
    edges = gray.filter(ImageFilter.FIND_EDGES)

    if (img_w / img_h) > (ratio_w / ratio_h):
        # 横向裁剪：找最优 x 起点
        crop_w = int(img_h * ratio_w / ratio_h)
        if crop_w >= img_w:
            return (0, 0, img_w, img_h)
        step = max(1, (img_w - crop_w) // 30)
        best_x, best_score = 0, -1
        for x in range(0, img_w - crop_w + 1, step):
            region = edges.crop((x, 0, x + crop_w, img_h))
            score = sum(region.getdata())
            if score > best_score:
                best_score, best_x = score, x
        return (best_x, 0, best_x + crop_w, img_h)
    else:
        # 纵向裁剪：找最优 y 起点
        crop_h = int(img_w * ratio_h / ratio_w)
        if crop_h >= img_h:
            return (0, 0, img_w, img_h)
        step = max(1, (img_h - crop_h) // 30)
        best_y, best_score = 0, -1
        for y in range(0, img_h - crop_h + 1, step):
            region = edges.crop((0, y, img_w, y + crop_h))
            score = sum(region.getdata())
            if score > best_score:
                best_score, best_y = score, y
        return (0, best_y, img_w, best_y + crop_h)


def crop_image(input_path, output_path, ratio=None, size=None, mode='center', quality=95):
    """
    裁剪单张图片并保存。

    Args:
        input_path:  输入图片路径
        output_path: 输出图片路径
        ratio:       目标比例 (w, h)，与 size 二选一
        size:        精确输出尺寸 (w, h)，优先于 ratio
        mode:        裁剪模式 center / top / smart
        quality:     JPEG 输出质量

    Returns:
        输出图片的实际尺寸 (w, h)
    """
    img = Image.open(input_path)

    # 修正 EXIF 旋转方向
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    img_w, img_h = img.size

    # 确定裁剪比例
    if size:
        ratio_w, ratio_h = size
    elif ratio:
        ratio_w, ratio_h = ratio
    else:
        ratio_w, ratio_h = 1, 1

    # 计算裁剪框
    if mode == 'smart':
        box = smart_crop_box(img, ratio_w, ratio_h)
    elif mode == 'top':
        box = top_crop_box(img_w, img_h, ratio_w, ratio_h)
    else:
        box = center_crop_box(img_w, img_h, ratio_w, ratio_h)

    cropped = img.crop(box)

    # 若指定了精确尺寸则缩放
    if size:
        cropped = cropped.resize(size, Image.LANCZOS)

    # 保存
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ext = output_path.suffix.lower()
    if ext in ('.jpg', '.jpeg'):
        if cropped.mode in ('RGBA', 'LA', 'P'):
            cropped = cropped.convert('RGB')
        cropped.save(output_path, 'JPEG', quality=quality)
    elif ext == '.png':
        cropped.save(output_path, 'PNG')
    elif ext == '.webp':
        cropped.save(output_path, 'WEBP', quality=quality)
    else:
        cropped.save(output_path)

    return cropped.size


def main():
    parser = argparse.ArgumentParser(
        description='智能图片裁剪工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  %(prog)s photo.jpg                          # 1:1 居中裁剪
  %(prog)s photo.jpg --ratio 16:9             # 16:9 居中裁剪
  %(prog)s photo.jpg --size 1080x1920         # 精确尺寸
  %(prog)s photo.jpg --mode top               # 顶部对齐（人像）
  %(prog)s photo.jpg --mode smart             # 智能裁剪
  %(prog)s ./photos/ --ratio 4:3 -o ./out/   # 批量裁剪
        """
    )
    parser.add_argument('input', help='输入图片路径或包含图片的文件夹')
    parser.add_argument('--ratio', '-r', default='1:1',
                        help='裁剪比例，如 16:9 / 1:1 / 4:3 / 9:16（默认 1:1）')
    parser.add_argument('--size', '-s',
                        help='精确输出尺寸，如 1080x1080（会覆盖 --ratio）')
    parser.add_argument('--mode', '-m', choices=['center', 'top', 'smart'],
                        default='center',
                        help='裁剪模式：center 居中 / top 顶部 / smart 智能（默认 center）')
    parser.add_argument('--output', '-o', default='./cropped',
                        help='输出目录（默认 ./cropped）')
    parser.add_argument('--quality', '-q', type=int, default=95,
                        help='JPEG 输出质量 1-100（默认 95）')

    args = parser.parse_args()

    # 解析尺寸 / 比例
    size = None
    ratio = None
    if args.size:
        try:
            size = parse_size(args.size)
        except ValueError as e:
            print(f"❌ {e}")
            sys.exit(1)
    else:
        try:
            ratio = parse_ratio(args.ratio)
        except ValueError as e:
            print(f"❌ {e}")
            sys.exit(1)

    input_path = Path(args.input)
    output_dir = Path(args.output)

    if not input_path.exists():
        print(f"❌ 找不到输入路径：{input_path}")
        sys.exit(1)

    # 收集图片文件
    if input_path.is_dir():
        files = sorted([f for f in input_path.iterdir()
                        if f.suffix.lower() in SUPPORTED_FORMATS])
    else:
        files = [input_path]

    if not files:
        print(f"❌ 未找到支持的图片（{', '.join(SUPPORTED_FORMATS)}）")
        sys.exit(1)

    ratio_display = args.size if args.size else args.ratio
    print(f"📁 找到 {len(files)} 张图片")
    print(f"✂️  目标：{ratio_display}  模式：{args.mode}")
    print(f"📂 输出：{output_dir.resolve()}")
    print()

    success = 0
    for f in files:
        try:
            ext = f.suffix.lower()
            out_ext = ext if ext in ('.png', '.webp') else '.jpg'
            out_file = output_dir / f"{f.stem}_cropped{out_ext}"

            final_size = crop_image(
                f, out_file,
                ratio=ratio, size=size,
                mode=args.mode, quality=args.quality
            )
            print(f"  ✅ {f.name}  →  {out_file.name}  ({final_size[0]}×{final_size[1]})")
            success += 1
        except Exception as e:
            print(f"  ❌ {f.name}  失败：{e}")

    print()
    print(f"✨ 完成！成功裁剪 {success}/{len(files)} 张")
    print(f"📂 输出目录：{output_dir.resolve()}")

    if success > 0:
        print()
        print("💡 配合 canvas-design 制作海报：")
        print(f"   告诉 Claude：'用 canvas-design 制作海报，将 {output_dir} 里的裁剪图片用 Image.open() 嵌入画布'")


if __name__ == '__main__':
    main()
