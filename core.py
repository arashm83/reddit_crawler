from bs4 import BeautifulSoup
from playwright.async_api import BrowserContext, TimeoutError, Page
from typing import List, Dict, Optional, Any
import re

async def get_posts(subreddit: str, context: BrowserContext, db_posts: set[str], page: Optional[Page] = None, post_count: int = 50) -> List[Dict[str, Any]]:
    page_created = False
    if page is None or page.is_closed():
        page = await context.new_page()
        page_created = True

    def get_page_posts(html: str):
        posts_data = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            posts = soup.find_all("shreddit-post")
            
            for post in posts:
                if post.get("id", "") in db_posts:
                    continue
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
            print(f"[get_page_posts] Error fetching posts from {subreddit}: {e}")

        return posts_data
    
    
    try:
        await page.goto(f"https://www.reddit.com/r/{subreddit}/new/?feedViewType=compactView", wait_until="load")
        new_posts = get_page_posts(await page.content())
        visited_urls = set()
        res_urls = []
        page.on("response", lambda res: res_urls.append(res.url) if re.match(r"https://www.reddit.com/svc/shreddit/community-more-posts/new/.*", res.url) and not res.url in visited_urls else None)
        while len(new_posts) <= post_count:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            await page.wait_for_timeout(5000)
            if not res_urls:
                break
            url = res_urls.pop()
            if url not in visited_urls:
                visited_urls.add(url)
                await page.goto(url, wait_until="load")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(5000)
                new_posts.extend(get_page_posts(await page.content()))

        print(f"found {len(new_posts)} new posts for {subreddit}")

    except TimeoutError as e:
        print(f"[get_posts] Timeout error fetching posts from {subreddit}: {e}")
    
    finally:
        if page_created:
            await page.close()
    return new_posts

async def get_posts_details(
    url: str, 
    contex: BrowserContext,
    post_type: str,
    page: Optional[Page] = None
) -> Optional[Dict[str, Any]]:
    page_created = False
    if page is None or page.is_closed():
        page = await contex.new_page()
        page_created = True

    def safe_attr(element, attr):
        return element[attr].strip() if element and element.has_attr(attr) else ""

    def get_content(post: BeautifulSoup) -> str:
        content = post.find("div", class_="text-neutral-content")
        if not content:
            return ""
        texts = content.find_all("p")
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
    
    def get_images(post: BeautifulSoup):
        imgs =  [
            img.get("src", "").strip() or img.get("data-lazy-src", "").strip()
            for img in post.find_all("img", class_="media-lightbox-img")
            if img.get("src") or img.get("data-lazy-src")
        ]
        content = post.find('div', class_='text-neutral-content')
        if content:
            multi_media_imgs = [
                figure.a['href'] for figure in content.find_all('figure', class_="rte-media")
            ]
        else:
            multi_media_imgs = []

        return imgs + multi_media_imgs

    def get_video(post: BeautifulSoup):
        video_elem = post.find("shreddit-player-2")
        return safe_attr(video_elem, "src") if video_elem else None

    try:
        await page.goto(f"https://www.reddit.com{url}", wait_until="load")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(5000)
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        post = soup.find("shreddit-post")
        if not post:
            print(f"[get_posts_details] No post found at {url}")
            return None
        
        post_details = {
            "content": get_content(post),
            "imgs": get_images(post),
            "video": get_video(post),
            "comments": get_comments(soup)
        }

        if post_type=='crosspost' or post_type=='link':
            original_post_link = post.get('content-href', '')
            if original_post_link:
                post_details['content'] = post_details['content'].strip() + f'\nOriginal post: https://www.reddit.com{original_post_link}'


        return post_details
    except Exception as e:
        print(f"[get_posts_details] Error fetching post details from {url}: {e}")
        return None
    finally:
        if page_created:
            await page.close()







