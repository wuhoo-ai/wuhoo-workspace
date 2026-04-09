#!/bin/bash
# QuantaAlpha 快速启动脚本
# 用法：./quantaalpha.sh "研究方向"

QUANTA_DIR="$HOME/.openclaw/workspace/agents/main/skills/quantaalpha-deep"

cd "$QUANTA_DIR" || exit 1

# 激活虚拟环境
source venv/bin/activate

# 检查参数
if [ -z "$1" ]; then
    echo "用法：$0 \"研究方向\""
    echo ""
    echo "示例:"
    echo "  $0 \"量价因子挖掘\""
    echo "  $0 \"Price-Volume Factor Mining\""
    echo "  $0 \"Microstructure Factors\""
    exit 1
fi

echo "========================================"
echo "QuantaAlpha 因子挖掘"
echo "========================================"
echo "研究方向：$1"
echo "数据目录：$QUANTA_DIR"
echo "========================================"

# 运行因子挖掘
./run.sh "$1"

echo ""
echo "========================================"
echo "挖掘完成！"
echo "结果位置：$QUANTA_DIR/data/results/"
echo "因子库：$QUANTA_DIR/data/results/all_factors_library.json"
echo "========================================"
