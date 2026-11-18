#!/usr/bin/env python3
"""注释 OpenHarmony build.sh 中的 ohpm 初始化代码块。"""

import sys
from pathlib import Path
from patch_utils import patch_file, run_operation

root = Path(sys.argv[1])

def patch_ohpm_initialization() -> bool:
    path = root / "build.sh"
    source = '''init_ohpm
  if [[ "$?" -ne 0 ]]; then
    echo -e "\\033[31m[OHOS ERROR] ohpm initialization failed!\\033[0m"
    exit 1
  fi'''
    new = '''# init_ohpm
  # if [[ "$?" -ne 0 ]]; then
  #   echo -e "\\033[31m[OHOS ERROR] ohpm initialization failed!\\033[0m"
  #   exit 1
  # fi'''
    replacements = ((source, new, 1),)
    return patch_file(path, replacements)

results = (
    run_operation("ohpm 初始化", patch_ohpm_initialization),
)

if all(results):
    raise SystemExit(0)
else:
    raise SystemExit(1)
