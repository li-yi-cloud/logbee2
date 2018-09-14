#coding:utf-8
'''
Created on Dec 4, 2017

@author: cloud
'''
import redis

class __simple_redis_connection():
    def __init__(self,host,port,passwd,db,max_connetion_number):
        self.host   = host
        self.port   = port
        self.passwd = passwd if passwd else None
        self.db     = db
        self.socket_timeout  = 5 
        self.max_connections = max_connetion_number
    def connection(self):
        return redis.StrictRedis(host=self.host,port=self.port,password=self.passwd,db=self.db,socket_timeout=self.socket_timeout,max_connections=self.max_connections)

def redis_connection_pool(host,port,passwd,database,max_connetion_number):
    simple_connection_pool = __simple_redis_connection(host=host,port=port,passwd=passwd,db=database,max_connetion_number = max_connetion_number)
    
    return simple_connection_pool.connection()
