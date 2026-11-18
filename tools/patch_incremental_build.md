# patch_incremental_build.py 说明

该脚本修复 OpenHarmony 增量构建中的输出缺失、路径不一致和依赖范围过大等问题，目标是减少没有源码变化时仍被 Ninja 重复执行的任务。

## 整体流程

```text
down-common.sh
    ↓
patch_incremental_build.py
    ↓
依次执行 12 项补丁；另有 11 项上游已修复的旧补丁保留为注释
    ↓
每项独立记录成功或失败
    ↓
全部完成后统一返回结果
```

单项失败不会阻止后续补丁执行；只要有一项失败，脚本最终返回失败。

## 公共机制

- `_prepare_patch()`：按照 `source`、`new` 和 `count` 校验并准备新内容，仅供公共工具内部使用。
- `_write_atomic()`：通过临时文件原子替换目标文件，仅供公共工具内部使用。
- `patch_file()`：应用一个文件的固定替换规则。
- `patch_files()`：先验证一组相互依赖的文件，再统一写入修改。
- `run_operation()`：单独执行一项补丁，捕获异常并记录结果，避免影响其他补丁。

## 已讲解函数

### 1. `patch_notice_outputs()`

修改文件：`build/ohos/notice/collect_module_notice_file.py`

原问题：没有 NOTICE 输入文件时，原脚本不会创建 GN 已声明的 NOTICE 和 JSON 输出。Ninja 每次检查都发现输出缺失，因此反复执行该任务。

修改方式：无论是否存在 NOTICE 输入，都遍历 `options.output`。有输入时按原逻辑生成内容；无输入时创建空 NOTICE，并生成对应 JSON。

修改原理：Ninja 声明的每个输出都必须真实存在；JSON 仅在内容变化时改写，避免无意义地更新时间戳。

### 2. `patch_idl_outputs()`（上游已修复，当前停用）

修改文件：`build/config/components/idl_tool/idl.gni`

原问题：IDL 名称含连续大写字母或以 `I` 开头时，GN 预测的头文件名可能与 IDL 工具实际生成的文件名不一致，导致 Ninja 一直认为输出缺失。

修改方式：把最终规范化名称统一保存到 `interface_name`，主接口和回调接口都使用同一名称；同时删除会重复推导另一套头文件名的分支。

修改原理：让 GN 声明的输出文件名与 IDL 工具实际生成的文件名完全一致，消除“文件已经生成，但 Ninja 找错名字”的重复构建。

### 3. `patch_ets_build_system_directory()`（上游已修复，当前停用）

修改文件：`arkcompiler/ets_frontend/ets2panda/driver/build_system/BUILD.gn`

原问题：原规则把整个 `$target_gen_dir` 当作生成结果和复制来源。该目录还会被其他任务写入，任何无关变化都可能使 ETS 构建系统任务重新执行。

修改方式：新增独立目录 `$target_gen_dir/generated`，再把四处完整的 `"$target_gen_dir"` 统一替换为 `generated_output_dir`。

修改原理：把本任务的输出限定在专属目录，缩小 Ninja 的依赖范围，避免其他任务修改共享目录后触发重复生成和复制。

### 4. `patch_ets_koala_wrapper_directory()`（上游已修复，当前停用）

修改文件：`developtools/ace_ets2bundle/koala-wrapper/BUILD.gn`

原问题：Koala Wrapper 的生成动作把整个 `$target_gen_dir` 当作输出和复制来源。该目录包含其他目标的文件，目录中的无关变化也可能触发本任务重新生成和复制。

修改方式：新增独立目录 `$target_gen_dir/generated`，生成命令、`outputs` 以及两个复制目标全部改用 `generated_output_dir`。

修改原理：让 Koala Wrapper 只跟踪自己的生成目录，避免共享目录中的其他文件干扰 Ninja 的增量判断。

### 5. `patch_ets2panda_consistency()`（上游已修复，当前停用）

修改文件：`arkcompiler/ets_frontend/ets2panda/BUILD.gn`、`arkcompiler/ets_frontend/ets2panda/scripts/check_build_system_consistency.py`

原问题：GN 声明了 `consistency_check.stamp` 输出，但没有把该文件路径传给检查脚本，脚本无法实际创建它。Ninja 因此一直认为输出缺失。

修改方式：用 `consistency_stamp` 保存输出路径，将它作为第二个参数传给 Python 脚本；脚本检查成功后创建对应的空 stamp 文件。

修改原理：GN 负责声明并传入输出路径，Python 脚本负责在检查成功后创建该文件。两个文件先全部验证，再一起修改，避免只有一侧生效。

### 6. `patch_sdk_interface_stamp()`（上游已修复，当前停用）

修改文件：`interface/sdk-js/BUILD.gn`、`build/ohos/sdk/parse_interface_sdk.py`

原问题：GN 把时间戳文件作为接口解析任务的完成标记，但没有把它的路径传给解析脚本，脚本执行成功后也不会创建该文件。Ninja 因此会认为任务输出不完整。

修改方式：GN 增加 `--stamp-file` 参数；Python 脚本接收该参数，在接口解析成功后创建父目录和空的时间戳文件。

修改原理：解析成功后再创建时间戳，给 Ninja 一个明确且稳定的完成标记。GN 和 Python 文件先全部验证，再一起修改。

### 7. `patch_sdk_internal_process_stamp()`（上游已修复，当前停用）

修改文件：`interface/sdk-js/BUILD.gn`、`interface/sdk-js/process_internal.py`

原问题：内部接口处理任务缺少实际生成的时间戳文件，导致 Ninja 反复把它判断为输出不完整。

修改方式：GN 的 `process_internal` 任务传入 `--stamp-file`；`process_internal.py` 接收该参数，并在处理成功后创建时间戳文件。

修改原理：任务只在内部接口处理完成后写入完成标记。两个文件先全部验证，再统一写入。

### 8. `patch_sdk_internal_declaration_stamp()`（上游已修复，当前停用）

修改文件：`interface/sdk-js/BUILD.gn`、`interface/sdk-js/remove_internal.py`

原问题：内部声明过滤任务缺少实际生成的时间戳文件，导致 Ninja 反复把它判断为输出不完整。

修改方式：GN 的 `remove_internal` 任务传入 `--stamp-file`；`remove_internal.py` 接收该参数，在复制声明文件后创建时间戳，同时增加所需的 `Path` 导入。

修改原理：只有声明过滤和复制成功后才写入完成标记。两个文件先全部验证，再统一写入。

### 9. `patch_fusion_idl()`（上游已修复，当前停用）

修改文件：`foundation/communication/fusion_connectivity/partner_agent/idl/BUILD.gn`

原问题：`partner_agent_extension_interface` 同时包含主接口和 `sources_common`，使该目标跟踪了不属于自身主要输出的公共 IDL，容易造成 IDL 输出判断不一致和重复生成。

修改方式：删除 `sources_common`，并把 `sources` 统一为 `IPartnerAgentExtension.idl`。

修改原理：让该目标只处理自己的主 IDL，不再额外处理公共 IDL，避免预期输出与实际生成结果不一致而触发重复构建。

### 10. `patch_hap_sign_stamp()`（上游已修复，当前停用）

修改文件：`build/ohos/app/app_internal.gni`、`build/scripts/app_sign.py`

原问题：GN 把 `.stamp` 声明为 HAP 签名任务的输出，但签名脚本执行成功后没有创建它，导致 Ninja 反复认为任务输出不完整。

修改方式：GN 通过 `--stamp-file` 传入完成标记路径；签名脚本接收该参数，在全部 HAP 签名成功后创建空的 `.stamp` 文件。

修改原理：只有签名流程正常结束才创建完成标记，使 Ninja 能准确区分签名成功与中途失败。两个文件先全部验证，再统一写入。

### 11. `patch_kernel_outputs()`

修改文件：`device/board/hihope/rk3568/kernel/build_kernel.sh`

原问题：脚本只根据内核源码是否变化决定跳过部分操作，没有完整确认内核、Loader、U-Boot、参数文件等产物是否仍然存在；脚本提前退出或正常编译结束时也可能没有生成 Ninja 需要的 `compile_check`。

修改方式：源码未变化时先按当前 ramdisk 和 AB 分区配置检查全部必要产物；产物齐全才跳过重编译，缺少任意文件就继续构建。提前退出和正常构建完成时都创建 `out/kernel/checkpoint/compile_check`。

修改原理：只有“源码未变化、实际产物齐全”两个条件同时满足才复用旧结果，并始终为成功流程补齐检查点，避免缺失产物被错误跳过或 Ninja 因检查点不存在反复执行内核任务。

### 12. `patch_js_framework_dependency()`（上游已修复，当前停用）

修改文件：`third_party/css-what/BUILD.gn`

原问题：`css-what` 把输出指向 `../jsframework/runtime`，与 JS Framework 共用目录。一个任务清理或更新该目录时，会影响另一个任务的增量状态。

修改方式：把输出目录改为当前目标独立使用的 `css_what_sources`。

修改原理：让 `css-what` 不再写入 JS Framework 的共享运行时目录，避免不同任务互相覆盖输出或更新时间戳而触发重复构建。

### 13. `patch_camera_generated_file()`

修改文件：`device/board/hihope/rk3568/camera/vdi_impl/v4l2/BUILD.gn`

原问题：Camera 规则声明了不会真正生成的 `tmp.c`，再把生成的 `config.c` 和 `params.c` 复制回源码目录并主动更新时间。Ninja 会看到声明输出缺失，源码目录也会不断产生变化。

修改方式：删除伪造的复制任务和源码文件 `touch`；直接取得 `generate_source` 的真实输出，筛选出 `config.c`、`params.c`，让安装和编译目标直接使用这些生成文件。

修改原理：让 GN 声明的依赖、实际生成文件和编译输入完全一致，不再使用假输出，也不再修改源码目录。

### 14. `patch_sane_airscan_outputs()`（上游已修复，当前停用）

修改文件：`third_party/sane-airscan/BUILD.gn`、`third_party/sane-airscan/patch_install.py`

原问题：补丁脚本直接修改 `third_party/sane-airscan` 源码目录，而 GN 声明的输出只覆盖部分文件并且与脚本实际写入位置不一致，容易造成源码污染、补丁重复应用和任务重复执行。

修改方式：在 `${target_gen_dir}/airscan_patched` 创建完整源码副本并对副本应用补丁；GN 明确列出全部输入和输出，编译目标改为使用补丁副本中的源文件和头文件。

修改原理：源码目录只作为输入，所有构建修改都进入 `out` 下的专属目录；GN 能准确跟踪每个输入和输出，重复构建不会再次修改源码。

### 15. `patch_arkui_generated_outputs()`

修改文件：`foundation/arkui/idlize/libohos/src/peer-generation/common.ts`、`foundation/arkui/idlize/arkgen/src/arkoala.ts`

原问题：ArkUI 生成器即使生成内容完全相同，也会重新写入 GNI、API、头文件和 Meson 文件，导致文件时间变化并触发下游大范围重编译。

修改方式：公共写入函数先比较已有文件内容，相同则直接返回；ArkUI 各生成位置统一改用这个公共写入函数。

修改原理：只有生成内容真正变化时才更新文件和时间戳，使 Ninja 不会把内容未变的生成文件误判为新的输入变化。

### 16. `patch_arkts_config_copy()`

修改文件：`build/config/components/ets_frontend/generate_static_abc.py`

原问题：构建过程先备份源码中的 `arktsconfig.json`，再截断重写，最后把 `.bak` 移回。即使内容恢复，文件时间仍会变化；并行任务还可能同时修改同一个配置文件。

修改方式：读取源码配置并在缓存目录生成构建副本；把相对 `baseUrl` 按原配置目录转换为绝对路径，将副本的 `outDir` 指向缓存目录，再把后续构建使用的配置路径切换到该副本，同时删除备份和恢复逻辑。

修改原理：源码配置始终只读，构建只修改自己的缓存副本，从而避免无效时间戳、Git 工作区变化和并行任务互相覆盖；绝对 `baseUrl` 保证配置移动后仍指向原来的源码位置。

### 17. `patch_hap_ets_independent_cache()`

修改文件：`build/scripts/build_js_assets.py`

原问题：只有 JS 分支明确设置 `cachePath`，ETS 分支仍可能使用共享缓存，两个构建任务会互相覆盖缓存内容。

修改方式：通过 `asset_type` 为 JS 和 ETS 选择各自产物目录，并统一把 `cachePath` 设置为对应目录下的 `.cache`。其余 Loader 依赖和空资源 depfile 修复已经由上游实现，不再重复修改。

修改原理：JS 和 ETS 使用不同的缓存目录，避免不同类型的 HAP 编译互相覆盖缓存。

### 18. `patch_ark_stub_comment()`

修改文件：`arkcompiler/ets_runtime/script/run_ark_executable.py`、`arkcompiler/ets_runtime/ecmascript/compiler/BUILD.gn`

原问题：GN 声明了 `stub_code_comment.zip`，但执行脚本仍把它写到固定相对目录；目录不存在或编译输出为空时还会跳过生成，导致 Ninja 找不到声明的输出。

修改方式：增加 `--stub-code-comment-output` 参数，由 GN 把声明路径传给脚本；脚本创建父目录并直接写入该路径，即使编译输出为空也生成 ZIP；未传参数的普通调用不生成该文件。

修改原理：GN 负责声明并传递输出路径，Python 负责无条件创建对应文件，使实际产物与 Ninja 跟踪的路径完全一致，同时避免影响非 OHOS 调用。

### 19. `patch_optional_distributed_dependency()`（上游已修复，当前停用）

修改文件：`build/ohos/common/binary_install_info.py`

原问题：生成 depfile 时无条件加入 `dist_parts_info_file`，但该分布式部件文件是可选输入；文件不存在时，Ninja 会持续看到一个缺失依赖。

修改方式：始终记录必需的 `parts_src_installed_info_file`，仅在 `dist_parts_info_file` 确实存在时才把它追加到 depfile 输入列表。

修改原理：depfile 只记录本次构建真实存在的输入，避免可选文件缺失导致任务长期处于需要重新执行的状态。

### 20. `patch_rk3568_optional_images()`

修改文件：`build/ohos/images/BUILD.gn`

原问题：`make_images`、`eng_chipset_image` 和平台 `image_list` 都无条件包含 `eng_chipset`；RK3568 不需要该镜像且不会产生有效输出，相关依赖会造成缺失输出和重复构建。

修改方式：在三个依赖入口统一增加 `device_name != "rk3568"` 条件；RK3568 跳过 `eng_chipset`，其他设备继续保持原有依赖和镜像列表。

修改原理：只让支持该镜像的设备声明并构建 `eng_chipset`，使 RK3568 的目标图只包含实际能够生成的输出。

### 21. `patch_ramdisk_outputs()`（上游已修复，当前停用）

修改文件：`build/ohos/images/BUILD.gn`、`build/ohos/images/build_image.py`

原问题：GN 把根输出目录中的 `ramdisk.img` 和 `updater_ramdisk.img` 声明为输出，但底层 CPIO 工具实际生成平台 `images` 目录中的 `ramdisk.img` 和 `updater.img`，导致 Ninja 跟踪的路径与真实文件不一致。

修改方式：GN 分开保存传给镜像工具的路径和 Ninja 实际输出路径，并增加 `--ninja-output-image-path`；Python 仍用原工具路径触发正确的 ramdisk 类型，同时改用真实输出路径执行旧文件清理和 depfile 写入。

修改原理：镜像工具继续通过原文件名选择 ramdisk/updater 处理逻辑，Ninja 则跟踪底层工具真正生成的文件，使输出声明、清理目标和依赖记录保持一致。

### 22. `patch_system_module_output()`（上游已修复，当前停用）

修改文件：`build/ohos/packages/modules_install.py`

原问题：`arm64e_output_result` 为空时不会生成已经声明的模块信息 JSON；过滤 SA 文件时又使用 `depfiles.extend(过滤结果)`，导致原列表中的 SA 文件没有被删除，其他依赖还会重复追加。

修改方式：无论结果是否为空都调用 `write_json_file()` 创建模块信息文件；把 `depfiles.extend(...)` 改为 `depfiles = ...`，使用过滤结果直接替换原依赖列表。

修改原理：声明的 JSON 输出始终存在，depfile 只保留过滤后的真实依赖，避免缺失输出、SA 生成文件反向成为输入以及重复依赖。

### 23. `patch_image_check_results()`

修改文件：`build/ohos/packages/BUILD.gn`、`build/ohos/packages/check_seccomp_library_name.py`、`build/ohos/packages/process_field_validate.py`

原问题：Seccomp 和进程字段检查目标都声明了结果文件，但 GN 没有把路径传给检查脚本，脚本校验成功后也不会创建该输出，导致 Ninja 始终认为检查任务没有完成。

修改方式：GN 为两个检查动作增加 `--result-path`；Seccomp 脚本接收该参数并在校验成功后创建空结果文件；进程字段脚本把已经解析出的结果路径传给 `validate_cfg_file()`，并在全部检查通过后创建对应文件。

修改原理：结果文件同时作为“校验成功”标记和 Ninja 输出；检查失败时不会生成，检查成功时准确创建，使任务状态和实际校验结果保持一致。

## 维护规则

- 补丁以刚拉取的原始源码为修改起点，不兼容早期补丁格式。
- 每项补丁必须支持重复执行；已经生效时不再次写文件。
- 原始代码不唯一或无法定位时直接失败，不做模糊替换。
- 多文件补丁先完成全部校验，再开始写入，避免只修改一部分。
- 每条替换规则统一写成 `(source, new, count)`。
- `source` 和 `new` 字符串统一使用 `'''`。
- 匹配唯一时省略首行缩进和末尾换行；需要区分相似代码时保留必要边界。
- 文件最多保留一行连续空行。
