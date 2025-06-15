import os
from PIL import Image, ExifTags
from collections import defaultdict, Counter
import matplotlib.pyplot as plt

# 提取焦距和光圈
def extract_focal_and_aperture(img_path):
    try:
        img = Image.open(img_path)
        exif_data = img._getexif()
        if not exif_data:
            return None, None

        exif = {
            ExifTags.TAGS.get(k, k): v
            for k, v in exif_data.items()
        }

        # 焦距（优先等效35mm）
        focal = exif.get('FocalLengthIn35mmFilm')
        if not focal:
            raw_focal = exif.get('FocalLength')
            if isinstance(raw_focal, tuple):
                focal = round(raw_focal[0] / raw_focal[1])
            elif raw_focal:
                focal = round(raw_focal)

        # 光圈 FNumber
        aperture = exif.get('FNumber')
        if isinstance(aperture, tuple):
            aperture = round(aperture[0] / aperture[1], 1)
        elif aperture:
            aperture = round(aperture, 1)

        return focal, aperture

    except Exception as e:
        print(f"Error reading {img_path}: {e}")
        return None, None

# 遍历根目录和所有子目录
def analyze_folder_recursive(folder_path):
    stats = defaultdict(Counter)

    for root, _, files in os.walk(folder_path):
        for filename in files:
            if filename.lower().endswith((".jpg", ".jpeg")):
                path = os.path.join(root, filename)
                focal, aperture = extract_focal_and_aperture(path)
                if focal and aperture:
                    stats[focal][aperture] += 1

    return stats

# 绘制堆叠柱状图
def plot_stacked_bars(stats):
    focal_lengths = sorted(stats.keys())
    all_apertures = sorted({a for f in stats for a in stats[f]})

    # 构建堆叠数据
    stacked_values = {a: [] for a in all_apertures}
    for f in focal_lengths:
        for a in all_apertures:
            stacked_values[a].append(stats[f].get(a, 0))

    # 绘图
    bottom = [0] * len(focal_lengths)
    plt.figure(figsize=(12, 6))
    for a in all_apertures:
        plt.bar(focal_lengths, stacked_values[a], bottom=bottom, label=f"f/{a}")
        bottom = [i + j for i, j in zip(bottom, stacked_values[a])]

    plt.xlabel("Focal Length (35mm Equivalent)")
    plt.ylabel("Number of Photos")
    plt.title("Focal Length & Aperture Distribution")
    plt.legend(title="Aperture (f/)", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.show()

# 主函数
if __name__ == "__main__":
    # ✏️ 在这里直接修改你的照片根目录路径
    folder_path = "/Volumes/T7 Shield/Syndisk/Life/Photograph/202404_pamier"  # ← 请替换成你的本地路径

    stats = analyze_folder_recursive(folder_path)
    if stats:
        plot_stacked_bars(stats)
    else:
        print("No valid EXIF data found.")
