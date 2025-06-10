# Bilibili_VideoScraper

## 项目简介

Bilibili_VideoScraper 是基于 [bilibili-api](https://github.com/SocialSisterYi/bilibili-API-collect) 的 Python 爬虫工具集，包含两个主要功能模块：

1. **Bli_VIScraper.py**  
   根据 UP 主 UID 爬取指定时间范围内的视频数据（播放量、点赞、收藏、投币等），生成 SQLite 数据库和 CSV 文件

2. **Bli_CDScraper_BV.py**  
   根据 BV 号爬取视频的弹幕和评论数据，生成 CSV 文件

## 示例

依据该项目爬取数据完成的Tableau看板
![image](https://github.com/user-attachments/assets/c2214786-6938-4c1d-a45f-ddbe64a30e3c)


## 功能

- 根据 BV 号爬取视频弹幕，评论数据
- 生成结构化的db文件和 CSV 文件
- 可通过配置文件实现批量爬取
- 可通过自动化运行脚本实现定时任务调用

## 目录结构

Bilibili_VideoScraper/

├── Auto_runner.py # 自动运行脚本

├── Bli_CDScraper_BV.py # 弹幕评论爬取脚本

├── Bli_VIScraper.py # 视频信息爬取脚本

├── config.json # 配置文件示例

├── Requirements.txt # 依赖库

├── README.md # READ ME！

└── pycache/ # Python缓存文件夹

## 环境依赖

- Python 3.6+
- 推荐使用虚拟环境
- 需要安装用到的依赖库 pip install -r requirements.txt

## 使用指南
1. **配置文件说明（config.json）**
json
{

"uids": [63231],                   // UP主UID列表（可多个）

  "use_login": true,                 // 是否使用登录凭证
  
  "SESSDATA": "your_sessdata",       // 登录凭证1
  
  "bili_jct": "your_bili_jct",       // 登录凭证2
  
  "BUVID3": "your_buvid3",           // 设备标识
  
  "mode": "recent",                  // 爬取模式: recent/date_range
  
  "recent_days": 7,                  // 最近天数（仅recent模式）
  
  "start_date": "2023-01-01",        // 开始日期（仅date_range模式）
  
  "end_date": "2023-12-31",          // 结束日期（仅date_range模式）
  
  ]
}


3. **登录凭证获取**
    登录 Bilibili 网站
    按 F12 打开开发者工具
    转到 Application → Cookies
    复制以下值：
   
    SESSDATA
   
    bili_jct
   
    BUVID3
   
## 安全使用指南

1. **合规使用**  
   - 本项目仅用于**合法合规**的数据分析、学术研究等用途  
   - 使用者应遵守[Bilibili用户协议](https://www.bilibili.com/protocal/licence.html)  
   - 禁止将本项目用于商业爬取、数据贩卖等违反Bilibili规定的行为  

2. **访问频率控制**  
   - 默认配置已设置合理请求间隔(建议≥3秒/请求)  
   - 请勿修改代码提高请求频率，避免对Bilibili服务器造成压力  
   - 高频请求可能导致IP被封禁或账号受限  

3. **隐私保护**  
   - 获取的Cookies信息具有账号访问权限，请妥善保管  
   - 建议使用单独的小号进行数据采集  
   - 禁止收集、存储或传播用户隐私数据  
