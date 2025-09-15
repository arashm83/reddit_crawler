from random import randrange
from playwright.async_api import async_playwright, BrowserContext
import asyncio
from login import login, is_logged_in
from core import get_posts, get_posts_details
from db_manager import DbManager, init_db
import schedule
from datetime import datetime
from time import sleep
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(),
              logging.FileHandler("app.log")]
)

subreddits = ["learnmachinelearning", "linux", "IndiaFragMarketplace"]

async def process_subreddit(contex: BrowserContext, subreddit: str, db: DbManager, sem: asyncio.Semaphore):
    async with sem:
        await db.load_cache()
        page = await contex.new_page()
        try:
            posts = await get_posts(subreddit, contex, db.posts, page)
        except Exception as e:
            logging.error(f"[process_subreddit] Error fetching posts from {subreddit}: {e}")
            return
        for post in posts:
            try:
                if post["id"] in db.posts:
                    continue
                details = await get_posts_details(post["url"], contex, post["post_type"], page)
                post.update(details)
            except Exception as e:
                logging.error(f"[process_subreddit] Error fetching details for post {post['id']}: {e}")
                continue
            try:
                await db.add_post(post)
            except Exception as e:
                logging.error(f"[process_subreddit] Error adding post {post['id']} to database: {e}")
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

        await browser.close()

def job():
    logging.info(f"running at {datetime.now()}")
    
    asyncio.run(init_db())
    asyncio.run(main())

def schedule_time(start_hour=9, end_hour=22):
    schedule.clear("random_runs")
    run_times = []
    current_hour = start_hour
    current_minute = randrange(0, 60)
    run_times.append((current_hour, current_minute))

    while True:
        delta = randrange(25, 31)
        current_minute += delta
        if current_minute >= 60:
            current_hour += current_minute // 60
            current_minute = current_minute % 60
        if current_hour >= end_hour:
            break
        run_times.append((current_hour, current_minute))

    random_hours = [h for h, m in run_times]
    random_minutes = [m for h, m in run_times]

    for i in range(len(random_hours)):
        run_time = f"{random_hours[i]:02d}:{random_minutes[i]:02d}"
        logging.info(f"scheduled at {run_time}")
        schedule.every().day.at(run_time).do(job).tag("random_runs")

        
if __name__=="__main__":
    schedule.every().day.at("09:00").do(schedule_time)
    schedule_time()
    job()
    while True:
        schedule.run_pending()
        sleep(60)