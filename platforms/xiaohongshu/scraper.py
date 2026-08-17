# -*- coding: utf-8 -*-
"""
小红书开放平台 (ad-market.xiaohongshu.com) API文档 - 应答参数爬取脚本

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
    """爬取API文档的应答参数数据（小红书开放平台版）"""
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

        # 提取返回参数区域的链式表格结构
        result = await page.evaluate('''() => {
            // 找"返回参数"或"应答参数"或"响应参数"标题（支持 P/H2/H3/H4/H5 标签）
            const allTags = document.querySelectorAll('p, h2, h3, h4, h5');
            let respP = null;
            for (const p of allTags) {
                const t = p.textContent.trim();
                if (t === '返回参数' || t === '应答参数' || t === '响应参数') {
                    respP = p;
                    break;
                }
            }
            if (!respP) return {error: '未找到返回参数标题'};

            // 从返回参数开始，收集后续所有元素直到"示例"或下一个大标题
            const container = respP.closest('.html-content') || respP.parentElement;
            const children = Array.from(container.children);
            const startIdx = children.findIndex(c => c.contains(respP));

            const chain = [];  // [{type: 'title', text: '...'}, {type: 'table', rows: [...]}, ...]
            for (let i = startIdx; i < children.length; i++) {
                const c = children[i];
                const text = (c.textContent || '').trim();

                // 遇到"示例"相关标题则停止（示例：/请求示例/响应示例）
                if ((c.tagName === 'P' || c.tagName === 'H2' || c.tagName === 'H3' || c.tagName === 'H4' || c.tagName === 'H5') &&
                    (text === '示例：' || text === '请求示例' || text === '响应示例' || text.startsWith('示例'))) break;
                // 遇到PRE且之前已有表格则停止（示例代码块）
                if (c.tagName === 'PRE' && chain.some(x => x.type === 'table')) break;

                // 标题元素（P/H2/H3/H4/H5，文本长度<50，且非空）
                if ((c.tagName === 'P' || c.tagName === 'H2' || c.tagName === 'H3' || c.tagName === 'H4' || c.tagName === 'H5') && text && text.length < 50) {
                    chain.push({type: 'title', text: text});
                } else if (c.tagName === 'TABLE') {
                    // 表格元素 - 先获取表头判断列数
                    const headerCells = Array.from(c.querySelectorAll('th')).map(th => th.textContent.trim());
                    const hasCategory = headerCells.includes('指标分类');

                    const rows = [];
                    for (const tr of c.querySelectorAll('tr')) {
                        const cells = Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim());
                        if (cells.length >= 4) {
                            if (hasCategory && cells.length >= 5) {
                                // 5列：指标分类、字段、类型、说明、备注
                                rows.push({
                                    category: cells[0],
                                    field: cells[1],
                                    type: cells[2],
                                    desc: cells[3],
                                    note: cells[4]
                                });
                            } else {
                                // 4列：字段、类型、说明、备注
                                rows.push({
                                    category: '',
                                    field: cells[0],
                                    type: cells[1],
                                    desc: cells[2],
                                    note: cells[3]
                                });
                            }
                        }
                    }
                    chain.push({type: 'table', rows: rows, hasCategory: hasCategory});
                }
            }
            return {chain: chain};
        }''')

        await browser.close()
        return result


def build_rows(chain):
    """用栈构建父参数路径，生成5列结果行

    小红书的链式结构：
    - 第一个table是顶层（无标题）
    - 后续每个title+table对：title是父字段名，table是该字段的子字段
    - title对应的字段应该在**当前表格的父级表格**中找
    - 如果title在栈中找到的层级 < 当前表格的父层级，说明文档标题可能写错了，
      需要用当前表格父层级中的最后一个 struct/list 字段
    """
    result_rows = []
    # 栈元素: (字段名, 层级, 该字段所在表格的行列表)
    # 层级0=顶层表格的字段
    path_stack = []

    i = 0
    while i < len(chain):
        item = chain[i]

        if item['type'] == 'table':
            rows = item['rows']
            # 确定当前表格的父路径
            if not path_stack:
                # 第一个表格：顶层
                parent_path = ''
                current_level = 0
            else:
                # 后续表格：父路径 = 栈中所有字段名连接
                parent_path = '-'.join([f for f, _, _ in path_stack])
                current_level = len(path_stack)

            # 处理表格中的每一行
            for row in rows:
                field = row['field']
                if not field or field == '字段':
                    continue

                # 如果有指标分类列，将其并入备注列
                note = row.get('note', '')
                if row.get('category'):
                    note = f"[{row['category']}] {note}" if note else f"[{row['category']}]"

                result_rows.append({
                    '父参数': clean(parent_path),
                    '子参数': clean(field),
                    '类型': clean(row['type']),
                    '说明': clean(row['desc']),
                    '备注': clean(note),
                })

            # 如果下一个元素是title，说明某个字段有子表格
            if i + 1 < len(chain) and chain[i + 1]['type'] == 'title':
                next_title = chain[i + 1]['text']

                # 当前表格的父层级（即当前表格在栈中的深度）
                parent_level = len(path_stack) - 1 if path_stack else -1

                # 从栈顶向下找，看哪个层级的表格包含 next_title 字段
                found_level = -1
                matched_field = None
                for level in range(len(path_stack) - 1, -1, -1):
                    _, _, table_rows = path_stack[level]
                    for row in table_rows:
                        if row['field'] == next_title:
                            found_level = level
                            matched_field = row['field']
                            break
                    if found_level >= 0:
                        break

                # 如果找到了，但需要判断是否是"文档标题写错"的情况：
                # 情况1: found_level < parent_level（标题指向了祖父层级）
                # 情况2: found_level == parent_level 且 matched_field 就是当前表格的父字段本身
                #        （标题指向了父字段本身，而不是当前表格中的某个子字段）
                if found_level >= 0:
                    need_fix = False
                    if found_level < parent_level:
                        need_fix = True
                    elif found_level == parent_level and parent_level >= 0:
                        # 检查 matched_field 是否就是当前表格的父字段（栈顶元素）
                        stack_top_field = path_stack[parent_level][0]
                        if matched_field == stack_top_field:
                            need_fix = True

                    if need_fix:
                        # 在**当前表格**中找最后一个 struct/list 字段
                        # 因为当前表格的某个字段有子表格，标题写错了
                        for row in reversed(rows):
                            t = row['type'].lower()
                            if 'struct' in t or 'object' in t or 'list' in t:
                                found_level = current_level
                                matched_field = row['field']
                                break

                # 如果栈中没找到，检查当前表格
                if found_level < 0:
                    for row in rows:
                        if row['field'] == next_title:
                            found_level = current_level
                            matched_field = row['field']
                            break

                # 如果还没找到，尝试在当前表格找最后一个 struct/list 类型字段
                if found_level < 0:
                    for row in reversed(rows):
                        t = row['type'].lower()
                        if 'struct' in t or 'object' in t or 'list' in t:
                            found_level = current_level
                            matched_field = row['field']
                            break

                if found_level >= 0 and matched_field:
                    # 弹出栈中层级 > found_level 的元素
                    while path_stack and path_stack[-1][1] > found_level:
                        path_stack.pop()
                    # 如果栈顶就是 found_level，替换它；否则压入新层级
                    if path_stack and path_stack[-1][1] == found_level:
                        path_stack[-1] = (matched_field, found_level, rows)
                    else:
                        path_stack.append((matched_field, found_level, rows))

        i += 1

    return result_rows


def main():
    parser = argparse.ArgumentParser(description='爬取小红书开放平台API文档的应答参数')
    parser.add_argument('--url', required=True, help='接口文档URL')
    parser.add_argument('--name', required=True, help='接口名称（用于生成文件名）')
    parser.add_argument('--output', default='.', help='输出目录（默认当前目录）')
    parser.add_argument('--wait', type=int, default=10000, help='页面加载后等待JS渲染的毫秒数（默认10000）')
    args = parser.parse_args()

    output_file = os.path.join(args.output, f"响应参数_小红书开放平台_{args.name}接口数据.xlsx")

    result = asyncio.run(scrape_api(args.url, args.wait))

    if 'error' in result:
        print(f"错误: {result['error']}")
        return

    chain = result['chain']
    print(f"\n共发现 {len([x for x in chain if x['type'] == 'table'])} 个表格")

    result_rows = build_rows(chain)
    df = pd.DataFrame(result_rows, columns=['父参数', '子参数', '类型', '说明', '备注'])

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
