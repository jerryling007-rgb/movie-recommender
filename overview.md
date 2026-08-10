# 影片推荐系统 (MovieRec) v2.0

## 概述

基于 rrdynb.com 的智能影片推荐平台 v2.0 — 深色高级风格，详情页直接展示网盘下载链接+提取码。

## v2.0 更新亮点

- **隐藏老电影**：不主动抓取、不在首页/推荐中展示，保留搜索能力
- **详情页直达下载**：直接展示百度/夸克/迅雷/阿里云盘链接+提取码，无需跳转源站
- **深色高级风格**：金色点缀 (#fbbf24) + 深黑背景 (#0a0a0b) + 毛玻璃面板
- **扩量至~2000条**：3分类×70页上限

## 当前状态

| 指标 | 数值 |
|---|---|
| 影片总数 | 抓取中... |
| 主动抓取分类 | 电影 / 电视剧 / 动漫（不含老电影） |
| 下载链接 | 详情页直接展示 |
| 定时更新 | 每日 09:00 |
| UI风格 | 深黑+金色高级风 |

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.13 / FastAPI |
| 前端 | React 19 / TypeScript / Tailwind CSS v4 |
| 数据库 | SQLite (WAL模式) |
| AI推荐 | TF-IDF + 余弦相似度 (scikit-learn) |
| 爬虫 | httpx + BeautifulSoup4 + lxml |

## 快速开始

### 本地运行
```bash
cd backend && source venv/bin/activate
PYTHONPATH=. python -m uvicorn main:app --host 0.0.0.0 --port 3000
# 浏览器打开 http://localhost:3000
```

### Docker 部署（本地/服务器）
```bash
# 构建并启动
docker compose up -d
# 访问 http://localhost:8080

# 或手动构建
docker build -t movie-recommender .
docker run -d -p 8080:8080 -v $(pwd)/data:/app/data movie-recommender
```

### Render.com 一键部署（免费云端）
1. 将项目推送到 GitHub 仓库
2. 在 [Render.com](https://render.com) 创建 Blueprint，指向 `render.yaml`
3. 自动构建并部署，获得 `https://xxx.onrender.com` 公网地址
4. 免费额度 750小时/月，足够 24/7 运行

## API 接口

| 路径 | 说明 |
|---|---|
| GET /api/movies | 影片列表（默认排除老电影，支持筛选+分页） |
| GET /api/movies/{id} | 影片详情（含下载链接） |
| GET /api/movies/{id}/links | 按需获取下载链接（缓存优先，否则实时抓取） |
| GET /api/movies/{id}/recommend | AI智能推荐（排除老电影） |
| GET /api/recommend/search?q= | 文字描述搜索推荐 |
| GET /api/stats | 统计数据（排除老电影） |
| POST /api/crawl/start | 手动触发抓取（full=true全量，不含老电影） |

## 下载链接解析逻辑

从详情页HTML解析 `<a>` 标签中指向网盘分享链接的URL：
- 百度网盘: `pan.baidu.com/s/xxx`
- 夸克网盘: `pan.quark.cn/s/xxx`
- 迅雷云盘: `pan.xunlei.com/s/xxx`
- 阿里云盘: `alipan.com/s/xxx` / `aliyundrive.com/s/xxx`

提取码来源：
1. URL参数 `?pwd=xxxx`（百度/迅雷）
2. 页面文本 `提取码：xxxx`

## 项目结构

```
movie-recommender/
├── backend/
│   ├── main.py          # FastAPI v2.0 — 隐藏老电影+按需获取链接
│   ├── database.py      # SQLite 4张表
│   ├── scraper.py       # 爬虫v2.0 — 跳过老电影+下载链接解析
│   ├── recommender.py   # TF-IDF推荐引擎
│   ├── scheduler.py     # 每日09:00定时任务
│   └── venv/
├── frontend/
│   ├── src/
│   │   ├── pages/       # Home, Browse, Detail, Stats（深色高级风）
│   │   ├── components/  # Layout, MovieCard, SearchBar
│   │   └── index.css    # 金色@theme + 毛玻璃 + 高级动画
│   └── dist/
├── Dockerfile          # 容器化部署
├── docker-compose.yml  # Docker Compose 一键部署
├── render.yaml         # Render.com 云部署配置
├── .dockerignore       # Docker 忽略文件
└── overview.md
```
