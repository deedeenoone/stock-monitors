#!/usr/bin/env python3
"""
Halo Cloud 库存查询脚本 v1.0
单次执行，查询所有产品库存并汇报结果
"""

import os
import sys
import json
import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

# ============== 配置 ==============
PRODUCT_PAGES = {
    "jp_standard": {
        "name": "JP Tokyo Standard VPS",
        "url": "https://my.halocloud.net/index.php?rp=/store/tokyo-jp-standard-vps",
        "products": {
            # 需要根据实际页面填写产品信息
        }
    },
    "sg_standard": {
        "name": "SG Singapore Standard VPS",
        "url": "https://my.halocloud.net/index.php?rp=/store/singapore-sg-standard-vps",
        "products": {
            # 需要根据实际页面填写产品信息
        }
    }
}

# 展平所有产品
ALL_PRODUCTS = {}
for page_key, page_info in PRODUCT_PAGES.items():
    for pid, prod_info in page_info["products"].items():
        ALL_PRODUCTS[pid] = {
            **prod_info,
            "page_key": page_key,
            "url": page_info["url"]
        }


def parse_page_stock(html):
    """从页面HTML中提取所有产品的库存数量"""
    # 查找 $0.75 相关产品
    available_matches = re.findall(r'\$(\d+\.?\d*)\/mo.*?(\d+)\s+(?:available|in stock|left)', html, re.I | re.S)
    results = {}
    for price, count in available_matches:
        if float(price) == 0.75:
            results[float(price)] = int(count)
    return results


def check_page_products(page, page_info):
    """检查某主页的所有产品库存"""
    results = {}

    try:
        page.goto(page_info["url"], timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        html = page.content()

        # 提取所有产品卡片
        product_blocks = re.findall(
            r'<h4[^>]*>([^<]+)</h4>.*?<p[^>]*>.*?\$(\d+\.?\d*)/mo.*?</p>.*?(\d+)\s+(?:available|in stock)',
            html, re.I | re.S
        )

        for name, price, count in product_blocks:
            if float(price) == 0.75:
                pid = name.strip().lower().replace(" ", "-")
                results[pid] = {
                    "name": name.strip(),
                    "price": f"${price}/mo",
                    "stock": int(count)
                }

    except Exception as e:
        print(f"   ❌ {page_info['name']}: {e}")

    return results


def check_all_stock(page):
    """检查所有产品库存"""
    results = {}

    for page_key, page_info in PRODUCT_PAGES.items():
        print(f"   检查: {page_info['name']}...", flush=True)
        page_results = check_page_products(page, page_info)
        results.update(page_results)
        time.sleep(2)

    return results


def display_results(results):
    """显示库存结果"""
    available_list = []
    sold_out_list = []

    for pid, info in results.items():
        name = info["name"]
        price = info["price"]
        stock = info["stock"]

        if stock > 0:
            available_list.append(f"   ✅ {name} ({price}) - 剩余 {stock} 件")
        else:
            sold_out_list.append(f"   ❌ {name} ({price}) - 缺货")

    print()
    if available_list:
        print("【有货产品 - $0.75/mo】")
        for item in available_list:
            print(item)

    if sold_out_list:
        print("\n【缺货产品 - $0.75/mo】")
        for item in sold_out_list:
            print(item)

    print(f"\n📊 统计: 有货 {len(available_list)} 款, 缺货 {len(sold_out_list)} 款")

    return available_list, sold_out_list


def main():
    print("=" * 60)
    print("🔍 Halo Cloud 库存查询 ($0.75/mo 产品)")
    print("   监控: JP Tokyo, SG Singapore")
    print("=" * 60)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n⏰ 查询时间: {timestamp}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("开始检查...")
        results = check_all_stock(page)
        available_list, sold_out_list = display_results(results)

        browser.close()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
