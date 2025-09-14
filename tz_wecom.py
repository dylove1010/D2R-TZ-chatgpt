import logging
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from playwright.sync_api import sync_playwright
import time

# -----------------------------
# 配置区
# -----------------------------
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b0bcfe46-3aa1-4071-afd5-da63be5a8644"
FETCH_URL = "https://d2emu.com/tz-china"

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')


# -----------------------------
# 数据抓取函数
# -----------------------------
def fetch_data():
    """抓取当前和下一个恐怖地带时间"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(FETCH_URL, wait_until="networkidle")
        time.sleep(5)  # 等待 JS 渲染
        body_text = page.inner_text("body")
        browser.close()

    current_info, next_info = None, None
    for line in body_text.splitlines():
        line = line.strip()
        if "Current Terror Zone" in line:
            current_info = line
        elif "Next Terror Zone" in line:
            next_info = line

    logging.info(f"抓取到的当前: {current_info}, 下一个: {next_info}")
    return current_info, next_info


# -----------------------------
# 构建推送消息
# -----------------------------
def build_message():
    current, next_info = fetch_data()
    if not current or not next_info:
        return "⚠️ 暂未找到当前恐怖地带信息，请检查页面解析。"

    msg = f"⚠️ 当前恐怖地带: {current}\n⚠️ 下一个恐怖地带: {next_info}"
    logging.info(f"Built message: {msg}")
    return msg


# -----------------------------
# 发送企业微信消息
# -----------------------------
def send_wecom_message(msg):
    data = {
        "msgtype": "text",
        "text": {"content": msg}
    }
    try:
        resp = requests.post(WEBHOOK_URL, json=data, timeout=10)
        logging.info(f"Sent message to WeCom, response: {resp.json()}")
    except Exception as e:
        logging.error(f"发送企业微信消息失败: {e}")


# -----------------------------
# 定时任务
# -----------------------------
def scheduled_task():
    logging.info("Scheduled task triggered")
    msg = build_message()
    send_wecom_message(msg)
    logging.info("Scheduled task completed")


# -----------------------------
# 启动 APScheduler
# -----------------------------
if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    # 每小时推送一次
    scheduler.add_job(scheduled_task, 'cron', minute=0)
    scheduler.start()
    logging.info("Scheduler started")

    # 启动时立即推送一次
    scheduled_task()

    # 保持 Flask-like 循环
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Scheduler shutdown")
