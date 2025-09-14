import time
import requests
import logging
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from playwright.sync_api import sync_playwright

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 企业微信群机器人 Webhook 地址
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b0bcfe46-3aa1-4071-afd5-da63be5a8644"

app = Flask(__name__)

def fetch_data_chinese():
    """用 Playwright 渲染页面，抓取简体中文的恐怖地带信息"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # 模拟中文浏览器环境
        page.set_extra_http_headers({"Accept-Language": "zh-CN,zh;q=0.9"})
        page.goto("https://d2emu.com/tz-china", timeout=60000)

        # 等待页面加载渲染
        time.sleep(5)

        # 获取页面所有文字
        body_text = page.inner_text("body")
        browser.close()

    logging.info("Fetched Chinese page content:")
    logging.info(body_text)

    current_info, next_info = None, None
    for line in body_text.splitlines():
        if "当前恐怖地带" in line:
            current_info = line.strip()
        elif "下一个恐怖地带" in line:
            next_info = line.strip()

    return current_info, next_info

def send_to_wecom(content: str):
    """推送消息到企业微信"""
    headers = {"Content-Type": "application/json"}
    data = {"msgtype": "text", "text": {"content": content}}
    resp = requests.post(WEBHOOK_URL, headers=headers, json=data)
    logging.info(f"Sent message to WeCom, response: {resp.json()}")
    return resp.json()

def build_message():
    """组装消息"""
    current, next_info = fetch_data_chinese()
    if not current:
        msg = "⚠️ 暂未找到当前恐怖地带信息，请检查页面解析。"
    else:
        msg = f"""
⏰ {current}
➡️ {next_info if next_info else '下一个恐怖地带未知'}
        """.strip()
    logging.info(f"Built message: {msg}")
    return msg

@app.route("/push", methods=["GET"])
def push():
    """手动触发推送"""
    logging.info("Manual push triggered via /push")
    msg = build_message()
    result = send_to_wecom(msg)
    return jsonify({"message": msg, "result": result})

def scheduled_task():
    """定时任务推送"""
    logging.info("Scheduled task triggered")
    msg = build_message()
    send_to_wecom(msg)
    logging.info("Scheduled task completed")

if __name__ == "__main__":
    logging.info("Starting Flask app with scheduler...")

    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_task, "cron", minute=0)  # 每小时整点推送
    scheduler.start()

    # 启动时立即推送一次，方便测试
    scheduled_task()

    app.run(host="0.0.0.0", port=5000)
