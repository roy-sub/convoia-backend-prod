from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from hourly_tasks import hourly
import asyncio

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

class HourwiseSchedulerManager:
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

    def run_hourly_task(self):

        asyncio.run(hourly())

    def schedule_task(self, interval_minutes: int):

        try:
            self.scheduler.add_job(
                func=self.run_hourly_task,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id='hourly_task',
                name='Hourly Task',
                replace_existing=True
            )
            print(f"\nScheduled hourly task to run every {interval_minutes} minutes\n")
        except Exception as e:
            print(f"Error scheduling hourly task: {str(e)}")

    def shutdown(self):

        self.scheduler.shutdown()
        print("Hourwise Scheduler shut down")
