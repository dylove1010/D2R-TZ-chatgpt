# tz_wecom.py
import logging
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from playwright.sync_api import sync_playwright

# -----------------------
# 配置
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b0bcfe46-3aa1-4071-afd5-da63be5a8644"
FETCH_URL = "https://d2emu.com/tz-china"
TIMEZONE_OFFSET = 8  # 北京时间 UTC+8

logging.basicConfig(level=logging.INFO)

# -----------------------
app = Flask(__name__)
scheduler = BackgroundScheduler()

def fetch_terror_zone():
    logging.info("开始抓取恐怖地带信息...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(FETCH_URL)
        try:
            page.wait_for_selector("#a2x", timeout=10000)
        except:
            logging.warning("抓取失败: #a2x 未出现")
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # 当前恐怖地带
    current_zone_div = soup.find("div", id="a2x")
    current_time_div = soup.find("div", id="current-time")
    current_zone = current_zone_div.get_text(separator=" | ").strip() if current_zone_div else None
    current_time = current_time_div.text.strip() if current_time_div else None

    # 下一个恐怖地带
    next_zone_div = soup.find("div", id="x2a")
    next_time_div = soup.find("div", id="next-time")
    next_zone = next_zone_div.get_text(separator=" | ").strip() if next_zone_div else None
    next_time = next_time_div.text.strip() if next_time_div else None

    # 时间转换为北京时间
    def to_beijing(tstr):
        try:
            dt = datetime.strptime(tstr, "%Y/%m/%d %H:%M:%S")
            dt += timedelta(hours=TIMEZONE_OFFSET)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return tstr

    current_time = to_beijing(current_time) if current_time else None
    next_time = to_beijing(next_time) if next_time else None

    logging.info(f"抓取到的当前信息: {current_zone} {current_time}")
    logging.info(f"抓取到的下一个信息: {next_zone} {next_time}")

    return current_zone, current_time, next_zone, next_time

def build_message():
    current_zone, current_time, next_zone, next_time = fetch_terror_zone()
    if not current_zone and not next_zone:
        logging.info("未抓取到恐怖地带信息，跳过推送")
        return None

    msg = ""
    if current_zone:
        msg += f"⏰ 当前恐怖地带: {current_zone}\n时间: {current_time}\n"
    if next_zone:
        msg += f"➡️ 下一个恐怖地带: {next_zone}\n时间: {next_time}\n"
    return msg

def send_wecom(msg):
    if not msg:
        logging.info("消息为空，不发送")
        return
    data = {
        "msgtype": "text",
        "text": {"content": msg}
    }
    try:
        res = requests.post(WEBHOOK_URL, json=data)
        logging.info(f"已发送消息到 WeCom, response: {res.json()}")
    except Exception as e:
        logging.error(f"发送失败: {e}")

def scheduled_task():
    logging.info("Scheduled task triggered")
    msg = build_message()
    send_wecom(msg)
    logging.info("Scheduled task completed")

# -----------------------
# APScheduler 定时任务: 每小时执行一次
scheduler.add_job(scheduled_task, 'interval', hours=1)
scheduler.start()

# -----------------------
# Flask webservice
@app.route("/")
def index():
    return "D2R Terror Zone Tracker running"

# -----------------------
if __name__ == "__main__":
    scheduled_task()
    # 启动 Flask
    app.run(host="0.0.0.0", port=10000)
