import os
from datetime import datetime, timedelta, time

from bot.database.requests import get_latest_posts
from bot.misc.env_config_reader import settings

def create_file_if_not_exist(path):
    if os.path.isfile(path):
        return False
    
    database_dir = os.path.dirname(path)
    
    if not os.path.exists(database_dir):
        os.makedirs(database_dir)

    with open(path, 'a'):
        os.utime(path, None)

    return True

async def get_next_posts_datetime(posts_amount: int):
    posts = await get_latest_posts(start_post=0, posts_amount=1)
    if posts is None or len(posts) == 0:
        latest_date = datetime.now()
    else:
        post = posts[0]
        latest_date = datetime.now() if post is None else post["publish_date"]
    result_dates = []

    for _ in range(posts_amount):
        latest_date =  get_next_datetime_slot(latest_date)
        result_dates.append(latest_date)

    return result_dates
    
def get_next_datetime_slot(start_datetime: datetime):
    times = settings.post_timestamps.split(sep=",")
    format_data = "%H:%M"
    schedule_times = sorted([datetime.strptime(time.strip(), format_data).time() for time in times])

    current_time = start_datetime.time()

    for slot in schedule_times:
        if slot > current_time:      
            return datetime.combine(start_datetime.date(), slot)
        
    next_day = start_datetime.date() + timedelta(days=1)
    return datetime.combine(next_day, schedule_times[0])
