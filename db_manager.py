from sqlalchemy import String, ForeignKey, Integer, Column, JSON
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from typing import Dict, Any

Base = declarative_base()
engine = create_async_engine('sqlite+aiosqlite:///reddit.db')
AsyncSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class Post(Base):
    __tablename__ = "posts"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String, index=True)
    author_id = Column(String, index=True)
    post_type = Column(String, index=True)
    content = Column(String)
    imgs = Column(JSON)
    video = Column(String)
    subreddit = Column(String, index=True)
    url = Column(String, index=True)
    score = Column(Integer)
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"

    id = Column(String, primary_key=True, index=True)
    post_id = Column(String, ForeignKey("posts.id"), index=True)
    author = Column(String, index=True)
    content_type = Column(String)
    content = Column(String)
    parent_id = Column(String, ForeignKey("comments.id"), index=True, nullable=True)
    post = relationship("Post", back_populates="comments")

class DbManager:
    def __init__(self):
        self.posts = set()

    async def add_post(self, post_data: Dict[str, Any]) -> None:
        async with AsyncSessionLocal() as session:
            try:
                post = Post(
                    id=post_data["id"],
                    title=post_data.get("title"),
                    author=post_data.get("author"),
                    author_id=post_data.get("author_id"),
                    content=post_data.get("content"),
                    post_type=post_data.get("post_type"),
                    imgs=post_data.get("imgs"),
                    video=post_data.get("video"),
                    subreddit=post_data.get("subreddit"),
                    url=post_data.get("url"),
                    score=post_data.get("score"),
                )
                session.add(post)
                self.posts.add(post.id)

                comments = post_data.get("comments", [])
                for comment_data in comments:
                    comment = Comment(
                        id=comment_data["id"],
                        post_id=post.id,
                        author=comment_data.get("author"),
                        content_type=comment_data.get("content_type"),
                        content=comment_data.get("content"),
                        parent_id=comment_data.get("parent_id"),
                    )
                    session.add(comment)

                await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"[DbManager][add_post] Error: {e}")

    async def get_posts_id(self) -> set[str]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Post.id))
            return {row[0] for row in result.fetchall()}

    async def load_cache(self) -> None:
        self.posts = await self.get_posts_id()