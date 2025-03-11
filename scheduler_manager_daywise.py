from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from daily_tasks import daily
import asyncio

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

class DaywiseSchedulerManager:
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

    def run_daily_task(self):

        asyncio.run(daily())

    def schedule_task(self, hour: int = 0, minute: int = 0):

        try:
            self.scheduler.add_job(
                func=self.run_daily_task,
                trigger=CronTrigger(hour=hour, minute=minute),
                id='daily_task',
                name='Daily Task',
                replace_existing=True
            )
            print(f"\nScheduled daily task to run at {hour:02d}:{minute:02d}\n")
        except Exception as e:
            print(f"Error scheduling daily task: {str(e)}")

    def shutdown(self):

        self.scheduler.shutdown()
        print("Daywise Scheduler shut down")
