
import tarfile,zipfile,os,re,codecs,ftplib
import shutil,stat,time
import subprocess
from io import StringIO
from errors import OutListError
import logging

logger = logging.getLogger()

def shell_command(command):
    cm=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
    _,err=cm.communicate()
    return err

# compress_lib
def compress_tgz_file(tar_name,target_path):
    tar = tarfile.open(tar_name,"w:gz") 
    if os.path.isdir(target_path):
        for root,_,files in os.walk(target_path):  
            for file in files:  
                fullpath = os.path.join(root,file)  
                tar.add(fullpath)
    elif os.path.isfile(target_path):
        tar.add(target_path)
    tar.close()

def uncompress_tgz_file(tar_name,dist_path):
    try:  
        tar = tarfile.open(tar_name, "r:gz")  
        file_names = tar.getnames()  
        for file_name in file_names:  
            tar.extract(file_name, dist_path)  
        tar.close()  
    except Exception as e:  
        raise IOError(e)

def compress_zip_file(zip_name,target_path):
    czip = zipfile.ZipFile(zip_name,"w") 
    if os.path.isdir(target_path):
        for root,_,files in os.walk(target_path):  
            for file in files:  
                fullpath = os.path.join(root,file)  
                czip.write(fullpath, compress_type=zipfile.ZIP_LZMA)
    elif os.path.isfile(target_path):
        czip.write(target_path)
    czip.close()
    
def uncompress_zip_file(zip_name,dist_path):
    with zipfile.ZipFile(zip_name,"r") as zip_obj:
        zip_obj.extractall(dist_path)

def change_mod(filename):
    os.chmod(filename,stat.S_IRWXU|stat.S_IRWXG|stat.S_IRWXO)

def make_file(filename):
    if not os.path.exists(filename):
        os.mknod(filename)
    else:
        pass
    
def delete_file(filename):
    if os.path.isfile(filename):
        os.remove(filename)
    else:
        shutil.rmtree(filename)
    
def copy_file(source_file,target_path):
    shutil.copy(source_file,re.split(r'(/){1,}$',target_path)[0]+"/"+os.path.basename(source_file))
    
def read_file(filename):
    with codecs.open(filename,'r','utf-8') as fopen:
        return fopen.read()

def get_str_time():
    now_time=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    return now_time

def delete_file_line_by_linux_sed(filename,linenumber):
    command = "sed -i '%dd' %s ; echo $?"%(linenumber,filename)
    shell_command(command)

def write_lines(filename,contents):
    make_file(filename)
    contents = contents if re.match(r'(\n|\r\n|\r){1}$', contents) else contents+'\n'
    with codecs.open(filename, 'a+','utf-8') as log:
        log.write(contents)
        
def write_file(filename,contents=''):
    with codecs.open(filename, 'w','utf-8') as log:
        log.write(contents)
        
def read_lines(filename):
    change_mod(filename)
    with codecs.open(filename,'r','utf-8') as fopen:
        return [line.strip('\n') for line in fopen.readlines()]
    
#def dir_scan(scandirname):
#    return [i for i in os.listdir(scandirname) if re.match(r".{0,}\.json$",i)]

def scan_files(directory,match=None):  
    files_list=[]
    for root, sub_dirs, files in os.walk(directory):  
        for special_file in files:
            if match:
                if re.match(match, special_file):  
                    files_list.append(os.path.join(root,special_file))
            else:  
                files_list.append(os.path.join(root,special_file))
                            
    return files_list  

def scan_file_number(directory,file_number,match=None):  
    files_list=[]
    
    try:
        for root, sub_dirs, files in os.walk(directory):  
            for special_file in files:
                if len(files_list) >= file_number:
                    raise OutListError#("The maximum length of the file list has been reached.")
                else:
                    if match:
                        if re.match(match, special_file):  
                            files_list.append(os.path.join(root,special_file))
                    else:  
                        files_list.append(os.path.join(root,special_file))
    except OutListError:
        pass
    return files_list 

class logbee_ftp():
    def __init__(self,host,port,user,password,timeout):
        self.ftp_obj = ftplib.FTP()
        self.ftp_obj.connect(host=host, port=port,timeout=timeout)
        self.ftp_obj.login(user=user, passwd=password)
        
    def get_ftp_obj(self):
        return self.ftp_obj
        
# upload_file
def upload_with_ftp(ftp_obj,src_file_name,dist_path):
    ftp_obj.storbinary("STOR %s"%dist_path,open(src_file_name,"rb"))
    
def upload_with_local(source_file,target_path):
    shutil.move(source_file, target_path)
    
# download_file
def download_with_ftp(ftp_obj,source_file,target_path):
    f = open(target_path,"wb")
    ftp_obj.retrbinary("RETR %s"%source_file,f.write)
    
def download_with_local(source_file,target_path):
    shutil.move(source_file, target_path)
    
class logbeeIO(object):
    """abstract StringIO about logbee cache object"""
    def __init__(self,max_size):
        self.__logbee_io = StringIO()
        self.__size = 0
        self.__max_size = max_size
    
    @property
    def is_max_size(self):
        return self.__size >= self.__max_size
        
    def write_line(self,line):
        if not line.endswith("\n"):
            line+="\n"
        str_buffer = self.__logbee_io.write(line)
        self.__size += str_buffer
        
    def rewrite(self):
        self.__logbee_io.seek(0, 0)
        self.__size = 0
#         self.__logbee_io = StringIO(self.__logbee_io.read())
#         self.__logbee_io.seek(0, os.SEEK_END)
        
    def save_to_file(self,filename):
        self.__logbee_io.seek(0, 0)
        write_file(filename, self.__logbee_io.read())

    def readlines(self):
        self.__logbee_io.seek(0, 0)
        return self.__logbee_io.readlines()
    
    def clear(self):
#         self.__logbee_io = StringIO()
#         self.__size = 0
        self.__logbee_io.truncate(0)
        self.__logbee_io.seek(0, 0)
        self.__size = 0
        
    def close(self):
        self.__logbee_io.close()

class logbeeFileIO(object):
    """abstract FileIO about logbee cache object"""
    def __init__(self,filename,max_size):
        self.__logbee_file_io = codecs.open(filename, 'r+','utf-8')
        self.__size = 0
        self.__max_size = max_size
        
    @property
    def is_max_size(self):
        return self.__size >= self.__max_size

    def write_line(self,line):
        if not line.endswith("\n"):
            line+="\n"
        self.__logbee_file_io.write(line)
        self.__logbee_file_io.flush()
        self.__size += len(line)
        
    def rewrite(self): 
        self.__logbee_file_io.seek(0, 0)
        self.__size = 0
    
    def readlines(self):
        self.__logbee_file_io.seek(0, 0)
        return self.__logbee_file_io.readlines()

    def clear(self):
        self.__logbee_file_io.truncate(0)
        self.__logbee_file_io.seek(0, 0)
        self.__size=0
    
    def close(self):
#         logger.warning("close logbee file io.")
        self.__logbee_file_io.close()
    

if __name__=="__main__":
    pass


