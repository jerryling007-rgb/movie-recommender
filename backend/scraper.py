"""
网站爬虫模块 - 抓取 rrdynb.com 影片数据
- 深层抓取（每分类200+页）
- 智能分类：自动识别短剧、综艺
- 质量筛选：优先高热度内容
"""
import re
import asyncio
import random
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.rrdynb.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 主动抓取的分类
ACTIVE_CATEGORIES = ["movie", "tv", "anime", "classic"]

CATEGORY_MAP = {
    "movie":       {"name": "电影",   "url_path": "/movie/",     "list_prefix": "list_2"},
    "tv":          {"name": "电视剧", "url_path": "/dianshiju/",  "list_prefix": "list_6"},
    "classic":     {"name": "老电影", "url_path": "/zongyi/",     "list_prefix": "list_10"},
    "anime":       {"name": "动漫",   "url_path": "/dongman/",    "list_prefix": "list_13"},
    "short_drama": {"name": "短剧",   "url_path": "/dianshiju/",  "list_prefix": "list_6"},
    "variety":     {"name": "综艺",   "url_path": "/dianshiju/",  "list_prefix": "list_6"},
}

# 每个分类最大抓取页数
MAX_PAGES_PER_CATEGORY = 300

MIN_DELAY = 0.3
MAX_DELAY = 0.8

# 网盘域名 -> (平台名, 分享链接路径标识)
PAN_DOMAIN_MAP = {
    "pan.baidu.com":       ("百度网盘", "/s/"),
    "pan.quark.cn":         ("夸克网盘", "/s/"),
    "pan.xunlei.com":       ("迅雷云盘", "/s/"),
    "www.aliyundrive.com":  ("阿里云盘", "/s/"),
    "www.alipan.com":       ("阿里云盘", "/s/"),
    "aliyundrive.com":      ("阿里云盘", "/s/"),
    "pan.aliyundrive.com":  ("阿里云盘", "/s/"),
}

# ========== 热门综艺关键词库 ==========
VARIETY_KEYWORDS = [
    # 浙江卫视
    "奔跑吧", "王牌对王牌", "中国好声音", "天赐的声音", "无限超越班",
    "青春环游记", "嗨放派", "听说很好吃", "追星星的人",
    # 湖南卫视/芒果TV
    "向往的生活", "乘风破浪", "披荆斩棘", "你好星期六", "快乐大本营",
    "天天向上", "我是歌手", "歌手", "声生不息", "时光音乐会",
    "中餐厅", "花儿与少年", "妻子的浪漫旅行", "女儿们的恋爱",
    "密室大逃脱", "明星大侦探", "大侦探", "名侦探学院",
    "再见爱人", "爸爸当家", "快乐再出发",
    # 东方卫视
    "极限挑战", "我们的歌", "一路前行", "开播吧",
    # 江苏卫视
    "最强大脑", "非诚勿扰", "一站到底",
    # 央视
    "典籍里的中国", "国家宝藏", "朗读者", "经典咏流传",
    "中国诗词大会", "故事里的中国", "开讲啦",
    # 爱奇艺
    "中国新说唱", "乐队的夏天", "一年一度喜剧大赛", "奇葩说",
    "萌探探探案", "哈哈哈哈哈",
    # 腾讯视频
    "创造营", "明日之子", "脱口秀大会", "令人心动的offer",
    "心动的信号", "五十公里桃花坞", "现在就出发",
    # 优酷
    "这！就是街舞", "这！就是灌篮", "我们恋爱吧",
    # 其他
    "德云斗笑社", "欢乐喜剧人", "跨界歌王", "超新星运动会",
    "种地吧", "半熟恋人", "怦然心动",
    # B站
    "守护解放西", "非正式会谈",
    # 纪录片式综艺
    "奇遇人生", "是面包是空气是奇迹",
    # Netflix/国外热门
    "体能之巅", "单身即地狱", "粉红谎言",
]

# ========== 短剧识别关键词 ==========
SHORT_DRAMA_KEYWORDS = [
    "短剧", "微短剧", "竖屏短剧", "迷你剧", "泡面番",
    "小剧场", "微剧", "抖音短剧", "快手短剧",
]

# 短剧集数阈值（<=此值可能为短剧）
SHORT_DRAMA_MAX_EPISODES = 6

# ========== 质量筛选：高热度信号 ==========
QUALITY_HIGH = 2    # 高热度
QUALITY_MEDIUM = 1  # 中热度
QUALITY_LOW = 0     # 低热度（跳过）


class MovieScraper:
    def __init__(self, http_client=None):
        self.client = http_client

    async def _get_client(self):
        if self.client is None:
            self.client = httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True)
        return self.client

    async def _fetch(self, url: str) -> str:
        client = await self._get_client()
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        await asyncio.sleep(delay)
        resp = await client.get(url)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp.text

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None

    # ========== 质量评分 ==========

    @staticmethod
    def score_quality(info: dict) -> int:
        """评估影片热度质量，返回 QUALITY_HIGH/MEDIUM/LOW"""
        score = 0
        title = info.get("title", "")

        # 豆瓣评分
        douban = info.get("douban_rating", 0)
        if douban >= 7.0:
            score += 4
        elif douban >= 5.0:
            score += 2
        elif douban > 0:
            score += 1

        # 年份（越新越好）
        year = info.get("year", 0)
        if year >= 2024:
            score += 3
        elif year >= 2020:
            score += 2
        elif year >= 2015:
            score += 1

        # IMDB评分（从brief提取）
        resource = info.get("resource_info", "")
        imdb_match = re.search(r"IMDB[：:]\s*(\d+\.?\d*)", resource)
        if imdb_match:
            imdb = float(imdb_match.group(1))
            if imdb >= 7.0:
                score += 2
            elif imdb >= 5.0:
                score += 1

        # 热门综艺关键词
        if any(kw in title for kw in VARIETY_KEYWORDS):
            score += 3

        # 有海报
        if info.get("poster_url"):
            score += 1

        # 类型信息丰富
        if info.get("genres") and info.get("director"):
            score += 1

        # 有简介
        if info.get("summary") and len(info.get("summary", "")) > 50:
            score += 1

        if score >= 6:
            return QUALITY_HIGH
        elif score >= 3:
            return QUALITY_MEDIUM
        else:
            return QUALITY_LOW

    # ========== 智能分类 ==========

    @staticmethod
    def classify_special_category(info: dict) -> str | None:
        """自动识别短剧/综艺，返回 category_slug 或 None"""
        title = info.get("title", "")
        genres = info.get("genres", "")
        episodes_str = info.get("episodes", "")
        summary = info.get("summary", "")
        combined = f"{title} {genres} {summary}"

        # 综艺检测
        if any(kw in title for kw in VARIETY_KEYWORDS):
            return "variety"
        if "真人秀" in combined or "综艺" in combined:
            return "variety"
        # 综艺特征：无导演但多嘉宾、季数标记
        if re.search(r"第[一二三四五六七八九十\d]+季", title) and not info.get("director"):
            if "真人秀" in combined or "嘉宾" in combined or "节目" in combined:
                return "variety"

        # 短剧检测
        if any(kw in combined for kw in SHORT_DRAMA_KEYWORDS):
            return "short_drama"
        # 短集数判定
        if episodes_str:
            ep_nums = re.findall(r"\d+", episodes_str)
            for n in ep_nums:
                if 0 < int(n) <= SHORT_DRAMA_MAX_EPISODES:
                    if "微短剧" in combined or "竖屏" in combined or "短剧" in combined:
                        return "short_drama"
                    # 单集影片可能是微电影，不是短剧
                    if int(n) > 1 and ("短剧" in combined or "泡面" in combined):
                        return "short_drama"

        return None

    # ========== 首页列表抓取 ==========

    async def scrape_homepage(self) -> list[dict]:
        """抓取首页所有板块的影片列表（跳过老电影板块）"""
        html = await self._fetch(f"{BASE_URL}/index.html")
        soup = BeautifulSoup(html, "lxml")
        items = []

        panels = soup.select(".stui-pannel.stui-pannel-bg")
        for panel in panels:
            title_el = panel.select_one(".stui-pannel_hd h3.title a")
            if not title_el:
                title_el = panel.select_one(".stui-pannel_hd .title")
            section_title = title_el.get_text(strip=True) if title_el else ""

            category_slug, sub_category = self._parse_section_title(section_title)
            if not category_slug:
                continue
            if category_slug == "classic":
                continue

            movie_links = panel.select(".stui-vodlist__thumb")
            for link in movie_links:
                href = link.get("href", "")
                title = link.get("title", "")
                if not href or not title:
                    continue
                if not self._is_movie_url(href):
                    continue

                items.append({
                    "title": self._clean_title(title),
                    "detail_url": urljoin(BASE_URL, href),
                    "category_slug": category_slug,
                    "sub_category": sub_category,
                })

        return items

    async def scrape_category_list(self, category_slug: str, page: int = 1) -> tuple[list[dict], bool]:
        """抓取分类列表页（分页）- 列表页包含完整元数据"""
        cat = CATEGORY_MAP.get(category_slug)
        if not cat:
            return [], False

        if page == 1:
            url = f"{BASE_URL}{cat['url_path']}"
        else:
            url = f"{BASE_URL}{cat['url_path']}{cat['list_prefix']}_{page}.html"

        html = await self._fetch(url)
        soup = BeautifulSoup(html, "lxml")
        items = []

        movie_items = soup.select("#movielist li.pure-g")
        for li in movie_items:
            title_link = li.select_one(".intro h2 a")
            if not title_link:
                continue
            href = title_link.get("href", "")
            title = title_link.get("title", "") or title_link.get_text(strip=True)
            title = self._clean_title(title)

            if not href or not title:
                continue
            if not self._is_movie_url(href):
                continue

            poster_url = ""
            img_el = li.select_one("img.pure-img")
            if img_el:
                poster_url = urljoin(BASE_URL, img_el.get("data-original", "") or img_el.get("src", ""))

            brief_el = li.select_one(".brief")
            brief_text = brief_el.get_text(" ", strip=True) if brief_el else ""

            info = {
                "title": title,
                "poster_url": poster_url,
                "detail_url": urljoin(BASE_URL, href),
                "category_slug": category_slug,
                "sub_category": "latest",
                "director": "",
                "writers": "",
                "cast": "",
                "genres": "",
                "country": "",
                "language": "",
                "release_date": "",
                "episodes": "",
                "runtime": "",
                "aka": "",
                "summary": "",
                "year": 0,
                "douban_rating": 0,
                "source_id": "",
            }

            brief_patterns = {
                "director": r"导演[：:]\s*(.+?)(?:主演|编剧|类型|制片|语言|上映|首播|集数|片长|又名|剧情简介|资源|豆瓣|IMDb|$)",
                "writers": r"编剧[：:]\s*(.+?)(?:导演|主演|类型|制片|语言|上映|首播|集数|片长|又名|剧情简介|资源|豆瓣|IMDb|$)",
                "cast": r"主演[：:]\s*(.+?)(?:导演|编剧|类型|制片|语言|上映|首播|集数|片长|又名|剧情简介|资源|豆瓣|IMDb|$)",
                "genres": r"类型[：:]\s*(.+?)(?:导演|编剧|主演|制片|语言|上映|首播|集数|片长|又名|剧情简介|资源|豆瓣|IMDb|$)",
                "country": r"制片国家/地区[：:]\s*(.+?)(?:导演|编剧|主演|类型|语言|上映|首播|集数|片长|又名|剧情简介|资源|豆瓣|IMDb|$)",
                "language": r"语言[：:]\s*(.+?)(?:导演|编剧|主演|类型|制片|上映|首播|集数|片长|又名|剧情简介|资源|豆瓣|IMDb|$)",
                "release_date": r"(?:上映日期|首播)[：:]\s*(.+?)(?:导演|编剧|主演|类型|制片|语言|集数|片长|又名|剧情简介|资源|豆瓣|IMDb|$)",
                "aka": r"又名[：:]\s*(.+?)(?:导演|编剧|主演|类型|制片|语言|上映|首播|集数|片长|剧情简介|资源|豆瓣|IMDb|$)",
                "summary": r"剧情简介[：:]\s*(.+?)(?:导演|编剧|主演|类型|制片|语言|上映|首播|集数|片长|又名|资源|豆瓣|IMDb|$)",
            }

            for field, pattern in brief_patterns.items():
                match = re.search(pattern, brief_text, re.DOTALL)
                if match:
                    val = match.group(1).strip()
                    if val and val not in ("未知", "不详", "-"):
                        if field == "summary":
                            if len(val) > 20:
                                info[field] = val[:500]
                        else:
                            info[field] = val

            self._extract_from_url(href, info)
            if not info["year"] and info.get("release_date"):
                ym = re.search(r"(\d{4})", info["release_date"])
                if ym:
                    info["year"] = int(ym.group(1))
            if not info["year"]:
                info["year"] = self._extract_year_from_title(title)

            # 提取豆瓣评分
            dr_match = re.search(r"豆瓣(?:评分)?[：:]\s*(\d+\.?\d*)", brief_text)
            if dr_match:
                info["douban_rating"] = float(dr_match.group(1))

            # 质量评分
            info["_quality"] = self.score_quality(info)

            # 智能分类（短剧/综艺）
            special_cat = self.classify_special_category(info)
            if special_cat:
                info["_special_category"] = special_cat

            items.append(info)

        # 检查下一页
        next_link = f"{cat['list_prefix']}_{page + 1}.html"
        has_next = bool(soup.select_one(f"a[href='{next_link}']"))

        return items, has_next

    # ========== 详情页下载链接抓取 ==========

    async def scrape_download_links(self, detail_url: str) -> list[dict]:
        """从详情页HTML解析网盘下载链接+提取码"""
        try:
            html = await self._fetch(detail_url)
        except Exception as e:
            print(f"  ❌ 抓取下载链接失败 {detail_url}: {e}")
            return []

        soup = BeautifulSoup(html, "lxml")
        links = []
        seen_urls = set()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if not href or href.startswith("#"):
                continue

            platform = None
            for domain, (name, path_marker) in PAN_DOMAIN_MAP.items():
                if domain in href and path_marker in href:
                    platform = name
                    break

            if not platform:
                continue
            if href in seen_urls:
                continue
            seen_urls.add(href)

            access_code = ""
            pwd_match = re.search(r"[?&]pwd=([^&]+)", href)
            if pwd_match:
                access_code = pwd_match.group(1).rstrip("#")

            link_text = a_tag.get_text(strip=True)
            if link_text and any(k in link_text for k in ["百度", "夸克", "迅雷", "阿里"]):
                platform = link_text if len(link_text) <= 10 else platform

            if not access_code:
                parent = a_tag.parent
                if parent:
                    parent_text = parent.get_text(" ", strip=True)
                    code_match = re.search(r"提取码[：:]\s*([a-zA-Z0-9]{4,6})", parent_text)
                    if code_match:
                        access_code = code_match.group(1)

            links.append({
                "platform": platform,
                "url": href,
                "access_code": access_code,
            })

        return links

    async def scrape_detail_with_links(self, url: str) -> dict | None:
        """抓取影片详情页 - 包含元数据+下载链接"""
        try:
            html = await self._fetch(url)
        except Exception as e:
            print(f"  ❌ 抓取失败 {url}: {e}")
            return None

        soup = BeautifulSoup(html, "lxml")

        title_el = soup.select_one("h1, h2, .title h2, .title_all h1, .ctitle, strong")
        title = title_el.get_text(strip=True) if title_el else ""
        title = self._clean_title(title)
        if not title:
            page_title = soup.select_one("title")
            if page_title:
                title = self._clean_title(page_title.get_text(strip=True))

        poster_url = ""
        poster_el = soup.select_one("img[src*='upload'], img[src*='pic'], img[src*='image'], img[src*='poster']")
        if not poster_el:
            poster_el = soup.select_one(".v-pic img, .pic img, .intro img, .co_content8 img, img")
        if poster_el:
            poster_url = urljoin(BASE_URL, poster_el.get("src", ""))

        info = {
            "title": title,
            "poster_url": poster_url,
            "detail_url": url,
            "director": "",
            "writers": "",
            "cast": "",
            "genres": "",
            "country": "",
            "language": "",
            "release_date": "",
            "episodes": "",
            "runtime": "",
            "aka": "",
            "summary": "",
            "resource_info": "",
            "year": 0,
            "douban_rating": 0,
            "source_id": "",
            "download_links": [],
        }

        self._extract_from_url(url, info)

        text = soup.get_text(" ", strip=True)

        patterns = {
            "director": r"导演[：:]\s*(.+?)(?:主演|编剧|类型|制片|语言|上映|首播|集数|片长|又名|资源|豆瓣|IMDb|$)",
            "writers": r"编剧[：:]\s*(.+?)(?:导演|主演|类型|制片|语言|上映|首播|集数|片长|又名|资源|豆瓣|IMDb|$)",
            "cast": r"主演[：:]\s*(.+?)(?:导演|编剧|类型|制片|语言|上映|首播|集数|片长|又名|资源|豆瓣|IMDb|$)",
            "genres": r"类型[：:]\s*(.+?)(?:导演|编剧|主演|制片|语言|上映|首播|集数|片长|又名|资源|豆瓣|IMDb|$)",
            "country": r"制片国家/地区[：:]\s*(.+?)(?:导演|编剧|主演|类型|语言|上映|首播|集数|片长|又名|资源|豆瓣|IMDb|$)",
            "language": r"语言[：:]\s*(.+?)(?:导演|编剧|主演|类型|制片|上映|首播|集数|片长|又名|资源|豆瓣|IMDb|$)",
            "release_date": r"(?:上映日期|首播)[：:]\s*(.+?)(?:导演|编剧|主演|类型|制片|语言|集数|片长|又名|资源|豆瓣|IMDb|$)",
            "episodes": r"集数[：:]\s*(\d+)",
            "runtime": r"(?:片长|单集片长)[：:]\s*(.+?)(?:导演|编剧|主演|类型|制片|语言|上映|首播|集数|又名|资源|豆瓣|IMDb|$)",
            "aka": r"又名[：:]\s*(.+?)(?:导演|编剧|主演|类型|制片|语言|上映|首播|集数|片长|资源|豆瓣|IMDb|$)",
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.DOTALL)
            if match:
                val = match.group(1).strip()
                if val and val not in ("未知", "不详", "-"):
                    info[field] = val

        summary_match = re.search(
            r"(?:剧情简介|简介|◎简\s*介)[：:]*\s*(.+?)(?:导演|编剧|主演|类型|制片|语言|上映|首播|集数|片长|又名|资源下载|百度云|夸克|迅雷|$)",
            text, re.DOTALL,
        )
        if summary_match:
            summary = summary_match.group(1).strip()
            if len(summary) > 20:
                info["summary"] = summary[:500]

        info["resource_info"] = self._extract_resource_info(soup, text)

        douban_match = re.search(r"豆瓣(?:评分)?[：:]\s*(\d+\.?\d*)", text)
        if douban_match:
            info["douban_rating"] = float(douban_match.group(1))

        if info.get("release_date"):
            year_match = re.search(r"(\d{4})", info["release_date"])
            if year_match:
                info["year"] = int(year_match.group(1))
        if not info["year"]:
            info["year"] = self._extract_year_from_title(title)

        info["download_links"] = await self._parse_download_links_from_soup(soup)

        # 质量评分 + 智能分类
        info["_quality"] = self.score_quality(info)
        special_cat = self.classify_special_category(info)
        if special_cat:
            info["_special_category"] = special_cat

        return info

    async def _parse_download_links_from_soup(self, soup: BeautifulSoup) -> list[dict]:
        links = []
        seen_urls = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if not href or href.startswith("#"):
                continue
            platform = None
            for domain, (name, path_marker) in PAN_DOMAIN_MAP.items():
                if domain in href and path_marker in href:
                    platform = name
                    break
            if not platform:
                continue
            if href in seen_urls:
                continue
            seen_urls.add(href)
            access_code = ""
            pwd_match = re.search(r"[?&]pwd=([^&]+)", href)
            if pwd_match:
                access_code = pwd_match.group(1).rstrip("#")
            link_text = a_tag.get_text(strip=True)
            if link_text and any(k in link_text for k in ["百度", "夸克", "迅雷", "阿里"]):
                platform = link_text if len(link_text) <= 10 else platform
            if not access_code:
                parent = a_tag.parent
                if parent:
                    parent_text = parent.get_text(" ", strip=True)
                    code_match = re.search(r"提取码[：:]\s*([a-zA-Z0-9]{4,6})", parent_text)
                    if code_match:
                        access_code = code_match.group(1)
            links.append({"platform": platform, "url": href, "access_code": access_code})
        return links

    # ========== 辅助方法 ==========

    def _parse_section_title(self, title: str) -> tuple[str | None, str]:
        if "老电影" in title or "经典" in title:
            return ("classic", "hot" if "热" in title else "latest")
        if "电视剧" in title:
            return ("tv", "hot" if "热" in title else "latest")
        if "电影" in title:
            return ("movie", "hot" if "热" in title else "latest")
        if "动漫" in title or "动画" in title:
            return ("anime", "hot" if "热" in title else "latest")
        return None, "latest"

    def _is_movie_url(self, href: str) -> bool:
        return bool(re.search(r"/(movie|dianshiju|zongyi|dongman)/\d{4}/\d{4}/\d+\.html", href))

    def _clean_title(self, title: str) -> str:
        title = re.sub(r"(百度云网盘|百度云|百度网盘|夸克|阿里云盘|迅雷云盘|百度).*$", "", title).strip()
        title = title.replace("《", "").replace("》", "").strip()
        return title

    def _extract_from_url(self, url: str, info: dict):
        match = re.search(r"/(\d{4})/(\d{4})/(\d+)\.html", url)
        if match:
            info["year"] = info["year"] or int(match.group(1))
            info["source_id"] = match.group(3)

    def _extract_year_from_title(self, title: str) -> int:
        match = re.search(r"(\d{4})", title)
        return int(match.group(1)) if match else 0

    def _extract_resource_info(self, soup, text: str) -> str:
        lines = []
        patterns = [
            r"百度网盘[：:]\s*(.+?)(?:\n|$)",
            r"百度云[：:]\s*(.+?)(?:\n|$)",
            r"提取码[：:]\s*(\S+)",
            r"夸克网盘[：:]\s*(.+?)(?:\n|$)",
            r"迅雷云盘[：:]\s*(.+?)(?:\n|$)",
            r"阿里云盘[：:]\s*(.+?)(?:\n|$)",
            r"迅雷下载[：:]\s*(.+?)(?:\n|$)",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                lines.append(m.group(0).strip())
        return "\n".join(lines) if lines else ""


# ========== 批量抓取管理器 ==========

class BatchScraper:
    """批量抓取管理器 - 支持深层抓取 + 质量筛选 + 智能分类"""

    def __init__(self, db_module=None):
        self.db = db_module
        self.scraper = MovieScraper()
        self.stats = {"total_scraped": 0, "saved": 0, "skipped_low_quality": 0,
                       "short_drama": 0, "variety": 0}

    async def full_sync(self, max_pages_per_category: int = MAX_PAGES_PER_CATEGORY,
                        fetch_links: bool = True, quality_filter: bool = True,
                        continue_only: bool = True):
        """全量同步所有活跃分类
        
        Args:
            continue_only: True=仅抓取之前未覆盖的页(251+), False=从头开始
        """
        total_new = 0
        total_updated = 0

        for cat_slug in ACTIVE_CATEGORIES:
            cat_name = CATEGORY_MAP[cat_slug]["name"]
            start = 251 if (continue_only and cat_slug != "classic") else 1
            print(f"\n🔄 开始同步: {cat_name} ({cat_slug}) 从第{start}页")
            new, updated = await self._sync_category(
                cat_slug, max_pages=max_pages_per_category,
                quality_filter=quality_filter, start_page=start)
            total_new += new
            total_updated += updated
            print(f"  ✅ {cat_name}: 新增 {new}, 更新 {updated}")

        print(f"\n📊 总计: 抓取 {self.stats['total_scraped']}, "
              f"收录 {self.stats['saved']}, "
              f"跳过低质 {self.stats['skipped_low_quality']}, "
              f"短剧 {self.stats['short_drama']}, "
              f"综艺 {self.stats['variety']}")

        # 抓取下载链接（仅高质量内容）
        if fetch_links:
            print(f"\n🔗 开始抓取下载链接（优质内容优先）...")
            link_count = await self.fetch_all_download_links(quality_only=True)
            print(f"  ✅ 下载链接抓取完成: {link_count} 条链接")

        return total_new, total_updated

    async def quick_sync(self):
        """快速同步：只抓首页最新内容"""
        print("🚀 快速同步首页...")
        items = await self.scraper.scrape_homepage()
        print(f"  首页获取到 {len(items)} 条")

        new_count = 0
        updated_count = 0
        for item in items:
            detail = await self.scraper.scrape_detail_with_links(item["detail_url"])
            if detail:
                detail["category_slug"] = item["category_slug"]
                detail["sub_category"] = item["sub_category"]
                result = self._save_movie(detail, quality_filter=False)
                if result == "new":
                    new_count += 1
                elif result == "updated":
                    updated_count += 1

        return new_count, updated_count

    async def _sync_category(self, cat_slug: str, max_pages: int = MAX_PAGES_PER_CATEGORY,
                             quality_filter: bool = True, start_page: int = 1):
        new = 0
        updated = 0

        for page in range(start_page, max_pages + 1):
            print(f"  📄 第 {page} 页...", end=" ")
            try:
                items, has_next = await self.scraper.scrape_category_list(cat_slug, page)
            except Exception as e:
                print(f"❌ 错误: {e}")
                break

            self.stats["total_scraped"] += len(items)
            saved_this_page = 0

            for info in items:
                # 质量过滤
                quality = info.pop("_quality", QUALITY_MEDIUM)
                special_cat = info.pop("_special_category", None)

                if quality_filter and quality == QUALITY_LOW:
                    self.stats["skipped_low_quality"] += 1
                    continue

                # 智能分类重定向
                if special_cat:
                    info["category_slug"] = special_cat
                    if special_cat == "short_drama":
                        self.stats["short_drama"] += 1
                    elif special_cat == "variety":
                        self.stats["variety"] += 1

                result = self._save_movie(info)
                if result in ("new", "updated"):
                    saved_this_page += 1
                if result == "new":
                    new += 1
                elif result == "updated":
                    updated += 1

            self.stats["saved"] += saved_this_page
            print(f"{len(items)}条 → 收录{saved_this_page}条 | 累计收录{self.stats['saved']}")

            if not has_next:
                print(f"  🏁 已到最后一页")
                break

        return new, updated

    async def fetch_all_download_links(self, batch_size: int = 8, quality_only: bool = True):
        """为数据库中所有没有下载链接的影片抓取下载链接"""
        from database import get_db

        with get_db() as db:
            if quality_only:
                # 优先高质量内容
                movies_without_links = db.execute("""
                    SELECT m.id, m.detail_url, m.title
                    FROM movies m
                    WHERE m.is_active = 1
                      AND m.id NOT IN (SELECT DISTINCT movie_id FROM download_links)
                    ORDER BY m.douban_rating DESC, m.year DESC
                """).fetchall()
            else:
                movies_without_links = db.execute("""
                    SELECT m.id, m.detail_url, m.title
                    FROM movies m
                    WHERE m.is_active = 1
                      AND m.id NOT IN (SELECT DISTINCT movie_id FROM download_links)
                    ORDER BY m.id
                """).fetchall()

        total = len(movies_without_links)
        print(f"  需要抓取下载链接的影片: {total} 条")
        link_count = 0

        for i in range(0, total, batch_size):
            batch = movies_without_links[i:i + batch_size]
            tasks = [self._fetch_and_save_links(m["id"], m["detail_url"], m["title"]) for m in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, int):
                    link_count += r

            done = min(i + batch_size, total)
            if done % 50 == 0 or done == total:
                print(f"  进度: {done}/{total} ({done * 100 // total}%)")

        return link_count

    async def _fetch_and_save_links(self, movie_id: int, detail_url: str, title: str) -> int:
        try:
            links = await self.scraper.scrape_download_links(detail_url)
            if not links:
                return 0
            from database import get_db
            with get_db() as db:
                for link in links:
                    db.execute("""
                        INSERT OR IGNORE INTO download_links (movie_id, platform, url, access_code)
                        VALUES (?, ?, ?, ?)
                    """, (movie_id, link["platform"], link["url"], link["access_code"]))
            return len(links)
        except Exception as e:
            return 0

    async def fetch_links_for_movie(self, movie_id: int) -> list[dict]:
        from database import get_db
        with get_db() as db:
            movie = db.execute("SELECT detail_url FROM movies WHERE id = ?", (movie_id,)).fetchone()
            if not movie:
                return []
            existing = db.execute(
                "SELECT * FROM download_links WHERE movie_id = ?", (movie_id,)
            ).fetchall()
            if existing:
                return [dict(l) for l in existing]

        links = await self.scraper.scrape_download_links(movie["detail_url"])
        if links:
            with get_db() as db:
                for link in links:
                    db.execute("""
                        INSERT OR IGNORE INTO download_links (movie_id, platform, url, access_code)
                        VALUES (?, ?, ?, ?)
                    """, (movie_id, link["platform"], link["url"], link["access_code"]))
        return links

    def _save_movie(self, detail: dict) -> str:
        from database import get_db
        try:
            with get_db() as db:
                cat = db.execute("SELECT id FROM categories WHERE slug = ?",
                                 (detail.get("category_slug"),)).fetchone()
                if not cat:
                    return "skip"
                cat_id = cat["id"]

                existing = db.execute("SELECT id FROM movies WHERE detail_url = ?",
                                      (detail["detail_url"],)).fetchone()

                if existing:
                    db.execute("""
                        UPDATE movies SET
                            title=?, poster_url=?, director=?, writers=?, cast=?,
                            genres=?, country=?, language=?, release_date=?,
                            episodes=?, runtime=?, aka=?, summary=?, resource_info=?,
                            year=?, douban_rating=?, updated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    """, (
                        detail.get("title", ""),
                        detail.get("poster_url", ""),
                        detail.get("director", ""),
                        detail.get("writers", ""),
                        detail.get("cast", ""),
                        detail.get("genres", ""),
                        detail.get("country", ""),
                        detail.get("language", ""),
                        detail.get("release_date", ""),
                        detail.get("episodes", ""),
                        detail.get("runtime", ""),
                        detail.get("aka", ""),
                        detail.get("summary", ""),
                        detail.get("resource_info", ""),
                        detail.get("year", 0),
                        detail.get("douban_rating", 0),
                        existing["id"],
                    ))
                    movie_id = existing["id"]
                else:
                    db.execute("""
                        INSERT INTO movies
                        (title, category_id, sub_category, poster_url, detail_url,
                         director, writers, cast, genres, country, language,
                         release_date, episodes, runtime, aka, summary, resource_info,
                         year, douban_rating, source_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        detail.get("title", ""),
                        cat_id,
                        detail.get("sub_category", "latest"),
                        detail.get("poster_url", ""),
                        detail["detail_url"],
                        detail.get("director", ""),
                        detail.get("writers", ""),
                        detail.get("cast", ""),
                        detail.get("genres", ""),
                        detail.get("country", ""),
                        detail.get("language", ""),
                        detail.get("release_date", ""),
                        detail.get("episodes", ""),
                        detail.get("runtime", ""),
                        detail.get("aka", ""),
                        detail.get("summary", ""),
                        detail.get("resource_info", ""),
                        detail.get("year", 0),
                        detail.get("douban_rating", 0),
                        detail.get("source_id", ""),
                    ))
                    movie_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

                download_links = detail.get("download_links", [])
                if download_links:
                    for link in download_links:
                        db.execute("""
                            INSERT OR IGNORE INTO download_links (movie_id, platform, url, access_code)
                            VALUES (?, ?, ?, ?)
                        """, (movie_id, link["platform"], link["url"], link["access_code"]))

                return "updated" if existing else "new"
        except Exception as e:
            print(f"  ⚠️ 保存失败 {detail.get('title')}: {e}")
            return "error"

    async def close(self):
        await self.scraper.close()
