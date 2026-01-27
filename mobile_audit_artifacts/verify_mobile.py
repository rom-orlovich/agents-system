import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        # iPhone 13 Pro Max viewport
        iphone_13 = p.devices['iPhone 13 Pro Max']
        browser = await p.chromium.launch()
        context = await browser.new_context(**iphone_13)

        # --- Old Dashboard ---
        print("--- Testing Old Dashboard ---")
        page_old = await context.new_page()
        try:
            print("Visiting Overview...")
            await page_old.goto("http://localhost:8001/index.html")
            await page_old.wait_for_timeout(2000)
            await page_old.screenshot(path="old_dashboard_overview.png", full_page=True)

            tabs = ['analytics', 'tasks', 'webhooks', 'chat']
            for tab in tabs:
                print(f"Clicking tab {tab}...")
                try:
                    await page_old.click(f"button[data-tab='{tab}']")
                    await page_old.wait_for_timeout(1000)
                    await page_old.screenshot(path=f"old_dashboard_{tab}.png", full_page=True)
                except Exception as e:
                    print(f"Failed to click tab {tab}: {e}")

            # Toggle sidebar
            print("Toggling sidebar...")
            try:
                await page_old.click("#hamburger-btn")
                await page_old.wait_for_timeout(1000)
                await page_old.screenshot(path="old_dashboard_sidebar.png")
            except Exception as e:
                print(f"Failed to toggle sidebar: {e}")

        except Exception as e:
            print(f"Error checking old dashboard: {e}")
        finally:
            await page_old.close()

        # --- New Dashboard ---
        print("--- Testing New Dashboard ---")
        page_new = await context.new_page()

        routes = {
            "overview": "/",
            "analytics": "/analytics",
            "ledger": "/ledger",
            "webhooks": "/webhooks",
            "chat": "/chat",
            "registry": "/registry"
        }

        for name, route in routes.items():
            print(f"Visiting New Dashboard {name} ({route})...")
            try:
                await page_new.goto(f"http://localhost:5173{route}")
                await page_new.wait_for_timeout(2000) # Wait for load
                await page_new.screenshot(path=f"new_dashboard_{name}.png", full_page=True)
            except Exception as e:
                print(f"Error checking new dashboard route {route}: {e}")

        # Also try to find and toggle sidebar/menu in new dashboard if possible
        # I'll check Layout file next time if I can't find it, but let's just get the pages first.

        await page_new.close()
        await browser.close()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(run())
