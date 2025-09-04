from bs4 import BeautifulSoup
from playwright.async_api import BrowserContext, TimeoutError, Page
from typing import List, Dict, Optional, Any

async def get_posts(subreddit: str, context: BrowserContext, page: Optional[Page] = None) -> List[Dict[str, Any]]:
    page_created = False
    if page is None or page.is_closed():
        page = await context.new_page()
        page_created = True
    posts_data = []
    try:
        await page.goto(f"https://www.reddit.com/r/{subreddit}/new/?feedViewType=compactView", wait_until="load")
        for i in range(2):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(5000)
    except TimeoutError as e:
        print(f"[get_posts] Timeout error fetching posts from {subreddit}: {e}")
    
    try:
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        posts = soup.find_all("shreddit-post")
        for post in posts:
            posts_data.append({
                "id": post.get("id", ""),
                "title": post.get("post-title", ""),
                "author": post.get("author", ""),
                "author_id": post.get("author-id", ""),
                "post_type": post.get("post-type", ""),
                "subreddit": post.get("subreddit-name", ""),
                "url": post.get("permalink", ""),
                "score": post.get("score", "")
            })
    except Exception as e:
        print(f"[get_posts] Error fetching posts from {subreddit}: {e}")
    finally:
        if page_created:
            await page.close()
    return posts_data

async def get_posts_details(
    url: str, 
    context: BrowserContext,
    page: Optional[Page] = None
) -> Optional[Dict[str, Any]]:
    page_created = False
    if page is None or page.is_closed():
        page = await context.new_page()
        page_created = True

    def safe_attr(element, attr):
        return element[attr].strip() if element and element.has_attr(attr) else ""

    def get_content(post: BeautifulSoup) -> str:
        text = post.find("div", class_="text-neutral-content")
        if not text:
            return ""
        texts = text.find_all("p")
        return "\n".join([line.get_text().strip() for line in texts])

    def get_comments(soup: BeautifulSoup) -> List[Dict[str, Any]]:
        comments = []
        for comment in soup.find_all("shreddit-comment"):
            content_type = comment.get("content-type", "")
            if content_type != "text":
                continue
            text_div = comment.find("div", class_="py-0")
            if not text_div:
                continue
            texts = text_div.find_all("p")
            content = "\n".join([text.get_text().strip() for text in texts])
            comments.append({
                "id": comment.get("thingid", ""),
                "post_id": comment.get("postid", ""),
                "author": comment.get("author", ""),
                "parent_id": comment.get("parentid", ""),
                "content_type": content_type,
                "content": content
            })
        return comments

    try:
        await page.goto(f"https://www.reddit.com{url}", wait_until="load")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(3000)
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        post = soup.find("shreddit-post")
        if not post:
            print(f"[get_posts_details] No post found at {url}")
            return None
        imgs = [
            img.get("src", "").strip() or img.get("data-lazy-src", "").strip()
            for img in post.find_all("img", class_="media-lightbox-img")
            if img.get("src") or img.get("data-lazy-src")
        ]
        video_elem = post.find("shreddit-player-2")
        post_details = {
            "content": get_content(post),
            "imgs": imgs,
            "video": safe_attr(video_elem, "src") if video_elem else None,
            "comments": get_comments(soup)
        }
        return post_details
    except Exception as e:
        print(f"[get_posts_details] Error fetching post details from {url}: {e}")
        return None
    finally:
        if page_created:
            await page.close()







