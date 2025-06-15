import os
from PIL import Image, ExifTags
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import numpy as np  # 用于颜色渐变计算

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

        # 获取相机型号（从TIFF标签中读取）
        make = exif.get('Make', '').strip()  # 制造商
        model = exif.get('Model', '').strip()  # 型号

        # 根据相机型号确定转换系数
        if 'Canon' in make and 'EOS M' in model:
            crop_factor = 1.6  # Canon APS-C
        elif 'FUJIFILM' in make and 'X-T' in model:
            crop_factor = 1.5  # Fuji APS-C
        else:
            crop_factor = 1.0  # 全画幅或其他

        # 获取焦距（优先35mm等效）
        focal = exif.get('FocalLengthIn35mmFilm')
        # 如果是Canon相机且没有35mm等效焦距，则手动换算
        if crop_factor > 1.0 and not focal:  # 如果是APS-C相机且没有35mm等效焦距
            raw_focal = exif.get('FocalLength')
            if isinstance(raw_focal, tuple):
                focal = round((raw_focal[0] / raw_focal[1]) * crop_factor)
            elif raw_focal:
                focal = round(raw_focal * crop_factor)
        # 如果是Fuji相机，直接使用FocalLengthIn35mmFilm
        elif not focal:
            raw_focal = exif.get('FocalLength')
            if isinstance(raw_focal, tuple):
                focal = round(raw_focal[0] / raw_focal[1])
            elif raw_focal:
                focal = round(raw_focal)

        # 限制焦距在15-200范围内
        if focal:
            if focal < 15:
                focal = 15
            elif focal > 200:
                focal = 200

        # 获取光圈
        aperture = exif.get('FNumber')
        if isinstance(aperture, tuple):
            raw_aperture = aperture[0] / aperture[1]
            # 对APS-C相机，光圈值也需要乘以转换系数
            aperture = round(raw_aperture * crop_factor, 1)
        elif aperture:
            # 对APS-C相机，光圈值也需要乘以转换系数
            aperture = round(aperture * crop_factor, 1)

        return focal, aperture

    except Exception as e:
        print(f"Error reading {img_path}: {e}")
        return None, None

# 遍历根目录和所有子目录
def analyze_folder_recursive(folder_path):
    stats = defaultdict(Counter)

    for root, _, files in os.walk(folder_path):
        for filename in files:
            if filename.startswith("._"):
                continue  # 跳过 macOS 资源分叉文件
            if filename.lower().endswith((".jpg", ".jpeg")):
                path = os.path.join(root, filename)
                focal, aperture = extract_focal_and_aperture(path)
                if not focal or not aperture:
                    continue  # 缺少必要 EXIF 信息，跳过
                stats[focal][aperture] += 1

    return stats

# 绘制堆叠柱状图
def plot_stacked_bars(stats):
    focal_lengths = sorted(stats.keys())
    # 定义标准光圈值列表（从f1.4到f16）
    standard_apertures = [1.4, 2.0, 2.8, 4.0, 5.6, 8.0, 11.0, 16.0]

    # 处理光圈值，限制在f1.4到f16范围内
    processed_stats = defaultdict(Counter)
    for focal, apertures in stats.items():
        for aperture, count in apertures.items():
            # 将光圈值限制在范围内
            if aperture < 1.4:
                processed_aperture = 1.4
            elif aperture > 16.0:
                processed_aperture = 16.0
            else:
                # 找到最接近的标准光圈值
                processed_aperture = min(standard_apertures, key=lambda x: abs(x - aperture))
            processed_stats[focal][processed_aperture] += count

    # 使用处理后的统计数据
    stats = processed_stats
    all_apertures = standard_apertures

    # 构建堆叠数据
    stacked_values = {a: [] for a in all_apertures}
    for f in focal_lengths:
        for a in all_apertures:
            stacked_values[a].append(stats[f].get(a, 0))

    # 绘图
    bottom = [0] * len(focal_lengths)
    plt.figure(figsize=(12, 6))

    # 为每个光圈值设置固定的颜色
    aperture_colors = {
        1.4: '#8E44AD',  # 优雅紫
        2.0: '#E84393',  # 玫瑰粉
        2.8: '#E67E22',  # 暖橙色
        4.0: '#27AE60',  # 翠绿色
        5.6: '#3498DB',  # 天蓝色
        8.0: '#1A5F7A',  # 深邃蓝
        11.0: '#2C3E50',  # 深青灰
        16.0: '#7F8C8D'   # 高级灰
    }

    for idx, a in enumerate(all_apertures):
        plt.bar(
            focal_lengths,
            stacked_values[a],
            bottom=bottom,
            color=aperture_colors[a],
            label=f"f/{a:.1f}",
            width=1,  # 增加柱子宽度
        )
        bottom = [i + j for i, j in zip(bottom, stacked_values[a])]

    plt.xlabel("Focal Length")
    plt.ylabel("Number of Photos")
    # 从路径中提取文件夹名称
    folder_name = os.path.basename(folder_path)
    plt.title(f"{folder_name}_analysis")
    # 固定横坐标为常见定焦焦距值
    plt.xticks([15, 20, 24, 28, 35, 50, 85, 100, 135, 200])
    plt.legend(title="Aperture", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    # 保存图表，文件名与title相同
    plt.savefig(f"{folder_name}_analysis.png", dpi=300, bbox_inches='tight')
    plt.close()  # 关闭图表，释放内存

# 主函数
if __name__ == "__main__":
    # # ✏️ 在这里直接修改你的照片根目录路径
    # folder_path = "/Volumes/T7 Shield/Syndisk/Life/Photograph/202404_pamier"  # ← 请替换成你的本地路径
    # stats = analyze_folder_recursive(folder_path)
    # if stats:
    #     plot_stacked_bars(stats)
    # else:
    #     print("No valid EXIF data found.")


    # 要处理的文件夹列表
    folders = [
        "2021",
        "2024_campus",
        "202402_yunnan",
        "202406_graduation",
        "202404_pamier",
        "2024_Thanksgiving"
    ]

    # 基础路径
    base_path = "/Volumes/T7 Shield/Syndisk/Life/Photograph"

    # 处理每个文件夹
    for folder in folders:
        folder_path = os.path.join(base_path, folder)
        print(f"\n处理文件夹: {folder}")
        stats = analyze_folder_recursive(folder_path)
        if stats:
            plot_stacked_bars(stats)
        else:
            print(f"文件夹 {folder} 中没有找到有效的EXIF数据")
