class LogbeePermissionError(Exception):
    '''Logbee permission error [throw a error when change a  attribute about instance.]'''
    
class OutListError(Exception):
    """Exceeded list maximum length"""
    def __init__(self,error_info="Exceeded list maximum length"):
        if error_info:
            self.err=error_info
            self.__doc__=error_info