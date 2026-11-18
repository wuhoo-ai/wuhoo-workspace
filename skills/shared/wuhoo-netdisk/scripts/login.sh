#!/bin/bash
# 百度网盘登录助手 — 凭证只从用户自建的 0600 文件读取，全程不回显、不进聊天。
# 用法: bash login.sh
set -u
PCS="$(cd "$(dirname "$0")" && pwd)/pcs.sh"
CRED="$HOME/.config/baidupcs/credentials.env"

if [ ! -f "$CRED" ]; then
  cat <<'EOF'
[未找到凭证文件] 请按以下步骤自行创建（凭证不要发到聊天里）:
1. 浏览器登录 https://pan.baidu.com
2. F12 → Application/应用 → Cookies → https://pan.baidu.com
   复制 BDUSS 的值；同域下复制 STOKEN 的值（注意是 STOKEN 不是 bdstoken，
   STOKEN 必须含大写字母，否则拿错了；STOKEN 仅转存功能需要，上传下载可不填）
3. 在服务器上执行（值替换为你复制的）:
   mkdir -p ~/.config/baidupcs
   umask 077
   cat > ~/.config/baidupcs/credentials.env <<'CRED'
BDUSS=粘贴这里
STOKEN=粘贴这里
CRED
   chmod 600 ~/.config/baidupcs/credentials.env
4. 重新运行本脚本
EOF
  exit 2
fi

perm=$(stat -c %a "$CRED")
if [ "$perm" != "600" ]; then
  echo "[拒绝] 凭证文件权限 $perm 不安全，请先: chmod 600 $CRED" >&2
  exit 3
fi

BDUSS=$(sed -n 's/^BDUSS=//p' "$CRED" | head -1 | tr -d '\r' | sed 's/^"//;s/"$//')
STOKEN=$(sed -n 's/^STOKEN=//p' "$CRED" | head -1 | tr -d '\r' | sed 's/^"//;s/"$//')
if [ -z "$BDUSS" ]; then
  echo "[拒绝] credentials.env 缺 BDUSS 行" >&2; exit 3
fi

if [ -n "$STOKEN" ]; then
  out=$(bash "$PCS" login -bduss="$BDUSS" -stoken="$STOKEN" 2>&1)
else
  echo "[提示] 未填 STOKEN，仅登录 BDUSS（上传/下载可用，分享转存不可用）"
  out=$(bash "$PCS" login -bduss="$BDUSS" 2>&1)
fi
# 回显过滤：任何情况下不打印凭证值（bash 字面替换，无 sed 元字符/管道解析坑）
out=${out//$BDUSS/***}
if [ -n "$STOKEN" ]; then out=${out//$STOKEN/***}; fi
printf '%s\n' "$out"

echo "--- 验证 ---"
bash "$PCS" who
bash "$PCS" quota