'''
Created on May 3, 2018

@author: cloud
'''
import logging

logger = logging.getLogger()

class LogbeeBaseConfiguration(dict):
    '''logbee base configuration object'''
    def __init__(self,*args,**kwargs):
        super(LogbeeBaseConfiguration,self).__init__(*args,**kwargs)
            
    def __setattr__(self, key,value):
#         self.__dict__[key]=value
#         object.__setattr__(self,key,value)
        self[key]=value
        
    def __getattr__(self,key):
        value = self[key]
        if isinstance(value, dict):
            value = LogbeeBaseConfiguration(value)
        return value
     
    def __getattribute__(self,key):
        return super(LogbeeBaseConfiguration,self).__getattribute__(key)
    
    def __str__(self):
        return '<LogbeeBaseConfiguration >'
    
    @property
    def default_config(self):
        raise NotImplementedError("'default_config'  is not implemented.")
    
    @property
    def config_types(self):
        raise NotImplementedError("'config_types' is not implemented.")
    
    def __config_setter__(self,key,value):
        if isinstance(value, self.config_types[key]):
            self[key] = value
        else:
            logger.warn("invalid configuration '%s = %s',will use default: '%s'"%(key,value,self.default_config[key]))
            self[key] = self.default_config[key]
            
    def __call__(self,config_obj):
        _=[ self.__config_setter__(key, config_obj.get(key)) if key in config_obj.keys() else self.__config_setter__(key, self.default_config[key] ) for key in  self.default_config ]
        return self


class LogbeeConfiguration(LogbeeBaseConfiguration):
    """logbee configuration object"""
    def __init__(self,*args,**kwargs):
        super(LogbeeConfiguration,self).__init__(*args,**kwargs)
    
    def __str__(self):
        return '<LogbeeConfiguration object at %s>'%hex(id(self))
    
    @property
    def default_config(self):
        default_config = {
            "workdir":"/var/lib/logbee",
            "logdir":"/var/log/logbee",
            "elasticsearch_index": "logbee",
            }
        
        return default_config
    
    @property
    def config_types(self):
        config_types={
            "workdir":(str,),
            "logdir":(str,),
            "elasticsearch_index":(str,),
            }
        return config_types
    
class BroadcasterConfiguration(LogbeeBaseConfiguration):
    """Broadcaster  configuration object"""
    def __init__(self,*args,**kwargs):
        super(BroadcasterConfiguration,self).__init__(*args,**kwargs)
    
    def __str__(self):
        return '<BroadcasterConfiguration object at %s>'%hex(id(self))

    @property
    def default_config(self):
        default_config = {
            "redis":{
                "host":"localhost",
                "port":6379,
                "password":None,
                "database":0,
                "max_connections":10,
                "max_ele_in_queue":100000,
                },
            "ftp":{
                "host":"localhost",
                "port":21,
                "user":"ftp",
                "password":"ftp",
                }
            }
        return default_config
    
    @property
    def config_types(self):
        config_types={
            "redis":(dict,),
            "ftp":(dict,)
            }
        return config_types
            
    @property
    def redis(self):
        redis_config = RedisConfiguration()
        return redis_config(self["redis"])
    
    @property
    def ftp(self):
        ftp_config = FTPConfiguration()
        return ftp_config(self["ftp"])
    
class RedisConfiguration(LogbeeBaseConfiguration):
    """redis  configuration object"""
    def __init__(self,*args,**kwargs):
        super(RedisConfiguration,self).__init__(*args,**kwargs)
    
    def __str__(self):
        return '<RedisConfiguration object at %s>'%hex(id(self))

    @property
    def default_config(self):
        default_config = {
            "host":"localhost",
            "port":6379,
            "password":None,
            "database":0,
            "max_connections":10,
            "max_ele_in_queue":100000,
            }
        
        return default_config
    
    @property
    def config_types(self):
        config_types={
            "host":(str,),
            "port":(int,),
            "password":(str,type(None)),
            "database":(int,),
            "max_connections":(int,),
            "max_ele_in_queue":(int,),
            }
        return config_types

class FTPConfiguration(LogbeeBaseConfiguration):
    """ftp  configuration object"""
    def __init__(self,*args,**kwargs):
        super(FTPConfiguration,self).__init__(*args,**kwargs)
    
    def __str__(self):
        return '<FTPConfiguration object at %s>'%hex(id(self))

    @property
    def default_config(self):
        default_config = {
            "host":"localhost",
            "port":21,
            "user":"ftp",
            "password":"ftp",
            "timeout":-999
            }
        
        return default_config
    
    @property
    def config_types(self):
        config_types={
            "host":(str,),
            "port":(int,),
            "user":(str,),
            "password":(str,),
            "timeout":(int,)
            }
        return config_types
    
class WorkConfiguration(LogbeeBaseConfiguration):
    """work configuration object"""
    def __init__(self,*args,**kwargs):
        super(WorkConfiguration,self).__init__(*args,**kwargs)
    
    def __str__(self):
        return '<LogbeeWorkConfiguration object at %s>'%hex(id(self))
    
    @property
    def default_config(self):
        default_config = {
            "work_name":"logbee-work",
            "keep_source_file":False,
            "upload_method":"local",
            "sample_file_storage_path":"/home/SampleFile",
            "compression_method":None,
            "file_name_match": None,
            "alert_file_name_match":None,
            "source_dirs":["/var/log/logbee"],
            "max_threads":3,
            "data_type":"csv",
            "split_symbol":"|",
            "cache_file_size":10485760,
            "scan_file_number":50,
            }
        
        return default_config
    
    @property
    def config_types(self):
        config_types = {
            "work_name":(str,),
            "keep_source_file":(bool,),
            "upload_method":(str,),
            "sample_file_storage_path":(str,),
            "compression_method":(type(None),str),
            "file_name_match":(type(None),str),
            "alert_file_name_match":(type(None),str),
            "source_dirs":(list,),
            "max_threads":(int,),
            "data_type":(str,),
            "split_symbol":(str,),
            "cache_file_size":(int,),
            "scan_file_number":(int,),
            }
        return config_types

if __name__=="__main__":
    pass

