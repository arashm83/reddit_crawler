from playwright.async_api import async_playwright, BrowserContext
from time import sleep
import asyncio
from login import login, is_logged_in
from bs4 import BeautifulSoup
from core import get_posts, get_posts_details
from db_manager import DbManager, init_db

subreddits = ["learnmachinelearning", "linux", "IndiaFragMarketplace"]

async def process_subreddit(contex: BrowserContext, subreddit: str, db: DbManager, sem: asyncio.Semaphore):
    async with sem:
        page = await contex.new_page()
        db_posts = await db.get_posts_id()
        try:
            posts = await get_posts(subreddit, contex, page)
        except Exception as e:
            print(f"[process_subreddit] Error fetching posts from {subreddit}: {e}")
            return
        for post in posts:
            try:
                if post["id"] in db_posts:
                    continue
                details = await get_posts_details(post["url"], contex, page)
                post.update(details)
            except Exception as e:
                print(f"[process_subreddit] Error fetching details for post {post['id']}: {e}")
                continue
            try:
                await db.add_post(post)
            except Exception as e:
                print(f"[process_subreddit] Error adding post {post['id']} to database: {e}")
                continue

async def main():
    sem = asyncio.Semaphore(3)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        contex = await browser.new_context(storage_state="state.json")

        tasks = [process_subreddit(contex, subreddit, DbManager(), sem) for subreddit in subreddits]
        await asyncio.gather(*tasks)

if __name__=="__main__":
    asyncio.run(init_db())
    asyncio.run(main())