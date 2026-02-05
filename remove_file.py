#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量删除指定文件夹下统一后缀的文件
"""

import os
import sys
import argparse
from pathlib import Path


def remove_files_by_suffix(folder_path, suffix, dry_run=False, confirm=True):
    """
    批量删除指定文件夹下统一后缀的文件
    
    Args:
        folder_path: 文件夹路径
        suffix: 文件后缀（如 '.py', '.txt'，可以带或不带点号）
        dry_run: 是否只是预览，不实际删除
        confirm: 是否在删除前确认
    
    Returns:
        删除的文件数量
    """
    # 确保后缀格式正确（以点开头）
    if not suffix.startswith('.'):
        suffix = '.' + suffix
    
    folder = Path(folder_path)
    
    # 检查文件夹是否存在
    if not folder.exists():
        print(f"错误: 文件夹 '{folder_path}' 不存在")
        return 0
    
    if not folder.is_dir():
        print(f"错误: '{folder_path}' 不是一个文件夹")
        return 0
    
    # 查找所有匹配的文件
    matching_files = list(folder.glob(f'*{suffix}'))
    
    if not matching_files:
        print(f"在文件夹 '{folder_path}' 中没有找到后缀为 '{suffix}' 的文件")
        return 0
    
    # 显示要删除的文件列表
    print(f"\n找到 {len(matching_files)} 个匹配的文件:")
    for i, file_path in enumerate(matching_files, 1):
        print(f"  {i}. {file_path.name}")
    
    if dry_run:
        print(f"\n[预览模式] 将删除 {len(matching_files)} 个文件")
        return len(matching_files)
    
    # 确认删除
    if confirm:
        response = input(f"\n确定要删除这 {len(matching_files)} 个文件吗？(yes/no): ")
        if response.lower() not in ['yes', 'y', '是']:
            print("操作已取消")
            return 0
    
    # 执行删除
    deleted_count = 0
    failed_count = 0
    
    for file_path in matching_files:
        try:
            file_path.unlink()
            print(f"已删除: {file_path.name}")
            deleted_count += 1
        except Exception as e:
            print(f"删除失败: {file_path.name} - {str(e)}")
            failed_count += 1
    
    print(f"\n删除完成: 成功 {deleted_count} 个, 失败 {failed_count} 个")
    return deleted_count


def main():
    parser = argparse.ArgumentParser(
        description='批量删除指定文件夹下统一后缀的文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 删除当前文件夹下所有 .pyc 文件
  python remove_file.py . .pyc
  
  # 删除指定文件夹下所有 .txt 文件（预览模式）
  python remove_file.py /path/to/folder .txt --dry-run
  
  # 删除文件，不确认
  python remove_file.py /path/to/folder .log --no-confirm
        """
    )
    
    parser.add_argument(
        '--folder',
        type=str,
        default='/Users/liuwenlin/Documents/Self/quant/Selection_Strategy/聚宽2025年精选py_explain',
        help='要删除文件的文件夹路径'
    )
    
    parser.add_argument(
        '--suffix',
        type=str,
        default='.py',
        help='文件后缀（如 .pyc, .txt，可以带或不带点号）'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        help='预览模式，只显示要删除的文件，不实际删除'
    )
    
    parser.add_argument(
        '--no-confirm',
        action='store_true',
        default=False,
        help='不询问确认，直接删除'
    )
    
    args = parser.parse_args()
    
    # 执行删除
    args.dry_run = True  # True 预览模式，False 实际删除
    remove_files_by_suffix(
        folder_path=args.folder,
        suffix=args.suffix,
        dry_run=False,
        confirm=args.no_confirm
    )

if __name__ == '__main__':
    main()
