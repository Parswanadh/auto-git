"""
Pipeline Run: Telegram Business Communication Bot + Stock Tracker

Uses x-ai/grok-4.1-fast as primary model via OpenRouter.
Must run with conda auto-git environment.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.langraph_pipeline.workflow_enhanced import run_auto_git_pipeline


IDEA = """
Build a complete Telegram-based Business Communication Bot with Storage and Stock Tracker
for multiple business owners. This is a production-grade system with a robust database.

CORE FEATURES:

1. Telegram Bot Interface (python-telegram-bot or aiogram):
   - /start — Register as a business owner with company name, city, contact
   - /add_product — Add product with name, category, SKU, unit price, initial stock
   - /sell — Record a sale: product, quantity, buyer city, payment method
   - /stock — View current stock levels with low-stock alerts
   - /report — Generate sales reports with filters
   - /add_user — Owner can add staff members with roles (admin, manager, viewer)
   - /help — Show all available commands with examples

2. Multi-Owner Support:
   - Each owner has isolated data (multi-tenant architecture)
   - Role-based access: admin (full), manager (sell + view), viewer (view only)
   - Owner can manage multiple stores/branches

3. Database (SQLite with proper schema):
   - owners table: id, telegram_id, company_name, city, phone, created_at
   - users table: id, telegram_id, owner_id, role, name, created_at
   - products table: id, owner_id, name, category, sku, unit_price, stock_qty, min_stock_alert, created_at
   - sales table: id, owner_id, product_id, quantity, total_price, buyer_city, payment_method, sold_by_user_id, created_at
   - cities table: id, owner_id, city_name (for categorizing sales by city)
   - categories table: id, owner_id, category_name (for product categorization)

4. Sales Tracking by City:
   - Record which city each sale was made in
   - Filter reports by city: /report --city Mumbai
   - City-wise sales comparison
   - Top-selling products per city

5. Stock Management:
   - Real-time stock tracking (auto-decrement on sale)
   - Low stock alerts (configurable threshold per product)
   - Stock history log
   - Bulk stock update via CSV

6. Reports & Analytics:
   - Daily/weekly/monthly sales summary
   - Revenue by product, by category, by city
   - Top N products by revenue and quantity
   - Export reports as CSV/PDF
   - Inline keyboard buttons for interactive report filters

7. Configuration:
   - config.yaml for bot token, database path, default thresholds
   - Environment variables for sensitive data (BOT_TOKEN)

8. Testing:
   - Comprehensive pytest suite
   - Test database CRUD operations
   - Test bot command handlers with mocked Telegram API
   - Test report generation logic
   - Test role-based access control

Project Structure:
  bot.py — Main bot entry point with command handlers
  database.py — SQLAlchemy/sqlite3 models and CRUD operations  
  models.py — Data models (Owner, Product, Sale, User, City, Category)
  reports.py — Report generation and formatting
  stock_manager.py — Stock tracking and alerts
  config.py — Configuration loading
  utils.py — Helper functions (formatting, validation)
  tests/ — pytest test suite
  config.yaml — Default configuration
  requirements.txt — Dependencies
  README.md — Setup and usage guide
"""


async def main():
    print("=" * 70)
    print("  Auto-GIT Pipeline: Telegram Business Bot + Stock Tracker")
    print("  Primary Model: x-ai/grok-4.1-fast (via OpenRouter)")
    print("=" * 70)
    
    try:
        result = await run_auto_git_pipeline(IDEA)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"\n{'='*70}\n  PIPELINE CRASHED: {type(e).__name__}: {e}\n{'='*70}")
        print(tb)
        # Also write to dedicated crash log
        with open("logs/pipeline_crash.txt", "w", encoding="utf-8") as f:
            f.write(f"CRASH: {type(e).__name__}: {e}\n\n{tb}")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("  Pipeline Complete!")
    if result:
        stage = result.get("current_stage", "unknown") if isinstance(result, dict) else "unknown"
        print(f"  Final Stage: {stage}")
        if isinstance(result, dict) and result.get("github_repo"):
            print(f"  GitHub Repo: {result['github_repo']}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
