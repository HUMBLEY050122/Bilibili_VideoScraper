import asyncio
import json
from datetime import datetime, timedelta
from Bli_VIScraper import UpAnalyzer
from bilibili_api import Credential

def load_config(path: str = "config.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

async def run_for_uid(uid: int, start_ts: int, end_ts: int, credential=None):
    print(f"\n📊 正在抓取 UID: {uid}")
    analyzer = UpAnalyzer(uid, start_ts, end_ts, credential)
    try:
        await analyzer.fetch_all_data()
        analyzer.export_data()
    except Exception as e:
        print(f"❌ UID {uid} 抓取失败: {e}")

async def main():
    config = load_config()
    uids = config["uids"]
    mode = config.get("mode", "all")

    # 认证信息
    credential = None
    if config.get("use_login"):
        credential = Credential(
            sessdata=config["SESSDATA"],
            bili_jct=config["bili_jct"],
            buvid3=config["BUVID3"]
        )

    # 时间范围
    start_ts, end_ts = 0, 0
    if mode == "recent":
        days = config.get("recent_days", 7)
        now = datetime.now()
        start_ts = int((now - timedelta(days=days)).timestamp())
        end_ts = int(now.timestamp())
    elif mode == "date_range":
        start = datetime.strptime(config["start_date"], "%Y-%m-%d")
        end = datetime.strptime(config["end_date"], "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        start_ts = int(start.timestamp())
        end_ts = int(end.timestamp())

    # 多 UID 抓取
    for uid in uids:
        await run_for_uid(uid, start_ts, end_ts, credential)

if __name__ == "__main__":
    asyncio.run(main())
