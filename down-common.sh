#!/usr/bin/bash

# 脚本维护约定：
# 1. 所有面向用户的帮助、状态、错误和日志提示统一使用简体中文；命令、参数、路径和专有名词保持原样。
# 2. 函数原则上先集中解析并校验全部入参，再执行编译、复制、删除或设备操作；只有解析依赖执行结果时才例外。
# 3. 变量仅在需要复用或能明显提升可读性时定义，并在首次使用前就近声明；函数保持职责单一、结构简洁。
# 4. 可选行为使用含义明确的动作参数，默认行为保持简单安全；参数冲突或不受支持时应在执行操作前报错。
# 5. 命令参数优先使用数组传递，变量引用使用双引号，避免空格、通配符和参数拼接造成错误。
# 6. WSL 与 Windows 之间的路径统一使用 wslpath 转换，固定公共路径集中定义在文件开头。
# 7. 删除、覆盖、刷机和设备推送等操作必须使用明确目标并检查结果；失败返回非零状态，由调用方决定是否继续。
# 8. 普通命令尽量控制在 150 列以内；runStep 调用保持一行，便于直接查看完整操作。
# 9. 修改命令或参数时同步更新 printHelp、入口分发和相关调用方，同名动作参数在不同函数中保持一致含义。
# 10. 修改后至少执行 Bash 语法检查和 Git 差异检查；涉及关键流程时再使用低风险命令验证实际行为。
# 11. 源码补丁只适配刚拉取的原始状态和当前脚本结果，不兼容早期脚本生成的旧配置。
# 12. OpenHarmony 代码根目录由 down-common.sh 传入，Python 工具使用固定相对路径定位目标文件。
# 13. Python 补丁工具先定义各项补丁函数，文件末尾使用 results 元组和 run_operation 集中执行；不在 results 中展开 source/new，也不使用全局列表追加结果。
# 14. 脚本源码的相邻代码之间最多保留一行空行，不出现连续两行及以上空行；多行字符串内容除外。
# 15. 调用公共 patch_file 时先就近声明 path 和 replacements，再使用 patch_file(path, replacements)；不在调用参数中展开替换内容。
# 16. /home/shjb/work/Project/jiaoben/windows 是 D:\Project\jiaoben 的备份；修改其中的 Windows 文件时必须同步更新两处并保持内容一致。
# 17. Python 补丁的 source/new 字符串统一使用三单引号；匹配唯一时省略首行缩进和末尾换行，必要时保留边界确保唯一。
# 18. Windows BAT 文件统一使用 CRLF 换行，并通过 .gitattributes 固定格式，不依赖 cmd.exe 的 /q 隐藏格式问题。

# 公共脚本和 OpenHarmony 源码目录。
COMMON_SCRIPT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
OPENHARMONY_CODE_PATH="$OPENHARMONY_WORK_PATH/code"
# 统一命令日志路径。
LOG_PATH="$OPENHARMONY_WORK_PATH/down.log"
# 保证非交互脚本也能找到 repo。
PATH="/home/shjb/bin:$PATH"
# clangd 根目录和 rk3568 数据目录。
CLANGD_ROOT="$OPENHARMONY_WORK_PATH/clangd"
CLANGD_DATA_PATH="$CLANGD_ROOT/data/rk3568"
# Windows 命令、SDK、镜像和设备工具。
WINDOW_SDK_PATH='/mnt/d/Path/SDK'
WINDOW_CMD_PATH='/mnt/c/Windows/System32/cmd.exe'
WINDOW_PACKAGE_EXTRACT_SCRIPT='D:\Project\jiaoben\extract-package.bat'
WINDOW_SDK_SCRIPT='D:\Project\jiaoben\copy-windows-sdk.bat'
WINDOW_PREVIEWER_SCRIPT='D:\Project\jiaoben\replace-previewer.bat'
WINDOW_PREVIEWER_PATH='/mnt/d/Path/SDK/26.1.0/previewer/common/bin'
WINDOW_IMAGE_SCRIPT='D:\Project\jiaoben\copy-image.bat'
WINDOW_RK3568_SO_SCRIPT='D:\Project\jiaoben\replace-rk3568-so.bat'
WINDOW_RKDEVTOOL_CONTROL='/mnt/d/Project/jiaoben/rkdevtool-control.exe'
WINDOW_FAN_CONTROL='/mnt/d/Project/jiaoben/fan-control.exe'
WINDOW_HDC_PATH='/mnt/d/Path/hdc/hdc.exe'
WINDOWS_IMAGE_PATH='/mnt/d/rk3568/images'
WINDOWS_TEMP_IMAGE_PATH='/mnt/d/rk3568/imagestemp'
# ArkUI-X 编译产物、Windows SDK 目录和复制脚本。
WINDOW_ARKUIX_PATH='/mnt/d/Path/ArkUI-X'
WINDOW_ARKUIX_COPY_SCRIPT='D:\Project\jiaoben\copy-arkuix.bat'
ARKUIX_WINDOWS_SDK_PATH='/out/arkui-x/arkui-x/windows/arkui-x'
# Windows TDD 脚本、测试用例和报告目录。
WINDOW_TDD_SCRIPT='D:\Project\jiaoben\copy-tdd.bat'
WINDOW_TDD_RUN_SCRIPT='D:\Project\jiaoben\run-tdd.bat'
WINDOW_TDD_SYNC_SCRIPT='D:\Project\jiaoben\sync-tdd.bat'
WINDOW_TDD_TESTCASE_PATH='/mnt/d/rk3568/TDD/tests'
WINDOW_TDD_REPORT_PATH='/mnt/d/rk3568/TDD/developer_test/reports'
# Windows XTS 脚本、动态和静态测试框架目录。
WINDOW_XTS_COPY_SCRIPT='D:\Project\jiaoben\copy-xts.bat'
WINDOW_XTS_RUN_SCRIPT='D:\Project\jiaoben\run-xts.bat'
WINDOW_XTS_PATH='/mnt/d/rk3568/XTS'
# OpenHarmony 的 XTS、SDK、单元测试、镜像和系统相对目录。
XTS_CODE_PATH='/test/xts/acts'
XTS_TESTCASE_PATH='/out/rk3568/suites/acts/acts/testcases'
SDK_WINDOWS_PACKAGE_PATH='/out/sdk/packages/ohos-sdk/windows'
PREVIEWER_BIN_PATH='/out/sdk/ohos-sdk/windows/previewer/common/bin'
UNITTEST_PATH='/out/rk3568/tests'
IMAGE_PATH='/out/rk3568/packages/phone/images'
SYSTEM_PATH='/out/rk3568/packages/phone/system'

trap 'echo "操作已中断。"; exit 130' INT

# 公共函数
function runWindows() {
    (cd /mnt/c && "$@")
}

function runStep() {
    local max_attempts="$1"
    shift

    local command_line
    printf -v command_line '%q ' "$@"

    local attempt status result timestamp
    for ((attempt = 1; attempt <= max_attempts; attempt++)); do
        if ((max_attempts > 1)); then
            printf '尝试：%s/%s\n' "$attempt" "$max_attempts"
        fi
        printf '命令：%s\n' "$command_line"

        "$@"
        status=$?

        if ((status == 0)); then
            result="成功"
        else
            result="失败：$status"
        fi
        timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
        printf '[%s] [%s] %s\n' "$timestamp" "$result" "$command_line" >> "$LOG_PATH"
        printf '[%s] [%s]\n' "$timestamp" "$result"
        if ((status == 0)); then
            return 0
        fi
    done

    return "$status"
}

function runReport() {
    local report_type="$1" report_root="$2" report_tag="$3"
    shift 3

    local previous_report="$(ls -1dt "$report_root"/*/ 2>/dev/null | head -n 1)"
    "$@" >/dev/null 2>&1
    local status=$?
    local latest_report="$(ls -1dt "$report_root"/*/ 2>/dev/null | head -n 1)"

    if [ -z "$latest_report" ] || [ "$latest_report" = "$previous_report" ]; then
        echo "错误：$report_type 未生成新的报告。" >&2
        return 1
    fi
    if [ -n "$report_tag" ]; then
        local report_path="${latest_report%/}($report_tag)"
        runStep 1 mv -- "${latest_report%/}" "$report_path" || return 1
        latest_report="$report_path/"
    fi
    echo "$report_type 报告：$(wslpath -w "${latest_report%/}/summary_report.html")"
    return "$status"
}

function waitForDevice() {
    local deadline=$((SECONDS + 600))
    local boot_completed
    echo "等待设备启动。"
    while ((SECONDS < deadline)); do
        boot_completed="$(runWindows "$WINDOW_HDC_PATH" shell param get bootevent.boot.completed 2>/dev/null | tr -d '[:space:]')"
        if [ "$boot_completed" = true ]; then
            echo "设备已启动。"
            return 0
        fi
        sleep 5
    done
    echo "错误：等待设备启动超时。" >&2
    printf '[%s] [失败] 等待设备启动超时。\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_PATH"
    return 1
}

function readDeviceLayout() {
    runWindows "$WINDOW_HDC_PATH" shell uitest dumpLayout -p /data/local/tmp/down-layout.json >/dev/null 2>&1 || return 1
    runWindows "$WINDOW_HDC_PATH" shell cat /data/local/tmp/down-layout.json 2>/dev/null
}

function keepScreenOn() {
    waitForDevice || return 1
    echo "正在设置屏幕常亮。"
    runWindows "$WINDOW_HDC_PATH" shell power-shell wakeup >/dev/null || return 1
    sleep 1

    local layout
    layout="$(readDeviceLayout)" || return 1
    if [[ "$layout" == *上滑解锁* ]]; then
        runWindows "$WINDOW_HDC_PATH" shell uitest uiInput swipe 360 1000 360 250 500 >/dev/null || return 1
        sleep 1
        layout="$(readDeviceLayout)" || return 1
    fi
    if [[ "$layout" == *'USB 连接方式'* ]]; then
        runWindows "$WINDOW_HDC_PATH" shell uitest uiInput click 360 800 >/dev/null || return 1
    fi
    runWindows "$WINDOW_HDC_PATH" shell power-shell timeout -o 864000000 >/dev/null
}

function patchBuildCompatibility() {
    python3 -B "$COMMON_SCRIPT_PATH/tools/patch_build_compatibility.py" "$OPENHARMONY_CODE_PATH" "$@"
}

# 写入各工作区的 VS Code 配置。
function writeVscodeSettings() {
    local compile_commands_path
    local template_file="$COMMON_SCRIPT_PATH/tools/vscode-settings.json.in"
    local -a workspace_paths
    case "${1:-openharmony}" in
        openharmony)
            compile_commands_path="$CLANGD_DATA_PATH"
            workspace_paths=(
                "$OPENHARMONY_CODE_PATH"
                "$OPENHARMONY_CODE_PATH/foundation/arkui/ace_engine"
                "$OPENHARMONY_CODE_PATH/foundation/bundlemanager/bundle_framework"
            )
            ;;
        arkuix)
            compile_commands_path="$OPENHARMONY_CODE_PATH/out/arkui-x"
            workspace_paths=("$OPENHARMONY_CODE_PATH")
            ;;
        *)
            echo "错误：不支持的 VS Code 配置类型：$1" >&2
            return 1
            ;;
    esac

    local setting_info
    setting_info="$(<"$template_file")"
    setting_info="${setting_info//@OPENHARMONY_CODE_PATH@/$OPENHARMONY_CODE_PATH}"
    setting_info="${setting_info//@CLANGD_DATA_PATH@/$compile_commands_path}"

    local workspace_path
    for workspace_path in "${workspace_paths[@]}"; do
        if [ -d "$workspace_path" ]; then
            mkdir -p "$workspace_path/.vscode" || return 1
            printf '%s\n' "$setting_info" > "$workspace_path/.vscode/settings.json" || return 1
        fi
    done
}

# 覆盖 test 目录下各 Git 仓库的 VS Code 格式化配置。
function setupTestVscodeSettings() {
    local git_path repository
    for git_path in /home/shjb/work/test/*/.git; do
        repository="${git_path%/.git}"
        mkdir -p "$repository/.vscode" || return 1
        cp -- "$COMMON_SCRIPT_PATH/tools/vscode-format-settings.json" "$repository/.vscode/settings.json" || return 1
        grep -qxF '/.vscode/settings.json' "$git_path/info/exclude" || printf '%s\n' '/.vscode/settings.json' >> "$git_path/info/exclude" || return 1
    done
    echo "VS Code：test 目录下的 Git 仓库已统一配置。"
}

# 屏蔽 bundle_framework 和 bundle_tool 的本地构建变化。
function setupBundleManagerGitExclude() {
    local exclude_file="$OPENHARMONY_CODE_PATH/foundation/bundlemanager/bundle_framework/.git/info/exclude"
    local pattern
    local -a patterns=(
        '# down.sh：忽略 bundle_framework 本地构建产物。'
        '/.vscode/settings.json'
        '/test/sceneProject/**/.hvigor/'
        '/test/sceneProject/**/build/'
        '/test/sceneProject/**/oh_modules/'
        '/test/sceneProject/**/.cxx/'
        '/test/sceneProject/**/local.properties'
        '/test/sceneProject/**/oh-package-lock.json5'
        '/test/sceneProject/systemtest/bundle_hsp/hsp_A/**/libs/**/*.so'
        '/test/sceneProject/systemtest/testHapNoSo/**/libs/**/*.so'
        '/test/sceneProject/systemtest/testHapSo/**/libs/**/*.so'
        '/test/sceneProject/unittest/bundle_so/**/libs/**/*.so'
        '/test/sceneProject/unittest/test_bundle/otaUpdateTest*/**/libs/**/*.so'
    )
    for pattern in "${patterns[@]}"; do
        grep -qxF "$pattern" "$exclude_file" || printf '%s\n' "$pattern" >> "$exclude_file" || return 1
    done

    exclude_file="$OPENHARMONY_CODE_PATH/foundation/bundlemanager/bundle_tool/.git/info/exclude"
    patterns=(
        '# down.sh：忽略 bundle_tool test_app_one 本地构建产物。'
        '/test/sceneProject/tools/bm/test_app_one/.hvigor/'
        '/test/sceneProject/tools/bm/test_app_one/build/build.log'
        '/test/sceneProject/tools/bm/test_app_one/entry/build/'
        '/test/sceneProject/tools/bm/test_app_one/local.properties'
        '/test/sceneProject/tools/bm/test_app_one/oh_modules/.ohpm/@ohos+hypium@1.0.6/oh_modules/@ohos/hypium/CHANGELOG.md'
        '/test/sceneProject/tools/bm/test_app_one/oh_modules/.ohpm/@ohos+hypium@1.0.6/oh_modules/@ohos/hypium/README.md'
        '/test/sceneProject/tools/bm/test_app_one/oh_modules/.ohpm/@ohos+hypium@1.0.6/oh_modules/@ohos/hypium/src/main/module/assert/deepEquals/assertDeepEquals.js'
        '/test/sceneProject/tools/bm/test_app_one/oh_modules/.ohpm/@ohos+hypium@1.0.6/oh_modules/@ohos/hypium/src/main/service.js'
    )
    for pattern in "${patterns[@]}"; do
        grep -qxF "$pattern" "$exclude_file" || printf '%s\n' "$pattern" >> "$exclude_file" || return 1
    done

    local repository="$OPENHARMONY_CODE_PATH/foundation/bundlemanager/bundle_tool"
    local -a tracked_files
    mapfile -t tracked_files < <(git -C "$repository" ls-files -- \
        test/sceneProject/tools/bm/test_app_one/oh-package-lock.json5 \
        test/sceneProject/tools/bm/test_app_one/oh_modules/.ohpm/@ohos+hypium@1.0.6/oh_modules/@ohos/hypium)
    git -C "$repository" update-index --assume-unchanged -- "${tracked_files[@]}"
}

# 配置 ccache、日志策略和相对调试路径。
function patchBuildEnvironment() {
    python3 -B "$COMMON_SCRIPT_PATH/tools/patch_build_environment.py" "$OPENHARMONY_CODE_PATH" >> "$LOG_PATH" 2>&1
}

# 配置 clangd 索引规则以减少内存占用，并自动更新编译数据库。
function setupClangdOptimization() {
    local packaged_tool="$COMMON_SCRIPT_PATH/tools/update_clangd_compile_commands.py"
    local tool_path="$CLANGD_ROOT/tools/update_clangd_compile_commands.py"
    local status=0

    # 写入 clangd 索引规则。
    if ! cp -- "$COMMON_SCRIPT_PATH/tools/clangd-config.yaml" "$OPENHARMONY_CODE_PATH/.clangd"; then
        printf '[%s] [失败] clangd 索引配置\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_PATH"
        status=1
    fi

    # 安装 clangd 编译数据库优化工具。
    if ! { [ -f "$packaged_tool" ] && mkdir -p "$CLANGD_ROOT/tools" "$CLANGD_DATA_PATH" && ln -sfn "$packaged_tool" "$tool_path"; }; then
        printf '[%s] [失败] clangd 优化工具\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_PATH"
        status=1
    fi

    # 配置并校验 clangd 的 GN 自动更新逻辑。
    local result
    if ! result="$(python3 -B "$COMMON_SCRIPT_PATH/tools/patch_gn_for_clangd.py" "$OPENHARMONY_CODE_PATH" 2>&1)"; then
        printf '%s\n' "$result" >> "$LOG_PATH"
        status=1
    fi
    return "$status"
}

# 修复导致增量构建重复执行的输出规则。
function patchIncrementalBuild() {
    python3 -B "$COMMON_SCRIPT_PATH/tools/patch_incremental_build.py" "$OPENHARMONY_CODE_PATH" >> "$LOG_PATH" 2>&1
}

# 统一配置开发环境；各项独立执行、记录结果，单项失败不影响后续配置。
function setupDevelopmentEnvironment() {
    runStep 1 writeVscodeSettings
    runStep 1 setupBundleManagerGitExclude
    runStep 1 patchBuildEnvironment
    runStep 1 setupClangdOptimization
    runStep 1 patchIncrementalBuild
}

# 注释 build.sh 中的 ohpm 初始化退出逻辑。
function patchOhpmInitialization() {
    python3 -B "$COMMON_SCRIPT_PATH/tools/patch_ohpm_initialization.py" "$OPENHARMONY_CODE_PATH"
}

# 帮助信息
function printHelp() {
    cat <<'EOF'
用法：
  ./down.sh <命令> [参数]

日志：
  重要命令的执行时间、完整命令和最终状态追加写入当前工作目录的 down.log。

命令：
  -h, --help
      显示帮助信息。

  -p, --pull [flash]
      删除现有 code，重新执行 repo init、repo sync、Git LFS 和预编译下载，并配置开发环境。
      依次编译 rk3568 镜像、Windows SDK、bundle_tool_test 和 bundle_framework_test，不编译 XTS。
      整个流程默认开启 ccache 详细日志。
      镜像或 SDK 首次失败时应用对应修复并重试一次；TDD 首次失败时应用目标修复并重试一次。
      镜像和 SDK 编译成功后自动复制，产物名称追加 base。
      默认不运行 TDD 和 XTS。
      flash   镜像复制后执行刷机；运行编译成功的 TDD，并使用 Windows 中现有产物运行 bundlemanager XTS。
              报告目录名追加工作版本，例如 (<工作目录名>base)。

  -c, --continue [flash]
      在代码、预编译和开发环境已经准备完成时，继续编译镜像、SDK 和两个默认 TDD 目标。
      整个流程默认开启 ccache 详细日志。
      每项编译失败时最多再执行一次；成功的镜像和 SDK 自动复制，产物名称追加 base。
      flash   镜像复制后执行刷机，并将编译成功的 TDD 目标合并运行。

  -u, --update [flash]
      暂存各仓本地修改，回到 manifest 指定版本，更新代码和预编译，配置开发环境并重新编译 rk3568。
      编译成功后将镜像保存到 images<工作目录名>base，并创建 <工作目录名>base.txt。
      flash   镜像复制后执行刷机；默认不刷机。

  -arkuix
      删除现有 code，重新拉取 ArkUI-X master 代码和 Git LFS，并下载 ArkUI-X 预编译。
      预编译首次下载失败时自动应用兼容修复。
      编译 Android 目标、生成 compile_commands.json，将组件保存为 <版本名>base，随后使用 VS Code 打开源码根目录。

  -buildArkuiX [save] [fast]
      编译当前 ArkUI-X Android 代码，默认替换 D:\Path\ArkUI-X\26.1.0\arkui-x。
      save   不替换默认 SDK，使用去掉 arkui-x 前缀的工作目录名新建组件目录。
      fast   启用快速重编译。

  -copyArkuiX
      不执行编译，直接使用现有 ArkUI-X 构建产物替换 Windows SDK。

  -pr <GitCode PR地址>
      自动定位 PR 对应的本地子仓，应用并暂存 PR Diff；不暂存工作区原有修改，也不创建提交。
      示例：./down.sh -pr https://gitcode.com/openharmony/bundlemanager_bundle_framework/pull/12346

  -build [flash]
      在 base 成功的基础上验证 PR 或本地修改；编译 image、SDK、bundle_tool_test 和 bundle_framework_test。
      image 和 SDK 编译成功后自动复制；默认不复制或运行 TDD。
      flash   镜像复制后执行刷机，复制并运行编译成功的 TDD，再使用 Windows 现有产物运行 bundlemanager XTS。
              TDD 和 XTS 报告目录追加当前工作目录名，例如 (1030)。

  -clangd
      安装或刷新 clangd 优化配置。

  -testVscode
      使用统一的 C/C++ 格式化规则覆盖 /home/shjb/work/test 下各 Git 仓库的 VS Code 设置。

  -ohpm
      注释 build.sh 中的 ohpm 初始化失败退出逻辑。

  -fix [image] [sdk] [tdd <编译目标>] [arkuix]
      手动应用当前已知的构建修复；不传参数时应用 image 和 sdk 修复，可重复执行。
      arkuix                      修复 ArkUI-X 预编译下载请求和错误返回。
      tdd ace_engine_test        应用 ace_engine_test 的 TDD 构建修复，当前不修改源码。
      tdd bundle_framework_test  应用 bundle_framework_test 的 TDD 构建修复，当前不修改源码。

  -image [clangd] [fast] [flash] [cachelog]
      编译 rk3568 镜像。
      clangd  生成 compile_commands.json。
      fast    启用快速重编译。
      flash   编译并复制成功后执行刷机。
      cachelog  临时开启本次编译的 ccache 详细日志。
      默认只复制镜像，不刷机。

  -copyImage [base] [flash] [device=<connect-key>]
      将 rk3568 镜像同步到 D:\rk3568\images<工作目录名>。
      base    目标目录和标记文件名称追加 base。
      flash   临时切换为 images，启动 RKDevTool 并让设备进入 Loader。
              识别到 Loader 后自动点击“执行”；刷机失败时重新点击，最多执行三次。
              刷机结束后自动关闭 RKDevTool；三次均失败时返回错误，但不阻塞后续流程。
      device  检测到多个 HDC 设备时指定 connect-key。
              RKDevTool 关闭后，脚本会恢复新旧镜像目录的名称。

  -flash
      使用已经复制好的 images<工作目录名>base 镜像补做刷机，不重新复制或编译。
      刷机成功后运行 ace_engine 和 bundle_framework TDD，并生成一份带 base 标记的报告。

  -so
      将当前 rk3568 Ace Engine 的 ABC 和 SO 推送到 rk3568 板子，然后重启设备。

  -addr <SO文件名> <地址 ...>
      在 out/rk3568/lib.unstripped 中查找指定 SO，并将一个或多个地址转换为函数名、源码文件和行号。
      示例：./down.sh -addr libarkui_navigator.z.so 0x4504 0x476c

  -sdk [1.1] [full] [fast] [cachelog]
      编译 OpenHarmony SDK。
      默认      完整 SDK + 完整 ArkTS，仅生成 Windows SDK。
      1.1       不启用完整 ArkTS。
      full      生成 Windows、Linux、OHOS SDK。
      fast      复用上一次 GN 配置进行快速重编译。
      cachelog  临时开启本次编译的 ccache 详细日志。
      编译成功后自动复制 Windows SDK，并将编译命令写入标记文件。

  -copySdk
      将 Windows SDK 压缩包复制到 D:\Path\SDK 下的新目录并解压。
      默认使用工作目录名作为目录名，例如 work/<工作目录名> 对应 <工作目录名>。

  -previewer
      将已编译 SDK 的 Windows 预览器覆盖到 D:\Path\SDK\26.1.0\previewer\common\bin。
      替换前自动关闭正在运行的 Previewer.exe，不关闭 DevEco Studio。
      只替换可执行程序、DLL、运行时模块和字体，不替换 common\resources。

  -syncTdd
      将 TDD 超时时间设置为 60 秒、配置 Windows 测试目录，再同步 developer_test 和 xdevice 到 D:\rk3568\TDD。
      只保留 developer_test 中的历史报告，其余内容全部同步。

  -tdd [目标] [fast] [cachelog] [run [测试类 [测试用例]] | report [报告参数 ...]]
      编译 rk3568 TDD 测试目标。
      默认      只编译 Ace Engine 全部测试，目标为 ace_engine_test。
      目标      编译一个 GN/Ninja 测试目标；可以是部件测试目标或单个测试套。
      fast      复用上一次 GN 配置进行快速重编译。
      cachelog  临时开启本次编译的 ccache 详细日志。
      run       编译后通过 HDC 直接运行单个测试套，可继续指定测试类和测试用例，不生成报告。
      report    编译并复制后通过 TDD 框架运行，可继续传入 TDD 框架参数，生成报告。
      run 和 report 的参数规则与 -copyTdd 完全相同。

  -copyTdd [部件名|测试套] [run [测试类 [测试用例]] | report [报告参数 ...] [tag=<标记>]]
      默认处理完整的 ace_engine 部件。
      部件名 复制完整部件目录；支持默认复制和 report，不支持 run。
      测试套 复制模式下替换测试套所在的最小目录；run 模式下直接推送并运行。
      run     通过 HDC 直接运行单个测试套，不生成报告；测试类和测试用例都可省略。
              只传测试类时运行该类的全部用例，同时传测试类和测试用例时只运行指定用例。
      report  复制成功后通过 TDD 框架运行并输出报告。

      report 自动参数：
        -t UT               固定运行单元测试。
        -tp 部件名          根据输入的部件或测试套路径自动确定部件。
        -ts 测试套名        输入单个测试套时自动添加，只运行该测试套。
                            输入部件名时不添加 -ts，运行该部件下的全部测试套。
        tag=<标记>          报告目录名追加指定标记，例如 tag=1030base 对应 (1030base)。

      report 常用参数：
        -tm 模块名          只运行部件中的指定测试模块。
        -tc 类名.用例名     只运行指定用例；类名.* 表示运行该类的全部用例。
        -tl 级别            只运行指定级别，可选 0～4，多个级别使用逗号分隔；不能和 -tc 同时使用。
        -iter 次数          在一次框架任务内通过 gtest 重复运行测试。
        --repeat 次数       让 TDD 框架重复执行整个测试任务。
        -ra random          随机打乱 gtest 用例执行顺序。
        -ta 参数            传递驱动参数，格式为 键:值；多个参数使用分号分隔。
        -hlg                不在控制台显示任务运行日志，报告仍会生成。
        -hg 0               不采集或显示设备 hilog。
        -cov                执行覆盖率流程，需要框架已经配置覆盖率环境。

      report 参数会原样传给 TDD 框架，不需要再次传 run、-t UT、-tp 或 -ts。

  -xts [dynamic|static] [套件列表|full] [run]
      编译一个、多个或全部 XTS 测试套件，并复制测试产物。
      默认    编译 dynamic 测试套件。
      dynamic 编译非强基测试套件，也是默认值。
      static  编译强基测试套件。
      多个套件使用分号分隔，参数需要放在引号中。
      不传套件或传入 full 时编译全部套件。
      run     复制后通过对应的 XTS 框架执行本次编译产物。

  -copyXTS [dynamic|static] [run]
      将现有编译产物复制到对应的 Windows XTS 框架。
      默认复制到 D:\rk3568\XTS\dynamic\acts\testcases。
      static  复制到 D:\rk3568\XTS\static\acts\testcases。
      run     复制后执行 XTS 框架命令 run acts。

  -findXTS 字符串 [...]
      在 ArkUI XTS 源码中按一个或多个固定字符串分别查找测试套件。
      搜索时忽略 // 和 /* */ 注释中的内容。
      输出格式为 dynamic：套件一;套件二; 和 static：套件一;套件二;。

  -fan [秒数|auto]
      默认将两个主板风扇调到最高转速，10 秒后自动恢复主板调速。
      秒数    自定义最高转速持续时间，例如 -fan 60。
      auto    立即恢复主板自动调速。

  -win image [Windows 压缩包路径]
  -win tdd [Windows 压缩包路径] <部件或测试套>
  -win xts [Windows 压缩包路径] <subsystem或测试套>
      使用 Windows 7-Zip 依次解压外层和内层压缩包，并自动定位对应产物。
      image   外层解压到 temp，内层 tar 解压到 imagestemp，临时切换后刷机并恢复原 images。
      tdd     传入部件名时执行整个部件，传入测试套时自动识别所属部件并执行该测试套。
      xts     传入 subsystem 时执行整个子系统，传入测试套时执行对应 test list。
      不传压缩包时跳过解压和目录替换，直接使用当前 imagestemp、TDD或XTS产物执行。
      示例：./down.sh -win image "C:\Users\Administrator\Downloads\Artifacts-dayu200.tar.gz"
            ./down.sh -win tdd "C:\Users\Administrator\Downloads\Artifacts-tdd.tar.gz" bundle_framework
            ./down.sh -win xts bundlemanager

  -screen <on|off>
      on   唤醒并解锁板子，关闭 USB 连接方式弹窗，然后设置屏幕常亮。
      off  关闭板子屏幕。

关键示例：
代码拉取和验证：
  ./down.sh -h
  ./down.sh -p flash
  ./down.sh -c
  ./down.sh -u flash
  ./down.sh -pr https://gitcode.com/openharmony/bundlemanager_bundle_framework/pull/12346
  ./down.sh -build flash

ArkUI-X：
  ./down.sh -arkuix
  ./down.sh -buildArkuiX fast save
  ./down.sh -copyArkuiX

开发环境：
  ./down.sh -clangd
  ./down.sh -testVscode
  ./down.sh -ohpm
  ./down.sh -fix image

镜像和系统产物：
  ./down.sh -image clangd fast
  ./down.sh -copyImage base flash
  ./down.sh -flash
  ./down.sh -so
  ./down.sh -addr libarkui_navigator.z.so 0x4504 0x476c

SDK：
  ./down.sh -sdk 1.1 full fast
  ./down.sh -copySdk
  ./down.sh -previewer

TDD：
  ./down.sh -syncTdd
  ./down.sh -tdd select_test_ng run SelectControlSizeNg ResetShowInSubWindow001
  ./down.sh -copyTdd bundle_framework report

XTS：
  ./down.sh -xts dynamic "ActsAceBasicSelectTest;ActsAceCArkUI22Test;" run
  ./down.sh -copyXTS static run
  ./down.sh -findXTS "字符串一" "字符串二"

Windows 流水线产物：
  ./down.sh -win image "C:\Users\Administrator\Downloads\Artifacts-dayu200.tar.gz"
  ./down.sh -win tdd "C:\Users\Administrator\Downloads\Artifacts-tdd.tar.gz" bundle_framework
  ./down.sh -win xts bundlemanager

设备控制：
  ./down.sh -fan 60
  ./down.sh -screen on
EOF
}

# 代码拉取和更新
function pullCode() {
    local image_mode=copy argument
    for argument in "$@"; do
        case "$argument" in
            flash)
                image_mode=flash
                ;;
            *)
                echo "错误：不支持的拉取参数：$argument" >&2
                return 1
            ;;
        esac
    done

    export CCACHE_LOGFILE="$HOME/.ccache/ccache.log"

    runStep 1 rm -rf -- "$OPENHARMONY_CODE_PATH"
    runStep 1 mkdir -p "$OPENHARMONY_CODE_PATH"
    runStep 1 cd "$OPENHARMONY_CODE_PATH"
    runStep 3 repo init -u https://gitcode.com/openharmony/manifest.git -b master --no-repo-verify
    runStep 3 repo sync -c
    runStep 3 repo forall -c 'git lfs pull'
    runStep 3 bash build/prebuilts_download.sh
    setupDevelopmentEnvironment

    local image_status=1
    local -a image_command=(./build.sh --product-name rk3568 --ccache --gn-flags="--export-compile-commands")
    runStep 1 "${image_command[@]}"
    local build_rk3568_status=$?
    if [ "$build_rk3568_status" -eq 0 ]; then
        runStep 1 patchBuildCompatibility --remove image
    else
        runStep 1 patchBuildCompatibility image
        runStep 1 "${image_command[@]}"
        build_rk3568_status=$?
    fi
    if [ "$build_rk3568_status" -eq 0 ]; then
        runStep 1 patchOhpmInitialization
        runStep 1 copyImage base "$image_mode"
        image_status=$?
    fi

    local -a sdk_command=(./build.sh --product-name ohos-sdk --gn-args "sdk_build_arkts=true sdk_platform=win" --ccache)
    runStep 1 "${sdk_command[@]}"
    local build_sdk_status=$?
    if [ "$build_sdk_status" -eq 0 ]; then
        runStep 1 patchBuildCompatibility --remove sdk
    else
        runStep 1 patchBuildCompatibility sdk
        runStep 1 "${sdk_command[@]}"
        build_sdk_status=$?
    fi
    if [ "$build_sdk_status" -eq 0 ]; then
        runStep 1 copySdk base "${sdk_command[@]}"
    fi

    local tdd_target
    local -a tdd_parts=()
    # for tdd_target in ace_engine_test bundle_framework_test; do
    for tdd_target in bundle_framework_test; do
    # for tdd_target in bundle_tool_test bundle_framework_test; do
        local -a tdd_command=(./build.sh --product-name rk3568 --ccache --build-target "$tdd_target")
        runStep 1 "${tdd_command[@]}"
        local tdd_status=$?
        if [ "$tdd_status" -eq 0 ]; then
            runStep 1 patchBuildCompatibility --remove tdd "$tdd_target"
        else
            runStep 1 patchBuildCompatibility tdd "$tdd_target"
            runStep 1 "${tdd_command[@]}"
            tdd_status=$?
        fi
        if [ "$tdd_status" -eq 0 ]; then
            tdd_parts+=("${tdd_target%_test}")
        fi
    done

    # runStep 1 code ./foundation/arkui/ace_engine --goto ./foundation/arkui/ace_engine/adapter/ohos/services/uiservice/src/common_statistic_event.cpp:1
    runStep 1 code . --goto ./foundation/bundlemanager/bundle_framework/services/bundlemgr/src/bundle_multiuser_installer.cpp:1

    if [ "$image_mode" = flash ] && [ "$image_status" -eq 0 ]; then
        if [ "${#tdd_parts[@]}" -gt 0 ]; then
            local tdd_part
            for tdd_part in "${tdd_parts[@]:1}"; do
                runStep 1 copyTdd "$tdd_part"
            done
            runStep 1 copyTdd "${tdd_parts[0]}" report "${tdd_parts[@]:1}" "tag=${OPENHARMONY_WORK_PATH##*/}base"
        fi
        runStep 1 runWindowsPackage xts bundlemanager "tag=${OPENHARMONY_WORK_PATH##*/}base"
    fi
    echo "详细日志：$LOG_PATH"
}

function pullCodeContinue() {
    local image_mode=copy argument
    for argument in "$@"; do
        case "$argument" in
            flash)
                image_mode=flash
                ;;
            *)
                echo "错误：不支持的继续执行参数：$argument" >&2
                return 1
            ;;
        esac
    done

    export CCACHE_LOGFILE="$HOME/.ccache/ccache.log"

    runStep 1 cd "$OPENHARMONY_CODE_PATH"

    local image_status=1
    local -a image_command=(./build.sh --product-name rk3568 --ccache --gn-flags="--export-compile-commands")
    runStep 2 "${image_command[@]}"
    local build_rk3568_status=$?
    if [ "$build_rk3568_status" -eq 0 ]; then
        runStep 1 copyImage base "$image_mode"
        image_status=$?
    fi

    local -a sdk_command=(./build.sh --product-name ohos-sdk --gn-args "sdk_build_arkts=true sdk_platform=win" --ccache)
    runStep 2 "${sdk_command[@]}"
    local build_sdk_status=$?
    if [ "$build_sdk_status" -eq 0 ]; then
        runStep 1 copySdk base "${sdk_command[@]}"
    fi

    local tdd_target
    local -a tdd_parts=()
    for tdd_target in ace_engine_test bundle_framework_test; do
        local -a tdd_command=(./build.sh --product-name rk3568 --ccache --build-target "$tdd_target")
        runStep 2 "${tdd_command[@]}"
        local tdd_status=$?
        if [ "$tdd_status" -eq 0 ]; then
            tdd_parts+=("${tdd_target%_test}")
        fi
    done
    if [ "$build_rk3568_status" -eq 0 ] && [ "$build_sdk_status" -eq 0 ]; then
        runStep 1 patchOhpmInitialization
    fi
    runStep 1 code ./foundation/arkui/ace_engine --goto ./foundation/arkui/ace_engine/adapter/ohos/services/uiservice/src/common_statistic_event.cpp:1
    
    if [ "$image_mode" = flash ] && [ "$image_status" -eq 0 ] && [ "${#tdd_parts[@]}" -gt 0 ]; then
        local tdd_part
        for tdd_part in "${tdd_parts[@]:1}"; do
            runStep 1 copyTdd "$tdd_part"
        done
        runStep 1 copyTdd "${tdd_parts[0]}" report "${tdd_parts[@]:1}" "tag=${OPENHARMONY_WORK_PATH##*/}base"
    fi
    echo "详细日志：$LOG_PATH"
}

function updateCode() {
    local image_mode=copy argument
    for argument in "$@"; do
        case "$argument" in
            flash)
                image_mode=flash
                ;;
            *)
                echo "错误：不支持的更新参数：$argument" >&2
                return 1
                ;;
        esac
    done

    runStep 1 cd "$OPENHARMONY_CODE_PATH"
    runStep 1 rm -rf -- "$OPENHARMONY_CODE_PATH/vendor" "$OPENHARMONY_CODE_PATH/device"
    runStep 1 repo forall -c 'git stash'
    runStep 2 repo sync -c -d
    runStep 2 repo forall -c 'git lfs pull'
    runStep 2 bash build/prebuilts_download.sh
    setupDevelopmentEnvironment

    local -a image_command=(./build.sh --product-name rk3568 --ccache --gn-flags="--export-compile-commands")
    runStep 1 "${image_command[@]}"
    local build_rk3568_status=$?
    if [ "$build_rk3568_status" -eq 0 ]; then
        runStep 1 copyImage base "$image_mode"
        runStep 1 patchOhpmInitialization
    fi
    runStep 1 code ./foundation/arkui/ace_engine --goto ./foundation/arkui/ace_engine/adapter/ohos/services/uiservice/src/common_statistic_event.cpp:1
    echo "详细日志：$LOG_PATH"
}

# ArkUI-X
function pullArkuiX() {
    runStep 1 rm -rf -- "$OPENHARMONY_CODE_PATH"
    runStep 1 mkdir -p "$OPENHARMONY_CODE_PATH"
    runStep 1 cd "$OPENHARMONY_CODE_PATH"
    runStep 3 repo init -u https://gitcode.com/arkui-x/manifest.git -b master --no-repo-verify
    runStep 3 repo sync -c
    runStep 3 repo forall -c 'git lfs pull'
    runStep 1 writeVscodeSettings arkuix
    local -a prebuilt_command=(bash build/prebuilts_download.sh --build-arkuix --skip-ssl)
    runStep 1 "${prebuilt_command[@]}"
    local prebuilt_status=$?
    if [ "$prebuilt_status" -eq 0 ]; then
        runStep 1 patchBuildCompatibility --remove arkuix
    else
        runStep 1 patchBuildCompatibility arkuix || return 1
        runStep 1 "${prebuilt_command[@]}"
        prebuilt_status=$?
    fi
    if [ "$prebuilt_status" -ne 0 ]; then
        return 1
    fi
    runStep 1 ./build.sh --product-name arkui-x --target-os android --ccache --gn-flags="--export-compile-commands" || return 1
    copyArkuiX base
    runStep 1 code . --goto ./foundation/arkui/ace_engine/frameworks/core/components_ng/pattern/dialog/dialog_pattern.cpp:1
}

function buildArkuiX() {
    local copy_mode="" argument
    local -a build_command=(./build.sh --product-name arkui-x --target-os android --ccache)
    for argument in "$@"; do
        case "$argument" in
            save) copy_mode=save ;;
            fast) build_command+=(--fast-rebuild) ;;
            *)
                echo "错误：不支持的 ArkUI-X 编译参数：$argument" >&2
                return 1
                ;;
        esac
    done

    cd "$OPENHARMONY_CODE_PATH"
    runStep 1 "${build_command[@]}" || return 1
    if [ "$copy_mode" = save ]; then
        copyArkuiX save
    else
        copyArkuiX
    fi
}

function copyArkuiX() {
    local target_name='26.1.0/arkui-x'
    local argument
    for argument in "$@"; do
        case "$argument" in
            base)
                target_name="26.1.0/${OPENHARMONY_WORK_PATH##*/arkui-x}base"
                ;;
            save)
                target_name="26.1.0/${OPENHARMONY_WORK_PATH##*/arkui-x}"
                ;;
            *)
                echo "错误：不支持的 ArkUI-X 替换参数：$argument" >&2
                return 1
                ;;
        esac
    done

    local source_path="$(wslpath -w "$OPENHARMONY_CODE_PATH$ARKUIX_WINDOWS_SDK_PATH")"
    local target_path="$(wslpath -w "$WINDOW_ARKUIX_PATH/$target_name")"
    echo "正在替换 ArkUI-X Windows SDK：$target_path"
    runStep 1 runWindows "$WINDOW_CMD_PATH" /d /c "$WINDOW_ARKUIX_COPY_SCRIPT" "$source_path" "$target_path" || return 1
    echo "ArkUI-X Windows SDK 已更新：$target_path"
}

# 下载 GitCode PR Diff，并应用和暂存到对应的本地子仓。
function applyPullRequest() {
    local pr_url="${1%/}"
    if [[ ! "$pr_url" =~ ^https://gitcode\.com/[^/]+/([^/]+)/pull/[0-9]+$ ]]; then
        echo "错误：请提供完整的 GitCode PR 地址。" >&2
        return 1
    fi

    local repository_name="${BASH_REMATCH[1]}"
    local repository_path
    repository_path="$(cd "$OPENHARMONY_CODE_PATH" && repo list | awk -F ' : ' -v project="$repository_name" '$2 == project {print $1; exit}')"
    if [ -z "$repository_path" ]; then
        echo "错误：本地代码中未找到 PR 对应仓库：$repository_name" >&2
        return 1
    fi

    local diff_file
    diff_file="$(mktemp --suffix=.diff)" || return 1
    if ! curl -fsSL --retry 2 "${pr_url}.diff" -o "$diff_file"; then
        echo "错误：PR Diff 下载失败：$pr_url" >&2
        rm -f -- "$diff_file"
        return 1
    fi
    if ! grep -q '^diff --git ' "$diff_file"; then
        echo "错误：下载内容不是有效的 Git Diff。" >&2
        rm -f -- "$diff_file"
        return 1
    fi

    local repository="$OPENHARMONY_CODE_PATH/$repository_path"
    local status=0
    if git -C "$repository" apply --check -- "$diff_file" 2>/dev/null &&
        git -C "$repository" apply --cached --check -- "$diff_file" 2>/dev/null; then
        runStep 1 git -C "$repository" apply -- "$diff_file"
        status=$?
        if [ "$status" -eq 0 ]; then
            runStep 1 git -C "$repository" apply --cached -- "$diff_file"
            status=$?
        fi
        if [ "$status" -eq 0 ]; then
            echo "PR 已应用并暂存到：$repository_path"
        fi
    elif git -C "$repository" apply --reverse --check -- "$diff_file" 2>/dev/null &&
        git -C "$repository" apply --cached --reverse --check -- "$diff_file" 2>/dev/null; then
        echo "PR 已经应用并暂存，无需重复操作：$repository_path"
    elif git -C "$repository" apply --reverse --check -- "$diff_file" 2>/dev/null &&
        git -C "$repository" apply --cached --check -- "$diff_file" 2>/dev/null; then
        runStep 1 git -C "$repository" apply --cached -- "$diff_file"
        status=$?
        if [ "$status" -eq 0 ]; then
            echo "PR 已存在于工作区，现已单独暂存：$repository_path"
        fi
    else
        echo "错误：PR Diff 与当前工作区或暂存区不匹配，未应用 PR。" >&2
        status=1
    fi

    rm -f -- "$diff_file"
    return "$status"
}

# 编译并验证。
function build() {
    local image_mode=copy argument
    for argument in "$@"; do
        case "$argument" in
            flash)
                image_mode=flash
                ;;
            *)
                echo "错误：不支持的增量编译参数：$argument" >&2
                return 1
                ;;
        esac
    done

    local image_status
    if [ "$image_mode" = flash ]; then
        buildImages flash
    else
        buildImages
    fi
    image_status=$?

    buildOhosSdk

    local tdd_target tdd_part
    local -a tdd_parts=()
    for tdd_target in bundle_framework_test; do
    # for tdd_target in bundle_tool_test bundle_framework_test; do
        if buildTdd "$tdd_target"; then
            tdd_parts+=("${tdd_target%_test}")
        fi
    done

    runStep 1 code ./foundation/arkui/ace_engine --goto ./foundation/arkui/ace_engine/adapter/ohos/services/uiservice/src/common_statistic_event.cpp:1

    if [ "$image_mode" = flash ] && [ "$image_status" -eq 0 ]; then
        if [ "${#tdd_parts[@]}" -gt 0 ]; then
            for tdd_part in "${tdd_parts[@]:1}"; do
                runStep 1 copyTdd "$tdd_part"
            done
            runStep 1 copyTdd "${tdd_parts[0]}" report "${tdd_parts[@]:1}" "tag=${OPENHARMONY_WORK_PATH##*/}"
        fi
        runStep 1 runWindowsPackage xts bundlemanager "tag=${OPENHARMONY_WORK_PATH##*/}"
    fi
    echo "详细日志：$LOG_PATH"
}

# 镜像
function buildImages() {
    local image_mode=copy argument
    local -a build_command=(./build.sh --product-name rk3568 --ccache)

    for argument in "$@"; do
        case "$argument" in
            clangd)
                build_command+=(--gn-flags=--export-compile-commands)
                ;;
            fast)
                build_command+=(
                    --fast-rebuild
                    --deps-guard=false
                    --get-warning-list=false
                    --generate-ninja-trace=false
                    --compute-overlap-rate=false
                )
                ;;
            flash)
                image_mode=flash
                ;;
            cachelog)
                export CCACHE_LOGFILE="$HOME/.ccache/ccache.log"
                ;;
            *)
                echo "错误：不支持的镜像编译参数：$argument" >&2
                return 1
                ;;
        esac
    done

    cd "$OPENHARMONY_CODE_PATH" || return 1
    runStep 1 "${build_command[@]}" || return 1
    copyImage "$image_mode"
}

function copyImage() {
    local suffix="" mode=copy connect_key="" argument

    for argument in "$@"; do
        case "$argument" in
            base)  suffix=base ;;
            copy)  mode=copy ;;
            flash) mode=flash ;;
            device=*) connect_key="${argument#device=}" ;;
            *)
                echo "错误：不支持的镜像复制参数：$argument" >&2
                return 1
                ;;
        esac
    done

    local work_name="${OPENHARMONY_WORK_PATH##*/}$suffix"
    local image_path="$WINDOWS_IMAGE_PATH$work_name"
    local marker_name="$work_name.txt"
    local source_path="$(wslpath -w "$OPENHARMONY_CODE_PATH$IMAGE_PATH")"
    local target_path="$(wslpath -w "$image_path")"

    echo "正在复制镜像到：$target_path"
    if runStep 1 runWindows "$WINDOW_CMD_PATH" /d /c "$WINDOW_IMAGE_SCRIPT" "$source_path" "$target_path"; then
        : > "$image_path/$marker_name" || return 1
        echo "镜像已更新：$target_path"
    else
        echo "镜像更新失败。" >&2
        return 1
    fi

    if [ "$mode" = flash ]; then
        runStep 1 runWindows "$WINDOW_RKDEVTOOL_CONTROL" "$target_path" "$connect_key"
    fi
}

function flashImage() {
    if runStep 1 runWindows "$WINDOW_RKDEVTOOL_CONTROL" "$(wslpath -w "$WINDOWS_IMAGE_PATH${OPENHARMONY_WORK_PATH##*/}base")"; then
        copyTdd bundle_framework
        copyTdd ace_engine report bundle_framework "tag=${OPENHARMONY_WORK_PATH##*/}base"
    else
        return 1
    fi
    # copyTdd bundle_framework report "tag=${OPENHARMONY_WORK_PATH##*/}base"
}

function pushSo() {
    local source_path="$(wslpath -w "$OPENHARMONY_CODE_PATH$SYSTEM_PATH")"
    runStep 1 runWindows "$WINDOW_CMD_PATH" /d /c "$WINDOW_RK3568_SO_SCRIPT" "$source_path"
}

function symbolizeAddress() {
    local so_name="$1"
    shift
    if [ -z "$so_name" ] || [ "$#" -eq 0 ]; then
        echo "错误：请输入 SO 文件名和至少一个地址。" >&2
        return 1
    fi

    local so_path
    so_path="$(find "$OPENHARMONY_CODE_PATH/out/rk3568/lib.unstripped" -type f -name "$so_name" -print -quit)"
    if [ -z "$so_path" ]; then
        echo "错误：未找到 SO：$so_name" >&2
        return 1
    fi

    echo "符号文件：${so_path#"$OPENHARMONY_CODE_PATH/"}"
    "$OPENHARMONY_CODE_PATH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-addr2line" -aifC -e "$so_path" "$@"
}

# SDK
function buildOhosSdk() {
    local full_arkts=true windows_only=true fast_rebuild=false argument
    local -a build_args

    for argument in "$@"; do
        case "$argument" in
            1.1)
                full_arkts=false
                ;;
            full)
                windows_only=false
                ;;
            fast)
                fast_rebuild=true
                ;;
            cachelog)
                export CCACHE_LOGFILE="$HOME/.ccache/ccache.log"
                ;;
            *)
                echo "错误：不支持的 SDK 编译参数：$argument" >&2
                return 1
                ;;
        esac
    done

    if [ "$full_arkts" = true ] && [ "$windows_only" = true ]; then
        build_args+=(--gn-args "sdk_build_arkts=true sdk_platform=win")
    elif [ "$full_arkts" = true ]; then
        build_args+=(--gn-args sdk_build_arkts=true)
    elif [ "$windows_only" = true ]; then
        build_args+=(--gn-args sdk_platform=win)
    fi

    if [ "$fast_rebuild" = true ]; then
        build_args+=(--fast-rebuild)
    fi

    cd "$OPENHARMONY_CODE_PATH" || return 1
    local -a build_command=(./build.sh --product-name ohos-sdk --ccache "${build_args[@]}")
    runStep 1 "${build_command[@]}" || return 1
    copySdk "${build_command[@]}"
}

function copySdk() {
    local suffix="" argument
    local -a command_args=()

    for argument in "$@"; do
        case "$argument" in
            base) suffix=base ;;
            *)    command_args+=("$argument") ;;
        esac
    done

    local target_name="$(basename -- "$OPENHARMONY_WORK_PATH")$suffix"
    local target_path="$WINDOW_SDK_PATH/$target_name"
    local source_path="$(wslpath -w "$OPENHARMONY_CODE_PATH$SDK_WINDOWS_PACKAGE_PATH")"
    local windows_path="$(wslpath -w "$target_path")"

    local build_command
    if [ "${#command_args[@]}" -gt 0 ]; then
        printf -v build_command '%q ' "${command_args[@]}"
        build_command="${build_command% }"
    fi

    echo "正在复制 Windows SDK 到：$windows_path"
    if runStep 1 runWindows "$WINDOW_CMD_PATH" /d /c "$WINDOW_SDK_SCRIPT" "$source_path" "$windows_path"; then
        if [ -n "$build_command" ]; then
            printf '%s\n' "$build_command" > "$target_path/$target_name.txt" || return 1
        fi
        echo "Windows SDK 已更新：$windows_path"
    else
        echo "Windows SDK 更新失败。" >&2
        return 1
    fi
}

function replacePreviewer() {
    local source_path="$OPENHARMONY_CODE_PATH$PREVIEWER_BIN_PATH"
    local target_path="$WINDOW_PREVIEWER_PATH"

    if [ ! -d "$source_path" ]; then
        echo "错误：未找到已编译的 Windows 预览器：$source_path" >&2
        return 1
    fi
    if [ ! -d "$target_path" ]; then
        echo "错误：未找到预览器目标目录：$(wslpath -w "$target_path")" >&2
        return 1
    fi

    echo "正在替换预览器：$(wslpath -w "$target_path")"
    runStep 1 runWindows "$WINDOW_CMD_PATH" /d /c "$WINDOW_PREVIEWER_SCRIPT" "$(wslpath -w "$source_path")" "$(wslpath -w "$target_path")" || return 1
    echo "预览器已更新：$(wslpath -w "$target_path")"
}

# 配置源码并更新 Windows TDD 框架。
function syncTddEnvironment() {
    python3 -B "$COMMON_SCRIPT_PATH/tools/patch_tdd_environment.py" "$OPENHARMONY_CODE_PATH" >> "$LOG_PATH" 2>&1 || return 1
    runStep 1 runWindows "$WINDOW_CMD_PATH" /d /c "$WINDOW_TDD_SYNC_SCRIPT" "$(wslpath -w "$OPENHARMONY_CODE_PATH")"
}

# TDD
function buildTdd() {
    local argument target=ace_engine_test mode=
    local -a build_args=(--product-name rk3568 --ccache --get-warning-list=false
        --generate-ninja-trace=false --compute-overlap-rate=false --deps-guard=false)
    local -a extra_args=()

    for argument in "$@"; do
        if [ "$argument" = cachelog ]; then
            export CCACHE_LOGFILE="$HOME/.ccache/ccache.log"
            continue
        fi
        if [ -n "$mode" ]; then
            extra_args+=("$argument")
        else
            case "$argument" in
                fast) build_args+=(--fast-rebuild) ;;
                run|report) mode="$argument" ;;
                *) target="$argument" ;;
            esac
        fi
    done

    if [ "$mode" = run ]; then
        if [ "${#extra_args[@]}" -gt 2 ]; then
            echo "错误：run 最多只支持测试类和测试用例两个参数。" >&2
            return 1
        fi
        if [ -f "$OPENHARMONY_CODE_PATH/out/rk3568/build_configs/infos_for_testfwk.json" ] && \
                python3 -B -c 'import json, sys; data = json.load(open(sys.argv[1], encoding="utf-8")); sys.exit(sys.argv[2] not in data["phone"]["part_infos"])' \
                "$OPENHARMONY_CODE_PATH/out/rk3568/build_configs/infos_for_testfwk.json" "${target%_test}"; then
            echo "错误：run 模式需要单个可执行测试套，不能使用部件测试目标：$target" >&2
            return 1
        fi
    fi
    build_args+=(--build-target "$target")

    cd "$OPENHARMONY_CODE_PATH" || return 1
    runStep 1 ./build.sh "${build_args[@]}" || return 1

    if [ -n "$mode" ]; then
        copyTdd "$target" "$mode" "${extra_args[@]}"
    fi
}

function copyTdd() {
    local target="" mode=copy report_tag="" argument
    local -a extra_args=()

    for argument in "$@"; do
        case "$argument" in
            run|report) mode="$argument" ;;
            tag=*) report_tag="${argument#tag=}" ;;
            *)
                if [ -z "$target" ]; then
                    target="$argument"
                else
                    extra_args+=("$argument")
                fi
                ;;
        esac
    done

    if [ "$mode" = run ]; then
        case "${#extra_args[@]}" in
            0) ;;
            1) extra_args=("--gtest_filter=${extra_args[0]}.*") ;;
            2) extra_args=("--gtest_filter=${extra_args[0]}.${extra_args[1]}") ;;
            *)
                echo "错误：run 最多只支持测试类和测试用例两个参数。" >&2
                return 1
                ;;
        esac
    fi

    target="${target:-ace_engine}"
    local test_root="$OPENHARMONY_CODE_PATH$UNITTEST_PATH"
    local part_name="$target"
    local source_dir executable
    if [[ "$target" == *_test ]]; then
        part_name="${target%_test}"
    fi

    if python3 -B -c 'import json, sys; data = json.load(open(sys.argv[1], encoding="utf-8")); sys.exit(sys.argv[2] not in data["phone"]["part_infos"])' \
            "$OPENHARMONY_CODE_PATH/out/rk3568/build_configs/infos_for_testfwk.json" "$part_name"; then
        if [ "$mode" = run ]; then
            echo "错误：run 模式需要单个可执行测试套，不能使用部件：$part_name" >&2
            return 1
        fi
        source_dir="$test_root/unittest/$part_name"
        if [ ! -d "$source_dir" ]; then
            echo "错误：TDD 框架认可部件 $part_name，但未找到已编译的测试产物。" >&2
            return 1
        fi
    else
        executable="$(find "$test_root" -type f -name "$target" -perm /111 -print -quit)"
        if [ -z "$executable" ]; then
            echo "错误：未找到可执行测试套：$target" >&2
            return 1
        fi
        source_dir="$(dirname -- "$executable")"
        part_name="${source_dir#"$test_root/unittest/"}"
        part_name="${part_name%%/*}"
    fi

    if [ "$mode" = run ]; then
        waitForDevice || return 1
        local target_path="/data/$target"
        echo "正在直接运行 TDD：$target ${extra_args[*]}"
        runStep 1 runWindows "$WINDOW_HDC_PATH" file send "$(wslpath -w "$executable")" "$target_path"
        local status=$?
        if [ "$status" -eq 0 ]; then
            echo "TDD 测试套已发送到设备：$target_path"
            runStep 1 runWindows "$WINDOW_HDC_PATH" shell chmod 777 "$target_path"
            status=$?
        fi
        if [ "$status" -eq 0 ]; then
            runStep 1 runWindows "$WINDOW_HDC_PATH" shell "cd /data && ./$target ${extra_args[*]}"
            status=$?
        fi
        return "$status"
    fi

    local target_path="$(wslpath -w "$WINDOW_TDD_TESTCASE_PATH/${source_dir#"$test_root"/}")"

    echo "正在替换 TDD 目录：$target_path"
    runStep 1 runWindows "$WINDOW_CMD_PATH" /d /c "$WINDOW_TDD_SCRIPT" "$(wslpath -w "$source_dir")" "$target_path" || return 1
    echo "TDD 已更新：$target_path"

    if [ "$mode" = report ]; then
        local -a run_args=(run -t UT -tp "$part_name")
        if [ -n "$executable" ]; then
            run_args+=(-ts "$target")
        fi
        run_args+=("${extra_args[@]}")

        waitForDevice || return 1
        echo "正在执行 TDD：${run_args[*]}"
        runReport TDD "$WINDOW_TDD_REPORT_PATH" "$report_tag" runStep 1 runWindows "$WINDOW_CMD_PATH" /d /c "$WINDOW_TDD_RUN_SCRIPT" "${run_args[@]}"
    fi
}

# XTS
function buildXTS() {
    local argument suite requested_type mode=copy
    local suite_type="" full_build=false
    local -a suites=()
    local -a parsed_suites=()
    local -a build_args=(product_name=rk3568 system_size=standard)
    local -A seen_suites=()

    for argument in "$@"; do
        requested_type=""
        case "$argument" in
            run)
                mode=run
                argument=""
                ;;
            dynamic|static)
                requested_type="$argument"
                argument=""
                ;;
            dynamic：*|static：*)
                requested_type="${argument%%：*}"
                argument="${argument#*：}"
                ;;
        esac

        if [ -n "$requested_type" ]; then
            if [ -n "$suite_type" ] && [ "$suite_type" != "$requested_type" ]; then
                echo "错误：dynamic 和 static 不能同时使用" >&2
                return 1
            fi
            suite_type="$requested_type"
        fi

        if [ -z "$argument" ]; then
            continue
        fi
        case "$argument" in
            full)
                full_build=true
                continue
                ;;
        esac

        IFS=';' read -r -a parsed_suites <<< "$argument"
        for suite in "${parsed_suites[@]}"; do
            if [ -z "$suite" ]; then
                continue
            fi
            if [ -z "${seen_suites[$suite]+x}" ]; then
                suites+=("$suite")
                seen_suites["$suite"]=1
            fi
        done
    done

    if [ "$full_build" = true ] && [ "${#suites[@]}" -gt 0 ]; then
        echo "错误：全量编译不能同时指定测试套件" >&2
        return 1
    fi

    if [ "$suite_type" = "static" ]; then
        build_args+=(xts_suitetype=hap_static)
    else
        build_args+=(xts_suitetype=bin,hap_dynamic)
    fi

    if [ "${#suites[@]}" -gt 0 ]; then
        build_args+=("suite=${suites[*]}")
    fi
    local -a generated_paths=(
        "$OPENHARMONY_CODE_PATH/out/rk3568/obj/test/xts/acts/arkui/"
        "$OPENHARMONY_CODE_PATH/out/rk3568/suites/"
        "$OPENHARMONY_CODE_PATH/out/rk3568/gen/test/xts/acts/arkui/"
    )
    runStep 1 rm -rf -- "${generated_paths[@]}" || return 1

    cd "$OPENHARMONY_CODE_PATH$XTS_CODE_PATH" || return 1
    runStep 1 ./build.sh "${build_args[@]}" || return 1
    copyXTS "${suite_type:-dynamic}" "$mode"
}

function copyXTS() {
    local argument suite_type=dynamic mode=copy

    for argument in "$@"; do
        case "$argument" in
            dynamic|static) suite_type="$argument" ;;
            copy) ;;
            run) mode=run ;;
            *)
                echo "错误：不支持的 XTS 复制参数：$argument" >&2
                return 1
                ;;
        esac
    done

    local source_path="$OPENHARMONY_CODE_PATH$XTS_TESTCASE_PATH"
    local target_root="$WINDOW_XTS_PATH/$suite_type/acts"
    if [ ! -d "$source_path" ]; then
        echo "错误：未找到已编译的 XTS 测试产物：$source_path" >&2
        return 1
    fi

    echo "正在替换 $suite_type XTS 测试套。"
    runStep 1 runWindows "$WINDOW_CMD_PATH" /d /c "$WINDOW_XTS_COPY_SCRIPT" "$(wslpath -w "$source_path")" "$(wslpath -w "$target_root/testcases")" || return 1
    echo "XTS 测试套已更新：$(wslpath -w "$target_root/testcases")"

    if [ "$mode" = run ]; then
        runStep 1 keepScreenOn || return 1
        echo "正在执行 $suite_type XTS：run acts"
        runReport XTS "$target_root/reports" "" runStep 1 runWindows "$WINDOW_CMD_PATH" /d /c "$WINDOW_XTS_RUN_SCRIPT" "$(wslpath -w "$target_root")" "run acts"
        local status=$?
        controlScreen off || status=1
        return "$status"
    fi
}

function findXTSSuites() {
    local query="$1"
    local search_root="$OPENHARMONY_CODE_PATH$XTS_CODE_PATH/arkui"
    local source_file directory build_file
    local dynamic_pattern='s/^[[:space:]]*ohos_js_app_suite\("([^"]+)"\).*/dynamic\t\1/p'
    local static_pattern='s/^[[:space:]]*ohos_js_app_static_suite\("([^"]+)"\).*/static\t\1/p'

    while IFS= read -r -d '' source_file; do
        directory="$(dirname -- "$source_file")"
        while [[ "$directory" == "$search_root"/* ]]; do
            build_file="$directory/BUILD.gn"
            if [ -f "$build_file" ]; then
                sed -nE -e "$dynamic_pattern" -e "$static_pattern" "$build_file"
                if grep -Eq '^[[:space:]]*ohos_js_app(_static)?_suite\(' "$build_file"; then
                    break
                fi
            fi
            directory="$(dirname -- "$directory")"
        done
    done < <(
        find "$search_root" -type f \( -name '*.ets' -o -name '*.ts' -o -name '*.cpp' \) -exec grep -FIlZ -- "$query" {} + |
            XTS_QUERY="$query" xargs -0 -r perl -0777 -ne '
                my $source = $_;
                $source =~ s{
                    (?:
                        "(?:\\.|[^"\\])*"
                        | \x27(?:\\.|[^\x27\\])*\x27
                        | `(?:\\.|[^`\\])*`
                    )(*SKIP)(*F)
                    | //[^\r\n]*
                    | /\*.*?\*/
                }{}gsx;
                print "$ARGV\0" if index($source, $ENV{XTS_QUERY}) >= 0;
            '
    ) | sort -u
}

function findAllXTSSuites() {
    local argument suite_type suite
    local -a dynamic_suites=()
    local -a static_suites=()
    local -A dynamic_seen=()
    local -A static_seen=()

    if [ "$#" -eq 0 ]; then
        echo "错误：请至少输入一个要查找的字符串" >&2
        return 1
    fi

    for argument in "$@"; do
        while IFS=$'\t' read -r suite_type suite; do
            if [ -z "$suite" ]; then
                continue
            fi
            if [ "$suite_type" = "static" ]; then
                if [ -z "${static_seen[$suite]+x}" ]; then
                    static_suites+=("$suite")
                    static_seen["$suite"]=1
                fi
            elif [ -z "${dynamic_seen[$suite]+x}" ]; then
                dynamic_suites+=("$suite")
                dynamic_seen["$suite"]=1
            fi
        done < <(findXTSSuites "$argument")
    done

    if [ "${#dynamic_suites[@]}" -eq 0 ] && [ "${#static_suites[@]}" -eq 0 ]; then
        echo "没有找到包含这些字符串的 XTS 测试套件" >&2
        return 1
    fi

    if [ "${#dynamic_suites[@]}" -gt 0 ]; then
        printf 'dynamic：'
        printf '%s;' "${dynamic_suites[@]}"
        printf '\n'
    fi

    if [ "${#static_suites[@]}" -gt 0 ]; then
        printf 'static：'
        printf '%s;' "${static_suites[@]}"
        printf '\n'
    fi
}

function controlFan() {
    local duration="${1:-10}"
    if [ "$duration" = auto ]; then
        runStep 1 runWindows "$WINDOW_FAN_CONTROL" auto
    else
        runStep 1 runWindows "$WINDOW_FAN_CONTROL" boost "$duration"
    fi
}

function runWindowsPackage() {
    local package_type="$1"
    local test_name archive report_tag
    case "$package_type" in
        image)
            archive="$2"
            ;;
        tdd|xts)
            if [[ "$3" == tag=* ]]; then
                test_name="$2"
                report_tag="${3#tag=}"
            elif [ -n "$3" ]; then
                archive="$2"
                test_name="$3"
                if [[ "$4" == tag=* ]]; then
                    report_tag="${4#tag=}"
                fi
            else
                test_name="$2"
            fi
            if [ -z "$test_name" ]; then
                echo "错误：请提供 $package_type 测试套。" >&2
                return 1
            fi
            ;;
        *)
            echo "错误：-win 只支持 image、tdd 或 xts。" >&2
            return 1
            ;;
    esac
    if [ -n "$archive" ]; then
        local archive_path="$archive"
        if [[ "$archive" == [A-Za-z]:\\* ]]; then
            archive_path="$(wslpath -u "$archive")"
        fi
        if [ ! -f "$archive_path" ]; then
            echo "错误：未找到压缩包：$archive" >&2
            return 1
        fi
        runStep 1 runWindows "$WINDOW_CMD_PATH" /d /c "$WINDOW_PACKAGE_EXTRACT_SCRIPT" "$package_type" "$(wslpath -w "$archive_path")" || return 1
    fi

    case "$package_type" in
        image)
            if [ ! -f "$WINDOWS_TEMP_IMAGE_PATH/config.cfg" ]; then
                echo "错误：镜像目录中未找到 config.cfg：$(wslpath -w "$WINDOWS_TEMP_IMAGE_PATH")" >&2
                return 1
            fi
            runStep 1 runWindows "$WINDOW_RKDEVTOOL_CONTROL" "$(wslpath -w "$WINDOWS_TEMP_IMAGE_PATH")"
            ;;
        tdd)
            local test_root="$WINDOW_TDD_TESTCASE_PATH/unittest"
            local -a run_args=(run -t UT)
            if [ -d "$test_root/$test_name" ]; then
                run_args+=(-tp "$test_name")
            else
                local test_path="$(find "$test_root" -type f -name "$test_name" -print -quit)"
                if [ -z "$test_path" ]; then
                    echo "错误：压缩包中未找到 TDD 部件或测试套：$test_name" >&2
                    return 1
                fi
                local part_name="${test_path#"$test_root"/}"
                part_name="${part_name%%/*}"
                run_args+=(-tp "$part_name" -ts "$test_name")
            fi
            waitForDevice || return 1
            echo "正在执行 TDD：${run_args[*]}"
            runReport TDD "$WINDOW_TDD_REPORT_PATH" "$report_tag" runStep 1 runWindows "$WINDOW_CMD_PATH" /d /c "$WINDOW_TDD_RUN_SCRIPT" "${run_args[@]}"
            ;;
        xts)
            local target_root="$WINDOW_XTS_PATH/dynamic/acts"
            local run_command
            if grep -RFq --include='*.moduleInfo' "\"subsystem\": \"$test_name\"" "$WINDOW_XTS_PATH/dynamic/acts/testcases"; then
                run_command="run acts -s $test_name"
            else
                run_command="run acts -l $test_name"
            fi
            runStep 1 keepScreenOn || return 1
            echo "正在执行 XTS：$run_command"
            runReport XTS "$target_root/reports" "$report_tag" runStep 1 runWindows "$WINDOW_CMD_PATH" /d /c "$WINDOW_XTS_RUN_SCRIPT" "$(wslpath -w "$target_root")" "$run_command"
            local status=$?
            controlScreen off || status=1
            return "$status"
            ;;
    esac
}

function controlScreen() {
    case "$1" in
        on)
            runStep 1 keepScreenOn
            ;;
        off)
            waitForDevice || return 1
            echo "正在恢复屏幕超时时间并关闭屏幕。"
            local status=0
            runStep 1 runWindows "$WINDOW_HDC_PATH" shell power-shell timeout -r >/dev/null || status=1
            runStep 1 runWindows "$WINDOW_HDC_PATH" shell power-shell suspend >/dev/null || status=1
            return "$status"
            ;;
        *)
            echo "错误：-screen 只支持 on 或 off。" >&2
            return 1
            ;;
    esac
}

# 命令入口
type=$1

case "$type" in
    -h|--help) printHelp ;;
    -p|--pull) pullCode "${@:2}" ;;
    -c|--continue) pullCodeContinue "${@:2}" ;;
    -u|--update) updateCode "${@:2}" ;;
    -arkuix) pullArkuiX ;;
    -buildArkuiX) buildArkuiX "${@:2}" ;;
    -copyArkuiX) copyArkuiX ;;
    -pr) applyPullRequest "$2" ;;
    -build) build "${@:2}" ;;
    -clangd) setupClangdOptimization ;;
    -testVscode) setupTestVscodeSettings ;;
    -ohpm) patchOhpmInitialization ;;
    -fix) patchBuildCompatibility "${@:2}" ;;
    -image) buildImages "${@:2}" ;;
    -copyImage) copyImage "${@:2}" ;;
    -flash) flashImage ;;
    -so) pushSo ;;
    -addr) symbolizeAddress "${@:2}" ;;
    -sdk) buildOhosSdk "${@:2}" ;;
    -copySdk) copySdk ;;
    -previewer) replacePreviewer ;;
    -syncTdd) syncTddEnvironment ;;
    -tdd) buildTdd "${@:2}" ;;
    -copyTdd) copyTdd "${@:2}" ;;
    -xts) buildXTS "${@:2}" ;;
    -copyXTS) copyXTS "${@:2}" ;;
    -findXTS) findAllXTSSuites "${@:2}" ;;
    -fan) controlFan "${@:2}" ;;
    -win) runWindowsPackage "${@:2}" ;;
    -screen) controlScreen "$2" ;;
    *)
        echo "错误：不支持的命令：$type" >&2
        exit 1
        ;;
esac
