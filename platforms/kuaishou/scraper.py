# -*- coding: utf-8 -*-
"""
磁力引擎 (developers.e.kuaishou.com) API文档 - 应答参数爬取脚本

使用方法:
    python scraper.py --url "https://..." --name "接口名" --output "./output"
"""
import asyncio
import sys
import os
import argparse

# 添加父目录到路径，以便导入 core 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.utils import setup_console_encoding, clean, save_excel
from playwright.async_api import async_playwright
import pandas as pd

setup_console_encoding()


async def scrape_api(url, wait_ms=8000):
    """爬取API文档的应答参数数据（磁力引擎版）"""
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
        await page.wait_for_timeout(wait_ms)

        # 提取所有表格数据
        all_tables = await page.evaluate('''() => {
            const results = [];
            const tables = document.querySelectorAll('table');

            for (let i = 0; i < tables.length; i++) {
                const table = tables[i];
                const rows = table.querySelectorAll('tr');
                const tableData = [];

                for (const row of rows) {
                    // 跳过表头行和测量行
                    if (row.closest('thead')) continue;
                    if (row.classList.contains('ant-table-measure-row')) continue;

                    const cells = row.querySelectorAll('td');
                    if (cells.length < 5) continue;  // 磁力引擎是6列（字段、类型、示例、描述、备注）

                    // ---- 层级: 磁力引擎用 ant-table-row-level-N class ----
                    let level = 0;
                    const className = row.className || '';
                    const levelMatch = className.match(/ant-table-row-level-(\\d+)/);
                    if (levelMatch) {
                        level = parseInt(levelMatch[1]);
                    }

                    // ---- 字段名: 第一个cell ----
                    // 磁力引擎的字段名在span中，需要排除标识span
                    const fieldCell = cells[0];
                    let field = '';

                    const allSpans = fieldCell.querySelectorAll('span');
                    for (const span of allSpans) {
                        const spanClass = span.className || '';
                        // 跳过标识标签
                        if (spanClass.includes('ant-table-row-indent') ||
                            spanClass.includes('field-add') ||
                            spanClass.includes('field-adjust') ||
                            spanClass.includes('field-')) {
                            continue;
                        }

                        const text = span.textContent.trim();
                        // 只接受长度>1的文本或英文字段名
                        if (text && (text.length > 1 || /^[a-zA-Z0-9_]+$/.test(text))) {
                            field = text;
                            break;
                        }
                    }

                    // 备用方法：取整个cell文本，去掉标识
                    if (!field) {
                        let allText = fieldCell.textContent.trim();
                        // 去掉末尾的标识文字
                        allText = allText.replace(/(新|调|调试)$/, '').trim();
                        field = allText;
                    }

                    // ---- 类型(第2列)、示例(第3列)、描述(第4列)、备注(第5列) ----
                    const type_ = cells[1] ? cells[1].textContent.trim() : '';
                    const example = cells[2] ? cells[2].textContent.trim() : '';
                    const desc = cells[3] ? cells[3].textContent.trim() : '';
                    const note = cells[4] ? cells[4].textContent.trim() : '';

                    tableData.push({level, field, type: type_, example, desc, note});
                }

                results.push({index: i, rowCount: rows.length, data: tableData});
            }

            return results;
        }''')

        await browser.close()
        return all_tables


def find_response_table(tables):
    """定位应答参数表格：优先找含 code/message/data 的表格"""
    for t in tables:
        fields = [r['field'] for r in t['data']]
        if 'code' in fields and 'message' in fields and 'data' in fields:
            return t
    # 找不到则返回数据行最多的表格
    print("警告: 未找到标准应答表格(含code/message/data)，使用行数最多的表格")
    return max(tables, key=lambda t: len(t['data']))


def build_rows(table_data):
    """用栈构建父参数路径，生成6列结果行"""
    result_rows = []
    path_stack = []

    for item in table_data:
        level = item['level']
        field = item['field']

        if field == '字段' or not field:
            continue

        # 弹出所有层级 >= 当前层级的元素
        while path_stack and path_stack[-1][0] >= level:
            path_stack.pop()

        # 父参数: 用 - 连接路径栈
        parent = '-'.join([it[1] for it in path_stack]) if path_stack else ''

        result_rows.append({
            '父参数': clean(parent),
            '子参数': clean(field),
            '类型': clean(item['type']),
            '示例': clean(item['example']),
            '描述': clean(item['desc']),
            '备注': clean(item['note']),
        })

        path_stack.append((level, field))

    return result_rows


def main():
    parser = argparse.ArgumentParser(description='爬取磁力引擎API文档的应答参数')
    parser.add_argument('--url', required=True, help='接口文档URL')
    parser.add_argument('--name', required=True, help='接口名称（用于生成文件名）')
    parser.add_argument('--output', default='.', help='输出目录（默认当前目录）')
    parser.add_argument('--wait', type=int, default=8000, help='页面加载后等待JS渲染的毫秒数（默认8000）')
    args = parser.parse_args()

    output_file = os.path.join(args.output, f"响应参数_磁力引擎_{args.name}接口数据.xlsx")

    tables = asyncio.run(scrape_api(args.url, args.wait))
    print(f"\n共发现 {len(tables)} 个表格")

    if not tables:
        print("错误: 未发现任何表格，请检查URL或网络")
        return

    response_table = find_response_table(tables)
    print(f"使用表格 index={response_table['index']}, 数据行={len(response_table['data'])}")

    result_rows = build_rows(response_table['data'])
    df = pd.DataFrame(result_rows, columns=['父参数', '子参数', '类型', '示例', '描述', '备注'])

    print(f"\n=== 爬取结果 ===")
    print(f"总行数: {len(df)}")

    # 检查单字字段（可能是标识误提取）
    if len(df) > 0:
        single_char = df[df['子参数'].str.len() == 1]['子参数'].unique()
        if len(single_char) > 0:
            print(f"警告：发现单字字段（可能是标识被误提取）: {single_char}")

    out = save_excel(df, output_file)
    print(f"\n文件已保存: {out}")
    print(f"总数据行数: {len(df)}")


if __name__ == '__main__':
    main()
