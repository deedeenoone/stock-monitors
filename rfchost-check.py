#!/usr/bin/env python3
"""
RFCHost 库存查询脚本 v1.0
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
    "jp2_co": {
        "name": "JP2 China Optimization",
        "url": "https://payment.rfchost.com/index.php?rp=/store/jp-2-china-optimization-network",
        "products": {
            "jp2-co-micro": {"Name": "JP2-CO-Micro", "price": "$11.40/mo", "slug": "jp2-co-micro"},
            "jp2-co-mini": {"Name": "JP2-CO-Mini", "price": "$16.49/mo", "slug": "jp2-co-mini"},
            "jp2-co-standard": {"Name": "JP2-CO-Standard", "price": "$26.49/mo", "slug": "jp2-co-standard"},
            "jp2-co-advanced": {"Name": "JP2-CO-Advanced", "price": "$36.49/mo", "slug": "jp2-co-advanced"},
        }
    },
    "jp2_co_lite": {
        "name": "JP2 China Optimization Lite",
        "url": "https://payment.rfchost.com/index.php?rp=/store/jp-2-china-optimization-network-lite",
        "products": {
            "jp2-co-micro-lite": {"Name": "JP2-CO-Micro-Lite", "price": "$7.49/mo", "slug": "jp2-co-micro-lite"},
            "jp2-co-mini-lite": {"Name": "JP2-CO-Mini-Lite", "price": "$10.49/mo", "slug": "jp2-co-mini-lite"},
            "jp2-co-standard-lite": {"Name": "JP2-CO-Standard-Lite", "price": "$14.49/mo", "slug": "jp2-co-standard-lite"},
            "jp2-co-advanced-lite": {"Name": "JP2-CO-Advanced-Lite", "price": "$23.49/mo", "slug": "jp2-co-advanced-lite"},
            "jp2-co-max-lite": {"Name": "JP2-CO-Max-Lite", "price": "$32.49/mo", "slug": "jp2-co-max-lite"},
        }
    },
    "hk_t1": {
        "name": "HK Tier 1 International",
        "url": "https://payment.rfchost.com/index.php?rp=/store/hk-tier-1-international-optimization-network",
        "products": {
            "hk-t1ion-balance": {"Name": "HK-T1ION-Balance", "price": "$29.99/mo", "slug": "t1ion-unlimited-speed-balance"},
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
            "url": f"{page_info['url']}/{prod_info['slug']}"
        }


def parse_page_stock(html):
    """从页面HTML中提取所有产品的库存数量"""
    available_matches = re.findall(r'(\d+)\s+(?:available|in stock)', html, re.I)
    return [int(x) for x in available_matches]


def check_page_products(page, page_info):
    """检查某主页的所有产品库存"""
    results = {}
    
    try:
        page.goto(page_info["url"], timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        
        html = page.content()
        stock_list = parse_page_stock(html)
        
        for i, pid in enumerate(page_info["products"]):
            if i < len(stock_list):
                results[pid] = stock_list[i]
            else:
                results[pid] = 0  # 默认缺货
            
    except Exception as e:
        print(f"   ❌ {page_info['name']}: {e}")
        for pid in page_info["products"]:
            results[pid] = None
    
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


def format_product_link(pid):
    """生成产品超链接"""
    name = ALL_PRODUCTS[pid]["Name"]
    url = ALL_PRODUCTS[pid]["url"]
    return f'<a href="{url}">{name}</a>'


def display_results(results):
    """显示库存结果"""
    available_list = []
    sold_out_list = []
    
    for pid, stock in results.items():
        name = ALL_PRODUCTS[pid]["Name"]
        price = ALL_PRODUCTS[pid]["price"]
        link = format_product_link(pid)
        
        if stock and stock > 0:
            available_list.append(f"   ✅ {link} ({price}) - 剩余 {stock} 件")
        elif stock == 0:
            sold_out_list.append(f"   ❌ {link} ({price}) - 缺货")
        else:
            sold_out_list.append(f"   ⚠️ {link} ({price}) - 未知")
    
    print()
    if available_list:
        print("【有货产品】")
        for item in available_list:
            print(item)
    
    if sold_out_list:
        print("\n【缺货产品】")
        for item in sold_out_list:
            print(item)
    
    # 统计
    total_available = len(available_list)
    total_sold_out = len(sold_out_list)
    print(f"\n📊 统计: 有货 {total_available} 款, 缺货 {total_sold_out} 款")
    
    return available_list, sold_out_list


def main():
    print("=" * 60)
    print("🔍 RFCHost 库存查询")
    print(f"   产品数: {len(ALL_PRODUCTS)}")
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
