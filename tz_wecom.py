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
    import time
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://d2emu.com/tz-china", wait_until="networkidle")

        # 等待 tz-data 表格加载
        try:
            page.wait_for_selector("table.tz-data", timeout=10000)
        except Exception as e:
            logging.error(f"等待表格超时: {e}")
            browser.close()
            return None, None

        # 截个 HTML 片段用于调试
        html_content = page.content()
        logging.info("页面 HTML 片段: " + html_content[:500])

        # 提取表格数据
        rows = page.query_selector_all("table.tz-data tr")
        data = []
        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) >= 2:
                time_text = cells[0].inner_text().strip()
                danger_text = cells[1].inner_text().strip()
                data.append({"time": time_text, "danger": danger_text})

        logging.info(f"提取到的行: {data}")

        browser.close()

    # 提取当前和下一个恐怖地带
    current_info, next_info = None, None
    for row in data:
        if "当前恐怖地带" in row["time"]:
            current_info = row
        elif "下一个恐怖地带" in row["time"]:
            next_info = row

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
