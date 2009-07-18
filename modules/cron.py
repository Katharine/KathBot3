from __future__ import with_statement
import threading
import time
import inspect
import os
import traceback
import modules

JOB_RESOLUTION = 60 # How often we check why we're here.

class ClearCronJob(Exception): pass

class CronManager(threading.Thread):
    cron_jobs = None
    at_jobs = None
    running = True
    lock = None
   
    def __init__(self):
        threading.Thread.__init__(self)
        self.cron_jobs = []
        self.at_jobs = []
        self.lock = threading.Lock()
        self.running = True
        self.setDaemon(True)
        self.start()
    
    def run(self):
        logger.info("Starting thread")
        while self.running:
            self.handle_cron()
            self.handle_at()
            time.sleep(JOB_RESOLUTION)
        logger.info("Stopping thread.")
    
    def handle_cron(self):
        now = time.time()
        toclear = []
        with self.lock:
            for i in range(0, len(self.cron_jobs)):
                job = self.cron_jobs[i]
                if job.last_execution + job.interval <= now:
                    try:
                        job.last_execution = now
                        threading.Thread(target=job.handler, args=job.args, name="CronJob/%s" % job.module).start()
                    except ClearCronJob:
                        toclear.append(i)
                    except Exception, msg:
                        logger.error("Error running cronjob for %s: %s" % (job.module, traceback.format_exc()))
                    else:
                        logger.info("Ran cronjob for %s." % job.module)
            
            toclear.reverse() # So the indexes don't change on us.
            for i in toclear:
                del self.cron_jobs[i]
    
    def handle_at(self):
        now = time.time()
        with self.lock:
            while len(self.at_jobs) > 0 and self.at_jobs[0].at <= now:
                job = self.at_jobs.pop(0)
                try:
                    if job.module in modules.mods:
                        threading.Thread(target=job.handler, args=job.args, name="AtJob/%s" % job.module).start()
                except Exception, msg:
                    logger.error("Error running cronjob for %s: %s" % (job.module, traceback.format_exc()))
    
    def add_at(self, module, at, handler, args):
        job = AtJob(module=module, at=at, handler=handler, args=args)
        with self.lock:
            for i in range(0, len(self.at_jobs)):
                if at < self.at_jobs[i].at:
                    self.at_jobs[i:i] = [job]
                    break
            else:
                self.at_jobs.append(job)
        logger.info("Added at job for %s" % module)
    
    def add_cron(self, module, period, handler, args):
        job = CronJob(module=module, period=period, handler=handler, args=args)
        with self.lock:
            self.cron_jons.append(job)
        logger.info("Added cron job for %s" % module)

manager = None
            
def add_cron(period, handler, *args):
    module = get_calling_module()
    manager.add_cron(module, period, handler, args)

def add_at(at, handler, *args):
    module = get_calling_module()
    manager.add_at(module, at, handler, args)

def get_calling_module():
    record = inspect.stack()[2][1]
    filename = os.path.split(record)
    if filename[1].startswith('__init__.py'):
        filename = os.path.split(filename[0])
    
    module = filename[1].split('.')[0]
    
    return module

def init():
    global manager
    manager = CronManager()
    add_hook('unloaded', module_unloaded)

def shutdown():
    manager.running = False

def module_unloaded(module):
    with manager.lock:
        for i in range(len(manager.cron_jobs) - 1, -1, -1):
            if manager.cron_jobs[i].module == module:
                del manager.cron_jobs[i]
        
        for i in range(len(manager.at_jobs) - 1, -1, -1):
            if manager.at_jobs[i].module == module:
                del manager.at_jobs[i]

class CronJob(object):
    def __init__(self, module='', period=0, handler=None, args=()):
        self.module = module
        self.period = period
        self.handler = handler
        self.args = args or ()

class AtJob(object):
    def __init__(self, module='', at=0, handler=None, args=()):
        self.module = module
        self.at = at
        self.handler = handler
        self.args = args or ()