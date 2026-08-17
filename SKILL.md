---
name: api-doc-scraper
description: 爬取各广告平台 API 文档的响应参数，生成结构化 Excel。支持巨量引擎、小红书开放平台、磁力引擎等平台。
---

# API 文档爬取 Skill

## 功能

从各广告平台的 API 开放文档中爬取"响应参数"（或"应答参数"、"返回参数"）block 下的参数数据，提取所有嵌套子参数，生成包含"父参数"、"子参数"、"类型"、"说明/描述"、"备注"等列的 Excel 文件。

## 支持的平台

| 平台 | 域名 | 输出列 | 特点 |
|------|------|--------|------|
| 巨量引擎 | open.oceanengine.com | 父参数、子参数、类型、描述 (4列) | 支持 table 和 section 两种布局 |
| 小红书开放平台 | ad-market.xiaohongshu.com | 父参数、子参数、类型、说明、备注 (5列) | 链式多表格结构，支持"指标分类"列 |
| 磁力引擎 | developers.e.kuaishou.com | 父参数、子参数、类型、示例、描述、备注 (6列) | ant-table-row-level-N 层级，需排除 field-add/field-adjust 标识 |

## 使用方法

### 方式1：直接调用（推荐）

```
请爬取[平台名]的[接口名]API文档：
- URL: [文档链接]
- 输出文件名: 响应参数_[平台名]_[接口名]接口数据.xlsx
- 输出目录: [目标目录]
```

Claude Code 会自动：
1. 识别平台
2. 加载对应平台的爬取脚本
3. 执行爬取并保存 Excel

### 方式2：手动运行脚本

```bash
# 巨量引擎
python platforms/oceanengine/scraper.py --url "https://..." --name "接口名" --output "./output"

# 小红书开放平台
python platforms/xiaohongshu/scraper.py --url "https://..." --name "接口名" --output "./output"
```

## 平台特性说明

### 巨量引擎

- **两种布局**：标准 `<table>` 和 `<section class="row body">` 模拟表格
- **字段名提取**：优先取裸文本节点，排除 `qz-tag-*` 标注 span 和 `new`/`废弃` 等标记词
- **层级标识**：`data-level` 属性或 `qz-table-level` class
- **应答过滤**：section 布局时只提取"应答/应答参数/应答字段"标题之后的行

### 小红书开放平台

- **链式多表格**：返回参数由多个并列表格组成，每个表格前有标题（`<P>`/`<H2>`/`<H3>`/`<H4>`/`<H5>`）表示父字段
- **标题纠错**：文档标题可能写错（如 `trade_amount_agg_list` 的子表格前标题误写为 `wallet_trade_agg_list`），自动检测并修正
- **指标分类**：部分接口有"指标分类"列，自动并入备注列（格式：`[指标分类] 备注`）
- **停止条件**：遇到 `示例：`/`请求示例`/`响应示例` 标题或 `PRE` 代码块时停止

### 磁力引擎

- **层级标识**：`ant-table-row-level-{n}` class
- **字段名提取**：从 span 中提取，需排除 `ant-table-row-indent`（缩进）、`field-add`（新增）、`field-adjust`（调试）等标识 span
- **标识词**："新"、"调" 等单字标识需排除
- **表格列**：字段 | 类型 | 示例 | 描述 | 备注 (6列)

## 常见问题

| 问题 | 原因 | 解决方法 |
|------|------|----------|
| 字段名提取为"废弃"/"new" | 标注 span 被误提取 | 优先取裸文本节点；排除标记词 |
| 层级关系错误 | data-level 提取失败或文档标题写错 | 检查 row 的 class 属性；自动检测标题纠错 |
| 页面加载超时 | networkidle 等待过久 | 改用 domcontentloaded |
| 文件被占用 | Excel 文件打开 | 自动改用带时间戳的备用文件名 |
| 请求参数混入 | section 布局合并了请求/响应参数 | 只提取"应答"标题之后的行 |

## 技术方案

- **工具**: Playwright (Python)
- **浏览器**: Chromium (headless模式)
- **页面加载策略**: `domcontentloaded` (避免networkidle超时)
- **等待时间**: 8-10秒 (确保JavaScript渲染完成)
- **反爬规避**: 真实User-Agent、1920x1080视口

## 输出格式

所有平台统一输出 Excel 文件，列名根据平台略有不同：

- **巨量引擎**: 父参数、子参数、类型、描述
- **小红书开放平台**: 父参数、子参数、类型、说明、备注
- **磁力引擎**: 父参数、子参数、类型、示例、描述、备注

父参数使用 `-` 连接完整路径，例如：`data-list-advertiser_id`

## 扩展新平台

1. 在 `platforms/` 下创建新平台目录
2. 编写 `config.yaml`（平台配置）和 `scraper.py`（爬取逻辑）
3. 在 `SKILL.md` 中添加平台说明
4. 提交 PR 或推送到你的仓库

## 示例

参见 `examples/` 目录下的爬取指南和示例 Excel 文件。
