from subprocess import call
from datetime import datetime, timedelta
import pytz
import time

ist = pytz.timezone('Asia/Kolkata')

def run_file():
    call(['python', 'main.py'])

def get_next_run_time():
    now = datetime.now(ist)
    next_run = now.replace(hour=8, minute=15, second=0, microsecond=0)
    if now >= next_run:
        next_run += timedelta(days=1)
    return next_run

while True:
    next_run = get_next_run_time()
    time_to_wait = (next_run - datetime.now(ist)).total_seconds()
    time.sleep(time_to_wait)
    print(f'now sleeping for {time_to_wait} will run program after then')
    print('NOW AWAKE!')
    run_file()
    
    # Wait for 60 seconds to avoid running multiple times if the script execution is very fast
    time.sleep(60)
    


