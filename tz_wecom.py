import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

logging.basicConfig(level=logging.INFO)

WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b0bcfe46-3aa1-4071-afd5-da63be5a8644"
URL = "https://d2emu.com/tz-china"

app = Flask(__name__)
scheduler = BackgroundScheduler()

def fetch_tz():
    logging.info("开始抓取恐怖地带信息...")
    try:
        res = requests.get(URL, timeout=15)
        res.raise_for_status()
    except Exception as e:
        logging.warning("抓取失败: %s", e)
        return None, None, None, None

    soup = BeautifulSoup(res.text, "html.parser")
    current_zone = soup.select_one("#a2x")
    next_zone = soup.select_one("#x2a")
    current_time_div = soup.select_one("#current-time")
    next_time_div = soup.select_one("#next-time")

    def convert_time(node):
        if not node:
            return None
        text = node.text.strip()
        for fmt in ("%Y/%m/%d %H:%M:%S", "%m/%d/%Y, %I:%M:%S %p"):
            try:
                utc_time = datetime.strptime(text, fmt)
                utc_time = utc_time.replace(tzinfo=timezone.utc)
                beijing_time = utc_time.astimezone(timezone(timedelta(hours=8)))
                return beijing_time.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        logging.warning("时间解析失败: %s", text)
        return text

    cur_time = convert_time(current_time_div)
    next_time = convert_time(next_time_div)

    cur_zone_text = current_zone.get_text(separator=" | ").strip() if current_zone else None
    next_zone_text = next_zone.get_text(separator=" | ").strip() if next_zone else None

    logging.info("抓取到的当前信息: %s %s", cur_zone_text, cur_time)
    logging.info("抓取到的下一个信息: %s %s", next_zone_text, next_time)

    return cur_zone_text, cur_time, next_zone_text, next_time

def send_wecom(cur_zone, cur_time, next_zone, next_time):
    msg = f"⏰ 当前恐怖地带: {cur_zone or '暂无信息'} {cur_time or ''}\n" \
          f"➡️ 下一个恐怖地带: {next_zone or '暂无信息'} {next_time or ''}"
    payload = {"msgtype": "text", "text": {"content": msg}}
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        logging.info("Sent message to WeCom, response: %s", r.json())
    except Exception as e:
        logging.warning("发送失败: %s", e)

def scheduled_task():
    logging.info("Scheduled task triggered")
    cur_zone, cur_time, next_zone, next_time = fetch_tz()
    # 无论是否抓到数据都推送，方便测试
    send_wecom(cur_zone, cur_time, next_zone, next_time)
    logging.info("Scheduled task completed")

scheduler.add_job(scheduled_task, 'interval', hours=1)
scheduler.start()

@app.route('/')
def index():
    return "Terror Zone service running."

@app.route('/test')
def test():
    logging.info("手动测试推送触发")
    scheduled_task()
    return "Test push triggered."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
