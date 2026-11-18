#!/usr/bin/env python3
"""独立配置 OpenHarmony 的 ccache、日志策略、相对调试路径和资源监控。"""

import sys
from pathlib import Path
from patch_utils import patch_file, run_operation

root = Path(sys.argv[1])

# 配置 build.sh 的 ccache 环境。
# CCACHE_BASEDIR 统一源码路径，CCACHE_MAXSIZE 限制容量，CCACHE_NOHASHDIR 忽略工作目录差异。
def patch_build_script() -> bool:
    path = root / "build.sh"
    source = '''set -e
set +e'''
    new = '''set -e
set +e
export CCACHE_BASEDIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export CCACHE_MAXSIZE=200G
export CCACHE_NOHASHDIR=true'''
    replacements = ((source, new, 1),)
    return patch_file(path, replacements)

# 开启相对调试路径，减少工作目录变化对 ccache 的影响。
def patch_compiler_config() -> bool:
    path = root / "build/config/compiler/BUILD.gn"
    source = '''strip_absolute_paths_from_debug_symbols = false'''
    new = '''strip_absolute_paths_from_debug_symbols = true'''
    replacements = ((source, new, 1),)
    return patch_file(path, replacements)

# 让 ccache 详细日志和统计只在显式开启时运行。
def patch_resolver(path: Path) -> bool:
    source_log_block = '''ccache_log_suffix = os.environ.get('CCACHE_LOG_SUFFIX')
            if ccache_log_suffix:
                logfile = os.path.join(
                    ccache_base, "ccache.{}.log".format(ccache_log_suffix))
            elif os.environ.get('CCACHE_LOGFILE'):
                logfile = os.environ.get('CCACHE_LOGFILE')
                if not os.path.exists(os.path.dirname(logfile)):
                    os.makedirs(os.path.dirname(logfile), exist_ok=True)
            else:
                logfile = os.path.join(ccache_base, "ccache.log")
            if os.path.exists(logfile):
                oldfile = '{}.old'.format(logfile)
                if os.path.exists(oldfile):
                    os.unlink(oldfile)
                rename_file(logfile, oldfile)'''
    new_log_block = '''logfile = os.environ.get('CCACHE_LOGFILE')
            ccache_log_suffix = os.environ.get('CCACHE_LOG_SUFFIX')
            if ccache_log_suffix:
                logfile = os.path.join(
                    ccache_base, "ccache.{}.log".format(ccache_log_suffix))
            if logfile:
                log_directory = os.path.dirname(logfile)
                if log_directory and not os.path.exists(log_directory):
                    os.makedirs(log_directory, exist_ok=True)
                if os.path.exists(logfile):
                    oldfile = '{}.old'.format(logfile)
                    if os.path.exists(oldfile):
                        os.unlink(oldfile)
                    rename_file(logfile, oldfile)'''
    source_assignment = '''os.environ['CCACHE_LOGFILE'] = logfile'''
    new_assignment = '''if logfile:
                os.environ['CCACHE_LOGFILE'] = logfile'''
    source_stat_block = '''ccache_log_suffix = os.environ.get('CCACHE_LOG_SUFFIX')
            if ccache_log_suffix:
                logfile = "ccache.{}.log".format(ccache_log_suffix)
            else:
                logfile = "ccache.log"
            ccache_local_dir = os.environ.get('CCACHE_LOCAL_DIR')
            if not ccache_local_dir:
                ccache_local_dir = '.ccache'
            ccache_base = os.environ.get('CCACHE_BASE')

            # The default value is HOME for local users
            if not ccache_base:
                ccache_base = os.environ.get('HOME')
            ccache_base = os.path.join(ccache_base, ccache_local_dir)
            if os.environ.get('CCACHE_LOGFILE'):
                logfile = os.environ.get('CCACHE_LOGFILE')
            else:
                logfile = os.path.join(ccache_base, logfile)'''
    new_stat_block = '''logfile = os.environ.get('CCACHE_LOGFILE')
            ccache_log_suffix = os.environ.get('CCACHE_LOG_SUFFIX')
            if ccache_log_suffix:
                ccache_local_dir = os.environ.get('CCACHE_LOCAL_DIR', '.ccache')
                ccache_base = os.environ.get('CCACHE_BASE', os.environ.get('HOME'))
                logfile = os.path.join(
                    ccache_base, ccache_local_dir,
                    "ccache.{}.log".format(ccache_log_suffix))
            if not logfile:
                return'''

    replacements = [
        (source_log_block, new_log_block, 1),
        (source_assignment, new_assignment, 1),
    ]
    if path.name == "build_args_resolver.py":
        replacements.append((source_stat_block, new_stat_block, 1))
    return patch_file(path, replacements)

def patch_main_resolver() -> bool:
    path = root / "build/hb/resolver/build_args_resolver.py"
    return patch_resolver(path)

def patch_independent_resolver() -> bool:
    path = root / "build/hb/resolver/indep_build_args_resolver.py"
    return patch_resolver(path)

# 关闭构建结束后的 CPU、内存和磁盘资源快照。
def patch_build_monitor() -> bool:
    path = root / "build/hb/modules/ohos_build_module.py"
    source_import = '''from util.monitor import Monitor
from dfx.build_tracker import build_tracker'''
    new_import = '''# 构建结束后不采集系统资源快照。
from dfx.build_tracker import build_tracker'''
    source_run = '''@throw_exception
    def run(self):
        monitor = Monitor()
        try:
            super().run()
        except OHOSException as exception:
            monitor.run()
            raise exception
        else:
            monitor.run()
            if self._configuration_cache is not None:
                self._configuration_cache.commit()
            LogUtil.hb_info('{} build success'.format(
                self.args_dict.get('product_name').arg_value))
            LogUtil.hb_info('Cost Time:  {}'.format(self.build_time))
            # Report artifact completion before recording the workspace baseline.
            # Still wait for the seal before HB returns to build.sh and CI exits.
            self._record_incremental_baseline()'''
    new_run = '''@throw_exception
    def run(self):
        super().run()
        if self._configuration_cache is not None:
            self._configuration_cache.commit()
        LogUtil.hb_info('{} build success'.format(
            self.args_dict.get('product_name').arg_value))
        LogUtil.hb_info('Cost Time:  {}'.format(self.build_time))
        # Report artifact completion before recording the workspace baseline.
        # Still wait for the seal before HB returns to build.sh and CI exits.
        self._record_incremental_baseline()'''
    replacements = (
        (source_import, new_import, 1),
        (source_run, new_run, 1),
    )
    return patch_file(path, replacements)

results = (
    run_operation("ccache 环境变量", patch_build_script),
    run_operation("相对调试路径", patch_compiler_config),
    run_operation("主构建 ccache 日志策略", patch_main_resolver),
    run_operation("独立构建 ccache 日志策略", patch_independent_resolver),
    run_operation("关闭构建资源监控", patch_build_monitor),
)

if all(results):
    raise SystemExit(0)
else:
    raise SystemExit(1)
