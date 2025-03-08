from PIL import Image, ImageDraw
import os

# 确保资源目录存在
os.makedirs('resources', exist_ok=True)

# 创建Windows图标
icon_size = (256, 256)
icon = Image.new('RGBA', icon_size, color=(255, 255, 255, 0))
draw = ImageDraw.Draw(icon)

# 绘制一个简单的PDF图标
# 背景矩形
draw.rectangle([(50, 30), (206, 226)], fill=(220, 220, 220), outline=(100, 100, 100), width=2)
# PDF文字
draw.text((90, 120), "PDF", fill=(200, 50, 50), width=5)
# 折角
draw.polygon([(206, 30), (206, 70), (166, 30)], fill=(180, 180, 180), outline=(100, 100, 100), width=2)

# 保存为Windows图标
icon.save('resources/app_icon.ico', format='ICO')
print("Windows图标已创建: resources/app_icon.ico")

# 保存为PNG (可以在macOS上转换为icns)
icon.save('resources/app_icon.png', format='PNG')
print("PNG图标已创建: resources/app_icon.png") 