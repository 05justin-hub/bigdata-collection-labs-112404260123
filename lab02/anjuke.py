# -*- coding: utf-8 -*-
"""实验二：安居客教学站房源采集，保存为 CSV（入库见 load_mysql.py）"""
import csv
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "http://www.bspider.top/anjuke/"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
    "Referer": "http://www.bspider.top/",
}
MAX_PAGES = 30          # 安全页数上限，防止无限循环
CSV_PATH = Path(__file__).parent / "data" / "houseinfo.csv"
FIELDS = ["title", "house", "address", "struct",
          "area", "floor", "maketime", "price"]


def fetch(url):
    """请求页面，检测是否被拦截（访问验证页）。"""
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    soup = BeautifulSoup(r.text, "html.parser")
    if "访问验证" in soup.title.get_text():
        raise RuntimeError(f"被访问验证页拦截：{url}")
    return soup


def parse_row(row):
    """从一条 div.property 中解析 8 个字段，顺序固定。"""
    # 标题
    node = row.select_one("h3.property-content-title-name")
    title = node.get_text(strip=True) if node else ""

    # 楼盘
    node = row.select_one("p.property-content-info-comm-name")
    house = node.get_text(strip=True) if node else ""

    # 地址：文字分散在多个 span 中，get_text 直接拼接，不插入空格
    node = row.select_one("p.property-content-info-comm-address")
    address = node.get_text(strip=True) if node else ""

    # 户型：带 property-content-info-attribute 的段落
    node = row.select_one("p.property-content-info-attribute")
    struct = node.get_text(strip=True) if node else ""

    # 面积 / 朝向 / 楼层 / 年代都在普通 p.property-content-info-text 中
    texts = [p.get_text(strip=True)
             for p in row.select("p.property-content-info-text")]
    area, floor, maketime = "", "", ""
    for t in texts:
        if "㎡" in t:
            area = t                      # 带单位的建筑面积
        elif "建造" in t:
            maketime = t                  # 如 “2019年建造”
        elif "层" in t:
            floor = t                     # 如 “低层(共27层)”，朝向是“南北”不含层
    # 建造年代可能缺失，保持空字符串

    # 单价：取 property-price-average（元/㎡），不能取成“万元”总价
    node = row.select_one("p.property-price-average")
    price = node.get_text(strip=True) if node else ""

    return [title, house, address, struct, area, floor, maketime, price]


def main():
    current_url = BASE_URL
    visited = set()
    records = []
    page_no = 0
    stop_reason = ""

    while current_url:
        page_no += 1
        soup = fetch(current_url)
        rows = soup.select("div.property")
        if not rows:
            raise RuntimeError(f"第{page_no}页未解析到房源，结构异常，中止")
        records.extend(parse_row(r) for r in rows)
        print(f"页码 {page_no} | {current_url} | 本页 {len(rows)} 条 | "
              f"累计 {len(records)} 条")

        # 找下一页：a.next.next-active 表示可点击
        visited.add(current_url)
        nxt = soup.select_one("a.next.next-active")
        if nxt is None:
            stop_reason = "下一页按钮无 next-active（已到末页），正常停止"
            break
        href = nxt.get("href")
        if not href:
            stop_reason = "下一页无 href，结构异常，中止"
            break
        next_url = urljoin(current_url, href)
        if next_url in visited or page_no >= MAX_PAGES:
            stop_reason = ("达到安全页数上限" if page_no >= MAX_PAGES
                           else "下一页地址重复，中止")
            break
        current_url = next_url
        time.sleep(1.2)   # 礼貌等待，再请求下一页

    print(f"采集完成/中止：{stop_reason}")

    # 按 8 个字段完全相同去重
    unique = []
    seen = set()
    for rec in records:
        key = tuple(rec)
        if key not in seen:
            seen.add(key)
            unique.append(rec)
    print(f"去重前 {len(records)} 条，重复 {len(records) - len(unique)} 条，"
          f"去重后 {len(unique)} 条")

    # 保存 CSV
    CSV_PATH.parent.mkdir(exist_ok=True)
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        writer.writerows(unique)
    print(f"已保存 {CSV_PATH}")

    # 回读核对
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == FIELDS, "表头不符"
        back = list(reader)
    print(f"回读数据行数（不含表头）：{len(back)}")
    print("首条：", back[0])
    print("末条：", back[-1])


if __name__ == "__main__":
    main()
