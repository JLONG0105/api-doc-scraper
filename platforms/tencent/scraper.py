# -*- coding: utf-8 -*-
"""
腾讯营销开放平台 (developers.e.qq.com) API文档 - 应答参数爬取脚本

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


async def scrape_api(url, wait_ms=10000):
    """爬取API文档的应答参数数据（腾讯营销开放平台版）"""
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
                    // 跳过表头行
                    if (row.closest('thead')) continue;

                    const cells = row.querySelectorAll('td');
                    if (cells.length < 3) continue;

                    // ---- 层级: 腾讯营销用 class + 图标 标识 ----
                    // 无 class = 顶层字段
                    // dynamic-generate-tr isShown = 一级子字段
                    // hidd isShown = 二级子字段
                    // 但如果字段有 mkt-icon-folded 图标，说明它有子字段，需要特殊处理
                    let level = 0;
                    const className = row.className || '';
                    if (className.includes('dynamic-generate-tr')) {
                        level = 1;
                    } else if (className.includes('hidd')) {
                        level = 2;
                    }

                    // ---- 字段名: 第一个cell ----
                    const field = cells[0].textContent.trim();
                    // 去掉末尾的 * （必填标记）
                    const field_clean = field.replace(/\\*$/, '').trim();

                    // ---- 类型(第2列)、描述(第3列) ----
                    const type_ = cells[1] ? cells[1].textContent.trim() : '';
                    const desc = cells[2] ? cells[2].textContent.trim() : '';

                    // ---- 检查是否有子字段（通过图标判断） ----
                    const icon = cells[0].querySelector('i.icon');
                    const hasChildren = icon && icon.className.includes('mkt-icon-folded');

                    tableData.push({level, field: field_clean, type: type_, desc, hasChildren});
                }

                results.push({index: i, rowCount: rows.length, data: tableData});
            }

            return results;
        }''')

        await browser.close()
        return all_tables


def find_response_table(tables):
    """定位应答参数表格：优先找含 list/page_info 的表格"""
    for t in tables:
        fields = [r['field'] for r in t['data']]
        if 'list' in fields or 'page_info' in fields:
            return t
    # 找不到则返回数据行最多的表格
    print("警告: 未找到标准应答表格(含list/page_info)，使用行数最多的表格")
    return max(tables, key=lambda t: len(t['data']))


def build_rows(table_data):
    """用栈构建父参数路径，生成4列结果行

    腾讯营销的层级规则：
    - 无 class = 顶层字段（level 0）
    - dynamic-generate-tr isShown = 一级子字段（level 1）
    - hidd isShown = 二级子字段（level 2）
    - 但如果字段有 mkt-icon-folded 图标，说明它有子字段，后续字段应该挂到它下面
    - 特殊情况：如果当前字段是叶子节点（无子字段），且栈顶元素有子字段，则当前字段应该挂到栈顶元素下
    """
    result_rows = []
    path_stack = []

    for item in table_data:
        level = item['level']
        field = item['field']
        has_children = item.get('hasChildren', False)

        if field == '名称' or not field:
            continue

        # 特殊处理：如果当前字段是叶子节点，且栈顶元素有子字段，则当前字段应该挂到栈顶元素下
        # 例如：effect_funds（有子字段）→ effect_date（叶子节点，应该挂到 effect_funds 下）
        if not has_children and path_stack and path_stack[-1][0] == level:
            # 栈顶元素层级 == 当前层级，说明当前字段是栈顶元素的子字段
            # 不弹出栈顶元素
            pass
        else:
            # 弹出所有层级 >= 当前层级的元素
            while path_stack and path_stack[-1][0] >= level:
                path_stack.pop()

        # 父参数: 用 - 连接路径栈
        parent = '-'.join([it[1] for it in path_stack]) if path_stack else ''

        result_rows.append({
            '父参数': clean(parent),
            '子参数': clean(field),
            '类型': clean(item['type']),
            '描述': clean(item['desc']),
        })

        # 如果当前字段有子字段，压入栈；否则不压栈（叶子节点）
        if has_children:
            path_stack.append((level, field))

    return result_rows


def main():
    parser = argparse.ArgumentParser(description='爬取腾讯营销开放平台API文档的应答参数')
    parser.add_argument('--url', required=True, help='接口文档URL')
    parser.add_argument('--name', required=True, help='接口名称（用于生成文件名）')
    parser.add_argument('--output', default='.', help='输出目录（默认当前目录）')
    parser.add_argument('--wait', type=int, default=10000, help='页面加载后等待JS渲染的毫秒数（默认10000）')
    args = parser.parse_args()

    output_file = os.path.join(args.output, f"响应参数_腾讯营销_{args.name}接口数据.xlsx")

    tables = asyncio.run(scrape_api(args.url, args.wait))
    print(f"\n共发现 {len(tables)} 个表格")

    if not tables:
        print("错误: 未发现任何表格，请检查URL或网络")
        return

    response_table = find_response_table(tables)
    print(f"使用表格 index={response_table['index']}, 数据行={len(response_table['data'])}")

    result_rows = build_rows(response_table['data'])
    df = pd.DataFrame(result_rows, columns=['父参数', '子参数', '类型', '描述'])

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
