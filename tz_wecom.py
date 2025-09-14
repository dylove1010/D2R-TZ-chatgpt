import requests
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 你的企业微信群机器人 Webhook 地址
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx"

app = Flask(__name__)

def fetch_data():
    url = "https://d2emu.com/tz-china"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "zh-CN,zh;q=0.9"
    }
    logging.info(f"Fetching data from {url}")
    resp = requests.get(url, headers=headers, timeout=10)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    tz_data = []
    for row in soup.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) >= 2:
            tz_data.append({
                "time": cols[0].get_text(strip=True),
                "danger": cols[1].get_text(strip=True)
            })

    # 调试：打印所有行
    logging.info("Fetched rows:")
    for item in tz_data:
        logging.info(item)

    return tz_data

def get_current_and_next_info():
    data = fetch_data()
    now = datetime.now()
    current_hour = now.strftime("%H:00")

    current_info, next_info = None, None
    for i, row in enumerate(data):
        # 修改匹配逻辑：用 "in" 而不是 startswith
        if current_hour in row["time"]:
            current_info = row
            if i + 1 < len(data):
                next_info = data[i + 1]
            break

    return current_info, next_info

def send_to_wecom(content: str):
    headers = {"Content-Type": "application/json"}
    data = {"msgtype": "text", "text": {"content": content}}
    resp = requests.post(WEBHOOK_URL, headers=headers, json=data)
    result = resp.json()
    logging.info(f"Sent message to WeCom, response: {result}")
    return result

def build_message():
    current, next_info = get_current_and_next_info()
    if not current:
        msg = "⚠️ 暂未找到当前恐怖地带信息（请检查 tz_data 日志输出）"
    else:
        msg = f"""
⏰ 当前时间段：{current['time']}
📍 当前恐怖地带：{current['danger']}

➡️ 下一个时间段：{next_info['time'] if next_info else '未知'}
📍 下一个恐怖地带：{next_info['danger'] if next_info else '未知'}
        """.strip()
    logging.info(f"Built message: {msg}")
    return msg

@app.route("/push", methods=["GET"])
def push():
    logging.info("Manual push triggered via /push")
    msg = build_message()
    result = send_to_wecom(msg)
    return jsonify({"message": msg, "result": result})

def scheduled_task():
    logging.info("Scheduled task triggered")
    msg = build_message()
    result = send_to_wecom(msg)
    logging.info("Scheduled task completed")
    return result

if __name__ == "__main__":
    logging.info("Starting Flask app with scheduler...")

    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_task, "cron", minute=0)  # 每小时整点推送
    scheduler.start()

    logging.info("Triggering first push on startup")
    scheduled_task()

    app.run(host="0.0.0.0", port=5000)
