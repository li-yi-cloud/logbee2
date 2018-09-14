import os
import helper
import codecs
import logging
from yaml import load
from logging.config import dictConfigClass
from settings.config import LogbeeConfiguration,WorkConfiguration,BroadcasterConfiguration

logger = logging.getLogger()
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

__conf_dir=os.getenv(key="LOGBEE_CONF_DIR", default=BASE_DIR+"/conf")

def init_env():
    global CONFIG
    global logbee_config
    global logging_config
    
    with codecs.open(__conf_dir+"/logbee.yaml",'r',"utf-8") as  config_open:
        CONFIG = load(config_open)
    
    logbee_config = LogbeeConfiguration()
    if "logbee"  not in CONFIG:
        logger.warn("logbee configuration is not set will use default.")
        logbee_config({})
    else:
        logbee_config(CONFIG["logbee"])
    
    logger.info("Initialize the operating environment.")
    if not os.path.exists(logbee_config["workdir"]):
        logger.warn("Work directory '%s' is not exist.now create it."%logbee_config["workdir"])
        os.makedirs(logbee_config["workdir"])
    if not os.path.exists(logbee_config["logdir"]):
        logger.warn("Log directory '%s' is not exist.now create it."%logbee_config["logdir"])
        os.makedirs(logbee_config["logkdir"])
        
    with codecs.open(__conf_dir+'/logging.yaml','r',"utf-8") as config_open:
        logging_config = load(config_open)
        logging_config.setdefault("version",1)
        logging_config["handlers"]["file"]["filename"]=logbee_config.logdir+"/"+logging_config["handlers"]["file"]["filename"]
        dictConfigClass(logging_config).configure()
    
def get_logbee_config():
    return logbee_config

def get_config():
    return CONFIG

def get_logging_config():
    return logging_config

def get_broadcaster_config():
    if "broadcaster" in CONFIG:
        broadcaster_config = BroadcasterConfiguration()
        return broadcaster_config(CONFIG["broadcaster"])
    else:
        return None

def get_works_config():
    if "works" in CONFIG:
        return CONFIG["works"]
    else:
        return None

UNCOMPRESSION_FUNCTION = {
    "tar.gz": helper.uncompress_tgz_file,
    "tgz": helper.uncompress_tgz_file,
    "zip": helper.uncompress_zip_file,
    }

__all__=["LogbeeConfiguration","WorkConfiguration","BroadcasterConfiguration"]

if __name__=="__main__":
    pass
    



