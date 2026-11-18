#!/usr/bin/env python3
"""修正会导致 rk3568 增量构建反复执行的缺失输出。"""

import sys
from pathlib import Path
from patch_utils import patch_file, patch_files, run_operation

root = Path(sys.argv[1])

def patch_notice_outputs() -> bool:
    path = root / "build/ohos/notice/collect_module_notice_file.py"
    source = '''if notice_file:
        if other_files:
            notice_file = f"{notice_file},{','.join(other_files)}"
        for output in options.output:
            notice_info_json = '{}.json'.format(output)
            os.makedirs(os.path.dirname(output), exist_ok=True)
            os.makedirs(os.path.dirname(notice_info_json), exist_ok=True)
            notice_files = [file for file in notice_file.split(",") if file]

            write_file_content(notice_files, options, output, notice_info_json, module_notice_info_list, depfiles)'''
    new = '''if notice_file and other_files:
        notice_file = f"{notice_file},{','.join(other_files)}"
    for output in options.output:
        notice_info_json = '{}.json'.format(output)
        os.makedirs(os.path.dirname(output), exist_ok=True)
        if notice_file:
            notice_files = [file for file in notice_file.split(",") if file]
            write_file_content(notice_files, options, output, notice_info_json, module_notice_info_list, depfiles)
        else:
            if not os.path.exists(output) or os.path.getsize(output) != 0:
                with open(output, 'w', encoding='utf-8'):
                    pass
            write_json_file(notice_info_json, module_notice_info_list, check_changes=True)'''
    replacements = ((source, new, 1),)
    return patch_file(path, replacements)

# 上游已经修复，旧补丁停用并保留备查。
# def patch_idl_outputs() -> bool:
#     path = root / "build/config/components/idl_tool/idl.gni"
#     source_name = '''if (name_split[0] == "") {
#       init_with_i = true
#       name = string_replace(name, "_i_", "", 1)
#     }
#     name_split = []
#     name_split = string_split(name, "_")
#     if (name_split[0] == "") {
#       name = string_replace(name, "_", "", 1)
#     }
#
#     # second letter of result is '_\''''
#     new_name = '''if (name_split[0] == "") {
#       init_with_i = true
#       name = string_replace(name, "_i_", "", 1)
#     }
#     name_split = []
#     name_split = string_split(name, "_")
#     if (name_split[0] == "") {
#       name = string_replace(name, "_", "", 1)
#     }
#
#     if (init_with_i) {
#       interface_name = name
#     }
#
#     # second letter of result is '_\''''
#     source_main_header = '''sources_all += [ "${target_gen_dir}/" + "i" + name + ".h" ]'''
#     new_main_header = '''sources_all += [ "${target_gen_dir}/" + "i" + interface_name + ".h" ]'''
#     source_callback_header = '''if (init_with_i) {
#       out_full_name_i = string_replace(idl_full_name, idl_name, "i" + name)
#       sources_all += [ "${target_gen_dir}/" + out_full_name_i + ".h" ]
#     } else {
#       sources_all += [ "${target_gen_dir}/" + out_full_name + ".h" ]
#     }
#     sources_all += [
# '''
#     new_callback_header = '''if (init_with_i) {
#       out_full_name_i = string_replace(idl_full_name, idl_name, "i" + interface_name)
#       sources_all += [ "${target_gen_dir}/" + out_full_name_i + ".h" ]
#     } else {
#       sources_all += [ "${target_gen_dir}/" + out_full_name + ".h" ]
#     }
#     sources_all += [
# '''
#     source_common_header = '''out_full_name = string_replace(idl_full_name, idl_name, name)
#
#     if (init_with_i) {
#       out_full_name_i = string_replace(idl_full_name, idl_name, "i" + name)
#       sources_all += [ "${target_gen_dir}/" + out_full_name_i + ".h" ]
#     } else {
#       sources_all += [ "${target_gen_dir}/" + out_full_name + ".h" ]
#     }'''
#     new_common_header = '''out_full_name = string_replace(idl_full_name, idl_name, name)
#
#     sources_all += [ "${target_gen_dir}/" + out_full_name + ".h" ]'''
#     replacements = (
#         (source_name, new_name, 2),
#         (source_main_header, new_main_header, 1),
#         (source_callback_header, new_callback_header, 1),
#         (source_common_header, new_common_header, 1),
#     )
#     return patch_file(path, replacements)
#
# 上游已经使用 build-system 和 koala-wrapper 专属目录，旧补丁停用并保留备查。
# def _patch_generated_directory(path: Path) -> bool:
#     source = '''npm_path = "//prebuilts/build-tools/common/nodejs/current/bin/npm"'''
#     new = '''npm_path = "//prebuilts/build-tools/common/nodejs/current/bin/npm"
# generated_output_dir = "$target_gen_dir/generated"'''
#     source_directory = '''"$target_gen_dir"'''
#     new_directory = '''generated_output_dir'''
#     replacements = (
#         (source, new, 1),
#         (source_directory, new_directory, 4),
#     )
#     return patch_file(path, replacements)
#
# def patch_ets_build_system_directory() -> bool:
#     path = root / "arkcompiler/ets_frontend/ets2panda/driver/build_system/BUILD.gn"
#     return _patch_generated_directory(path)
#
# def patch_ets_koala_wrapper_directory() -> bool:
#     path = root / "developtools/ace_ets2bundle/koala-wrapper/BUILD.gn"
#     return _patch_generated_directory(path)

def patch_idlize_bundle_cache() -> bool:
    path1 = root / "developtools/ace_ets2bundle/ets1.2/gn/script/npm.py"
    source_import = '''import argparse
import shutil'''
    new_import = '''import argparse
import filecmp
import shutil'''
    source_archive = '''    # Move the generated tarball to the destination
    shutil.move(tgz_filename, pack_destination)'''
    new_archive = '''    # 内容不变时保留原文件时间，避免触发下游重复构建。
    if os.path.isfile(pack_destination) and filecmp.cmp(tgz_filename, pack_destination, shallow=False):
        os.remove(tgz_filename)
    else:
        shutil.move(tgz_filename, pack_destination)'''
    replacements1 = (
        (source_import, new_import, 1),
        (source_archive, new_archive, 1),
    )
    path2 = root / "foundation/arkui/idlize/tools/ohos/build_bundle.py"
    source_install = '''            "--no-package-lock",
            "--no-audit",'''
    new_install = '''            "--no-package-lock",
            "--prefer-offline",
            "--no-audit",'''
    replacements2 = ((source_install, new_install, 1),)
    patches = (
        (path1, replacements1),
        (path2, replacements2),
    )
    return patch_files(patches)

# 上游已经修复，旧补丁停用并保留备查。
# def patch_ets2panda_consistency() -> bool:
#     path1 = root / "arkcompiler/ets_frontend/ets2panda/BUILD.gn"
#     source_consistency_target = '''action("check_build_system_consistency") {
#   script = "./scripts/check_build_system_consistency.py"
#   args = [ rebase_path(".", root_build_dir) ]
#   outputs = [ "$target_gen_dir/consistency_check.stamp" ]
# }'''
#     new_consistency_target = '''action("check_build_system_consistency") {
#   script = "./scripts/check_build_system_consistency.py"
#   consistency_stamp = "$target_gen_dir/consistency_check.stamp"
#   args = [
#     rebase_path(".", root_build_dir),
#     rebase_path(consistency_stamp, root_build_dir),
#   ]
#   outputs = [ consistency_stamp ]
# }'''
#     replacements1 = (
#         (source_consistency_target, new_consistency_target, 1),
#     )
#     path2 = root / "arkcompiler/ets_frontend/ets2panda/scripts/check_build_system_consistency.py"
#     source_consistency_script = '''if src_consistent and hdr_consistent and yaml_consistent:
#         print("all file types are consistent beetween CMake and GN")
#         return 0'''
#     new_consistency_script = '''if src_consistent and hdr_consistent and yaml_consistent:
#         stamp_path = sys.argv[2]
#         os.makedirs(os.path.dirname(stamp_path), exist_ok=True)
#         with open(stamp_path, "w", encoding="utf-8"):
#             pass
#         print("all file types are consistent beetween CMake and GN")
#         return 0'''
#     replacements2 = (
#         (source_consistency_script, new_consistency_script, 1),
#     )
#     patches = (
#         (path1, replacements1),
#         (path2, replacements2),
#     )
#     return patch_files(patches)

# 上游已经修复，旧补丁停用并保留备查。
# def patch_sdk_interface_stamp() -> bool:
#     path1 = root / "interface/sdk-js/BUILD.gn"
#     source_sdk_target = '''"--sdk-api-version",
#     "${platform_version}",
#   ]'''
#     new_sdk_target = '''"--sdk-api-version",
#     "${platform_version}",
#     "--stamp-file",
#     rebase_path("${target_out_dir}/${target_name}.timestamp", root_build_dir),
#   ]'''
#     replacements1 = (
#         (source_sdk_target, new_sdk_target, 1),
#     )
#     path2 = root / "build/ohos/sdk/parse_interface_sdk.py"
#     source_sdk_parser = '''parser.add_argument('--sdk-api-version', required=True)
#
#     options = parser.parse_args()
#
#     parse_step(options)'''
#     new_sdk_parser = '''parser.add_argument('--sdk-api-version', required=True)
#     parser.add_argument('--stamp-file', required=True)
#
#     options = parser.parse_args()
#
#     parse_step(options)
#     os.makedirs(os.path.dirname(options.stamp_file), exist_ok=True)
#     with open(options.stamp_file, 'w', encoding='utf-8'):
#         pass'''
#     replacements2 = (
#         (source_sdk_parser, new_sdk_parser, 1),
#     )
#     patches = (
#         (path1, replacements1),
#         (path2, replacements2),
#     )
#     return patch_files(patches)
#
# 上游已经修复，旧补丁停用并保留备查。
# def patch_sdk_internal_process_stamp() -> bool:
#     path1 = root / "interface/sdk-js/BUILD.gn"
#     source_process_target = '''"--output",
#       rebase_path(target_out_dir + "/${target_name}", root_build_dir),
#     ]'''
#     new_process_target = '''"--output",
#       rebase_path(target_out_dir + "/${target_name}", root_build_dir),
#       "--stamp-file",
#       rebase_path("${target_out_dir}/${target_name}.timestamp", root_build_dir),
#     ]'''
#     replacements1 = (
#         (source_process_target, new_process_target, 1),
#     )
#     path2 = root / "interface/sdk-js/process_internal.py"
#     source_process_option = '''parser.add_option('--output', help='output path')
#     options, _ = parser.parse_args(args)'''
#     new_process_option = '''parser.add_option('--output', help='output path')
#     parser.add_option('--stamp-file', help='incremental build stamp path')
#     options, _ = parser.parse_args(args)'''
#     source_process_stamp = '''# 更新输出文件夹的修改时间，防止后续编译工具误认为文件未修改而跳过编译
#     os.utime(options.output)
#     return 0'''
#     new_process_stamp = '''# 更新输出文件夹的修改时间，防止后续编译工具误认为文件未修改而跳过编译
#     os.utime(options.output)
#     stamp_file = Path(options.stamp_file)
#     stamp_file.parent.mkdir(parents=True, exist_ok=True)
#     stamp_file.touch()
#     return 0'''
#     replacements2 = (
#         (source_process_option, new_process_option, 1),
#         (source_process_stamp, new_process_stamp, 1),
#     )
#     patches = (
#         (path1, replacements1),
#         (path2, replacements2),
#     )
#     return patch_files(patches)
#
# 上游已经修复，旧补丁停用并保留备查。
# def patch_sdk_internal_declaration_stamp() -> bool:
#     path1 = root / "interface/sdk-js/BUILD.gn"
#     source_declaration_target = '''"--output",
#       rebase_path(root_out_dir + "/ohos_declaration/${target_name}/",
#                   root_build_dir),
#     ]'''
#     new_declaration_target = '''"--output",
#       rebase_path(root_out_dir + "/ohos_declaration/${target_name}/",
#                   root_build_dir),
#       "--stamp-file",
#       rebase_path("${target_out_dir}/${target_name}.timestamp", root_build_dir),
#     ]'''
#     replacements1 = (
#         (source_declaration_target, new_declaration_target, 1),
#     )
#     path2 = root / "interface/sdk-js/remove_internal.py"
#     source_path_import = '''import shutil
# import time'''
#     new_path_import = '''import shutil
# import time
# from pathlib import Path'''
#     source_declaration_option = '''parser.add_option('--output', help='d.ts document output path')
#     options, _ = parser.parse_args(args)'''
#     new_declaration_option = '''parser.add_option('--output', help='d.ts document output path')
#     parser.add_option('--stamp-file', help='incremental build stamp path')
#     options, _ = parser.parse_args(args)'''
#     source_declaration_stamp = '''os.utime(options.output, (current_time, current_time))
#     copy_files(options.input, options.output)'''
#     new_declaration_stamp = '''os.utime(options.output, (current_time, current_time))
#     copy_files(options.input, options.output)
#     stamp_file = Path(options.stamp_file)
#     stamp_file.parent.mkdir(parents=True, exist_ok=True)
#     stamp_file.touch()
#     return 0'''
#     replacements2 = (
#         (source_path_import, new_path_import, 1),
#         (source_declaration_option, new_declaration_option, 1),
#         (source_declaration_stamp, new_declaration_stamp, 1),
#     )
#     patches = (
#         (path1, replacements1),
#         (path2, replacements2),
#     )
#     return patch_files(patches)
#
# 上游已经修复，旧补丁停用并保留备查。
# def patch_fusion_idl() -> bool:
#     path = root / "foundation/communication/fusion_connectivity/partner_agent/idl/BUILD.gn"
#     source_fusion_idl = '''sources = [ "$FUSION_CONN/partner_agent/idl/IPartnerAgentExtension.idl" ]\x20
#   sources_common = [\x20
#     "$FUSION_CONN/partner_agent/idl/IFusionConnectivityTypes.idl",\x20
#   ]\x20'''
#     new_fusion_idl = '''sources = [ "IPartnerAgentExtension.idl" ]\x20'''
#     replacements = (
#         (source_fusion_idl, new_fusion_idl, 1),
#     )
#     return patch_file(path, replacements)
#
# 上游已经修复，旧补丁停用并保留备查。
# def patch_hap_sign_stamp() -> bool:
#     path1 = root / "build/ohos/app/app_internal.gni"
#     source_sign_target = '''"--hap-name",
#       hap_name,
#     ]'''
#     new_sign_target = '''"--hap-name",
#       hap_name,
#       "--stamp-file",
#       rebase_path("${target_out_dir}/${target_name}.stamp", root_build_dir),
#     ]'''
#     replacements1 = (
#         (source_sign_target, new_sign_target, 1),
#     )
#     path2 = root / "build/scripts/app_sign.py"
#     source_sign_option = '''parser.add_argument('--hap-list', help='')'''
#     new_sign_option = '''parser.add_argument('--hap-list', help='')
#     parser.add_argument('--stamp-file', help='incremental build stamp path')'''
#     source_sign_stamp = '''sign_app(options, unsigned_hap_path, output_hap)
#
#
# if __name__ == '__main__':'''
#     new_sign_stamp = '''sign_app(options, unsigned_hap_path, output_hap)
#
#     if options.stamp_file:
#         os.makedirs(os.path.dirname(options.stamp_file), exist_ok=True)
#         with open(options.stamp_file, 'w', encoding='utf-8'):
#             pass
#     return 0
#
#
# if __name__ == '__main__':'''
#     replacements2 = (
#         (source_sign_option, new_sign_option, 1),
#         (source_sign_stamp, new_sign_stamp, 1),
#     )
#     patches = (
#         (path1, replacements1),
#         (path2, replacements2),
#     )
#     return patch_files(patches)
#
def patch_kernel_outputs() -> bool:
    path = root / "device/board/hihope/rk3568/kernel/build_kernel.sh"
    source_checkpoint_path = '''KERNEL_OBJ_TMP_PATH=${ROOT_DIR}/out/kernel/OBJ/${KERNEL_VERSION}'''
    new_checkpoint_path = '''KERNEL_OBJ_TMP_PATH=${ROOT_DIR}/out/kernel/OBJ/${KERNEL_VERSION}
KERNEL_CHECKPOINT_PATH=${ROOT_DIR}/out/kernel/checkpoint/compile_check'''
    source_kernel_skip = '''else
    echo "no changes to kernel, skip source copy."
fi'''
    new_kernel_skip = '''else
    echo "no changes to kernel, skip source copy."
    KERNEL_OUTPUTS=(
        "${KERNEL_SRC_TMP_PATH}/boot_linux"
        "${2}/resource.img"
        "${2}/MiniLoaderAll.bin"
        "${2}/uboot.img"
    )
    if [ "$RAMDISK_ARG" != "enable_ramdisk" ]; then
        KERNEL_OUTPUTS+=("${2}/boot_linux.img")
    fi
    if [ "enable_absystem" == "${15}" ]; then
        KERNEL_OUTPUTS+=("${2}/parameter_ab.txt" "${2}/config_ab.cfg")
    else
        KERNEL_OUTPUTS+=("${2}/parameter.txt" "${2}/config.cfg")
    fi
    KERNEL_OUTPUTS_READY=true
    for output in "${KERNEL_OUTPUTS[@]}"; do
        if [ ! -e "$output" ]; then
            KERNEL_OUTPUTS_READY=false
            break
        fi
    done
    if [ "$KERNEL_OUTPUTS_READY" = true ]; then
        echo "kernel outputs already exist, skip rebuild."
        mkdir -p "$(dirname -- "$KERNEL_CHECKPOINT_PATH")"
        : > "$KERNEL_CHECKPOINT_PATH"
        popd
        exit 0
    fi
fi'''
    source_kernel_finish = '''else
    echo "kernel compile finish."
fi'''
    new_kernel_finish = '''else
    echo "kernel compile finish."
fi

mkdir -p "$(dirname -- "$KERNEL_CHECKPOINT_PATH")"
: > "$KERNEL_CHECKPOINT_PATH"'''
    replacements = (
        (source_checkpoint_path, new_checkpoint_path, 1),
        (source_kernel_skip, new_kernel_skip, 1),
        (source_kernel_finish, new_kernel_finish, 1),
    )
    return patch_file(path, replacements)

# 上游已经修复，旧补丁停用并保留备查。
# def patch_js_framework_dependency() -> bool:
#     path = root / "third_party/css-what/BUILD.gn"
#     source_runtime_output = '''output = "../jsframework/runtime"'''
#     new_runtime_output = '''output = "css_what_sources"'''
#     replacements = (
#         (source_runtime_output, new_runtime_output, 1),
#     )
#     return patch_file(path, replacements)

def patch_camera_generated_file() -> bool:
    path = root / "device/board/hihope/rk3568/camera/vdi_impl/v4l2/BUILD.gn"
    source_camera_copy = '''action("copy_source") {
    script = "/usr/bin/env"
    outputs = [ "$target_out_dir/tmp.c" ]  # no use, just for gn complains
    args = [
      "cp",
      "-f",
    ]
    args += rebase_path(get_target_outputs(":generate_source"))
    args += [ rebase_path(
            "$camera_path/pipeline_core/pipeline_impl/src/strategy/config/") ]
    deps = [ ":generate_source" ]
  }

  ohos_prebuilt_etc("config.c") {
    deps = [ ":copy_source" ]
    source =
        "$camera_path/pipeline_core/pipeline_impl/src/strategy/config/config.c"
    exec_script(
        "/usr/bin/env",
        [
          "touch",
          rebase_path(
              "$camera_path/pipeline_core/pipeline_impl/src/strategy/config/config.c"),
        ])
  }

  ohos_prebuilt_etc("params.c") {
    deps = [ ":copy_source" ]
    source =
        "$camera_path/pipeline_core/pipeline_impl/src/strategy/config/params.c"
    exec_script(
        "/usr/bin/env",
        [
          "touch",
          rebase_path(
              "$camera_path/pipeline_core/pipeline_impl/src/strategy/config/params.c"),
        ])
  }'''
    new_camera_copy = '''generated_camera_outputs = get_target_outputs(":generate_source")
  generated_camera_configs =
      filter_include(generated_camera_outputs, [ "*config.c" ])
  generated_camera_params_list =
      filter_include(generated_camera_outputs, [ "*params.c" ])
  generated_camera_config = "//" + generated_camera_configs[0]
  generated_camera_params = "//" + generated_camera_params_list[0]
  generated_camera_include_dir = get_path_info(generated_camera_config, "dir")

  ohos_prebuilt_etc("config.c") {
    deps = [ ":generate_source" ]
    source = generated_camera_config
    output = "config.c"
  }

  ohos_prebuilt_etc("params.c") {
    deps = [ ":generate_source" ]
    source = generated_camera_params
    output = "params.c"
  }'''
    source_camera_library = '''ohos_shared_library("camera_pipeline_config") {
    sources = [
      "$camera_path/pipeline_core/pipeline_impl/src/strategy/config/config.c",
      "$camera_path/pipeline_core/pipeline_impl/src/strategy/config/params.c",
    ]
    include_dirs =
        [ "$camera_path/pipeline_core/pipeline_impl/src/strategy/config" ]'''
    new_camera_library = '''ohos_shared_library("camera_pipeline_config") {
    sources = [
      generated_camera_config,
      generated_camera_params,
    ]
    include_dirs = [ generated_camera_include_dir ]
    deps = [ ":generate_source" ]'''
    replacements = (
        (source_camera_copy, new_camera_copy, 1),
        (source_camera_library, new_camera_library, 1),
    )
    return patch_file(path, replacements)

# 上游已经修复，旧补丁停用并保留备查。
# def patch_sane_airscan_outputs() -> bool:
#     path1 = root / "third_party/sane-airscan/BUILD.gn"
#     source_airscan_build = '''source_dir = "//third_party/sane-airscan"
# target_dir = "${target_gen_dir}/patches"

# action("airscan_action") {
#   script = "//third_party/sane-airscan/patch_install.py"
#   inputs = [
#     "${source_dir}/patches/oh-transplant.patch",
#     "${source_dir}/patches/oh-fix-subtraction-underflow.patch",
#     "${source_dir}/patches/oh-fix-heap-overflow-dimension.patch",
#     "${source_dir}/patches/oh-fix-resolution-overflow.patch",
#     "${source_dir}/patches/oh-fix-http-hdr-params-parse-null-deref.patch",
#     "${source_dir}/patches/oh-fix-http-body-limit.patch",
#     "${source_dir}/patches/oh-fix-empty-source-caps.patch",
#     "${source_dir}/patches/oh-fix-eloop-uv-run-mutex-serialization.patch",
#   ]
#   outputs = [
#     "${target_dir}/patches/airscan-conf.c",
#     "${target_dir}/patches/airscan-device.c",
#     "${target_dir}/patches/airscan-devops.c",
#     "${target_dir}/patches/airscan-eloop.c",
#     "${target_dir}/patches/airscan-http.c",
#     "${target_dir}/patches/airscan-init.c",
#     "${target_dir}/patches/airscan-log.c",
#     "${target_dir}/patches/airscan-mdns.c",
#     "${target_dir}/patches/airscan-netif.c",
#     "${target_dir}/patches/airscan-pollable.c",
#     "${target_dir}/patches/airscan-tiff.c",
#     "${target_dir}/patches/airscan-wsd.c",
#     "${target_dir}/patches/airscan-zeroconf.c",
#     "${target_dir}/patches/airscan.c",
#     "${target_dir}/patches/airscan.h",
#   ]
#   airscan_source_dir = rebase_path("${source_dir}", root_build_dir)
#   args = [
#     "--source-dir",
#     "$airscan_source_dir",
#   ]
# }

# config("airscan_config") {
#   cflags = [
#     "-fno-exceptions",
#     "-fdata-sections",
#     "-ffunction-sections",
#     "-fno-asynchronous-unwind-tables",
#     "-fno-unwind-tables",
#     "-flto",
#     "-Os",
#     "-DOH_AIRSCAN",
#     "-fstack-protector-all",
#   ]
# }

# ohos_shared_library("sane-airscan") {
#   include_dirs = [ "./airscan.h" ]
#   sources = [
#     "airscan-array.c",
#     "airscan-bmp.c",
#     "airscan-conf.c",
#     "airscan-devcaps.c",
#     "airscan-device.c",
#     "airscan-devid.c",
#     "airscan-devops.c",
#     "airscan-eloop.c",
#     "airscan-escl.c",
#     "airscan-filter.c",
#     "airscan-http.c",
#     "airscan-id.c",
#     "airscan-image.c",
#     "airscan-init.c",
#     "airscan-ip.c",
#     "airscan-jpeg.c",
#     "airscan-log.c",
#     "airscan-math.c",
#     "airscan-memstr.c",
#     "airscan-netif.c",
#     "airscan-os.c",
#     "airscan-png.c",
#     "airscan-pollable.c",
#     "airscan-rand.c",
#     "airscan-trace.c",
#     "airscan-xml.c",
#     "airscan-zeroconf.c",
#     "airscan.c",
#     "http_parser.c",
#     "sane_strstatus.c",
#   ]'''
#     new_airscan_build = '''source_dir = "//third_party/sane-airscan"
# patched_dir = "${target_gen_dir}/airscan_patched"

# airscan_sources = [
#   "airscan-array.c",
#   "airscan-bmp.c",
#   "airscan-conf.c",
#   "airscan-devcaps.c",
#   "airscan-device.c",
#   "airscan-devid.c",
#   "airscan-devops.c",
#   "airscan-eloop.c",
#   "airscan-escl.c",
#   "airscan-filter.c",
#   "airscan-http.c",
#   "airscan-id.c",
#   "airscan-image.c",
#   "airscan-init.c",
#   "airscan-ip.c",
#   "airscan-jpeg.c",
#   "airscan-log.c",
#   "airscan-math.c",
#   "airscan-memstr.c",
#   "airscan-netif.c",
#   "airscan-os.c",
#   "airscan-png.c",
#   "airscan-pollable.c",
#   "airscan-rand.c",
#   "airscan-trace.c",
#   "airscan-xml.c",
#   "airscan-zeroconf.c",
#   "airscan.c",
#   "http_parser.c",
#   "sane_strstatus.c",
# ]
# airscan_generated_files = airscan_sources + [
#                             "airscan-mdns.c",
#                             "airscan-tiff.c",
#                             "airscan-wsd.c",
#                             "airscan.h",
#                             "http_parser.h",
#                           ]
# airscan_inputs = []
# airscan_outputs = []
# foreach(file, airscan_generated_files) {
#   airscan_inputs += [ "${source_dir}/${file}" ]
#   airscan_outputs += [ "${patched_dir}/${file}" ]
# }

# action("airscan_action") {
#   script = "//third_party/sane-airscan/patch_install.py"
#   inputs = airscan_inputs + [
#     "${source_dir}/patches/oh-transplant.patch",
#     "${source_dir}/patches/oh-fix-subtraction-underflow.patch",
#     "${source_dir}/patches/oh-fix-heap-overflow-dimension.patch",
#     "${source_dir}/patches/oh-fix-resolution-overflow.patch",
#     "${source_dir}/patches/oh-fix-http-hdr-params-parse-null-deref.patch",
#     "${source_dir}/patches/oh-fix-http-body-limit.patch",
#     "${source_dir}/patches/oh-fix-empty-source-caps.patch",
#     "${source_dir}/patches/oh-fix-eloop-uv-run-mutex-serialization.patch",
#   ]
#   outputs = airscan_outputs
#   args = [
#     "--source-dir",
#     rebase_path(source_dir, root_build_dir),
#     "--output-dir",
#     rebase_path(patched_dir, root_build_dir),
#   ]
# }

# config("airscan_config") {
#   cflags = [
#     "-fno-exceptions",
#     "-fdata-sections",
#     "-ffunction-sections",
#     "-fno-asynchronous-unwind-tables",
#     "-fno-unwind-tables",
#     "-flto",
#     "-Os",
#     "-DOH_AIRSCAN",
#     "-fstack-protector-all",
#   ]
# }

# ohos_shared_library("sane-airscan") {
#   include_dirs = [ patched_dir ]
#   sources = []
#   foreach(file, airscan_sources) {
#     sources += [ "${patched_dir}/${file}" ]
#   }'''
#     replacements1 = (
#         (source_airscan_build, new_airscan_build, 1),
#     )
#     path2 = root / "third_party/sane-airscan/patch_install.py"
#     source_airscan_script = '''import tarfile
# import argparse
# import os
# import subprocess
# import sys
# import shutil


# def apply_patch(source_dir):
#     patch_list = [
#         'oh-transplant.patch',
#         'oh-fix-subtraction-underflow.patch',
#         'oh-fix-heap-overflow-dimension.patch',
#         'oh-fix-resolution-overflow.patch',
#         'oh-fix-http-hdr-params-parse-null-deref.patch',
#         'oh-fix-http-body-limit.patch',
#         'oh-fix-empty-source-caps.patch',
#         'oh-fix-eloop-uv-run-mutex-serialization.patch',
#     ]

#     for patch in patch_list:
#         patch_dir = os.path.join(source_dir, 'patches', patch)
#         patch_dir = os.path.abspath(patch_dir)
#         source_dir = os.path.abspath(source_dir)
#         patch_cmd = ['patch', '-p1', "--fuzz=0", "--no-backup-if-mismatch", '-i', patch_dir, '-d', source_dir]
#         try:
#             result = subprocess.run(patch_cmd, check=True, text=True, capture_output=True)
#             if result.returncode != 0:
#                 raise subprocess.CalledProcessError(result.returncode, result.args)
#         except subprocess.CalledProcessError:
#             print("sane-backends: {} apply error!".format(patch))

# def main():
#     backends_path = argparse.ArgumentParser()
#     backends_path.add_argument('--source-dir', help='generate path of log', required=True)
#     args = backends_path.parse_args()
#     source_dir = args.source_dir
#     apply_patch(source_dir)
#     return 0'''
#     new_airscan_script = '''import argparse
# import subprocess
# import sys
# import shutil
# from pathlib import Path


# def apply_patches(source_dir, output_dir):
#     patch_names = [
#         'oh-transplant.patch',
#         'oh-fix-subtraction-underflow.patch',
#         'oh-fix-heap-overflow-dimension.patch',
#         'oh-fix-resolution-overflow.patch',
#         'oh-fix-http-hdr-params-parse-null-deref.patch',
#         'oh-fix-http-body-limit.patch',
#         'oh-fix-empty-source-caps.patch',
#         'oh-fix-eloop-uv-run-mutex-serialization.patch',
#     ]

#     shutil.rmtree(output_dir, ignore_errors=True)
#     shutil.copytree(
#         source_dir,
#         output_dir,
#         ignore=shutil.ignore_patterns('.git', '*.rej', '*.orig', '__pycache__'),
#     )
#     for patch_name in patch_names:
#         subprocess.run(
#             [
#                 'patch', '-p1', '--batch', '--fuzz=0',
#                 '--no-backup-if-mismatch', '--reject-file=-',
#                 '-i', str(source_dir / 'patches' / patch_name),
#                 '-d', str(output_dir),
#             ],
#             check=True,
#         )

# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument('--source-dir', required=True)
#     parser.add_argument('--output-dir', required=True)
#     args = parser.parse_args()
#     apply_patches(Path(args.source_dir).resolve(), Path(args.output_dir).resolve())
#     return 0'''
#     replacements2 = (
#         (source_airscan_script, new_airscan_script, 1),
#     )
#     patches = (
#         (path1, replacements1),
#         (path2, replacements2),
#     )
#     return patch_files(patches)

# 仅在内容变化时更新 ArkUI 生成文件，避免无效时间戳触发大范围重编译。
def patch_arkui_generated_outputs() -> bool:
    path1 = root / "foundation/arkui/idlize/libohos/src/peer-generation/common.ts"
    source_integrated_writer = '''fs.mkdirSync(path.dirname(filename), { recursive: true })
        fs.writeFileSync(filename, content)
        return true'''
    new_integrated_writer = '''if (fs.existsSync(filename) && fs.readFileSync(filename, "utf8") === content)
            return true
        fs.mkdirSync(path.dirname(filename), { recursive: true })
        fs.writeFileSync(filename, content)
        return true'''
    replacements1 = (
        (source_integrated_writer, new_integrated_writer, 1),
    )
    path2 = root / "foundation/arkui/idlize/arkgen/src/arkoala.ts"
    source_gni_write = '''fs.writeFileSync(libace.gniComponents, gniFile(gniSources))'''
    new_gni_write = '''writeIntegratedFile(libace.gniComponents, gniFile(gniSources))'''
    source_api_write = '''fs.writeFileSync(libace.generatedArkoalaApi, api)
    fs.writeFileSync(libace.userConverterHeader, converterHeader)'''
    new_api_write = '''writeIntegratedFile(libace.generatedArkoalaApi, api)
    writeIntegratedFile(libace.userConverterHeader, converterHeader)'''
    source_meson_write = '''fs.writeFileSync(libace.mesonBuild, mesonBuildFile(mesonBuild))'''
    new_meson_write = '''writeIntegratedFile(libace.mesonBuild, mesonBuildFile(mesonBuild))'''
    replacements2 = (
        (source_gni_write, new_gni_write, 1),
        (source_api_write, new_api_write, 1),
        (source_meson_write, new_meson_write, 1),
    )
    patches = (
        (path1, replacements1),
        (path2, replacements2),
    )
    return patch_files(patches)

def patch_arkts_config_copy() -> bool:
    path = root / "build/config/components/ets_frontend/generate_static_abc.py"
    source_arkts_config_function = '''def modify_arktsconfig_with_cache(arktsconfig_path: str, cache_path: str) -> None:
    """
    Modify arktsconfig.json to use cache_path as outDir.
    Backup the original file, modify it, and restore it after use.
    """
    backup_path = arktsconfig_path + ".bak"
    shutil.copy(arktsconfig_path, backup_path)

    try:
        config = {}
        if os.path.exists(arktsconfig_path):
            with open(arktsconfig_path, "r") as f:
                content = f.read()
                config = json.loads(content)
            if "compilerOptions" in config:
                config["compilerOptions"]["outDir"] = cache_path

        if os.path.exists(arktsconfig_path):
            fd = os.open(arktsconfig_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o777)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
    except json.JSONDecodeError as e:
        print(f"{arktsconfig_path} Invalid JSON format (cache): {e}", file=sys.stderr)
        sys.exit()
    except Exception as e:
        restore_arktsconfig(arktsconfig_path)
        raise e


def restore_arktsconfig(arktsconfig_path: str) -> None:
    """Restore the original arktsconfig.json from backup."""
    backup_path = arktsconfig_path + ".bak"
    if os.path.exists(backup_path):
        shutil.move(backup_path, arktsconfig_path)'''
    new_arkts_config_function = '''def create_cached_arktsconfig(arktsconfig_path: str, cache_path: str) -> str:
    """Create a build-only arktsconfig without modifying the source file."""
    with open(arktsconfig_path, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    compiler_options = config.setdefault("compilerOptions", {})
    base_url = compiler_options.get("baseUrl", ".")
    if not os.path.isabs(base_url):
        compiler_options["baseUrl"] = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(arktsconfig_path)), base_url))
    compiler_options["outDir"] = cache_path

    cached_config = os.path.join(cache_path, "arktsconfig.json")
    with open(cached_config, "w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=2, ensure_ascii=False)
    return cached_config'''
    source_arkts_config_call = '''modify_arktsconfig_with_cache(args.arktsconfig, args.cache_path)'''
    new_arkts_config_call = '''args.arktsconfig = create_cached_arktsconfig(args.arktsconfig, args.cache_path)'''
    source_arkts_restore = '''except Exception as e:
        print(f"[UNKNOWN] Unexpected error: {e}", file=sys.stderr)
        sys.exit(EXIT_CODE["UNKNOWN_ERROR"])
    finally:
        if not args.base_url:
            restore_arktsconfig(args.arktsconfig)'''
    new_arkts_restore = '''except Exception as e:
        print(f"[UNKNOWN] Unexpected error: {e}", file=sys.stderr)
        sys.exit(EXIT_CODE["UNKNOWN_ERROR"])

    # Source arktsconfig is never modified, so no restore is required.'''
    replacements = (
        (source_arkts_config_function, new_arkts_config_function, 1),
        (source_arkts_config_call, new_arkts_config_call, 1),
        (source_arkts_restore, new_arkts_restore, 1),
    )
    return patch_file(path, replacements)

def patch_hap_ets_independent_cache() -> bool:
    path = root / "build/scripts/build_js_assets.py"
    source = '''if js2abc:
            build_dir = os.path.abspath(os.path.join(options.manifest_file_path, 'js', src_path))
            my_env.update({"cachePath": os.path.join(build_dir, ".cache")})
        else:
            build_dir = os.path.abspath(os.path.join(options.manifest_file_path, 'ets', src_path))'''
    new = '''asset_type = 'js' if js2abc else 'ets'
        build_dir = os.path.abspath(os.path.join(options.manifest_file_path, asset_type, src_path))
        my_env["cachePath"] = os.path.join(build_dir, ".cache")'''
    replacements = ((source, new, 1),)
    return patch_file(path, replacements)

def patch_ark_stub_comment() -> bool:
    path1 = root / "arkcompiler/ets_runtime/script/run_ark_executable.py"
    source_stub_option = '''parser.add_argument('--clean-path', action='append', default=[],
                        help='remove file/dir before execute, can be specified multiple times')'''
    new_stub_option = '''parser.add_argument('--clean-path', action='append', default=[],
                        help='remove file/dir before execute, can be specified multiple times')
    parser.add_argument('--stub-code-comment-output',
                        help='write stub compiler comments to this zip file')'''
    source_stub_function = '''def generate_stub_code_comment(out_str:str):
    dir_path = './gen/arkcompiler/ets_runtime/'
    if not os.path.exists(dir_path):
        return
    zip_path = dir_path + 'stub_code_comment.zip'
    if out_str != '':
        memory_file = StringIO()
        memory_file.write(out_str)
        memory_file.seek(0)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('stub_code_comment.txt', memory_file.getvalue())'''
    new_stub_function = '''def generate_stub_code_comment(out_str: str, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    memory_file = StringIO()
    memory_file.write(out_str)
    memory_file.seek(0)
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('stub_code_comment.txt', memory_file.getvalue())'''
    source_stub_call = '''generate_stub_code_comment(out_str)'''
    new_stub_call = '''if args.stub_code_comment_output:
        generate_stub_code_comment(out_str, args.stub_code_comment_output)'''
    replacements1 = (
        (source_stub_option, new_stub_option, 1),
        (source_stub_function, new_stub_function, 1),
        (source_stub_call, new_stub_call, 1),
    )
    path2 = root / "arkcompiler/ets_runtime/ecmascript/compiler/BUILD.gn"
    source_stub_target = '''outputs += [ "$stub_file_gen_dir/stub_code_comment.zip" ]'''
    new_stub_target = '''stub_comment_output = "$stub_file_gen_dir/stub_code_comment.zip"
    args += [
      "--stub-code-comment-output",
      rebase_path(stub_comment_output, root_build_dir),
    ]
    outputs += [ stub_comment_output ]'''
    replacements2 = (
        (source_stub_target, new_stub_target, 1),
    )
    patches = (
        (path1, replacements1),
        (path2, replacements2),
    )
    return patch_files(patches)

# 上游已经修复，旧补丁停用并保留备查。
# def patch_optional_distributed_dependency() -> bool:
#     path = root / "build/ohos/common/binary_install_info.py"
#     source_distributed_dependency = '''_dep_files.append(args.dist_parts_info_file)'''
#     new_distributed_dependency = '''if os.path.isfile(args.dist_parts_info_file):
#             _dep_files.append(args.dist_parts_info_file)'''
#     replacements = (
#         (source_distributed_dependency, new_distributed_dependency, 1),
#     )
#     return patch_file(path, replacements)
#
def patch_rk3568_optional_images() -> bool:
    path = root / "build/ohos/images/BUILD.gn"
    source_platform_chipset_dependency = '''foreach(_platform, target_platform_list) {
      deps += [
        ":${_platform}_eng_chipset_image",
        ":${_platform}_eng_system_image",'''
    new_platform_chipset_dependency = '''foreach(_platform, target_platform_list) {
      deps += [
        ":${_platform}_eng_system_image",'''
    source_rk3568_chipset_dependency = '''":${_platform}_vendor_image",
      ]
      if (enable_ramdisk) {'''
    new_rk3568_chipset_dependency = '''":${_platform}_vendor_image",
      ]
      if (device_name != "rk3568") {
        deps += [ ":${_platform}_eng_chipset_image" ]
      }
      if (enable_ramdisk) {'''
    source_chipset_group = '''foreach(_platform, target_platform_list) {
    deps += [ ":${_platform}_eng_chipset_image" ]'''
    new_chipset_group = '''if (device_name != "rk3568") {
    foreach(_platform, target_platform_list) {
      deps += [ ":${_platform}_eng_chipset_image" ]
    }'''
    source_rk3568_image_list = '''"eng_system",
    "eng_chipset",
  ]
  if (enable_ramdisk) {'''
    new_rk3568_image_list = '''"eng_system",
  ]
  if (device_name != "rk3568") {
    image_list += [ "eng_chipset" ]
  }
  if (enable_ramdisk) {'''
    replacements = (
        (source_platform_chipset_dependency, new_platform_chipset_dependency, 1),
        (source_rk3568_chipset_dependency, new_rk3568_chipset_dependency, 1),
        (source_chipset_group, new_chipset_group, 1),
        (source_rk3568_image_list, new_rk3568_image_list, 1),
    )
    return patch_file(path, replacements)

# 上游已经修复，旧补丁停用并保留备查。
# def patch_ramdisk_outputs() -> bool:
#     path1 = root / "build/ohos/images/BUILD.gn"
#     source_ramdisk_output_paths = '''if (_image_name == "ramdisk" || _image_name == "updater_ramdisk") {
#         output_image_file = "$root_build_dir/${_image_name}.img"
#       } else {
#         output_image_file = "$current_platform_dir/images/${_image_name}.img"
#       }'''
#     new_ramdisk_output_paths = '''if (_image_name == "ramdisk") {
#         output_image_file = "$current_platform_dir/images/ramdisk.img"
#         image_tool_output_file = "$root_build_dir/ramdisk.img"
#       } else if (_image_name == "updater_ramdisk") {
#         output_image_file = "$current_platform_dir/images/updater.img"
#         image_tool_output_file = "$root_build_dir/updater_ramdisk.img"
#       } else {
#         output_image_file = "$current_platform_dir/images/${_image_name}.img"
#         image_tool_output_file = output_image_file
#       }'''
#     source_ramdisk_target_arguments = '''"--output-image",
#         rebase_path(output_image_file, root_build_dir),
#         "--target-cpu",
#         target_cpu,
#         "--build-variant",'''
#     new_ramdisk_target_arguments = '''"--output-image",
#         rebase_path(image_tool_output_file, root_build_dir),
#         "--ninja-output-image-path",
#         rebase_path(output_image_file, root_build_dir),
#         "--target-cpu",
#         target_cpu,
#         "--build-variant",'''
#     replacements1 = (
#         (source_ramdisk_output_paths, new_ramdisk_output_paths, 1),
#         (source_ramdisk_target_arguments, new_ramdisk_target_arguments, 1),
#     )
#     path2 = root / "build/ohos/images/build_image.py"
#     source_image_output_option = '''parser.add_argument('--output-image-path', required=True)
#     parser.add_argument('--sparse-image','''
#     new_image_output_option = '''parser.add_argument('--output-image-path', required=True)
#     parser.add_argument('--ninja-output-image-path', required=True)
#     parser.add_argument('--sparse-image','''
#     source_image_cleanup_path = '''if os.path.exists(args.output_image_path):
#         os.remove(args.output_image_path)'''
#     new_image_cleanup_path = '''if os.path.exists(args.ninja_output_image_path):
#         os.remove(args.ninja_output_image_path)'''
#     source_image_depfile_path = '''build_utils.write_depfile(args.depfile,
#                                   args.output_image_path,'''
#     new_image_depfile_path = '''build_utils.write_depfile(args.depfile,
#                                   args.ninja_output_image_path,'''
#     replacements2 = (
#         (source_image_output_option, new_image_output_option, 1),
#         (source_image_cleanup_path, new_image_cleanup_path, 1),
#         (source_image_depfile_path, new_image_depfile_path, 1),
#     )
#     patches = (
#         (path1, replacements1),
#         (path2, replacements2),
#     )
#     return patch_files(patches)
#
# 上游已经使用完成标记和可选 arm64e 输出，旧补丁停用并保留备查。
# def patch_system_module_output() -> bool:
#     path = root / "build/ohos/packages/modules_install.py"
#     source_module_output = '''# write pac only module info file
#     if arm64e_output_result:
#         write_json_file(arm64e_modules_info_file, arm64e_output_result)'''
#     new_module_output = '''# 始终生成 Ninja 声明的输出文件。
#     write_json_file(arm64e_modules_info_file, arm64e_output_result)'''
#     source_module_depfiles = '''depfiles.extend([item for item in depfiles if item not in sa_files])'''
#     new_module_depfiles = '''depfiles = [item for item in depfiles if item not in sa_files]'''
#     replacements = (
#         (source_module_output, new_module_output, 1),
#         (source_module_depfiles, new_module_depfiles, 1),
#     )
#     return patch_file(path, replacements)

def patch_image_check_results() -> bool:
    path1 = root / "build/ohos/packages/BUILD.gn"
    source_seccomp_target = '''"--system-seccomp-lib-path",
      rebase_path(_system_seccomp_folder, root_build_dir),'''
    new_seccomp_target = '''"--system-seccomp-lib-path",
      rebase_path(_system_seccomp_folder, root_build_dir),
      "--result-path",
      rebase_path(process_validate_result, root_build_dir),'''
    source_process_target = '''"--critical-reboot-process-list-path",
      rebase_path(_critical_whitelist, root_build_dir),'''
    new_process_target = '''"--critical-reboot-process-list-path",
      rebase_path(_critical_whitelist, root_build_dir),
      "--result-path",
      rebase_path(process_validate_result, root_build_dir),'''
    replacements1 = (
        (source_seccomp_target, new_seccomp_target, 1),
        (source_process_target, new_process_target, 1),
    )
    path2 = root / "build/ohos/packages/check_seccomp_library_name.py"
    source_seccomp_option = '''parser.add_argument('--system-seccomp-lib-path', type=str,
                        help='input system seccomp cfg path\\n')'''
    new_seccomp_option = '''parser.add_argument('--system-seccomp-lib-path', type=str,
                        help='input system seccomp cfg path\\n')

    parser.add_argument('--result-path', type=str, required=True,
                        help='output file written after successful validation')'''
    source_seccomp_result = '''system_seccomp_services_name = collect_seccomp_services_name(args.system_seccomp_lib_path)
    check_seccomp_services_name(system_services_name, system_seccomp_services_name)'''
    new_seccomp_result = '''system_seccomp_services_name = collect_seccomp_services_name(args.system_seccomp_lib_path)
    check_seccomp_services_name(system_services_name, system_seccomp_services_name)
    with open(args.result_path, 'w', encoding='utf-8'):
        pass'''
    replacements2 = (
        (source_seccomp_option, new_seccomp_option, 1),
        (source_seccomp_result, new_seccomp_result, 1),
    )
    path3 = root / "build/ohos/packages/process_field_validate.py"
    source_process_result = '''check_container(critical_process_path)'''
    new_process_result = '''check_container(critical_process_path)
    with open(result_path, 'w', encoding='utf-8'):
        pass'''
    source_process_argument = '''validate_cfg_file(privilege_process_path, critical_process_path, None)'''
    new_process_argument = '''validate_cfg_file(privilege_process_path, critical_process_path, opts[4][1])'''
    replacements3 = (
        (source_process_result, new_process_result, 1),
        (source_process_argument, new_process_argument, 1),
    )
    patches = (
        (path1, replacements1),
        (path2, replacements2),
        (path3, replacements3),
    )
    return patch_files(patches)

results = (
    run_operation("补齐 NOTICE 输出", patch_notice_outputs),
    # run_operation("修复 IDL 大写命名", patch_idl_outputs),
    # run_operation("固定 ETS 构建目录", patch_ets_build_system_directory),
    # run_operation("固定 Koala Wrapper 目录", patch_ets_koala_wrapper_directory),
    run_operation("复用 IDLize 包与依赖缓存", patch_idlize_bundle_cache),
    # run_operation("修复 ets2panda 重复检查", patch_ets2panda_consistency),
    # run_operation("修复 SDK 接口时间戳", patch_sdk_interface_stamp),
    # run_operation("修复 SDK 内部处理时间戳", patch_sdk_internal_process_stamp),
    # run_operation("修复 SDK 内部声明时间戳", patch_sdk_internal_declaration_stamp),
    # run_operation("缩小 Fusion IDL 输入范围", patch_fusion_idl),
    # run_operation("修复 HAP 签名时间戳", patch_hap_sign_stamp),
    run_operation("修复 Kernel 重复构建", patch_kernel_outputs),
    # run_operation("修复 JS Framework 重复构建", patch_js_framework_dependency),
    run_operation("修复 Camera 重复生成", patch_camera_generated_file),
    # run_operation("修复 sane-airscan 重复生成", patch_sane_airscan_outputs),
    run_operation("修复 ArkUI 重复写入", patch_arkui_generated_outputs),
    run_operation("使用 ArkTS 配置副本", patch_arkts_config_copy),
    run_operation("分离 HAP/ETS 缓存", patch_hap_ets_independent_cache),
    run_operation("补齐 Ark Stub 注释输出", patch_ark_stub_comment),
    # run_operation("忽略不存在的分布式依赖", patch_optional_distributed_dependency),
    run_operation("精简 RK3568 镜像目标", patch_rk3568_optional_images),
    # run_operation("修复 Ramdisk 输出路径", patch_ramdisk_outputs),
    # run_operation("修复系统模块重复生成", patch_system_module_output),
    run_operation("补齐镜像检查结果", patch_image_check_results),
)

if all(results):
    raise SystemExit(0)
else:
    raise SystemExit(1)
