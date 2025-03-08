#!/usr/bin/env python3
"""
在Mac上将PNG图标转换为icns格式
需要在Mac上运行此脚本
"""
import os
import subprocess

def convert_png_to_icns(png_file, output_icns):
    """将PNG图标转换为icns格式"""
    # 创建临时图标集文件夹
    iconset_dir = 'app.iconset'
    os.makedirs(iconset_dir, exist_ok=True)
    
    # 定义不同尺寸的图标
    icon_sizes = [
        (16, 16), (32, 32), (64, 64), (128, 128), (256, 256), 
        (512, 512), (1024, 1024)
    ]
    
    # 生成不同尺寸的图标
    for size in icon_sizes:
        output_file = f"{iconset_dir}/icon_{size[0]}x{size[1]}.png"
        subprocess.run(['sips', '-z', str(size[0]), str(size[1]), png_file, '--out', output_file])
        
        # 为Retina显示器创建@2x版本
        if size[0] <= 512:
            output_file_2x = f"{iconset_dir}/icon_{size[0]}x{size[1]}@2x.png"
            subprocess.run(['sips', '-z', str(size[0]*2), str(size[1]*2), png_file, '--out', output_file_2x])
    
    # 使用iconutil将iconset转换为icns
    subprocess.run(['iconutil', '-c', 'icns', iconset_dir, '-o', output_icns])
    
    # 清理临时文件
    subprocess.run(['rm', '-rf', iconset_dir])
    
    print(f"已成功创建icns图标: {output_icns}")

if __name__ == "__main__":
    # 确保资源目录存在
    os.makedirs('resources', exist_ok=True)
    
    # 转换图标
    convert_png_to_icns('resources/app_icon.png', 'resources/app_icon.icns') 