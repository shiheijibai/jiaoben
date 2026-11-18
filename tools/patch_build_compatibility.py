#!/usr/bin/env python3
"""应用当前 master 分支中已知的构建兼容补丁。"""

import sys
from pathlib import Path
from patch_utils import patch_file, patch_files, run_operation

root = Path(sys.argv[1])
arguments = sys.argv[2:]
supported_targets = {"image", "sdk", "tdd", "arkuix"}

def parse_arguments():
    selected = arguments.copy()
    if selected[:1] == ["--remove"]:
        if len(selected) == 2 and selected[1] in {"image", "sdk", "arkuix"}:
            return "remove", selected[1], selected[1], set(), ""
        if len(selected) == 3 and selected[1] == "tdd":
            return "remove", f"tdd_{selected[2]}", f"TDD {selected[2]}", set(), ""
        raise ValueError("--remove 后必须指定 image、sdk、arkuix 或 tdd <编译目标>。")

    tdd_target = ""
    if "tdd" in selected:
        tdd_index = selected.index("tdd")
        if tdd_index + 1 >= len(selected) or selected[tdd_index + 1] in supported_targets:
            raise ValueError("tdd 后必须指定编译目标，例如 ace_engine_test。")
        tdd_target = selected.pop(tdd_index + 1)

    targets = set(selected or ("image", "sdk"))
    unsupported_targets = targets - supported_targets
    if unsupported_targets:
        raise ValueError(f"不支持的构建修复参数：{' '.join(sorted(unsupported_targets))}")
    return "patch", "", "", targets, tdd_target

def remove_fix(name: str) -> bool:
    path = Path(__file__)
    text = path.read_text(encoding="utf-8")
    start_marker = f"# BUILD_FIX_{name.upper()}_START"
    end_marker = f"# BUILD_FIX_{name.upper()}_END"
    start = text.index("\n", text.index(start_marker)) + 1
    end_marker_position = text.index(end_marker, start)
    end = text.rfind("\n", 0, end_marker_position) + 1
    if not text[start:end].strip():
        return False
    replacements = ((text[start:end], "", 1),)
    return patch_file(path, replacements)

def patch_image() -> bool:
    # BUILD_FIX_IMAGE_START
    # BUILD_FIX_IMAGE_END
    return False

def patch_sdk() -> bool:
    # BUILD_FIX_SDK_START
    path = root / (
        "foundation/arkui/ace_engine/frameworks/core/interfaces/native/"
        "implementation/web_modifier.cpp"
    )
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        new = text
        platform_guard = "#if !defined(WINDOWS_PLATFORM) && !defined(LINUX_PLATFORM) && !defined(MAC_PLATFORM)\n"
        function_start = platform_guard + "void SetOnContextMenuUpdateImpl("
        function_end = "}\n#endif\n\nvoid SetMediaPlayGestureAccessImpl("
        entry = platform_guard + "        WebAttributeModifier::SetOnContextMenuUpdateImpl,\n" + "#endif\n"
        if function_start in new:
            new = new.replace(function_start, "void SetOnContextMenuUpdateImpl(", 1)
            new = new.replace(function_end, "}\n\nvoid SetMediaPlayGestureAccessImpl(", 1)
        if entry in new:
            new = new.replace(entry, "        WebAttributeModifier::SetOnContextMenuUpdateImpl,\n", 1)
        replacements = ((text, new, 1),)
        return patch_file(path, replacements)
    # BUILD_FIX_SDK_END
    return False

def patch_arkuix() -> bool:
    # BUILD_FIX_ARKUIX_START
    path1 = root / "build/prebuilts_download.py"
    path2 = root / "build_plugins/prebuilts_download_config.json"
    source_rich_download = '''        try:
            response = urlopen(url)
        except urllib.error.HTTPError as e:
            progress.console.log("Failed to open {}, HTTPError: {}".format(url, e.code), style='red')'''
    new_rich_download = '''        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urlopen(request)
        except urllib.error.HTTPError as e:
            progress.console.log("Failed to open {}, HTTPError: {}".format(url, e.code), style='red')
            retry_times += 1
            continue'''
    source_plain_download = '''    try:
        response = urlopen(url)
    except urllib.error.HTTPError as e:
        print("Failed to open {}, HTTPError: {}".format(url, e.code))'''
    new_plain_download = '''    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(request)
    except urllib.error.HTTPError as e:
        print("Failed to open {}, HTTPError: {}".format(url, e.code))
        raise'''
    source_future = '''        for task in as_completed(tasks):
            if not args.disable_rich:'''
    new_future = '''        for task in as_completed(tasks):
            task.result()
            if not args.disable_rich:'''
    source_npm_timeout = '''            cmd = ['timeout', '-s', '9', '90s', npm, 'install', '--registry', args.npm_registry, '--cache', npm_cache_dir]'''
    new_npm_timeout = '''            cmd = ['timeout', '-s', '9', '600s', npm, 'install', '--registry', args.npm_registry, '--cache', npm_cache_dir]'''
    source_npm_failure = '''        if retry_times == max_retry_times:
            for error_info in error.split('\\n'):
                if error_info.endswith('debug.log'):
                    log_path = error_info.split()[-1]
                    cmd = ['cat', log_path]
                    process_cat = subprocess.Popen(cmd)
                    process_cat.communicate(timeout=60)
                    raise Exception("npm install error with three times, prebuilts download exit")
        retry_times += 1'''
    new_npm_failure = '''        if retry_times == max_retry_times:
            for error_info in error.split('\\n'):
                if error_info.endswith('debug.log'):
                    log_path = error_info.split()[-1]
                    cmd = ['cat', log_path]
                    process_cat = subprocess.Popen(cmd)
                    process_cat.communicate(timeout=60)
                    break
            raise Exception("npm install error with three times, prebuilts download exit")
        retry_times += 1'''
    replacements1 = (
        (source_rich_download, new_rich_download, 1),
        (source_plain_download, new_plain_download, 1),
        (source_future, new_future, 1),
        (source_npm_timeout, new_npm_timeout, 1),
        (source_npm_failure, new_npm_failure, 1),
    )
    source_ace_loader = '''    "developtools/ace_ets2bundle/compiler",
    "developtools/ace_js2bundle/ace-loader",
    "third_party/parse5/packages/parse5",'''
    new_ace_loader = '''    "developtools/ace_ets2bundle/compiler",
    "third_party/parse5/packages/parse5",'''
    source_last_npm = '''    "arkcompiler/runtime_core/static_core/plugins/ets/tools/declgen_ts2sts"'''
    new_last_npm = '''    "arkcompiler/runtime_core/static_core/plugins/ets/tools/declgen_ts2sts",
    "developtools/ace_js2bundle/ace-loader"'''
    replacements2 = (
        (source_ace_loader, new_ace_loader, 1),
        (source_last_npm, new_last_npm, 1),
    )
    return patch_files(((path1, replacements1), (path2, replacements2)))
    # BUILD_FIX_ARKUIX_END
    return False

def patch_tdd(target: str) -> bool:
    if target == "ace_engine_test":
        # BUILD_FIX_TDD_ACE_ENGINE_TEST_START
        # BUILD_FIX_TDD_ACE_ENGINE_TEST_END
        return False
    if target == "bundle_tool_test":
        # BUILD_FIX_TDD_BUNDLE_TOOL_TEST_START
        # BUILD_FIX_TDD_BUNDLE_TOOL_TEST_END
        return False
    if target == "bundle_framework_test":
        # BUILD_FIX_TDD_BUNDLE_FRAMEWORK_TEST_START
        # BUILD_FIX_TDD_BUNDLE_FRAMEWORK_TEST_END
        return False
    return False

try:
    mode, remove_name, remove_label, targets, tdd_target = parse_arguments()
except ValueError as error:
    raise SystemExit(f"错误：{error}")

if mode == "remove":
    results = (
        run_operation(f"删除 {remove_label} 构建兼容", remove_fix, remove_name),
    )
else:
    results = (
        run_operation("Image 构建兼容", patch_image) if "image" in targets else True,
        run_operation("SDK 构建兼容", patch_sdk) if "sdk" in targets else True,
        run_operation(f"TDD {tdd_target} 构建兼容", patch_tdd, tdd_target) if "tdd" in targets else True,
        run_operation("ArkUI-X 预编译下载", patch_arkuix) if "arkuix" in targets else True,
    )

if all(results):
    raise SystemExit(0)
else:
    raise SystemExit(1)
