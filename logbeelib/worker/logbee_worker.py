'''
Created on Dec 5, 2017

@author: cloud
'''
import re,os,sys,time
import signal,logging,json
import threading
from threading import Lock
from concurrent.futures import ThreadPoolExecutor,wait

import helper
import settings
import broadcaster
from functools import reduce
from logging.config import dictConfigClass

logger = logging.getLogger()

work_job = None

class _field():
    Protocol         = None
    MSISDN           = None 
    IMSI             = None 
    MEID             = None 
    ESN              = None 
    ServiceOption    = None 
    BSID             = None 
    Subnet           = None 
    NAI              = None 
    PDSNIP           = None 
    SIP              = None 
    Sport            = None 
    DIP              = None 
    Dport            = None 
    Ltime            = None 
    MalwareName      = None 
    Filename         = None 
    FileLen          = None 
    FileMD5          = None 
    UserAgent        = None 
    ContentType      = None 
    ContentLength    = None
    HTTPCMD          = None 
    MSGType          = None 
    ProtocolFeatures = None 
    CityNumber       = None
#======== Add properties =======
    AlertFileName    = None
    EngineType       = None
    LogbeeTime       = None
    IndexName        = None

class __worker():
    def __init__(self,logbee_config,work_config_obj):
        self.logger = logger
        
        broadcaster_config = settings.get_broadcaster_config()
        redis_config = broadcaster_config.redis
        
        self.redis_host = redis_config.host
        self.redis_port = int(redis_config.port)
        self.redis_passwd = redis_config.password
        self.redis_database = redis_config.database
        self.redis_max_connections = int(redis_config.max_connections)
        self.redis_max_ele_in_queue = int(redis_config.max_ele_in_queue)
        
        self.logbee_workdir = re.split(r'(/){1,}$',logbee_config.workdir)[0]+"/"
        self.logbee_ealsticsearch_index = logbee_config.elasticsearch_index
        
        work_config = work_config_obj
        self.log_data_tpye = work_config.data_type
        self.log_work_name = work_config.work_name
        self.log_keep_source_file = work_config.keep_source_file
        self.log_compression_method = work_config.compression_method
        self.log_file_name_match = work_config.file_name_match
        self.log_alert_file_name_match=work_config.alert_file_name_match
        self.log_upload_method = work_config.upload_method
        self.log_source_dirs = work_config.source_dirs

        self.log_max_threads = int(work_config.max_threads)
        self.log_sample_file_storage_path = re.split(r'(/){1,}$',work_config.sample_file_storage_path)[0]+"/"
        self.log_split_symbol = work_config.split_symbol
        self.log_alert_cache_file_size = int(work_config.cache_file_size)
 
        self.work_thread_pool = None
        self.work_thread_dirs = []
        
        self.work_redis_connetion_pool = None
        
        self.timer_job_running = False
        
        self.thread_scan_file_number = work_config.scan_file_number #maximum file number in a thread.
        
        self.work_cache_file = self.logbee_workdir+self.log_work_name+"_fail_content.log"
        
        self.logbee_work_stringio = helper.logbeeIO(self.log_alert_cache_file_size)
        self.logbee_work_fileio = helper.logbeeFileIO(self.work_cache_file,self.log_alert_cache_file_size)
        
        self.work_job_term = False
        
    def make_thread_workdir(self):
        self.logger.info("Start create thread workdir.")
        for thread_workdir in range(self.log_max_threads):
            thread_workdir_name=self.logbee_workdir+self.log_work_name+"/"+str(thread_workdir)+"/"
            self.logger.debug("Start create dir: %s"%thread_workdir_name)
            os.makedirs(thread_workdir_name, exist_ok=True)
            self.work_thread_dirs.append(thread_workdir_name)
        
    def generate_thread_pool(self):
        self.logger.info("Start crate work thread pool")
        self.work_thread_pool = ThreadPoolExecutor(self.log_max_threads)
#     
    def generate_redis_connection_pool(self):
        self.logger.info("Start crate redis connection pool")
        self.work_redis_connetion_pool = broadcaster.redis_connection_pool(host=self.redis_host,port=self.redis_port,passwd=self.redis_passwd,database=self.redis_database,max_connetion_number=self.redis_max_connections)

    def to_send_redis_fail_fileio(self,line,lock):
        self.logger.debug("write content in python FileIO.")
        lock.acquire(1)
        if self.logbee_work_fileio.is_max_size:
            self.logger.warning("fail content file size bigger than setting. will loss alert content.")
            self.logbee_work_fileio.rewrite()
        self.logbee_work_fileio.write_line(line)
        lock.release()
        
    def to_send_redis_fail_srtingio(self,line,lock):
        self.logger.debug("write content in python StringIO.")
        lock.acquire(1)
        if self.logbee_work_stringio.is_max_size:
            self.logger.warning("fail content file size bigger than setting. will loss alert content.")
            self.logbee_work_stringio.rewrite()
        self.logbee_work_stringio.write_line(line)
        lock.release()
        
    def broadcast_to_redis_queue(self,key,message):
        self.logger.info("broadcast message to redis queue.key: [%s] message: [%s]"%(key,message))
        if self.work_redis_connetion_pool.llen(self.logbee_ealsticsearch_index) >= self.redis_max_ele_in_queue:
            self.logger.warning("The \"%s\" queue length is large than %d,last message will loss."%(key,self.redis_max_ele_in_queue))
            self.work_redis_connetion_pool.rpop(self.logbee_ealsticsearch_index)
            
        self.work_redis_connetion_pool.lpush(self.logbee_ealsticsearch_index,message)
            
    def uncompress_file(self,logfile,dist_path):
        self.logger.info("Start uncommpress file '%s' to '%s' ."%(logfile,dist_path))
        if self.log_compression_method == None:
            try:
                self.logger.debug("copy logfile to %s"%dist_path)
                helper.copy_file(logfile, dist_path)
            except Exception as e:
                helper.delete_file(logfile)
#                 common.upload_with_local(logfile, self.logbee_workdir+self.log_work_name+"_error/"+os.path.basename(logfile))
                self.logger.warning("Copy file fail.%s"%e)
        elif self.log_compression_method in settings.UNCOMPRESSION_FUNCTION.keys():
            try:
                settings.UNCOMPRESSION_FUNCTION[self.log_compression_method](logfile,dist_path)
            except Exception as e:
                helper.delete_file(logfile)
#                 common.upload_with_local(logfile, self.logbee_workdir+self.log_work_name+"_error/"+os.path.basename(logfile))
                self.logger.warning("uncompress logfile fail .%s"%e)
        else:
            self.logger.error("Unsupported commpression method: %s"%self.log_compression_method)
            
    def create_fields_csv(self,text_logfile,logfile):
        self.logger.info("Create fields csv.")
        try:
            self.logger.info("get logfile [%s] content.%s"%(logfile,text_logfile))
            log_lines = helper.read_lines(text_logfile)
            return [reduce(lambda x,y:x+self.log_split_symbol+y, field) for field in [[self.logbee_ealsticsearch_index,self.log_work_name,os.path.basename(logfile),helper.get_str_time(),line] for line in log_lines if line ]]
        except Exception as e:
            self.logger.error("get logfile [%s] content fail.%s \n %s"%(logfile,text_logfile,e))       
        return []
 
    def csv_to_json(self,content):
        field_keys=[
            "Protocol", 
            "MSISDN",
            "IMSI",
            "MEID",
            "ESN",
            "ServiceOption",
            "BSID",
            "Subnet",
            "NAI",
            "PDSNIP",
            "SIP",
            "Sport",
            "DIP",
            "Dport",
            "Ltime",
            "MalwareName",
            "Filename",
            "FileLen",
            "FileMD5",
            "UserAgent",
            "ContentType",
            "ContentLength",
            "HTTPCMD",
            "MSGType",
            "ProtocolFeatures",
            "CityNumber",
            "AlertFileName",
            "WorkName",
            "LogbeeTime",
            "IndexName",
        ]
        field_values = re.split('\%s'%self.log_split_symbol,content)
        if len(field_keys)==len(field_values):
            self.logger.info("csv_to_json pattern content success.")
            return json.dumps(dict(zip(field_keys,field_values)))
        else:
            self.logger.warning("csv_to_json pattern content fail")
            return 'None'
        
    def task(self,args):
        logfiles,dist_path,lock = args[0],args[1],args[2]

        for logfile in logfiles:
            self.logger.info("start work task.")
            self.uncompress_file(logfile, dist_path)
            text_logfiles = helper.scan_files(directory=dist_path,match=self.log_alert_file_name_match)
            for text_logfile in text_logfiles:
                ret = self.create_fields_csv(text_logfile,logfile)
                for line in ret:
                    try:
                        self.broadcast_to_redis_queue(self.logbee_ealsticsearch_index,line)
                    except Exception as e:
                        self.logger.warning("broadcast to redis fail.%s"%e)
                        #fileio or stringio
#                         self.to_send_redis_fail_srtingio(line, lock)
                        self.to_send_redis_fail_fileio(line, lock)
            if self.log_keep_source_file==True:
                self.logger.info("upload log file '%s' to :%s"%(os.path.basename(logfile),self.log_sample_file_storage_path))
                helper.upload_with_local(logfile, self.log_sample_file_storage_path+os.path.basename(logfile))
            else:
                self.logger.info("delete log file '%s'"%logfile)
                helper.delete_file(logfile)
#             self.logger.info(helper.scan_files(dist_path))
            self.logger.info("clean %s"%dist_path)
            for filename in os.listdir(dist_path):
                helper.delete_file(dist_path+filename)
#            common.shell_command("rm -rf %s*"%dist_path)
            
    def timer_job_for_fail(self,lock):
        self.logger.info("create a job for take send redis fail massage.")
#         job=threading.Thread(target=self.__work_for_fail_stringio,args=(lock,))
        job=threading.Thread(target=self.__work_for_fail_fileio,args=(lock,))
        job.start()
        
    def __work_for_fail_stringio(self,lock):
        self.logger.info("work for send redis fail content in StringIO.")
        self.timer_job_running = True
        lock.acquire(1)
        content_list = self.logbee_work_stringio.readlines()
        self.logger.debug("clean content in StringIO.")
        self.logbee_work_stringio.clear()
        lock.release()
        for content in content_list:
            if re.match('^%s%s%s(.){1,}'%(self.logbee_ealsticsearch_index,self.log_split_symbol,self.log_work_name),content):
                self.logger.info("send fail field log to redis.")
                try:
                    self.work_redis_connetion_pool.lpush(self.logbee_ealsticsearch_index,content)
                except Exception as e:
                    self.logger.warning("send to redis fail.%s"%e)
                    self.to_send_redis_fail_srtingio(content, lock)
        
        self.timer_job_running = False
        
    def __work_for_fail_fileio(self,lock):
        self.logger.info("work for send redis fail content in FileIO.")
        self.timer_job_running = True
        lock.acquire(1)
        content_list = self.logbee_work_fileio.readlines()
        self.logger.debug("clean content in StringIO.")
        self.logbee_work_fileio.clear()
        lock.release()
        for content in content_list:
            if re.match('^%s%s%s(.){1,}'%(self.logbee_ealsticsearch_index,self.log_split_symbol,self.log_work_name),content):
                self.logger.info("send fail field log to redis.")
                try:
                    self.work_redis_connetion_pool.lpush(self.logbee_ealsticsearch_index,content)
                except Exception as e:
                    self.logger.warning("send to redis fail.%s"%e)
                    self.to_send_redis_fail_fileio(content, lock)
        
        self.timer_job_running = False
        
    def __work_for_fail(self,lock):
        self.logger.info("work for send redis fail content.")
        if os.path.exists(self.work_cache_file) and os.path.isfile(self.work_cache_file):
            self.logger.info("scan fail log file %s"%self.work_cache_file)
            lock.acquire(1)
            content_list = helper.read_lines(self.work_cache_file)
            self.logger.debug("clean fail log file %s"%self.work_cache_file)
            self.logbee_work_fileio.clear()
#             common.write_file(self.work_cache_file)
#             os.system("echo ''>%s"%work_fail_log_dir)
            lock.release()
            for content in content_list:
                if re.match('^%s%s%s(.){1,}'%(self.logbee_ealsticsearch_index,self.log_split_symbol,self.log_work_name),content):
                    self.logger.info("send fail field log to redis.")
                    try:
                        self.work_redis_connetion_pool.lpush(self.logbee_ealsticsearch_index,content)
                    except Exception as e:
                        self.logger.warning("send to redis fail.%s"%e)
                        self.to_send_redis_fail_fileio(content, lock)
#                         self.to_send_redis_fail_srtingio(content, lock)
        
    def _executor(self,lock):
        
        for log_source_dir in self.log_source_dirs:
            self.logger.info("Start scan log source directory.%s"%log_source_dir)
            logfile_list = helper.scan_file_number(directory=log_source_dir, file_number=self.thread_scan_file_number*self.log_max_threads, match=self.log_file_name_match)
            
            self.logger.debug("Start allocate thread workdir.")
            if len(logfile_list) > self.log_max_threads:
                task_args = [ reduce(lambda x,y:[x[0]+y[0],x[1],lock],filter(lambda x:x[1]==self.work_thread_dirs[tid],map(lambda x:([x[1]],self.work_thread_dirs[x[0]%self.log_max_threads]),enumerate(logfile_list)))) for tid in range(self.log_max_threads)] 
            else:
                task_args = [[[logfile_name],self.work_thread_dirs[file_index%self.log_max_threads],lock] for file_index,logfile_name in  enumerate(logfile_list)] 

            if task_args:
                self.logger.info("Run task...")
                tasks = []
                for task_arg in task_args:
                    tasks.append(self.work_thread_pool.submit(self.task,task_arg))
                wait(tasks)
#                 with ThreadPoolExecutor(self.log_max_threads) as pool:
#                     pool.map(self.task,task_args)
                
    def run_excutor(self):
        lock = Lock()
        
        self.generate_thread_pool()
        self.generate_redis_connection_pool()
        self.make_thread_workdir()
        self.__work_for_fail(lock)
        
#         self._executor(lock)
        s_time = time.time()
        while not self.work_job_term:
            self._executor(lock)
            if time.time() >= (s_time+1800) and not self.timer_job_running:
                s_time=time.time()
                self.timer_job_for_fail(lock)
    
    def close(self):
        self.work_job_term = True
        
        self.work_thread_pool.shutdown()
        while threading.active_count()>1:
            logger.info("current thread number. (%s)"%threading.active_count())
            time.sleep(1)
#        self.logbee_work_stringio.save_to_file(self.work_cache_file)
        
        logger.info("close logbee string io...")
        self.logbee_work_stringio.close()
        logger.info("close logbee file io...")
        self.logbee_work_fileio.close()
        
def end_of_job(sig,frame):
    logger.warn("stop job ...")

    work_job.close()        
    sys.exit(0)
    
def runworker(logbee_config,work_config):
    
    logbee_workdir = re.split(r'(/){1,}$',logbee_config.workdir)[0]+"/"
    logbee_logdir = re.split(r'(/){1,}$',logbee_config.logdir)[0]+"/"
    
    signal.signal(signal.SIGUSR1, end_of_job)

    work_name = work_config.work_name
    
    logfilename =logbee_logdir+"logbee-"+work_name+".log"
    if logger.handlers:
        logger.handlers = []
        
    work_logging_config=settings.get_logging_config()
    
    work_logging_config["handlers"]["file"]["filename"] = logfilename
    dictConfigClass(work_logging_config).configure()
    
    logger.debug("check work directory.")
    if not os.path.exists(logbee_workdir+work_name):
        logger.info("Try to create %s work directory:%s"%(work_name,logbee_workdir+work_name))
        os.makedirs(logbee_workdir+work_name)
    else:
        logger.warning("Work directory '%s' is already exist. now recreate it."%(logbee_workdir+work_name))
        try:
            helper.delete_file(logbee_workdir+work_name)
            os.makedirs(logbee_workdir+work_name)
        except Exception as e:
            logger.error("recreate work directory fail.\n%s"%e)
            sys.exit(1)
            
    work_cache_file = logbee_workdir+work_name+"_fail_content.log"
    logger.info("start create cache file: %s"%work_cache_file)
    try:
        helper.make_file(work_cache_file)
    except Exception as e:
        logger.error("can't create cache file: %s"%work_cache_file)
        logger.error(e)
        sys.exit(1)

    logger.info("Start run logbee work: %s"%work_name)
    global work_job
    work_job = __worker(logbee_config,work_config)
    work_job.run_excutor()

if __name__ == '__main__':
    pass
