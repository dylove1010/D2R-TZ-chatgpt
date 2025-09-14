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
    """抓取当前和下一个恐怖地带信息（时间 + 地点/免疫）"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(FETCH_URL, wait_until="networkidle")
        page.wait_for_timeout(5000)  # 等待 JS 渲染

        current_info, next_info = None, None

        try:
            # 当前恐怖地带
            current_block = page.locator("text=Current Terror Zone:").first
            current_info = current_block.locator("xpath=following-sibling::*").all_inner_texts()
            current_info = "\n".join([line.strip() for line in current_info if line.strip()])

            # 下一个恐怖地带
            next_block = page.locator("text=Next Terror Zone:").first
            next_info = next_block.locator("xpath=following-sibling::*").all_inner_texts()
            next_info = "\n".join([line.strip() for line in next_info if line.strip()])

        except Exception as e:
            logging.error(f"解析页面失败: {e}")
            browser.close()
            return None, None

        browser.close()

    logging.info(f"抓取到的当前信息:\n{current_info}")
    logging.info(f"抓取到的下一个信息:\n{next_info}")
    return current_info, next_info


# -----------------------------
# 构建推送消息
# -----------------------------
def build_message():
    current, next_info = fetch_data()
    if not current or not next_info:
        return "⚠️ 暂未找到当前恐怖地带信息，请检查页面解析。"

    msg = f"⚔️ 当前恐怖地带:\n{current}\n\n⏭️ 下一个恐怖地带:\n{next_info}"
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
    # 每小时整点推送一次
    scheduler.add_job(scheduled_task, 'cron', minute=0)
    scheduler.start()
    logging.info("Scheduler started")

    # 启动时立即推送一次
    scheduled_task()

    # 保持程序运行
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Scheduler shutdown")
