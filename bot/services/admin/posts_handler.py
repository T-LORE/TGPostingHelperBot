from bot.database.requests import delete_all_posts, delete_post

async def delete_all_posts_from_queue():
    await delete_all_posts()

async def delete_post_from_queue(post_id: int):
    await delete_post(post_id)