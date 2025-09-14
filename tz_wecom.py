import logging
import time
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from playwright.sync_api import sync_playwright

# 配置日志
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')

# 微信 Webhook
WECHAT_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b0bcfe46-3aa1-4071-afd5-da63be5a8644"

# 页面 URL
FETCH_URL = "https://d2emu.com/tz-china"

# Flask app
app = Flask(__name__)

# 测试模式
TEST_MODE = True

def fetch_data():
    """
    抓取当前和下一个恐怖地带信息
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            logging.info(f"打开页面: {FETCH_URL}")
            page.goto(FETCH_URL)
            
            # 等待页面网络空闲
            page.wait_for_load_state("networkidle")
            # 再等待 5 秒，确保 JS 渲染完成
            page.wait_for_timeout(5000)
            
            # 尝试获取当前和下一个恐怖地带
            try:
                current = page.query_selector("#a2x")
                current_text = current.inner_text().strip() if current else None
            except Exception as e:
                logging.warning(f"抓取当前信息失败: {e}")
                current_text = None

            try:
                next_zone = page.query_selector("#x2a")
                next_text = next_zone.inner_text().strip() if next_zone else None
            except Exception as e:
                logging.warning(f"抓取下一个信息失败: {e}")
                next_text = None

            logging.info(f"抓取到的当前信息: {current_text}")
            logging.info(f"抓取到的下一个信息: {next_text}")

            browser.close()
            return current_text, next_text
    except Exception as e:
        logging.error(f"抓取页面失败: {e}")
        return None, None

def build_message():
    """
    构建要推送的消息
    """
    current, next_info = fetch_data()
    
    if not current and not next_info:
        msg = "⚠️ 暂未抓取到恐怖地带信息"
    else:
        msg_lines = []
        if current:
            msg_lines.append(f"⏰ 当前恐怖地带:\n{current}")
        if next_info:
            msg_lines.append(f"➡️ 下一个恐怖地带:\n{next_info}")
        msg = "\n\n".join(msg_lines)
    logging.info(f"Built message: {msg}")
    return msg

def send_wechat_message(message):
    """
    推送到企业微信
    """
    payload = {
        "msgtype": "text",
        "text": {
            "content": message
        }
    }
    try:
        resp = requests.post(WECHAT_WEBHOOK, json=payload)
        logging.info(f"Sent message to WeCom, response: {resp.json()}")
    except Exception as e:
        logging.error(f"发送微信消息失败: {e}")

def scheduled_task():
    """
    定时任务
    """
    logging.info("Scheduled task triggered")
    msg = build_message()
    if msg or TEST_MODE:
        send_wechat_message(msg)
    logging.info("Scheduled task completed")

if __name__ == "__main__":
    # 启动调度器
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_task, "interval", hours=1, id="scheduled_task")
    scheduler.start()
    logging.info("Starting Flask app with scheduler...")

    # 启动时强制推送一次
    scheduled_task()

    # Flask webservice 保持 Render 进程存活
    app.run(host="0.0.0.0", port=10000)
