# API 文档爬取工具

跨平台 API 开放文档响应参数爬取工具，支持巨量引擎、小红书开放平台、磁力引擎等广告平台。

## 特性

- ✅ **多平台支持**：巨量引擎、小红书开放平台、磁力引擎
- ✅ **自动层级构建**：父参数用 `-` 连接完整路径
- ✅ **智能字段提取**：自动排除"废弃"/"new"等标记词
- ✅ **布局自适应**：支持 table、section、链式多表格等多种布局
- ✅ **文档纠错**：自动检测并修正文档标题写错的情况
- ✅ **Claude Code Skill**：可作为 Skill 被 Claude Code 直接调用

## 快速开始

### 安装依赖

```bash
pip install playwright pandas openpyxl
playwright install chromium
```

### 使用方式

#### 方式1：作为 Claude Code Skill（推荐）

1. 将本仓库克隆到本地
2. 在 Claude Code 中，将 `SKILL.md` 所在目录添加到 Skill 搜索路径
3. 对 Claude 说："请爬取巨量引擎的查询账户日流水接口文档，URL是..."

#### 方式2：命令行直接运行

```bash
# 巨量引擎
python platforms/oceanengine/scraper.py \
  --url "https://open.oceanengine.com/labels/7/docs/1696710526682112" \
  --name "查询账户日流水" \
  --output "./output"

# 小红书开放平台
python platforms/xiaohongshu/scraper.py \
  --url "https://ad-market.xiaohongshu.com/docs-center?..." \
  --name "资金流水查询" \
  --output "./output"
```

## 项目结构

```
api-doc-scraper/
├── SKILL.md                    # Claude Code Skill 主文档
├── README.md                   # 本文件
├── platforms/                  # 平台特定爬取脚本
│   ├── oceanengine/
│   │   ├── config.yaml         # 平台配置
│   │   └── scraper.py          # 爬取逻辑
│   ├── xiaohongshu/
│   │   ├── config.yaml
│   │   └── scraper.py
│   └── kuaishou/
│       ├── config.yaml
│       └── scraper.py
├── core/                       # 通用框架
│   ├── base_scraper.py         # 基础爬取类
│   └── utils.py                # 工具函数
└── examples/                   # 示例和文档
    └── 爬取指南.md              # 详细爬取经验文档
```

## 平台支持

| 平台 | 状态 | 输出列 | 特殊处理 |
|------|------|--------|----------|
| 巨量引擎 | ✅ | 父参数、子参数、类型、描述 | 支持 table/section 两种布局 |
| 小红书开放平台 | ✅ | 父参数、子参数、类型、说明、备注 | 链式多表格、指标分类列 |
| 磁力引擎 | 🚧 | 父参数、子参数、类型、示例、描述、备注 | ant-table-row-level-N 层级 |

## 贡献

欢迎提交 Issue 和 PR！如果要添加新平台支持，请：

1. 在 `platforms/` 下创建新平台目录
2. 实现 `scraper.py`（继承 `core/base_scraper.py`）
3. 编写 `config.yaml`（平台配置）
4. 更新 `SKILL.md` 和 `README.md`
5. 提交 PR

## License

MIT License - 详见 [LICENSE](LICENSE) 文件

## 免责声明

使用本工具前，请仔细阅读 [免责声明](DISCLAIMER.md)。本工具仅供学习和研究目的，请遵守目标网站的 robots.txt 和使用条款。

## 作者

[@JLONG0105](https://github.com/JLONG0105)

---

**注意**：本工具仅用于学习和研究目的，请遵守各平台的 robots.txt 和使用条款。
