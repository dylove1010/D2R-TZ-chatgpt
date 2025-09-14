from playwright.sync_api import sync_playwright
import logging

FETCH_URL = "https://d2emu.com/tz-china"

def fetch_data_chinese():
    logging.info("开始抓取恐怖地带信息...")
    current_text = None
    next_text = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(FETCH_URL, wait_until="networkidle")

        # 延长等待，确保动态内容加载
        page.wait_for_timeout(8000)  # 等 8 秒

        # 打印页面 HTML 前 2000 字符，方便调试
        body_html = page.content()
        logging.info(f"页面 HTML 前2000字符:\n{body_html[:2000]}")

        # 尝试抓取当前和下一个恐怖地带
        try:
            current_el = page.query_selector("#a2x")
            next_el = page.query_selector("#x2a")
            current_text = current_el.inner_text().strip() if current_el else None
            next_text = next_el.inner_text().strip() if next_el else None
            logging.info(f"抓取到的当前信息: {current_text}")
            logging.info(f"抓取到的下一个信息: {next_text}")
        except Exception as e:
            logging.warning(f"抓取失败: {e}")

        browser.close()

    return current_text, next_text

# 测试调用
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    current, next_info = fetch_data_chinese()
    print("当前恐怖地带:", current)
    print("下一个恐怖地带:", next_info)
