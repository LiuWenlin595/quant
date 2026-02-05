#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件格式转换工具
支持：txt转py、py转md、py转txt
"""

import os
import shutil
import argparse
from pathlib import Path


def convert_txt_to_py(source_dir, target_dir):
    """将txt文件转换为py文件（直接复制并重命名）"""
    source_dir = Path(source_dir)
    target_dir = Path(target_dir)
    
    # 创建目标文件夹（如果不存在）
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 统计信息
    converted_count = 0
    skipped_count = 0
    
    # 遍历源文件夹中的所有文件
    for file_path in source_dir.iterdir():
        # 只处理txt文件
        if file_path.is_file() and file_path.suffix.lower() == '.txt':
            # 生成新的文件名（将.txt改为.py）
            new_filename = file_path.stem + '.py'
            target_file_path = target_dir / new_filename
            
            # 复制文件并重命名
            try:
                shutil.copy2(file_path, target_file_path)
                print(f"✓ 已转换: {file_path.name} -> {new_filename}")
                converted_count += 1
            except Exception as e:
                print(f"✗ 转换失败: {file_path.name} - {str(e)}")
                skipped_count += 1
        elif file_path.is_file():
            # 非txt文件，跳过
            print(f"- 跳过非txt文件: {file_path.name}")
            skipped_count += 1
    
    # 输出统计信息
    print("\n" + "="*50)
    print(f"转换完成！")
    print(f"成功转换: {converted_count} 个文件")
    print(f"跳过: {skipped_count} 个文件")
    print(f"目标文件夹: {target_dir}")
    print("="*50)


def convert_py_to_md(source_dir, target_dir):
    """将py文件转换为md文件（添加代码块标记）"""
    source_dir = Path(source_dir)
    target_dir = Path(target_dir)
    
    # 创建目标文件夹（如果不存在）
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 统计信息
    converted_count = 0
    skipped_count = 0
    
    # 遍历源文件夹中的所有文件
    for file_path in source_dir.iterdir():
        # 只处理py文件
        if file_path.is_file() and file_path.suffix.lower() == '.py':
            # 生成新的文件名（将.py改为.md）
            new_filename = file_path.stem + '.md'
            target_file_path = target_dir / new_filename
            
            try:
                # 读取py文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 如果内容已经是markdown格式（包含markdown标记），直接复制
                # 否则添加代码块标记
                if content.strip().startswith('#') or '##' in content[:200]:
                    # 可能是markdown格式，直接写入
                    md_content = content
                else:
                    # 添加Python代码块标记
                    md_content = f"```python\n{content}\n```\n"
                
                # 写入md文件
                with open(target_file_path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                
                print(f"✓ 已转换: {file_path.name} -> {new_filename}")
                converted_count += 1
            except Exception as e:
                print(f"✗ 转换失败: {file_path.name} - {str(e)}")
                skipped_count += 1
        elif file_path.is_file():
            # 非py文件，跳过
            print(f"- 跳过非py文件: {file_path.name}")
            skipped_count += 1
    
    # 输出统计信息
    print("\n" + "="*50)
    print(f"转换完成！")
    print(f"成功转换: {converted_count} 个文件")
    print(f"跳过: {skipped_count} 个文件")
    print(f"目标文件夹: {target_dir}")
    print("="*50)


def convert_py_to_txt(source_dir, target_dir):
    """将py文件转换为txt文件（直接复制并重命名，移除代码块标记）"""
    source_dir = Path(source_dir)
    target_dir = Path(target_dir)
    
    # 创建目标文件夹（如果不存在）
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 统计信息
    converted_count = 0
    skipped_count = 0
    
    # 遍历源文件夹中的所有文件
    for file_path in source_dir.iterdir():
        # 只处理py文件
        if file_path.is_file() and file_path.suffix.lower() == '.py':
            # 生成新的文件名（将.py改为.txt）
            new_filename = file_path.stem + '.txt'
            target_file_path = target_dir / new_filename
            
            try:
                # 读取py文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 如果内容包含markdown代码块标记，移除它们
                if content.strip().startswith('```'):
                    # 移除开头的```python或```标记
                    lines = content.split('\n')
                    # 移除第一行（```python或```）
                    if lines[0].strip().startswith('```'):
                        lines = lines[1:]
                    # 移除最后一行（```）
                    if lines and lines[-1].strip() == '```':
                        lines = lines[:-1]
                    content = '\n'.join(lines)
                
                # 写入txt文件
                with open(target_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✓ 已转换: {file_path.name} -> {new_filename}")
                converted_count += 1
            except Exception as e:
                print(f"✗ 转换失败: {file_path.name} - {str(e)}")
                skipped_count += 1
        elif file_path.is_file():
            # 非py文件，跳过
            print(f"- 跳过非py文件: {file_path.name}")
            skipped_count += 1
    
    # 输出统计信息
    print("\n" + "="*50)
    print(f"转换完成！")
    print(f"成功转换: {converted_count} 个文件")
    print(f"跳过: {skipped_count} 个文件")
    print(f"目标文件夹: {target_dir}")
    print("="*50)


def main():
    """主函数，支持命令行参数"""
    parser = argparse.ArgumentParser(
        description='文件格式转换工具：支持txt转py、py转md、py转txt',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # txt转py
  python convert_txt_to_py.py --mode txt2py --source ./聚宽2025年精选 --target ./聚宽2025年精选py
  
  # py转md
  python convert_txt_to_py.py --mode py2md --source ./聚宽2025年精选py --target ./聚宽2025年精选md
  
  # py转txt
  python convert_txt_to_py.py --mode py2txt --source ./聚宽2025年精选py --target ./聚宽2025年精选txt
        """
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        default='py2md',
        choices=['txt2py', 'py2md', 'py2txt'],
        help='转换模式: txt2py(文本转Python), py2md(Python转Markdown), py2txt(Python转文本)'
    )
    
    parser.add_argument(
        '--source',
        type=str,
        default='/Users/liuwenlin/Documents/Self/quant/Selection_Strategy/聚宽2025年精选py_explain',
        help='源文件夹路径'
    )
    
    parser.add_argument(
        '--target',
        type=str,
        default='/Users/liuwenlin/Documents/Self/quant/Selection_Strategy/聚宽2025年精选py_explain',
        help='目标文件夹路径'
    )
    
    args = parser.parse_args()
    
    # 根据模式执行相应的转换
    if args.mode == 'txt2py':
        print(f"开始转换: txt -> py")
        print(f"源文件夹: {args.source}")
        print(f"目标文件夹: {args.target}\n")
        convert_txt_to_py(args.source, args.target)
    elif args.mode == 'py2md':
        print(f"开始转换: py -> md")
        print(f"源文件夹: {args.source}")
        print(f"目标文件夹: {args.target}\n")
        convert_py_to_md(args.source, args.target)
    elif args.mode == 'py2txt':
        print(f"开始转换: py -> txt")
        print(f"源文件夹: {args.source}")
        print(f"目标文件夹: {args.target}\n")
        convert_py_to_txt(args.source, args.target)


if __name__ == "__main__":
    main()
