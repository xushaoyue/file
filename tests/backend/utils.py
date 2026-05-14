"""
测试辅助函数
"""

import os
import tempfile
from pathlib import Path


def create_test_file(path: str, content: str = "test content"):
    """创建测试文件"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path


def create_test_directory(path: str):
    """创建测试目录"""
    os.makedirs(path, exist_ok=True)
    return path


def cleanup_test_files(*paths):
    """清理测试文件"""
    import shutil
    for path in paths:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)


def get_temp_file(suffix: str = ".txt", content: str = "test content"):
    """创建临时文件并返回路径"""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path


def get_temp_directory():
    """创建临时目录并返回路径"""
    return tempfile.mkdtemp()
