#!/usr/bin/env python3
"""为指定的 GN 服务文件接入 clangd 编译数据库优化器。"""

import sys
from pathlib import Path

from patch_utils import patch_file, run_operation

root = Path(sys.argv[1])

# 在 GN 生成结束后接入 clangd 编译数据库更新。
def patch_gn() -> bool:
    path = root / "build/hb/services/gn.py"
    source_import = '''import threading'''
    new_import = '''import threading
import subprocess'''
    source_gn_block = '''
    \'\'\'Description: Execute 'gn path' command using registed args'''
    new_gn_block = '''

        clangd_root = os.path.join(
            os.path.dirname(self.config.root_path), 'clangd')
        clangd_generator = os.path.join(
            clangd_root, 'tools', 'update_clangd_compile_commands.py')
        if (
            os.path.basename(os.path.normpath(self.config.out_path)) == 'rk3568'
            and '--export-compile-commands' in gn_gen_cmd
            and os.path.isfile(clangd_generator)
        ):
            source = os.path.join(self.config.out_path, 'compile_commands.json')
            destination = os.path.join(
                clangd_root, 'data', 'rk3568', 'compile_commands.json')
            report = os.path.join(os.path.dirname(destination), 'generation-report.json')
            try:
                result = subprocess.run(
                    [sys.executable, '-B', clangd_generator,
                     '--source', source,
                     '--destination', destination,
                     '--report', report],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False)
                if result.returncode == 0:
                    LogUtil.hb_info('clangd compilation database updated: {}'.format(
                        result.stdout.strip()))
                else:
                    LogUtil.hb_warning(
                        'clangd compilation database update failed; keeping the '
                        'last-good file:\\n{}'.format(result.stdout.strip()))
            except Exception as exception:
                LogUtil.hb_warning(
                    'clangd compilation database update failed; keeping the '
                    'last-good file: {}'.format(exception))
''' + source_gn_block

    replacements = (
        (source_import, new_import, 1),
        (source_gn_block, new_gn_block, 1),
    )
    return patch_file(path, replacements)

if run_operation("clangd GN 配置", patch_gn):
    raise SystemExit(0)
else:
    raise SystemExit(1)
