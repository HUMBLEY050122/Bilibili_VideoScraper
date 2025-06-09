import asyncio
import os
import csv
import sqlite3
import time
import logging
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import pandas as pd
from bilibili_api import user, video, Credential, request_settings
from rich.console import Console
from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn

# 控制台美化输出
console = Console()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 常量定义: 强制导出到指定目录
DEFAULT_OUTPUT_DIR = r"D:\Program Files\Codefield\CODE_Python\Projects\Bilibili_DA\datas"
DB_FILENAME_TEMPLATE = "up_{uid}.db"
CSV_FILENAME_TEMPLATE = "up_{uid}_data.csv"

class FileManager:
    """
    负责数据库和CSV文件的初始化与路径管理
    """
    def __init__(self, uid: int) -> None:
        # 始终使用 DEFAULT_OUTPUT_DIR
        self.uid = uid
        self.output_dir = DEFAULT_OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        self.db_path = os.path.join(self.output_dir, DB_FILENAME_TEMPLATE.format(uid=uid))
        self.csv_path = os.path.join(self.output_dir, CSV_FILENAME_TEMPLATE.format(uid=uid))

    def init_database(self) -> None:
        """创建SQLite数据库及表结构"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS videos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bvid TEXT UNIQUE,
                        pubdate TIMESTAMP,
                        title TEXT,
                        view INTEGER,
                        danmaku INTEGER,
                        reply INTEGER,
                        favorite INTEGER,
                        coin INTEGER,
                        share INTEGER,
                        like INTEGER,
                        duration INTEGER,
                        current_fans INTEGER,
                        crawl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.commit()
            logger.info(f"数据库已初始化: {self.db_path}")
        except sqlite3.Error as err:
            logger.error(f"初始化数据库失败: {err}")
            raise

    def init_csv(self) -> None:
        """创建CSV文件并写入表头"""
        header = [
            'bvid', 'pubdate', 'title', 'view', 'danmaku',
            'reply', 'favorite', 'coin', 'share', 'like', 'duration', 'current_fans'
        ]
        try:
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(header)
            logger.info(f"CSV文件已初始化: {self.csv_path}")
        except IOError as err:
            logger.error(f"初始化CSV失败: {err}")
            raise

class DBManager:
    """
    负责与SQLite的交互：插入视频数据与导出CSV
    """
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def insert_video(self, data: Dict[str, Any], current_fans: int) -> None:
        """插入或更新单条视频记录"""
        sql = (
            "INSERT OR REPLACE INTO videos ("
            "bvid, pubdate, title, view, danmaku, reply, favorite, coin, share, like, duration, current_fans)"
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        params = (
            data['bvid'], data['pubdate'], data['title'], data['view'],
            data['danmaku'], data['reply'], data['favorite'], data['coin'],
            data['share'], data['like'], data['duration'], current_fans
        )
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(sql, params)
                conn.commit()
        except sqlite3.Error as err:
            logger.error(f"插入视频数据失败 (bvid={data['bvid']}): {err}")

    def export_to_csv(self, csv_path: str) -> bool:
        """从数据库读取数据并导出到CSV"""
        query = (
            "SELECT bvid, pubdate, title, view, danmaku, reply, favorite, coin, share, like, duration, current_fans "
            "FROM videos"
        )
        try:
            df = pd.read_sql_query(query, sqlite3.connect(self.db_path))
            if not df.empty:
                df.to_csv(csv_path, index=False)
                logger.info(f"成功导出 {len(df)} 条记录到 {csv_path}")
                return True
            else:
                logger.warning("数据库中无数据可导出")
                return False
        except Exception as err:
            logger.error(f"导出CSV失败: {err}")
            return False

class BilibiliFetcher:
    """
    负责与Bilibili API的交互，获取用户粉丝与视频数据
    """
    def __init__(self, uid: int, credential: Optional[Credential] = None) -> None:
        self.uid = uid
        self.credential = credential
        self.client_user = user.User(uid, credential=credential)

    async def get_current_fans(self) -> int:
        """获取当前粉丝数"""
        try:
            relation = await self.client_user.get_relation()
            return relation.get('follower', 0)
        except Exception:
            info = await self.client_user.get_user_info()
            return info.get('follower', info.get('data', {}).get('fans', 0))

    async def fetch_videos_page(self, page: int) -> Dict[str, Any]:
        """按页获取视频列表"""
        return await self.client_user.get_videos(pn=page)

    async def fetch_video_stats(self, bvid: str) -> Optional[Dict[str, Any]]:
        """获取单个视频的统计与信息"""
        try:
            v = video.Video(bvid=bvid, credential=self.credential)
            info = await v.get_info()
            stat = info.get('stat', {})
            return {
                'bvid': bvid,
                'pubdate': datetime.fromtimestamp(info.get('pubdate', 0)).strftime('%Y-%m-%d %H:%M'),
                'title': info.get('title', ''),
                'view': stat.get('view', 0),
                'danmaku': stat.get('danmaku', 0),
                'reply': stat.get('reply', 0),
                'favorite': stat.get('favorite', 0),
                'coin': stat.get('coin', 0),
                'share': stat.get('share', 0),
                'like': stat.get('like', 0),
                'duration': info.get('duration', 0)
            }
        except Exception as err:
            logger.warning(f"获取视频 {bvid} 数据失败: {err}")
            return None

class UpAnalyzer:
    """
    核心分析器，负责协调数据抓取、存储与导出流程
    """
    def __init__(
        self,
        uid: int,
        start_ts: int = 0,
        end_ts: int = 0,
        credential: Optional[Credential] = None
    ) -> None:
        self.uid = uid
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.credential = credential
        self.file_manager = FileManager(uid)
        self.db_manager = DBManager(self.file_manager.db_path)
        self.fetcher = BilibiliFetcher(uid, credential)
        self.total_videos = 0
        self.processed_videos = 0

        # 初始化存储结构
        self.file_manager.init_database()
        self.file_manager.init_csv()

    async def _process_page(self, page: int, current_fans: int) -> bool:
        """处理单页视频：过滤时间、获取详细数据并存储"""
        resp = await self.fetcher.fetch_videos_page(page)
        vlist = resp.get('list', {}).get('vlist', [])
        if not vlist:
            return False

        # 首次获取总视频数，动态设置进度条总数
        if page == 1:
            self.total_videos = resp.get('page', {}).get('count', 0) or 0
            logger.info(f"总视频数: {self.total_videos}")

        valid_count = 0
        for item in vlist:
            created_ts = item.get('created', 0)
            if (self.end_ts and created_ts > self.end_ts) or (created_ts < self.start_ts):
                continue

            stats = await self.fetcher.fetch_video_stats(item['bvid'])
            if not stats:
                continue

            stats['bvid'] = item['bvid']
            self.db_manager.insert_video(stats, current_fans)
            valid_count += 1
            self.processed_videos += 1

        return valid_count > 0

    async def fetch_all_data(self) -> None:
        """抓取所有视频数据并存入数据库"""
        request_settings.set("impersonate", "chrome110")
        request_settings.set("headers", {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://space.bilibili.com/"
        })
        request_settings.set("delay", 1.5)

        current_fans = await self.fetcher.get_current_fans()
        console.print(f"[bold cyan]当前粉丝数:[/bold cyan] {current_fans}")

        page = 1
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.completed]{task.completed}/{task.total}",
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task_id = progress.add_task("[green]抓取视频数据中...", total=0)

            while True:
                has_data = await self._process_page(page, current_fans)
                if not has_data:
                    break

                if page == 1 and self.total_videos:
                    progress.update(task_id, total=self.total_videos)

                if self.total_videos:
                    progress.update(task_id, completed=self.processed_videos)

                page += 1
                await asyncio.sleep(0.5)

        console.print(f"[bold green]数据抓取完成，共处理 {self.processed_videos} 条视频记录。[/bold green]")

    def export_data(self) -> bool:
        """将数据库中的数据导出到CSV文件"""
        return self.db_manager.export_to_csv(self.file_manager.csv_path)

async def main() -> None:
    console.print("\n[bold magenta]=== B站UP主数据分析工具 ===[/bold magenta]")
    try:
        uid = int(console.input("请输入UP主UID: "))
    except ValueError:
        console.print("[red]UID必须为数字[/red]")
        return

    credential = None
    if console.input("是否需要登录获取完整数据？(y/n): ").strip().lower() == 'y':
        console.print("请提供登录凭证：")
        sessdata = console.input("SESSDATA: ").strip()
        bili_jct = console.input("bili_jct: ").strip()
        buvid3 = console.input("BUVID3: ").strip()
        credential = Credential(sessdata=sessdata, bili_jct=bili_jct, buvid3=buvid3)
        console.print("[green]登录凭证已设置[/green]")

    # 选择时间范围
    start_ts, end_ts = 0, 0
    choice = console.input("\n请选择时间范围：1. 日期范围  2. 最近N天  3. 全部数据 (1/2/3): ")
    try:
        if choice == '1':
            start_date = datetime.strptime(console.input("开始日期 (YYYY-MM-DD): "), "%Y-%m-%d")
            end_date = datetime.strptime(console.input("结束日期 (YYYY-MM-DD): "), "%Y-%m-%d")
            start_ts = int(start_date.timestamp())
            end_ts = int(end_date.replace(hour=23, minute=59, second=59).timestamp())
            console.print(f"[cyan]时间范围:[/cyan] {start_date.date()} 至 {end_date.date()}")
        elif choice == '2':
            days = int(console.input("最近多少天: "))
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            start_ts = int(start_date.timestamp())
            end_ts = int(end_date.timestamp())
            console.print(f"[cyan]时间范围:[/cyan] 最近 {days} 天")
        else:
            console.print("[cyan]将获取全部数据[/cyan]")
    except ValueError:
        console.print("[red]输入不合法，将获取全部数据[/red]")

    analyzer = UpAnalyzer(uid, start_ts, end_ts, credential)
    console.print("\n[bold yellow]开始抓取数据...[/bold yellow]")
    try:
        await analyzer.fetch_all_data()
    except Exception as err:
        console.print(f"[red]数据抓取出错: {err}[/red]")
        return

    if analyzer.export_data():
        console.print(f"\n[green]数据抓取与导出完成，文件保存于:[/green] {analyzer.file_manager.output_dir}")
    else:
        console.print("\n[red]数据导出时发生问题。[/red]")

if __name__ == "__main__":
    asyncio.run(main())
