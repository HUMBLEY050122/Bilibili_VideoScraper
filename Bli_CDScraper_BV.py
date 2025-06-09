import csv
import os
import time
import requests
from bilibili_api import video, comment, Credential, sync
from xml.etree import ElementTree as ET

# 设置请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.bilibili.com/"
}

# 设置输出目录
OUTPUT_DIR = r"D:\Program Files\Codefield\CODE_Python\Projects\Bilibili_DA\datas"

def ensure_dir_exists():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    return OUTPUT_DIR

def get_credentials():
    sessdata = input("请输入SESSDATA: ").strip()
    bili_jct = input("请输入bili_jct: ").strip()
    buvid3 = input("请输入buvid3: ").strip()
    return Credential(sessdata=sessdata, bili_jct=bili_jct, buvid3=buvid3)

def get_video_comments(bvid: str, credential=None, max_comments=2000):
    comments = []
    try:
        v = video.Video(bvid=bvid, credential=credential)
        page = 1
        count = 0
        while count < max_comments:
            res = sync(comment.get_comments(
                oid=v.get_aid(),
                type_=comment.CommentResourceType.VIDEO,
                page_index=page,
                credential=credential
            ))
            replies = res.get("replies", [])
            if not replies:
                break
            for r in replies:
                comments.append(r["content"]["message"])
                count += 1
                for reply in r.get("replies", []):
                    comments.append(f"回复@{r['member']['uname']}: {reply['content']['message']}")
                    count += 1
            if res["page"]["num"] * res["page"]["size"] >= res["page"]["count"]:
                break
            page += 1
            time.sleep(0.3)
    except Exception as e:
        print(f"获取评论失败: {e}")
    return comments

def get_video_danmaku(bvid: str):
    danmaku = []
    try:
        url = f"https://api.bilibili.com/x/player/pagelist?bvid={bvid}&jsonp=jsonp"
        cid = requests.get(url, headers=HEADERS).json()["data"][0]["cid"]
        xml_url = f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}"
        response = requests.get(xml_url, headers=HEADERS)
        response.encoding = "utf-8"
        root = ET.fromstring(response.text)
        for d in root.findall("d"):
            danmaku.append(d.text)
    except Exception as e:
        print(f"获取弹幕失败: {e}")
    return danmaku

def save_to_csv(data, bvid):
    output_dir = ensure_dir_exists()
    path = os.path.join(output_dir, f"BVID_{bvid}_弹幕评论.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["bv", "comments", "danmaku"])
        writer.writeheader()
        writer.writerow(data)
    print(f"数据已保存至: {path}")

if __name__ == "__main__":
    print("===== B站指定BV号视频评论与弹幕采集 =====")
    bvid = input("请输入视频的BV号（如 BV1xx411c7mD）: ").strip()
    use_credential = input("是否使用登录凭证获取更多评论? (y/n): ").lower() == 'y'
    credential = get_credentials() if use_credential else None

    comments = get_video_comments(bvid, credential)
    danmaku = get_video_danmaku(bvid)

    save_to_csv({
        "bv": bvid,
        "comments": " | ".join(comments),
        "danmaku": " | ".join(danmaku)
    }, bvid)

    print(f"评论数: {len(comments)}, 弹幕数: {len(danmaku)}")
    print("采集完成！")
