# -*- coding: utf-8 -*-
"""
巨量引擎 (open.oceanengine.com) API文档 - 应答参数爬取脚本

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
    """爬取API文档的应答参数数据（巨量引擎版）"""
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
                    if (cells.length < 3) continue;

                    // ---- 层级: 巨量引擎用 data-level 属性 ----
                    let level = 0;
                    const dataLevel = row.getAttribute('data-level');
                    if (dataLevel !== null) {
                        level = parseInt(dataLevel);
                    } else {
                        // 兜底: ant-table-row-level-N
                        const m = (row.className || '').match(/ant-table-row-level-(\\d+)/);
                        if (m) level = parseInt(m[1]);
                    }

                    // ---- 字段名: 第一个cell ----
                    // 巨量引擎的字段名常是裸文本节点，后跟 qz-tag-* 标注span(如"废弃"/"新增")
                    const fieldCell = cells[0];
                    let field = '';

                    // 辅助: 判断span是否为标注/缩进标签(需排除)
                    const isTagSpan = (sc) => {
                        return sc.includes('indent') || sc.includes('field-add') ||
                               sc.includes('field-adjust') || sc.includes('expand-icon') ||
                               sc.includes('qz-tag') || sc.includes('tag-view') ||
                               sc.includes('qz-table-level');
                    };
                    // 辅助: 清理文本(去\xa0、零宽空格、普通空格)
                    const cleanText = (s) => (s||'').replace(/[\\xa0\\u200b\\u200c\\u200d\\ufeff]/g, '').replace(/ /g, '').trim();
                    // 辅助: 判断文本是否为标记词(如 new/废弃/新增/调/调试)
                    const isMarkerText = (t) => /^(new|废弃|新增|新|调|调试)$/i.test(t);

                    // 第一步: 优先取裸文本节点(字段名通常是裸文本)
                    for (const node of fieldCell.childNodes) {
                        if (node.nodeType === Node.TEXT_NODE) {
                            const t = cleanText(node.textContent);
                            if (t && /^[a-zA-Z0-9_]+$/.test(t)) { field = t; break; }
                        }
                    }

                    // 第二步: 从span中找(排除标注span和标记词)
                    if (!field) {
                        const allSpans = fieldCell.querySelectorAll('span');
                        for (const span of allSpans) {
                            const sc = span.className || '';
                            if (isTagSpan(sc)) continue;
                            const text = cleanText(span.textContent);
                            // 跳过标记词
                            if (isMarkerText(text)) continue;
                            // 只接受纯英文字段名，避免中文标注被误取
                            if (text && /^[a-zA-Z0-9_]+$/.test(text)) {
                                field = text;
                                break;
                            }
                        }
                    }

                    // 第三步: 兜底——取整个cell文本，去掉标注文字
                    if (!field) {
                        let allText = cleanText(fieldCell.textContent);
                        // 去掉末尾的中文标注词
                        allText = allText.replace(/(废弃|新增|新|调|调试|new)$/, '').trim();
                        // 若含空格，取第一段(字段名)+忽略后续标注
                        const m = allText.match(/[a-zA-Z0-9_]+/);
                        field = m ? m[0] : allText;
                    }

                    // ---- 类型(第2列)、描述(最后1列) ----
                    const type_ = cells[1] ? cells[1].textContent.trim() : '';
                    const desc = cells[cells.length - 1].textContent.trim();

                    tableData.push({level, field, type: type_, desc});
                }

                results.push({index: i, rowCount: rows.length, data: tableData});
            }

            // ===== 分支: 页面无 <table> 时，解析 section 模拟表格布局 =====
            // 部分新版文档页用 <section class="row body" data-level="N"> 模拟表格行
            if (results.length === 0 || results.every(t => t.data.length === 0)) {
                let secRows = [...document.querySelectorAll('section.row.body[data-level]')];
                // 只保留"应答"标题之后的行，避免把请求参数/Header混进来
                let anchor = null;
                const cand = document.querySelectorAll('h1,h2,h3,h4,h5,strong,p,span,div');
                for (const el of cand) {
                    const t = (el.textContent||'').trim();
                    if (/^应答(参数|字段)?$/.test(t)) { anchor = el; break; }
                }
                if (anchor) {
                    secRows = secRows.filter(r =>
                        !!(anchor.compareDocumentPosition(r) & Node.DOCUMENT_POSITION_FOLLOWING)
                    );
                }
                if (secRows.length > 0) {
                    const tableData = [];
                    for (const row of secRows) {
                        const level = parseInt(row.getAttribute('data-level') || '0');
                        // 字段名: .col_params_name (或 .col_params 内的p)
                        const nameEl = row.querySelector('.col_params_name') ||
                                       row.querySelector('.col_params p') ||
                                       row.querySelector('.col_params');
                        const field = nameEl ? nameEl.textContent.replace(/ /g,'').trim() : '';
                        // 类型: .col_param_type
                        const typeEl = row.querySelector('.col_param_type');
                        const type_ = typeEl ? typeEl.textContent.trim() : '';
                        // 描述: .description
                        const descEl = row.querySelector('.description');
                        const desc = descEl ? descEl.textContent.trim() : '';
                        if (field) tableData.push({level, field, type: type_, desc});
                    }
                    // 作为唯一一个"表格"返回
                    return [{index: 0, rowCount: secRows.length, data: tableData, layout: 'section'}];
                }
            }

            return results;
        }''')

        await browser.close()
        return all_tables


def find_response_table(tables):
    """定位应答参数表格：优先找含 code/message/data 的表格"""
    for t in tables:
        fields = [r['field'] for r in t['data']]
        if 'code' in fields and 'data' in fields:
            return t
    # 找不到则返回数据行最多的表格
    print("警告: 未找到标准应答表格(含code/data)，使用行数最多的表格")
    return max(tables, key=lambda t: len(t['data']))


def build_rows(table_data):
    """用栈构建父参数路径，生成4列结果行"""
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
            '描述': clean(item['desc']),
        })

        path_stack.append((level, field))

    return result_rows


def main():
    parser = argparse.ArgumentParser(description='爬取巨量引擎API文档的应答参数')
    parser.add_argument('--url', required=True, help='接口文档URL')
    parser.add_argument('--name', required=True, help='接口名称（用于生成文件名）')
    parser.add_argument('--output', default='.', help='输出目录（默认当前目录）')
    parser.add_argument('--wait', type=int, default=8000, help='页面加载后等待JS渲染的毫秒数（默认8000）')
    args = parser.parse_args()

    output_file = os.path.join(args.output, f"响应参数_巨量引擎_{args.name}接口数据.xlsx")

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
