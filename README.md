# UK Academic Funding Tracker

一个用于追踪英国大学学术人员可申请资助的静态网站系统。

## 项目结构

```
FundingCall_UK/
├── README.md
├── index.html              # 主展示页面
├── css/
│   └── style.css          # 样式文件
├── js/
│   └── main.js            # 前端交互逻辑
├── data/
│   ├── funding_database.json    # 主数据库
│   └── individual_fundings/     # 单独funding数据
├── scrapers/
│   ├── ukri_scraper.py         # UKRI爬虫
│   ├── academies_scraper.py     # 国家学院爬虫
│   ├── foundations_scraper.py   # 慈善基金会爬虫
│   └── utils.py                 # 爬虫工具函数
└── requirements.txt             # Python依赖
```

## 功能特性

- 📊 **数据库系统**: JSON格式存储所有funding信息
- 🕷️ **爬虫系统**: 自动获取最新funding信息
- 🎨 **现代UI**: 响应式设计与数据仪表盘，便于快速浏览
- 🔍 **搜索过滤**: 关键字检索、来源筛选、职业阶段筛选与排序
- 🧭 **时间窗口管理**: 仅保留截止日期在当前前后三个月内且元数据完整的机会
- 📱 **移动友好**: 适配各种设备

## 资助来源

### UK Research and Innovation (UKRI)
- Arts and Humanities Research Council (AHRC)
- Biotechnology and Biological Sciences Research Council (BBSRC)
- Economic and Social Research Council (ESRC)
- Engineering and Physical Sciences Research Council (EPSRC)
- Medical Research Council (MRC)
- Natural Environment Research Council (NERC)
- Science and Technology Facilities Council (STFC)
- Innovate UK
- Research England

### National Academies
- The Royal Society
- The British Academy
- The Royal Academy of Engineering
- The Academy of Medical Sciences

### Major Charitable Foundations
- The Wellcome Trust
- The Leverhulme Trust
- Nuffield Foundation
- The Wolfson Foundation

## 使用方法

1. 运行爬虫更新数据: `python scrapers/update_all.py`
2. 自动校验会剔除缺失字段、重复及不在 ±3 个月时间窗口内的机会
3. 在浏览器中打开 `index.html`
4. 使用侧边栏搜索和过滤功能查找相关funding

## 每日自动更新

- 在服务器上执行一次更新并生成AI摘要: `python scrapers/update_all.py`
- 持续运行的自动任务（默认每24小时运行一次）: `python scrapers/daily_scheduler.py`
  - 如需测试单次运行: `python scrapers/daily_scheduler.py --run-once`
  - 自定义运行间隔（例如每12小时）: `python scrapers/daily_scheduler.py --interval-hours 12`
- 也可以将 `scrapers/daily_scheduler.py --run-once` 加入系统cron任务或GitHub Actions，实现每天定时抓取

## AI 智能总结

- 每次更新会在 `data/ai_summary.json` 生成自动化总结，前端首页“Daily intelligence briefing” 模块将实时展示
- 总结内容包含：核心亮点、14 天内截止提醒、热门资助机构、面向的职业阶段、高额资助项目，以及当前滚动时间窗口说明
- 数据质量报告会在“Quality notes”中展示，便于追踪被剔除的条目类别
- 如需要自定义总结逻辑，可修改 `scrapers/summarizer.py`

## 每日自动更新

- 在服务器上执行一次更新并生成AI摘要: `python scrapers/update_all.py`
- 持续运行的自动任务（默认每24小时运行一次）: `python scrapers/daily_scheduler.py`
  - 如需测试单次运行: `python scrapers/daily_scheduler.py --run-once`
  - 自定义运行间隔（例如每12小时）: `python scrapers/daily_scheduler.py --interval-hours 12`
- 也可以将 `scrapers/daily_scheduler.py --run-once` 加入系统cron任务或GitHub Actions，实现每天定时抓取

## AI 智能总结

- 每次更新会在 `data/ai_summary.json` 生成自动化总结，前端首页“Daily AI Briefing”模块将实时展示
- 总结内容包含：核心亮点、14天内截止的资助提醒、热门资助机构、面向的职业阶段及高额资助项目
- 如需要自定义总结逻辑，可修改 `scrapers/summarizer.py`

## 部署到GitHub Pages

1. 推送代码到GitHub仓库
2. 在仓库设置中启用GitHub Pages
3. 选择主分支作为源
4. 访问生成的URL查看网站
