#!/bin/bash
# BaiduPCS-Go wrapper: 配置目录隔离 + 固定二进制路径
export BAIDUPCS_GO_CONFIG_DIR="${BAIDUPCS_GO_CONFIG_DIR:-$HOME/.config/baidupcs}"
mkdir -p "$BAIDUPCS_GO_CONFIG_DIR"
exec "$HOME/tools/baidupcs/BaiduPCS-Go" "$@"