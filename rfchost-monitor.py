#!/usr/bin/env python3
"""
RFCHost Stock Monitor v6.0
- Detects product availability and stock counts from storefront pages
- Displays stock count for each product
- Notifies only on status changes
"""

import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.error
import re
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# ============== Config ==============
TELEGRAM_BOT_TOKEN = "8690704672:AAFZBRHcULM2gDttZmwuHCExL4woWHN9hz8"
TELEGRAM_CHAT_ID = "1514702534"

# All products and their page mappings
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

# Flatten all products
ALL_PRODUCTS = {}
for page_key, page_info in PRODUCT_PAGES.items():
    for pid, prod_info in page_info["products"].items():
        ALL_PRODUCTS[pid] = {
            **prod_info,
            "page_key": page_key,
            "url": f"{page_info['url']}/{prod_info['slug']}"
        }

# State file
STATE_FILE = Path("/root/.openclaw/workspace/.rfchost-stock-state.json")

# ============== State Management ==============
def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {pid: {"available": 0, "last_check": None} for pid in ALL_PRODUCTS}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

# ============== Telegram Notification ==============
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8")).get("ok", False)
    except Exception as e:
        print(f"   ⚠️ Telegram notification failed: {e}")
        return False

# ============== Stock Check ==============
def parse_page_stock(html):
    """Extract all product stock counts from page HTML"""
    available_matches = re.findall(r'(\d+)\s+(?:available|in stock)', html, re.I)
    return [int(x) for x in available_matches]

def check_page_products(page, page_key, page_info):
    """Check all product statuses and stock for a given page"""
    results = {}
    
    try:
        page.goto(page_info["url"], timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        
        html = page.content()
        stock_list = parse_page_stock(html)
        
        # Match products in order
        for i, pid in enumerate(page_info["products"]):
            if i < len(stock_list):
                results[pid] = stock_list[i]
            else:
                results[pid] = None
            
    except Exception as e:
        print(f"   ❌ {page_info['name']}: {e}")
        for pid in page_info["products"]:
            results[pid] = None
    
    return results

def check_all_stock(page):
    """Check stock for all products"""
    results = {}
    
    for page_key, page_info in PRODUCT_PAGES.items():
        print(f"   Checking: {page_info['name']}...")
        page_results = check_page_products(page, page_key, page_info)
        results.update(page_results)
        time.sleep(2)
    
    return results

# ============== Display Results ==============
def format_product_link(pid):
    """Generate product hyperlink"""
    name = ALL_PRODUCTS[pid]["Name"]
    url = ALL_PRODUCTS[pid]["url"]
    return f'<a href="{url}">{name}</a>'


def display_results(results):
    """Display stock results"""
    available_list = []
    sold_out_list = []
    unknown_list = []
    
    for pid, stock in results.items():
        name = ALL_PRODUCTS[pid]["Name"]
        price = ALL_PRODUCTS[pid]["price"]
        link = format_product_link(pid)
        
        if stock is None:
            unknown_list.append(f"   ⚠️ {link} ({price}) - 未知")
        elif stock == 0:
            sold_out_list.append(f"   ❌ {link} ({price}) - 缺货")
        else:
            available_list.append(f"   ✅ {link} ({price}) - 剩余 {stock} 件")
    
    print()
    if available_list:
        print("[有货]")
        for item in available_list:
            print(item)
    
    if sold_out_list:
        print("\n[缺货]")
        for item in sold_out_list:
            print(item)
    
    if unknown_list:
        print("\n[未知状态]")
        for item in unknown_list:
            print(item)
    
    return available_list, sold_out_list, unknown_list

# ============== Main Program ==============
def run_monitor(loop=False, interval=300, headless=True):
    print("=" * 60)
    print("🚀 RFCHost Stock Monitor v6.0 (with stock count)")
    print(f"   Monitoring: {len(ALL_PRODUCTS)} products")
    print(f"   Check interval: {interval} seconds")
    print("=" * 60)
    
    last_state = load_state()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                '--no-sandbox',
                '--disable-gpu',
                '--disable-dev-shm-usage',
                '--disable-software-rasterizer',
                '--disable-gpu-compositing',
                '--no-zygote',
                '--single-process',
            ]
        )
        page = browser.new_page()
        
        try:
            while True:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{timestamp}] Checking stock...")
                
                current_state = check_all_stock(page)
                available_list, sold_out_list, unknown_list = display_results(current_state)
                
                # Count in-stock items
                total_available = sum(1 for s in current_state.values() if s and s > 0)
                total_sold_out = sum(1 for s in current_state.values() if s == 0)
                
                print(f"\n📊 统计: 有货 {total_available} 款, 缺货 {total_sold_out} 款")
                
                # Check for status changes and notify
                newly_available = []
                for pid, stock in current_state.items():
                    if stock and stock > 0:
                        was_stock = last_state.get(pid, {}).get("available", 0)
                        if was_stock == 0:
                            link = format_product_link(pid)
                            price = ALL_PRODUCTS[pid]["price"]
                            newly_available.append(f"• {link} ({price}) - 剩余 {stock} 件")
                
                if newly_available:
                    message = "🚨 <b>RFCHost 有货啦！</b>\n\n"
                    message += "刚补货的产品：\n"
                    for item in newly_available:
                        message += f"{item}\n"
                    message += f"\n⏰ Time: {timestamp}"
                    message += f"\n\n<a href='https://payment.rfchost.com'>立即购买 →</a>"
                    
                    print(f"\n📱 Sending Telegram notification...")
                    send_telegram(message)
                
                # Update state
                for pid, stock in current_state.items():
                    last_state[pid] = {
                        "available": stock if stock else 0,
                        "last_check": timestamp
                    }
                save_state(last_state)
                
                if loop:
                    print(f"\n⏰ Waiting {interval} seconds before next check...")
                    time.sleep(interval)
                else:
                    break
                    
        except KeyboardInterrupt:
            print("\n\n👋 Monitor stopped")
        finally:
            browser.close()

# ============== CLI ==============
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RFCHost Stock Monitor v6.0")
    parser.add_argument("--loop", "-l", action="store_true", help="Loop monitoring")
    parser.add_argument("--interval", "-i", type=int, default=300, help="Check interval (seconds)")
    parser.add_argument("--once", "-o", action="store_true", help="Single check")
    parser.add_argument("--headful", action="store_true", help="Show browser")
    
    args = parser.parse_args()
    
    run_monitor(
        loop=args.loop,
        interval=args.interval,
        headless=not args.headful
    )
