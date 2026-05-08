# Futu OpenD 账户调试 — GTWLog 方法论

> 创建日期: 2026-05-06 | 场景: OpenD v10.3.6308 账户过滤 Bug

## 问题背景

Python SDK `get_acc_list()` 只返回部分模拟账户（4/10），CN CASH 18767295 和 US MARGIN 18767293 返回 "Nonexisting acc_id"。但前一天 US 18767293 调仓正常。

## 三层验证体系

| 层级 | 数据源 | 可信度 | 获取方式 |
|------|--------|:---:|------|
| **服务器** | GTWLog `Trd_GetAccList` 响应 | ⭐⭐⭐ 金标准 | 解析 GTWLog 日志 |
| **OpenD** | `auth_acc_list` 文件 | ⭐⭐ 加密存储 | `~/.com.futunn.FutuOpenD/F3CNN/ftnet/auth_acc_list/` |
| **SDK** | `get_acc_list()` | ⭐ 可能被过滤 | Python `futu` SDK |

## GTWLog 分析命令

```bash
# 查最新 GTWLog，提取服务器返回的原始账户列表
find ~/wuhoo-workspace/tools/opend/logs/Log/ -name "GTWLog_*" -mmin -10 -type f | while read f; do
  grep "Trd_GetAccList.*Response" "$f" 2>/dev/null | python3.11 -c "
import sys, json
for line in sys.stdin:
    idx = line.find('ProtobufBodyToJson: ')
    if idx < 0: continue
    d = json.loads(line[idx+len('ProtobufBodyToJson: '):].strip())
    for a in d['s2c']['accList']:
        env = 'SIM' if a['trdEnv'] == 0 else 'REAL'
        status = 'ACTIVE' if a.get('accStatus',0)==0 else 'DISABLED'
        mkts = {1:'HK',2:'US',3:'CN',4:'HKCC',113:'HKFUND',123:'USFUND'}
        mkt_str = ','.join([mkts.get(m,'?') for m in a.get('trdMarketAuthList',[])])
        print(f'{env} {a[\"accID\"]}: {mkt_str} [{status}]')
    break
"
done
```

## 判断逻辑

- GTWLog 账户数 > SDK `get_acc_list()` 返回数 → **OpenD 过滤 Bug**，需升级 OpenD
- GTWLog 账户数 = SDK 返回数 → 账户确实不存在，需在富途牛牛 App 开通
- 某账户 GTWLog 有但 SDK 返回 "Nonexisting" → OpenD 过滤该账户

## OpenD 版本对比

| 版本 | 安装路径 | 账户过滤 Bug |
|------|---------|:---:|
| 10.3.6308 | `~/wuhoo-workspace/tools/opend/Futu_OpenD_10.3.6308_Centos7/` | ✅ 存在 |
| 10.10.151 | 未安装 | 未知（疑已修复） |

## SDK 版本对照

| SDK 版本 | OpenD 兼容性 |
|---------|------------|
| 10.02.6208 | 部分兼容（旧） |
| 10.04.6408 | 推荐（pip install futu-api --upgrade） |

## 相关文件路径

```
OpenD 进程:      /home/admin/wuhoo-workspace/tools/opend/Futu_OpenD_10.3.6308_Centos7/Futu_OpenD_10.3.6308_Centos7/FutuOpenD
启动脚本:        ~/wuhoo-workspace/scripts/start_opend.sh
GTWLog:          ~/wuhoo-workspace/tools/opend/logs/Log/GTWLog_*.log
auth_acc_list:   ~/.com.futunn.FutuOpenD/F3CNN/ftnet/auth_acc_list/
SDK 版本查询:    python3.11 -c "import futu; print(futu.__version__)"
OpenD 版本查询:  FutuOpenD --version (在交互控制台输入 version)
```
