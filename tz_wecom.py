import logging
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# WeCom 配置
WECHAT_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b0bcfe46-3aa1-4071-afd5-da63be5a8644"

app = Flask(__name__)
scheduler = BackgroundScheduler()

logging.basicConfig(level=logging.INFO)


def to_beijing_time(timestr: str):
    """将网页时间字符串转为北京时间 (yyyy/MM/dd HH:mm:ss)"""
    try:
        # 页面时间格式示例: 2025/9/14 13:00:00 (UTC)
        dt = datetime.strptime(timestr, "%Y/%m/%d %H:%M:%S")
        # 转换为北京时间 (UTC+8)
        bj_dt = dt + timedelta(hours=8)
        return bj_dt.strftime("%Y/%m/%d %H:%M:%S")
    except Exception:
        return timestr


def fetch_terror_zone():
    logging.info("开始抓取恐怖地带信息...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://d2emu.com/tz-china", timeout=60000)

            # 等待 header 出现
            page.wait_for_selector("header", timeout=30000)
            content = page.content()
            browser.close()

        soup = BeautifulSoup(content, "html.parser")

        # 当前 & 下一个恐怖地带
        current_zone = soup.select_one("#a2x")
        next_zone = soup.select_one("#x2a")

        current_zone_text = current_zone.get_text(strip=True) if current_zone else None
        next_zone_text = next_zone.get_text(strip=True) if next_zone else None

        # 时间
        current_time = soup.select_one("#current-time")
        next_time = soup.select_one("#next-time")

        current_time_text = to_beijing_time(current_time.get_text(strip=True)) if current_time else None
        next_time_text = to_beijing_time(next_time.get_text(strip=True)) if next_time else None

        logging.info(f"抓取到的当前信息: {current_zone_text} {current_time_text}")
        logging.info(f"抓取到的下一个信息: {next_zone_text} {next_time_text}")

        return current_zone_text, current_time_text, next_zone_text, next_time_text

    except Exception as e:
        logging.warning(f"抓取失败: {e}")
        return None, None, None, None


def send_wecom_message(text: str):
    headers = {"Content-Type": "application/json"}
    payload = {"msgtype": "text", "text": {"content": text}}
    response = requests.post(WECHAT_WEBHOOK, headers=headers, json=payload)
    logging.info(f"Sent message to WeCom, response: {response.json()}")


def scheduled_task():
    logging.info("Scheduled task triggered")
    current_zone, current_time, next_zone, next_time = fetch_terror_zone()

    # 即使抓取为空，也推送（便于测试）
    message = (
        f"当前恐怖地带: {current_zone or '未获取'} ({current_time or '未知'})\n"
        f"下一个恐怖地带: {next_zone or '未获取'} ({next_time or '未知'})"
    )

    send_wecom_message(message)
    logging.info("Scheduled task completed")


# 定时任务：每 5 分钟执行一次（便于测试）
scheduler.add_job(scheduled_task, "interval", minutes=1)
scheduler.start()

@app.route("/")
def index():
    return "D2R Terror Zone WeCom Bot is running!"

if __name__ == "__main__":
    logging.info("Starting Flask app with scheduler...")
    scheduled_task()  # 启动时立即运行一次，方便测试
    app.run(host="0.0.0.0", port=10000)
