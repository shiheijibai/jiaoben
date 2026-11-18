#!/usr/bin/env bash
# 版本目录入口。公共实现统一放在固定目录中，本文件只负责传递当前版本目录和命令参数。

export OPENHARMONY_WORK_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec /usr/bin/bash /home/shjb/work/Project/jiaoben/down-common.sh "$@"
