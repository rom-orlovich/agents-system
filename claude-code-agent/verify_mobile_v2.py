import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        # iPhone 12 Pro viewport
        iphone_12 = p.devices['iPhone 12 Pro']
        browser = await p.chromium.launch()
        context = await browser.new_context(**iphone_12)

        # Create artifacts directory
        os.makedirs("mobile_audit_artifacts", exist_ok=True)

        # ==========================================
        # 1. New Dashboard (Vite)
        #Routes: /, /analytics, /ledger, /webhooks, /chat, /registry
        # ==========================================
        new_dashboard_routes = [
            ("/", "overview"),
            ("/analytics", "analytics"),
            ("/ledger", "ledger"),
            ("/webhooks", "webhooks"),
            ("/chat", "chat"),
            ("/registry", "registry")
        ]

        print("--- Checking New Dashboard ---")
        page_new = await context.new_page()

        for route, name in new_dashboard_routes:
            url = f"http://localhost:5173{route}"
            print(f"Navigating to {url} ...")
            try:
                await page_new.goto(url, wait_until="networkidle", timeout=30000)
                # Wait a bit for animations or data fetch
                await page_new.wait_for_timeout(1000)
                screenshot_path = f"mobile_audit_artifacts/new_dashboard_{name}.png"
                await page_new.screenshot(path=screenshot_path)
                print(f"Saved {screenshot_path}")
            except Exception as e:
                print(f"Error checking New Dashboard {name}: {e}")

        # ==========================================
        # 2. Old Dashboard (Static + JS)
        # Tabs: overview, analytics, tasks, webhooks, chat
        # ==========================================
        old_dashboard_tabs = [
            "overview",
            "analytics",
            "tasks",
            "webhooks",
            "chat"
        ]

        print("\n--- Checking Old Dashboard ---")
        page_old = await context.new_page()
        base_url = "http://localhost:8000/static/index.html"

        try:
            print(f"Navigating to {base_url} ...")
            await page_old.goto(base_url, wait_until="networkidle", timeout=30000)

            for tab in old_dashboard_tabs:
                print(f"Switching to tab: {tab}")
                # Use JS to switch tabs to avoid menu interaction issues on mobile
                await page_old.evaluate(f"app.switchTab('{tab}')")
                # Wait for potential rendering/rendering transition
                await page_old.wait_for_timeout(1000)

                screenshot_path = f"mobile_audit_artifacts/old_dashboard_{tab}.png"
                await page_old.screenshot(path=screenshot_path)
                print(f"Saved {screenshot_path}")

        except Exception as e:
            print(f"Error checking Old Dashboard: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
