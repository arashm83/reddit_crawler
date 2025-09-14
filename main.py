from playwright.async_api import async_playwright, BrowserContext
import asyncio
from login import login, is_logged_in
from core import get_posts, get_posts_details
from db_manager import DbManager, init_db

subreddits = ["learnmachinelearning", "linux", "IndiaFragMarketplace"]

async def process_subreddit(contex: BrowserContext, subreddit: str, db: DbManager, sem: asyncio.Semaphore):
    async with sem:
        await db.load_cache()
        page = await contex.new_page()
        try:
            posts = await get_posts(subreddit, contex, db.posts, page)
        except Exception as e:
            print(f"[process_subreddit] Error fetching posts from {subreddit}: {e}")
            return
        for post in posts:
            try:
                if post["id"] in db.posts:
                    continue
                details = await get_posts_details(post["url"], contex, post["post_type"], page)
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
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(storage_state="state.json")

        success = await is_logged_in(context)
        if not success:
            await login(context)
        
        tasks = [process_subreddit(context, subreddit, DbManager(), sem) for subreddit in subreddits]
        await asyncio.gather(*tasks)
        
if __name__=="__main__":
    asyncio.run(init_db())
    asyncio.run(main())