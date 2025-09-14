import logging
import requests
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 固定 WebHook URL
WECHAT_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b0bcfe46-3aa1-4071-afd5-da63be5a8644"

# Flask 应用
app = Flask(__name__)

async def fetch_terror_zone():
    """使用 Playwright 抓取恐怖地带信息"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://d2emu.com/tz-china", timeout=60000)

            # 等待 header 出现
            await page.wait_for_selector("header", timeout=30000)
            content = await page.content()
            await browser.close()

        # 解析 HTML
        soup = BeautifulSoup(content, "html.parser")

        # 提取当前/下一个恐怖地带
        current_zone = soup.select_one("#a2x")
        next_zone = soup.select_one("#x2a")

        current_zone_text = current_zone.get_text(separator="\n", strip=True) if current_zone else None
        next_zone_text = next_zone.get_text(separator="\n", strip=True) if next_zone else None

        # 提取时间并转为北京时间
        def convert_time(div_id):
            node = soup.select_one(div_id)
            if not node:
                return None
            try:
                utc_time = datetime.strptime(node.text.strip(), "%Y/%m/%d %H:%M:%S")
                utc_time = utc_time.replace(tzinfo=timezone.utc)
                beijing_time = utc_time.astimezone(timezone(timedelta(hours=8)))
                return beijing_time.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                logging.warning("时间解析失败: %s", e)
                return node.text.strip()

        current_time = convert_time("#current-time")
        next_time = convert_time("#next-time")

        logging.info("抓取到的当前信息: %s %s", current_zone_text, current_time)
        logging.info("抓取到的下一个信息: %s %s", next_zone_text, next_time)

        return current_zone_text, current_time, next_zone_text, next_time

    except Exception as e:
        logging.error("抓取失败: %s", e)
        return None, None, None, None


def send_to_wecom(message: str):
    """推送到企业微信群"""
    payload = {
        "msgtype": "text",
        "text": {"content": message}
    }
    try:
        resp = requests.post(WECHAT_WEBHOOK, json=payload)
        logging.info("Sent message to WeCom, response: %s", resp.json())
    except Exception as e:
        logging.error("推送失败: %s", e)


def build_message(current_zone, current_time, next_zone, next_time):
    """构造消息"""
    if not current_zone and not next_zone:
        return "⚠️ 暂未找到恐怖地带信息，请检查页面解析。"

    msg = []
    msg.append("⏰ 当前恐怖地带:")
    msg.append(f"{current_time or ''} {current_zone or ''}")

    msg.append("\n➡️ 下一个恐怖地带:")
    msg.append(f"{next_time or ''} {next_zone or ''}")

    return "\n".join(msg)


def scheduled_task():
    """定时任务"""
    logging.info("Scheduled task triggered")
    current_zone, current_time, next_zone, next_time = asyncio.run(fetch_terror_zone())
    message = build_message(current_zone, current_time, next_zone, next_time)
    send_to_wecom(message)
    logging.info("Scheduled task completed")


@app.route("/")
def index():
    return "D2R Terror Zone Tracker WeCom Bot is running!"


if __name__ == "__main__":
    # 启动时立即推送一次
    scheduled_task()

    # 定时任务每小时执行一次
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_task, "interval", hours=1)
    scheduler.start()

    logging.info("Starting Flask app with scheduler...")
    app.run(host="0.0.0.0", port=10000)
