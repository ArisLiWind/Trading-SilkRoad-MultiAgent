#!/usr/bin/env python3
"""
Trading丝绸之路 · 实时行情数据接入
数据源：雅虎财经 (yfinance) + Binance 公开 API（无需 Key）
输出到：data/market_data.json（供军机处看板读取）
"""

import json, pathlib, datetime, time, logging, sys, urllib.request, urllib.error
from typing import Optional

log = logging.getLogger('market')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

BASE = pathlib.Path(__file__).parent.parent
DATA = BASE / 'data'
DATA.mkdir(exist_ok=True)
OUTPUT = DATA / 'market_data.json'

# ── 监控标的配置 ─────────────────────────────────────────────
WATCHLIST = {
    "crypto": [
        {"symbol": "BTC-USD",  "name": "比特币",    "binance": "BTCUSDT"},
        {"symbol": "ETH-USD",  "name": "以太坊",    "binance": "ETHUSDT"},
        {"symbol": "SOL-USD",  "name": "Solana",    "binance": "SOLUSDT"},
        {"symbol": "BNB-USD",  "name": "BNB",       "binance": "BNBUSDT"},
    ],
    "us_stocks": [
        {"symbol": "AAPL",  "name": "苹果"},
        {"symbol": "NVDA",  "name": "英伟达"},
        {"symbol": "MSFT",  "name": "微软"},
        {"symbol": "SPY",   "name": "标普500ETF"},
        {"symbol": "QQQ",   "name": "纳指ETF"},
    ],
    "cn_stocks": [
        {"symbol": "BABA",  "name": "阿里巴巴"},
        {"symbol": "BIDU",  "name": "百度"},
        {"symbol": "PDD",   "name": "拼多多"},
    ]
}

# ── Binance 公开 API（无需 Key，实时成交价）──────────────────
def fetch_binance_prices(symbols: list[str]) -> dict:
    """拉取 Binance 实时成交价，无需 API Key（用 curl_cffi 绕过 SSL 代理问题）"""
    result = {}
    try:
        import curl_cffi.requests as cffi_req
        resp = cffi_req.get(
            "https://api.binance.com/api/v3/ticker/24hr",
            timeout=10, impersonate="chrome"
        )
        data = resp.json()
        lookup = {d['symbol']: d for d in data}
        for sym in symbols:
            if sym in lookup:
                d = lookup[sym]
                result[sym] = {
                    "price":      round(float(d['lastPrice']), 4),
                    "change_pct": round(float(d['priceChangePercent']), 2),
                    "volume_24h": round(float(d['quoteVolume']) / 1e6, 1),
                    "high_24h":   round(float(d['highPrice']), 4),
                    "low_24h":    round(float(d['lowPrice']), 4),
                    "source":     "binance"
                }
        log.info(f"Binance 拉取成功: {len(result)} 个标的")
    except Exception as e:
        log.warning(f"Binance API 失败: {e}")
    return result

# ── 雅虎财经（yfinance）────────────────────────────────────
def fetch_yfinance_prices(symbols: list[str]) -> dict:
    """拉取雅虎财经行情"""
    result = {}
    try:
        import yfinance as yf
        tickers = yf.Tickers(" ".join(symbols))
        for sym in symbols:
            try:
                info = tickers.tickers[sym].fast_info
                prev = info.previous_close or 0
                price = info.last_price or 0
                change_pct = round((price - prev) / prev * 100, 2) if prev else 0
                result[sym] = {
                    "price":      round(price, 4),
                    "change_pct": change_pct,
                    "high_24h":   round(info.year_high or 0, 2),
                    "low_24h":    round(info.year_low or 0, 2),
                    "source":     "yahoo"
                }
            except Exception as e:
                log.warning(f"  {sym} 获取失败: {e}")
    except Exception as e:
        log.warning(f"yfinance 批量请求失败: {e}")
    return result

# ── 计算信号（简单技术指标）──────────────────────────────────
def compute_signal(item: dict) -> str:
    """基于24h涨跌幅给出简单信号"""
    pct = item.get("change_pct", 0)
    if pct > 3:   return "🟢 强势"
    if pct > 0.5: return "🟩 偏多"
    if pct > -0.5:return "⬜ 中性"
    if pct > -3:  return "🟥 偏空"
    return "🔴 弱势"

# ── 主拉取逻辑 ──────────────────────────────────────────────
def fetch_all() -> dict:
    log.info("开始拉取行情数据...")
    now = datetime.datetime.now().isoformat(timespec='seconds')

    # 1. Binance 拉加密货币（优先，更实时）
    binance_symbols = [c["binance"] for c in WATCHLIST["crypto"] if "binance" in c]
    binance_data = fetch_binance_prices(binance_symbols)

    # 2. Yahoo 拉股票 + 备用加密
    yf_symbols = (
        [c["symbol"] for c in WATCHLIST["crypto"]] +
        [s["symbol"] for s in WATCHLIST["us_stocks"]] +
        [s["symbol"] for s in WATCHLIST["cn_stocks"]]
    )
    yf_data = fetch_yfinance_prices(yf_symbols)

    # 3. 组装结果
    sections = {}

    for cat, items in WATCHLIST.items():
        section = []
        for item in items:
            sym = item["symbol"]
            bnc = item.get("binance")

            # 优先用 Binance 数据（加密货币）
            if bnc and bnc in binance_data:
                d = {**binance_data[bnc], "symbol": sym, "name": item["name"]}
            elif sym in yf_data:
                d = {**yf_data[sym], "symbol": sym, "name": item["name"]}
            else:
                d = {"symbol": sym, "name": item["name"], "price": None,
                     "change_pct": None, "source": "unavailable"}

            d["signal"] = compute_signal(d)
            section.append(d)

        sections[cat] = section

    # 4. 整体市场情绪
    all_pcts = [
        item["change_pct"]
        for cat in sections.values()
        for item in cat
        if item.get("change_pct") is not None
    ]
    avg_pct = round(sum(all_pcts) / len(all_pcts), 2) if all_pcts else 0
    mood = "贪婪" if avg_pct > 1 else "恐惧" if avg_pct < -1 else "中性"

    result = {
        "updatedAt": now,
        "market_mood": mood,
        "avg_change_pct": avg_pct,
        "sections": sections
    }
    log.info(f"行情拉取完成: {len(all_pcts)} 个标的，市场情绪={mood}({avg_pct:+.2f}%)")
    return result

# ── 写入 + 看板任务更新 ──────────────────────────────────────
def save_and_sync(data: dict):
    """写入 market_data.json，并同步到看板任务"""
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    log.info(f"已写入 {OUTPUT}")

    # 同步到看板任务（更新"实时行情数据接入"任务的进展）
    tasks_file = DATA / 'tasks_source.json'
    if tasks_file.exists():
        tasks = json.loads(tasks_file.read_text())
        summary_lines = []
        for cat, items in data["sections"].items():
            for item in items:
                if item.get("price"):
                    pct = item['change_pct']
                    summary_lines.append(
                        f"{item['name']} {item['price']:,.2f} ({pct:+.2f}%) {item['signal']}"
                    )

        progress = (
            f"[{data['updatedAt']}] 市场情绪: {data['market_mood']} ({data['avg_change_pct']:+.2f}%)\n"
            + " | ".join(summary_lines[:6])
        )

        updated = False
        for t in tasks:
            if "行情" in t["title"] or "market" in t["id"].lower():
                t["progress"] = progress
                t["updatedAt"] = data["updatedAt"]
                if t.get("state") == "Zhongshu":
                    t["state"] = "Doing"
                    t["official"] = "户部"
                    t["org"] = "户部"
                updated = True

        if updated:
            tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2))
            log.info("看板任务进展已同步")

# ── 入口 ────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Trading丝绸之路 · 行情数据接入")
    parser.add_argument("--watch", action="store_true", help="持续监控模式（每60秒刷新）")
    parser.add_argument("--interval", type=int, default=60, help="刷新间隔秒数（默认60）")
    args = parser.parse_args()

    if args.watch:
        log.info(f"进入持续监控模式，每 {args.interval} 秒刷新...")
        while True:
            try:
                data = fetch_all()
                save_and_sync(data)
            except Exception as e:
                log.error(f"刷新失败: {e}")
            time.sleep(args.interval)
    else:
        data = fetch_all()
        save_and_sync(data)
        # 打印摘要
        print(f"\n{'='*50}")
        print(f"市场情绪: {data['market_mood']}  均涨跌: {data['avg_change_pct']:+.2f}%")
        print(f"更新时间: {data['updatedAt']}")
        print(f"{'='*50}")
        for cat, items in data["sections"].items():
            cat_name = {"crypto":"加密货币","us_stocks":"美股","cn_stocks":"中概股"}.get(cat, cat)
            print(f"\n【{cat_name}】")
            for item in items:
                if item.get("price"):
                    v = item.get("volume_24h")
                    vol = f"  成交量: {v:.0f}M" if v else ""
                    print(f"  {item['name']:8s} {item['price']:>12,.4f}  {item['change_pct']:>+6.2f}%  {item['signal']}{vol}")
        print()

if __name__ == "__main__":
    main()
