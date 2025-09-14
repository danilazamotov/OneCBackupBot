from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

class SchedulerService:
    def __init__(self, *, timezone: str, logger):
        self.tz = pytz.timezone(timezone)
        self.logger = logger
        self.sched = BackgroundScheduler(timezone=self.tz)

    def add_cron_job(self, func, cron_expr: str, id: str):
        self.logger.info(f"Adding cron job {id} -> {cron_expr}")
        trigger = CronTrigger.from_crontab(cron_expr, timezone=self.tz)
        self.sched.add_job(func, trigger=trigger, id=id, replace_existing=True)

    def start(self):
        self.logger.info("Starting scheduler")
        self.sched.start()

    def shutdown(self):
        self.logger.info("Shutting down scheduler")
        self.sched.shutdown(wait=False)
