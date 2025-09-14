import logging
import requests
from datetime import datetime, timedelta
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from playwright.sync_api import sync_playwright

# ---------------- 配置 ----------------
FETCH_URL = "https://d2emu.com/tz-china"
WECHAT_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b0bcfe46-3aa1-4071-afd5-da63be5a8644"
TIMEZONE_OFFSET = 8  # 北京时间
TEST_MODE = True  # True 表示测试推送

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')

app = Flask(__name__)

# ---------------- 抓取数据 ----------------
def fetch_data():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(FETCH_URL, wait_until="networkidle")

            # 模拟点击切换到中文简体
            try:
                lang_button = page.locator("text=中文简体")
                if lang_button.count() > 0:
                    lang_button.click()
                    page.wait_for_timeout(2000)  # 等待语言切换
            except Exception:
                logging.info("未找到语言切换按钮或不需要切换")

            # 等待 div 渲染
            page.wait_for_selector("#a2x", timeout=15000)
            page.wait_for_selector("#x2a", timeout=15000)

            current_info = page.locator("#a2x").inner_text().strip()
            next_info = page.locator("#x2a").inner_text().strip()

            logging.info(f"抓取到的当前信息:\n{current_info}")
            logging.info(f"抓取到的下一个信息:\n{next_info}")

            browser.close()
            return current_info, next_info
    except Exception as e:
        logging.warning(f"抓取失败: {e}")
        return None, None

# ---------------- 构建消息 ----------------
def build_message(current, next_info):
    if not current:
        current = "未找到当前恐怖地带信息"
    if not next_info:
        next_info = "未找到下一个恐怖地带信息"

    now_utc = datetime.utcnow()
    beijing_time = now_utc + timedelta(hours=TIMEZONE_OFFSET)
    time_str = beijing_time.strftime("%Y-%m-%d %H:%M:%S")

    message = (
        f"🕒 北京时间: {time_str}\n"
        f"⚠️ 当前恐怖地带: {current}\n"
        f"⚠️ 下一个恐怖地带: {next_info}"
    )
    logging.info(f"Built message: {message}")
    return message

# ---------------- 推送消息 ----------------
def send_wecom_message(msg):
    data = {
        "msgtype": "text",
        "text": {
            "content": msg
        }
    }
    try:
        resp = requests.post(WECHAT_WEBHOOK, json=data)
        logging.info(f"Sent message to WeCom, response: {resp.json()}")
    except Exception as e:
        logging.error(f"Failed to send message: {e}")

# ---------------- 定时任务 ----------------
def scheduled_task():
    logging.info("Scheduled task triggered")
    current, next_info = fetch_data()

    if not current and not next_info:
        if TEST_MODE:
            msg = "🔧 测试推送: 暂未抓取到恐怖地带信息"
            send_wecom_message(msg)
            logging.info("测试模式下发送空信息推送")
        else:
            logging.info("未抓取到有效信息，跳过推送")
        return

    msg = build_message(current, next_info)
    send_wecom_message(msg)
    logging.info("Scheduled task completed")

# ---------------- Flask 健康检查 ----------------
@app.route("/")
def index():
    return "OK"

# ---------------- 启动 ----------------
if __name__ == "__main__":
    # APScheduler 后台定时任务，每小时抓取一次
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_task, 'interval', hours=1, next_run_time=datetime.now())
    scheduler.start()
    logging.info("Starting Flask app with scheduler...")

    # Flask 绑定端口，Render Web Service 检测用
    app.run(host="0.0.0.0", port=10000)
