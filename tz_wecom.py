import requests
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

# 你的企业微信群机器人 Webhook 地址
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b0bcfe46-3aa1-4071-afd5-da63be5a8644"

app = Flask(__name__)

def fetch_data():
    url = "https://d2emu.com/tz-china"
    resp = requests.get(url, timeout=10)
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
    return tz_data

def get_current_and_next_info():
    data = fetch_data()
    now = datetime.now()
    current_hour = now.strftime("%H:00")

    current_info, next_info = None, None
    for i, row in enumerate(data):
        if row["time"].startswith(current_hour):
            current_info = row
            if i + 1 < len(data):
                next_info = data[i + 1]
            break
    return current_info, next_info

def send_to_wecom(content: str):
    headers = {"Content-Type": "application/json"}
    data = {
        "msgtype": "text",
        "text": {"content": content}
    }
    resp = requests.post(WEBHOOK_URL, headers=headers, json=data)
    return resp.json()

def build_message():
    current, next_info = get_current_and_next_info()
    if not current:
        msg = "⚠️ 暂未找到当前恐怖地带信息"
    else:
        msg = f"""
⏰ 当前时间段：{current['time']}
📍 当前恐怖地带：{current['danger']}

➡️ 下一个时间段：{next_info['time'] if next_info else '未知'}
📍 下一个恐怖地带：{next_info['danger'] if next_info else '未知'}
        """.strip()
    return msg

@app.route("/push", methods=["GET"])
def push():
    msg = build_message()
    result = send_to_wecom(msg)
    return jsonify({"message": msg, "result": result})

def scheduled_task():
    """定时任务：推送一次"""
    msg = build_message()
    result = send_to_wecom(msg)
    print(f"[定时任务] 已推送: {msg}")
    return result

if __name__ == "__main__":
    # 创建调度器
    scheduler = BackgroundScheduler()
    # 每小时整点执行一次
    scheduler.add_job(scheduled_task, "cron", minute=0)
    scheduler.start()

    # 启动时立即推送一次（便于测试）
    scheduled_task()

    # 启动 Flask
    app.run(host="0.0.0.0", port=5000)
