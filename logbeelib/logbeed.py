'''
Created on May 3, 2018

@author: cloud
'''
import re
import grp
import daemon
import lockfile
import signal,logging
import time,os,shutil,sys
import multiprocessing
import settings
from worker.logbee_worker import runworker

import helper
import broadcaster

logger = logging.getLogger()

def end_of_daemon(sig,frame):
    logger.info("stop work ...")
    logbee_workdir = re.split(r'(/){1,}$',settings.get_logbee_config().workdir)[0]+"/"
    for child_process  in multiprocessing.active_children():
        logger.info("stop work: %s pid: %s"%(child_process.name,child_process.pid))
        os.kill(child_process.pid,signal.SIGUSR1)
        
        max_times = 0
        while child_process in multiprocessing.active_children():
            logging.info("%s work status is %s"%(child_process.name,{True:"alive",False:"exited"}[child_process in multiprocessing.active_children()]))
            time.sleep(2)
            if max_times>=10:
                break
            max_times +=1

        logging.info("clean %s workdir"%child_process.name)
        
        shutil.rmtree(logbee_workdir+child_process.name)
    sys.exit(0)
            
def work_config_check(configs,work_config_obj):
    default_config = work_config_obj.default_config
    
    logger.debug("check work configuration.")
    for key in default_config:
        if key not in configs:
            logger.warning("The configuration '%s' is not set. Will use default value '%s'"%(key,default_config[key]))
        else:
            logger.debug("Found key \"%s\" in configuration file."%(key))

def get_work_config_obj():
    logger.debug("get work configuration object.")
    works_config = settings.get_works_config()
    configs={}
    for key in works_config:
        work_config_check(works_config[key],settings.WorkConfiguration())
        work_config_object = settings.WorkConfiguration()
        work_config_object(works_config[key])
        configs[work_config_object.work_name] = work_config_object
    return configs

def logbee_daemon(pidname,logbee_config):
    logger.info("create logbee daemon pid file")
    with open(pidname+".lock",'w+') as pid:
        pid.write(str(os.getpid()))
    worker_configs = get_work_config_obj()
    logger.info("start create work queue.")
    logbee_work_queue = {}
    for work_name in worker_configs:
        logbee_work = multiprocessing.Process(name=work_name,target=runworker,args=(logbee_config,worker_configs[work_name]))
        logbee_work.daemon=True
        logbee_work.start()
        logbee_work.join(1)
        logbee_work_queue[work_name] = logbee_work
    while True:
        time.sleep(5)
        logger.info("check work process status.")
        for work_name in logbee_work_queue:
#             logger.info("work status [%s]"%logbee_work_queue[work_name].is_alive())
            if logbee_work_queue[work_name].is_alive():
                logger.info("work %s is alive."%work_name)
            else:
                logger.error("work %s is crashed."%work_name)
                logbee_work = multiprocessing.Process(name=work_name,target=runworker,args=(logbee_config,worker_configs[work_name],))
                logbee_work.daemon=True
                logbee_work.start()
                logbee_work.join(1)
                logbee_work_queue[work_name] = logbee_work
     
def main(args):
    
    settings.init_env()
    logbee_config = settings.get_logbee_config()
    
    context = daemon.DaemonContext(
    working_directory=logbee_config.workdir,
    umask=0,
    pidfile=lockfile.FileLock(args["pidname"]),
    )
    
    context.signal_map = {
#     signal.SIGTERM: end_of_daemon,
#     signal.SIGHUP: 'terminate',
        signal.SIGUSR1: end_of_daemon,
    }

    mail_gid = grp.getgrnam('root').gr_gid
    context.gid = mail_gid
    
    logger_io = [handler.stream for handler in logger.handlers]
    context.files_preserve = logger_io
    
    with context:
        logbee_daemon(args["pidname"],logbee_config)
        
if __name__ == '__main__':
    settings.init_env()
    redis_config=settings.get_broadcaster_config().redis
    logbee_config=settings.get_logbee_config()
    rediscli=broadcaster.redis_connection_pool(redis_config.host,redis_config.port,redis_config.password,redis_config.database,redis_config.max_connections)
    for i in range(rediscli.llen(logbee_config.elasticsearch_index)):
        print(rediscli.rpop(logbee_config.elasticsearch_index))
    
    
    