#!/usr/bin/env python3
"""图片压缩与格式转换工具

用法:
    compress.py compress <文件或目录>...        # 压缩图片
    compress.py webp <文件或目录>...            # 转 WebP（变小删原文件，变大跳过）
    compress.py compress webp <文件或目录>...   # 压缩 + 转 WebP

选项:
    --quality N   压缩质量 1-100（默认 80）
    --force       强制覆盖已存在的 WebP

示例:
    compress.py compress .                     # 压缩当前目录
    compress.py compress photo.jpg             # 压缩单张图片
    compress.py compress *.jpg img/            # 文件和目录混传
    compress.py webp --quality 90 *.png        # 指定质量转 WebP
    compress.py compress webp .                # 压缩 + 转 WebP
"""

from PIL import Image
import os, sys, hashlib, logging

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RECORD_FILE = os.path.join(SCRIPT_DIR, ".compressed")
IMAGE_EXTS = (".jpg", ".jpeg", ".png")
ACTIONS = ("compress", "webp")


def file_hash(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_records():
    records = {}
    if not os.path.exists(RECORD_FILE):
        return records
    with open(RECORD_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split("  ", 1)
                if len(parts) == 2:
                    records[os.path.abspath(parts[1])] = parts[0]
    return records


def save_records(records):
    with open(RECORD_FILE, "w", encoding="utf-8") as f:
        f.write("# auto-generated, do not edit\n")
        for path, h in sorted(records.items()):
            f.write(f"{h}  {path}\n")


def fmt_size(b):
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.2f}{u}"
        b /= 1024
    return f"{b:.2f}TB"


def expand_targets(paths):
    """展开文件和目录为去重后的图片列表"""
    seen = set()
    images = []
    for p in paths:
        p = os.path.abspath(p)
        if os.path.isdir(p):
            for f in sorted(os.listdir(p)):
                fp = os.path.join(p, f)
                if f.lower().endswith(IMAGE_EXTS) and fp not in seen:
                    seen.add(fp)
                    images.append(fp)
        elif os.path.isfile(p):
            if p.lower().endswith(IMAGE_EXTS):
                if p not in seen:
                    seen.add(p)
                    images.append(p)
            else:
                logging.warning(f"跳过非图片文件：{os.path.basename(p)}")
        else:
            logging.warning(f"路径不存在：{p}")
    return images


def compress_image(filepath, quality=80):
    """压缩图片。压缩后更大则保留原文件。返回是否已处理。"""
    try:
        img = Image.open(filepath)
    except Exception as e:
        logging.error(f"  无法打开：{e}")
        return False

    if img.format == "GIF":
        logging.warning(f"  跳过 GIF：{os.path.basename(filepath)}")
        return False

    tmp = filepath + ".tmp"
    try:
        fmt = (img.format or "").upper()
        if fmt in ("JPEG", "JPG"):
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(tmp, "JPEG", quality=quality, optimize=True, progressive=True)
        elif fmt == "PNG":
            if "A" in img.getbands():
                img.save(tmp, "PNG", optimize=True, compress_level=9)
            else:
                img = img.convert("RGB").quantize(method=Image.MEDIANCUT)
                img.save(tmp, "PNG", optimize=True, compress_level=9)
        else:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(tmp, optimize=True, quality=quality)

        orig, new = os.path.getsize(filepath), os.path.getsize(tmp)
        if new < orig:
            os.rename(tmp, filepath)
            logging.info(f"  ✅ {fmt_size(orig)} → {fmt_size(new)}")
        else:
            os.remove(tmp)
            logging.info(f"  ⏭ 压缩后更大，跳过")
        return True
    except Exception as e:
        logging.error(f"  压缩失败：{e}")
        if os.path.exists(tmp):
            os.remove(tmp)
        return False


def convert_to_webp(filepath, quality=80):
    """转 WebP。更小则删原文件，更大则删 WebP。返回是否保留了 WebP。"""
    try:
        img = Image.open(filepath)
    except Exception as e:
        logging.error(f"  无法打开：{e}")
        return False

    if img.format == "GIF":
        logging.warning(f"  跳过 GIF：{os.path.basename(filepath)}")
        return False

    webp = os.path.splitext(filepath)[0] + ".webp"
    try:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
        img.save(webp, "WEBP", quality=quality, method=6)

        orig, wp = os.path.getsize(filepath), os.path.getsize(webp)
        if wp < orig:
            os.remove(filepath)
            logging.info(f"  ✅ → WebP {fmt_size(orig)} → {fmt_size(wp)}，已删原文件")
            return True
        else:
            os.remove(webp)
            logging.info(f"  ⏭ WebP {fmt_size(wp)} >= 原文件 {fmt_size(orig)}，跳过")
            return False
    except Exception as e:
        logging.error(f"  WebP 转换失败：{e}")
        if os.path.exists(webp):
            os.remove(webp)
        return False


def main():
    # 解析参数：[compress] [webp] [--quality N] [--force] <文件或目录>...
    args_left = []
    quality = 80
    force = False
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--quality" and i + 1 < len(sys.argv):
            quality = int(sys.argv[i + 1])
            i += 2
        elif arg.startswith("--quality="):
            quality = int(arg.split("=", 1)[1])
            i += 1
        elif arg == "--force":
            force = True
            i += 1
        elif arg in ("--help", "-h"):
            print(__doc__.strip())
            sys.exit(0)
        else:
            args_left.append(arg)
            i += 1

    actions = [a for a in args_left if a in ACTIONS]
    paths = [a for a in args_left if a not in ACTIONS]

    if not actions:
        print("用法: compress.py compress|webp [选项] <文件或目录>...", file=sys.stderr)
        sys.exit(1)

    if not paths:
        paths = ["."]

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    images = expand_targets(paths)
    if not images:
        logging.warning("未找到图片文件")
        sys.exit(1)

    records = load_records() if "compress" in actions else {}

    logging.info(f"图片：{len(images)} 张  操作：{' + '.join(actions)}")

    stats = {"processed": 0, "compressed": 0, "webp": 0, "skip": 0}

    for fp in images:
        name = os.path.basename(fp)

        if "compress" in actions:
            if fp in records and file_hash(fp) == records[fp]:
                logging.info(f"⏭ {name}（已压缩）")
                stats["skip"] += 1
                if "webp" not in actions:
                    continue
            else:
                logging.info(f"📦 {name}")
                if compress_image(fp, quality=quality):
                    records[fp] = file_hash(fp)
                    stats["processed"] += 1

        if "webp" in actions:
            if not os.path.exists(fp):
                continue
            webp = os.path.splitext(fp)[0] + ".webp"
            if os.path.exists(webp) and not force:
                logging.info(f"⏭ {name}（WebP 已存在）")
                stats["skip"] += 1
                continue
            logging.info(f"📦 {name}")
            if convert_to_webp(fp, quality=quality):
                stats["webp"] += 1

    if "compress" in actions:
        save_records(records)

    logging.info(f"\n完成 — 处理 {stats['processed']} | WebP {stats['webp']} | 跳过 {stats['skip']}")


if __name__ == "__main__":
    main()
