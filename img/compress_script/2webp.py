import os
from PIL import Image

# 支持的输入格式
image_extensions = ('.jpg', '.jpeg', '.png')

# 遍历当前目录下所有文件
for filename in os.listdir('.'):
    if filename.lower().endswith(image_extensions):
        try:
            # 打开图像
            with Image.open(filename) as img:
                # 构造输出文件名
                webp_name = os.path.splitext(filename)[0] + '.webp'
                # 转换为RGB（防止P图透明图失败）
                img = img.convert('RGB')
                # 保存为webp格式
                img.save(webp_name, 'webp')
                print(f"✅ 转换完成: {filename} -> {webp_name}")
        except Exception as e:
            print(f"⚠️ 转换失败: {filename}, 错误信息: {e}")

