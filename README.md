# Stock Monitors

Automated stock monitoring scripts for various vendors. Checks product availability and sends notifications when items are back in stock.

## Scripts

### RFCHost Stock Monitor

Monitors RFCHost (https://payment.rfchost.com) for product availability.

**Files:**
- `rfchost-check.py` - One-time stock check
- `rfchost-monitor.py` - Continuous monitoring with Telegram notifications

**Usage:**
```bash
# One-time check
python rfchost-check.py

# Continuous monitoring (checks every 5 minutes by default)
python rfchost-monitor.py --loop

# With custom interval (e.g., every 60 seconds)
python rfchost-monitor.py --loop --interval 60

# Show browser (for debugging)
python rfchost-monitor.py --loop --headful
```

### Halo Cloud Stock Monitor

Monitors Halo Cloud (https://my.halocloud.net) for $0.75/mo VPS products in JP Tokyo and SG Singapore regions.

**Files:**
- `halo-check.py` - One-time stock check
- `halo-monitor.py` - Continuous monitoring with Telegram notifications

**Usage:**
```bash
# One-time check
python halo-check.py

# Continuous monitoring (checks every 5 minutes by default)
python halo-monitor.py --loop

# With custom interval (e.g., every 60 seconds)
python halo-monitor.py --loop --interval 60

# Show browser (for debugging)
python halo-monitor.py --loop --headful
```

## Requirements

- Python 3.8+
- Playwright (`pip install playwright && playwright install chromium`)
- Telegram Bot Token and Chat ID (configured in monitor scripts)

## Adding New Monitors

Simply add new vendor scripts to this repo following the naming convention:
- `[vendor]-check.py` - One-time check
- `[vendor]-monitor.py` - Continuous monitoring
