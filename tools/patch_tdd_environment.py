#!/usr/bin/env python3
"""配置 TDD 超时时间和 Windows 测试目录。"""

import sys
from pathlib import Path
from patch_utils import patch_file, run_operation

root = Path(sys.argv[1])

# 设置原生 TDD 单次命令的超时时间。
def patch_timeout() -> bool:
    path = root / "test/testfwk/developer_test/src/core/driver/drivers.py"
    source = '''TIME_OUT = 900 * 1000'''
    new = '''TIME_OUT = 60 * 1000'''
    replacements = ((source, new, 1),)
    return patch_file(path, replacements)

# 设置 Windows TDD 框架读取测试产物的目录。
def patch_test_directory() -> bool:
    path = root / "test/testfwk/developer_test/config/user_config.xml"
    source = '''<dir></dir>'''
    new = r'''<dir>D:\rk3568\TDD\tests</dir>'''
    replacements = ((source, new, 1),)
    return patch_file(path, replacements)

results = (
    run_operation("TDD 超时时间", patch_timeout),
    run_operation("TDD Windows 测试目录", patch_test_directory),
)

if all(results):
    raise SystemExit(0)
else:
    raise SystemExit(1)
