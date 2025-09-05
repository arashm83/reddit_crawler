from playwright.async_api import TimeoutError, BrowserContext

EMAIL = "example@gmail.com"
PASSWORD = "Password"

async def login(contex: BrowserContext, email= EMAIL, password= PASSWORD):
    try:
        page = await contex.new_page()
        await page.goto("https://reddit.com/login", wait_until="domcontentloaded")
        await page.fill("input[name=username]", email)
        await page.fill("input[name=password]", password)
        await page.click("button[type=button]")
        await page.wait_for_selector("div[class='ps-lg gap-xs flex items-center justify-end']")
        await contex.storage_state(path="state.json")

    except TimeoutError as e:
        print(f"login failed {e}")
    finally:
        await page.close()

async def is_logged_in(context: BrowserContext):
    try:
        page = await context.new_page()
        await page.goto("https://www.reddit.com", wait_until="domcontentloaded")

        await page.wait_for_selector("input[type=text]", timeout=10000)
        await page.close()
        return True
    except TimeoutError:
        await page.close()
        return False
    finally:
        await page.close()