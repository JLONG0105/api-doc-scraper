# -*- coding: utf-8 -*-
"""基础爬取类"""
from playwright.async_api import async_playwright


class BaseScraper:
    """API文档爬取基类"""

    def __init__(self, url, api_name, output_dir, wait_ms=8000):
        self.url = url
        self.api_name = api_name
        self.output_dir = output_dir
        self.wait_ms = wait_ms

    async def fetch_page(self, url):
        """获取页面内容（Playwright）"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
            )
            page = await context.new_page()
            print("Visiting page...")

            # 使用 domcontentloaded 避免 networkidle 超时
            response = await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            print(f"Page loaded, status: {response.status}")

            # 等待JS渲染完成
            await page.wait_for_timeout(self.wait_ms)

            yield page

            await browser.close()

    async def scrape(self):
        """爬取数据（子类实现）"""
        raise NotImplementedError

    def build_rows(self, raw_data):
        """构建结果行（子类实现）"""
        raise NotImplementedError
