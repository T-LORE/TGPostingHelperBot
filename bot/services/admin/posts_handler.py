from bot.database.requests import delete_all_posts

async def delete_all_posts_from_queue():
    await delete_all_posts()