#!/bin/bash
# GPU 健康监视器(monitor 脚本, 无 LLM): 输出必须是确定性的分桶状态, 变化才唤醒 agent
# 铁律: 不含时间戳; 连续量(nvidia 温度/显存)按桶归一化, 避免每次 tick 都"变化"
set -u
SSH="ssh -i /home/admin/.ssh/hermes-gpu -p 2222 -o ConnectTimeout=10 -o BatchMode=yes haohaijiao@localhost"

# 1) SSH 隧道
if $SSH "echo OK" >/dev/null 2>&1; then echo "ssh=OK"; else echo "ssh=FAIL"; fi

# 2) GPU 存在性 + 显存/利用率分桶(10%档)
G=$($SSH "nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits" 2>/dev/null | head -1 | tr -d '\r')
if [ -n "$G" ]; then
  used=$(echo "$G" | cut -d, -f1 | tr -d ' '); total=$(echo "$G" | cut -d, -f2 | tr -d ' '); util=$(echo "$G" | cut -d, -f3 | tr -d ' ')
  if [ -n "$total" ] && [ "$total" -gt 0 ]; then
    mbucket=$(( used / (total/10 + 1) )); ubucket=$(( util / 10 ))
    echo "gpu=present mem_bucket=$mbucket util_bucket=$ubucket"
  else echo "gpu=nodata"; fi
else echo "gpu=absent_or_smi_fail"; fi

# 3) ComfyUI
if $SSH "curl -s -m 5 http://127.0.0.1:8188/system_stats" 2>/dev/null | grep -qi cuda; then echo "comfy=UP"; else echo "comfy=DOWN"; fi

# 4) frpc (Windows 侧 NSSM 服务)
if $SSH "sc query frpc" 2>/dev/null | grep -q RUNNING; then echo "frpc=RUNNING"; else echo "frpc=NOT_RUNNING"; fi

# 5) C 盘剩余(10G 桶)
FREE=$($SSH "powershell -NoProfile -Command [math]::Floor((Get-PSDrive C).Free/10GB)" 2>/dev/null | tr -d ' \r\n')
if [ -n "$FREE" ]; then echo "disk_c_bucket=${FREE}x10G"; else echo "disk_c=unknown"; fi
