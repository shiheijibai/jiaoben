#!/usr/bin/env python3
"""源码补丁工具的公共文件写入操作。"""

import os
from datetime import datetime
from pathlib import Path

# 使用临时文件保留权限并原子替换目标文件。
def _write_atomic(path: Path, text: str) -> None:
    suffix = ".patch.tmp"
    temporary = path.with_name(path.name + suffix)
    temporary.write_text(text, encoding="utf-8")
    os.chmod(temporary, path.stat().st_mode)
    os.replace(temporary, path)

# 根据原内容、新内容和匹配次数校验并在内存中执行替换。
def _prepare_patch(path: Path, replacements):
    text = path.read_text(encoding="utf-8")
    changed = False
    for source, new, count in replacements:
        if new and text.count(new) >= count:
            continue
        if text.count(source) != count:
            raise RuntimeError(f"无法定位 {path} 的待修改代码，未修改源码")
        text = text.replace(source, new, count)
        changed = True
    return text, changed

# 按顺序应用 source/new 替换，已经生效时不重复写入。
def patch_file(path: Path, replacements) -> bool:
    text, changed = _prepare_patch(path, replacements)
    if not changed:
        return False
    _write_atomic(path, text)
    return True

# 先验证一组相互依赖的文件，再统一写入修改。
def patch_files(patches) -> bool:
    prepared = [
        (path, *_prepare_patch(path, replacements))
        for path, replacements in patches
    ]
    for path, text, changed in prepared:
        if changed:
            _write_atomic(path, text)
    return any(changed for _, _, changed in prepared)

# 输出统一的时间、状态和操作日志。
def log_result(result: str, label: str, message: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [{result}] {label}：{message}")

# 独立执行并记录一项补丁，失败时返回 False。
def run_operation(label, operation, *arguments) -> bool:
    try:
        changed = operation(*arguments)
    except Exception as error:
        log_result("失败", label, str(error))
        return False
    state = "已应用" if changed else "已经生效"
    log_result("成功", label, f"{state}。")
    return True
