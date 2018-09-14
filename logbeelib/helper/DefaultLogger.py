#coding:utf-8
'''
Python logging module
@author: cloud
Date: 20171205
'''
import logging.handlers

class Logger(object):
    def __init__(self,filename,loglevel=3):
        format_dict={
                1 : logging.Formatter('%(asctime)s - %(filename)s [line:%(lineno)d] - %(levelname)s - %(message)s'),
                2 : logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
                }
        loglevel_dict={
                1:logging.NOTSET,
                2:logging.DEBUG,
                3:logging.INFO,
                4:logging.WARNING,
                5:logging.ERROR,
                6:logging.CRITICAL
                }
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        
        if self.logger.handlers:
            self.logger.handlers = []
            
        file_handler =logging.handlers.RotatingFileHandler(filename, mode='a', maxBytes=10485760, backupCount=5, encoding="UTF-8", delay=0)
        file_handler.setLevel(loglevel_dict[int(loglevel)])
        
#         console = logging.StreamHandler(sys.stdout)
#         console.setLevel(loglevel_dict[int(loglevel)])
        
        file_handler.setFormatter(format_dict[2])
#         console.setFormatter(format_dict[2]) 

        self.logger.addHandler(file_handler)
#         self.logger.addHandler(console)
    def getlogger(self):
        return self.logger
    def debug(self,message):
        self.logger.debug(message)
    def info(self,message):
        self.logger.info(message)
    def warning(self,message):
        self.logger.warning(message)
    def error(self,message):
        self.logger.error(message)
    def critical(self,message):
        self.logger.critical(message)
        
        

if __name__=="__main__":
    pass

