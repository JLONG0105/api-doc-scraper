# 快速上手指南

本指南帮助你在**新电脑**上快速部署和使用 API 文档爬取工具。

## 📋 前置要求

- Python 3.9+
- Git
- Claude Code（可选，用于 AI 辅助爬取）

## 🚀 5分钟快速部署

### 步骤1：克隆仓库

```bash
git clone https://github.com/JLONG0105/api-doc-scraper.git
cd api-doc-scraper
```

### 步骤2：安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 步骤3：验证安装

```bash
# 测试巨量引擎爬取
python platforms/oceanengine/scraper.py \
  --url "https://open.oceanengine.com/labels/7/docs/1696710526682112" \
  --name "查询账户日流水" \
  --output "./test_output"

# 如果成功，会在 test_output/ 目录下生成 Excel 文件
```

✅ 如果看到 `文件已保存: ...` 说明安装成功！

## 💻 跨电脑使用场景

### 场景1：换新电脑

```bash
# 1. 克隆仓库
git clone https://github.com/JLONG0105/api-doc-scraper.git
cd api-doc-scraper

# 2. 安装依赖
pip install -r requirements.txt
playwright install chromium

# 3. 开始使用（无需任何配置）
python platforms/oceanengine/scraper.py --url "..." --name "..." --output "./output"
```

### 场景2：多人协作

```bash
# 同事A：添加新平台支持
git checkout -b feature/add-tencent-ads
# ... 编写代码 ...
git add .
git commit -m "feat: 添加腾讯广告平台支持"
git push origin feature/add-tencent-ads
# 在 GitHub 上创建 PR

# 同事B：拉取最新代码
git pull origin main
```

### 场景3：Claude Code 中使用

#### 方法1：本地 Skill（推荐）

1. 克隆仓库到本地
2. 在 Claude Code 中，告诉它：
   ```
   请读取 C:\path\to\api-doc-scraper\SKILL.md，然后爬取巨量引擎的XX接口
   ```

#### 方法2：远程 Skill（无需克隆）

直接在 Claude Code 中说：
```
请读取 https://raw.githubusercontent.com/JLONG0105/api-doc-scraper/main/SKILL.md，
然后爬取巨量引擎的XX接口
```

## 📖 详细使用说明

### 巨量引擎

```bash
python platforms/oceanengine/scraper.py \
  --url "https://open.oceanengine.com/labels/7/docs/1696710526682112" \
  --name "查询账户日流水" \
  --output "./output"
```

**参数说明**：
- `--url`：接口文档 URL（必填）
- `--name`：接口名称，用于生成文件名（必填）
- `--output`：输出目录（默认当前目录）
- `--wait`：页面加载后等待 JS 渲染的毫秒数（默认 8000）

**输出**：`响应参数_巨量引擎_查询账户日流水接口数据.xlsx`（4列：父参数、子参数、类型、描述）

### 小红书开放平台

```bash
python platforms/xiaohongshu/scraper.py \
  --url "https://ad-market.xiaohongshu.com/docs-center?..." \
  --name "资金流水查询" \
  --output "./output"
```

**输出**：`响应参数_小红书开放平台_资金流水查询接口数据.xlsx`（5列：父参数、子参数、类型、说明、备注）

**特殊处理**：
- 自动识别"指标分类"列并并入备注列
- 自动检测并修正文档标题写错的情况

### 磁力引擎

```bash
python platforms/kuaishou/scraper.py \
  --url "https://developers.e.kuaishou.com/docs/..." \
  --name "查询账户余额" \
  --output "./output"
```

**输出**：`响应参数_磁力引擎_查询账户余额接口数据.xlsx`（6列：父参数、子参数、类型、示例、描述、备注）

### 腾讯营销开放平台

```bash
python platforms/tencent/scraper.py \
  --url "https://developers.e.qq.com/v3.0/docs/api/daily_reports/get" \
  --name "获取日报表" \
  --output "./output"
```

**输出**：`响应参数_腾讯营销_获取日报表接口数据.xlsx`（4列：父参数、子参数、类型、描述）

**特殊处理**：
- 通过 class + 图标判断层级（`mkt-icon-folded` = 有子字段）
- 自动去除字段名末尾的 `*` 必填标记

## 🔧 常见问题

### Q1: 爬取失败，提示"未找到返回参数标题"

**原因**：页面结构与预期不符

**解决方法**：
1. 检查 URL 是否正确
2. 增加等待时间：`--wait 12000`
3. 查看页面源代码，确认"返回参数"标题的标签类型（P/H2/H3/H4/H5）

### Q2: 字段名提取错误（如提取为"废弃"、"new"）

**原因**：标注 span 被误提取

**解决方法**：已在脚本中自动处理，如果仍有问题，请提交 Issue

### Q3: 层级关系错误

**原因**：`data-level` 提取失败或文档标题写错

**解决方法**：
- 巨量引擎/磁力引擎：检查 row 的 class 属性
- 小红书：脚本已自动检测并修正，如果仍有问题，请提交 Issue

### Q4: 文件被占用

**原因**：Excel 文件已打开

**解决方法**：脚本会自动改用带时间戳的备用文件名，无需手动处理

## 🔄 更新和维护

### 拉取最新代码

```bash
cd api-doc-scraper
git pull origin main
```

### 添加新平台

1. 在 `platforms/` 下创建新平台目录
2. 参考现有平台实现 `scraper.py` 和 `config.yaml`
3. 更新 `SKILL.md` 和 `README.md`
4. 提交 PR

### 提交 Issue

如果遇到问题，请在 GitHub 上提交 Issue：
https://github.com/JLONG0105/api-doc-scraper/issues

**Issue 模板**：
```
平台：巨量引擎/小红书/磁力引擎
URL：https://...
错误信息：...
预期结果：...
实际结果：...
```

## 📚 更多资源

- **SKILL.md**：Claude Code Skill 文档
- **examples/爬取指南.md**：详细的爬取经验和坑点总结
- **DISCLAIMER.md**：免责声明

## 🆘 获取帮助

- **GitHub Issues**: https://github.com/JLONG0105/api-doc-scraper/issues
- **Email**: [你的邮箱]

---

**最后更新**: 2026-08-18
