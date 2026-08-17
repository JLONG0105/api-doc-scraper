# -*- coding: utf-8 -*-
"""通用工具函数"""
import sys
import io


def setup_console_encoding():
    """修复Windows控制台GBK编码问题"""
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def clean(text):
    """清理不间断空格、零宽空格等特殊字符"""
    if not text:
        return ''
    return str(text).replace('\xa0', ' ').replace('​', '').strip()


def save_excel(df, output_file):
    """保存DataFrame到Excel，处理文件占用情况"""
    import os
    from datetime import datetime

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    out = output_file
    try:
        df.to_excel(out, index=False, engine='openpyxl')
    except PermissionError:
        # 目标文件被占用(如Excel打开中)，改用带时间戳的备用文件名
        ts = datetime.now().strftime('%H%M%S')
        base, ext = os.path.splitext(output_file)
        out = f"{base}_{ts}{ext}"
        print(f"提示: 原文件被占用，已改用备用文件名")
        df.to_excel(out, index=False, engine='openpyxl')
    return out
