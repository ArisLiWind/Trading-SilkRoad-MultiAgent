# Trading 丝绸之路改造版

> 基于 [edict 三省六部制](https://github.com/cft0808/edict) 的 Multi-Agent 协作架构，针对量化交易场景改造。

## 架构目标

用 1300 年前的帝国分权制度，重新设计量化交易的 AI 多 Agent 协作架构：

```
皇上 (交易信号) → 太子 (信号分拣) → 中书省 (策略规划) → 门下省 (风控审核)
→ 尚书省 (任务派发) → 六部并行执行 → 奏折回报
```

## Trading 场景下的六部职责

| 部门 | 原职责 | Trading 改造 |
|------|--------|-------------|
| 户部 | 财政 | 资金管理、仓位控制 |
| 兵部 | 军事 | 交易执行、信号处理 |
| 工部 | 工程 | 数据管道、回测系统 |
| 礼部 | 礼仪 | 报告生成、推送通知 |
| 刑部 | 司法 | 异常检测、风控审计 |
| 吏部 | 人事 | Agent 调度、性能优化 |

## 核心差异（vs 原版 edict）

- **门下省** = 强制风控关卡，任何交易指令必须经过门下省审核才能执行
- **实时看板** = 军机处监控所有 Agent 执行状态、仓位、P&L
- **奏折系统** = 完整交易审计日志，可追溯每一笔决策来源

## 快速启动

```bash
# 克隆仓库
git clone https://github.com/ArisLiWind/Trading-SilkRoad-MultiAgent.git
cd Trading-SilkRoad-MultiAgent

# 启动看板（无需额外依赖）
python3 dashboard/server.py --port 8888

# 访问
open http://localhost:8888
```

## 项目状态

- [x] 三省六部制 Agent 架构复现
- [x] 军机处实时看板（本地运行）
- [x] Trading 场景 Demo 数据
- [ ] 接入真实行情数据
- [ ] 量化策略回测引擎
- [ ] 实盘交易 Agent 对接

---
*以古制御新技，以智慧驾驭 AI · Powered by edict + OpenClaw*
