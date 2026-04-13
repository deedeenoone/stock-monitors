#!/usr/bin/env python3
"""
Halo Cloud Stock Monitor v1.0
- Monitors $0.75/mo products in JP and SG regions
- Notifies on status changes via Telegram
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

PRODUCT_PAGES = {
    "jp_standard": {
        "name": "JP Tokyo Standard VPS",
        "url": "https://my.halocloud.net/index.php?rp=/store/tokyo-jp-standard-vps",
    },
    "sg_standard": {
        "name": "SG Singapore Standard VPS",
        "url": "https://my.halocloud.net/index.php?rp=/store/singapore-sg-standard-vps",
    }
}

# State file
STATE_FILE = Path("/root/.openclaw/workspace/.halo-stock-state.json")

# ============== State Management ==============
def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {}

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
def check_page_products(page, page_info):
    """Check all $0.75/mo products on a page"""
    results = {}

    try:
        page.goto(page_info["url"], timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        html = page.content()

        # Extract product cards with name, price, stock
        product_blocks = re.findall(
            r'<h4[^>]*>([^<]+)</h4>.*?<p[^>]*>.*?\$(\d+\.?\d*)/mo.*?</p>.*?(\d+)\s+(?:available|in stock)',
            html, re.I | re.S
        )

        for name, price, count in product_blocks:
            if float(price) == 0.75:
                pid = f"{page_info['name'].split()[0].lower()}-{name.strip().lower().replace(' ', '-')}"
                results[pid] = {
                    "name": name.strip(),
                    "price": f"${price}/mo",
                    "region": page_info["name"].split()[0],
                    "stock": int(count)
                }

    except Exception as e:
        print(f"   ❌ {page_info['name']}: {e}")

    return results

def check_all_stock(page):
    """Check stock for all regions"""
    results = {}

    for page_key, page_info in PRODUCT_PAGES.items():
        print(f"   Checking: {page_info['name']}...")
        page_results = check_page_products(page, page_info)
        results.update(page_results)
        time.sleep(2)

    return results

# ============== Display Results ==============
def format_product_link(pid, info):
    """Generate product info string"""
    name = info["name"]
    region = info["region"]
    url = PRODUCT_PAGES[[k for k, v in PRODUCT_PAGES.items() if v['name'].startswith(region)][0]]["url"]
    return f'{region} {name}'

def display_results(results):
    """Display stock results"""
    available_list = []
    sold_out_list = []

    for pid, info in results.items():
        region = info["region"]
        name = info["name"]
        price = info["price"]
        stock = info["stock"]

        if stock > 0:
            available_list.append(f"   ✅ {region} {name} ({price}) - {stock} in stock")
        else:
            sold_out_list.append(f"   ❌ {region} {name} ({price}) - Sold Out")

    print()
    if available_list:
        print("[In Stock - $0.75/mo]")
        for item in available_list:
            print(item)

    if sold_out_list:
        print("\n[Sold Out - $0.75/mo]")
        for item in sold_out_list:
            print(item)

    return available_list, sold_out_list

# ============== Main Program ==============
def run_monitor(loop=False, interval=300, headless=True):
    print("=" * 60)
    print("🚀 Halo Cloud Stock Monitor v1.0 ($0.75/mo products)")
    print(f"   Regions: JP Tokyo, SG Singapore")
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
                available_list, sold_out_list = display_results(current_state)

                total_available = len(available_list)
                total_sold_out = len(sold_out_list)

                print(f"\n📊 Stats: {total_available} in stock, {total_sold_out} sold out")

                # Check for status changes and notify
                newly_available = []
                for pid, info in current_state.items():
                    if info["stock"] > 0:
                        was_stock = last_state.get(pid, {}).get("stock", 0)
                        if was_stock == 0:
                            newly_available.append(f"• {info['region']} {info['name']} ({info['price']}) - {info['stock']} in stock")

                if newly_available:
                    message = "🚨 <b>Halo Cloud Restocked!</b>\n\n"
                    message += "$0.75/mo products just back in stock:\n"
                    for item in newly_available:
                        message += f"{item}\n"
                    message += f"\n⏰ Time: {timestamp}"
                    message += f"\n\n<a href='https://my.halocloud.net'>Buy Now →</a>"

                    print(f"\n📱 Sending Telegram notification...")
                    send_telegram(message)

                # Update state
                for pid, info in current_state.items():
                    last_state[pid] = {
                        "stock": info["stock"],
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
    parser = argparse.ArgumentParser(description="Halo Cloud Stock Monitor v1.0")
    parser.add_argument("--loop", "-l", action="store_true", help="Loop monitoring")
    parser.add_argument("--interval", "-i", type=int, default=300, help="Check interval (seconds)")
    parser.add_argument("--headful", action="store_true", help="Show browser")

    args = parser.parse_args()

    run_monitor(
        loop=args.loop,
        interval=args.interval,
        headless=not args.headful
    )
