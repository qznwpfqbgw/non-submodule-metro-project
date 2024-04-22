import subprocess
from subprocess import Popen
import os
import time

class Task:
    def __init__(self, cmd, expr_type, isUpload = False, upload_target = None):
        self.__cmd = cmd
        self.__expr_type = expr_type
        self.__process: Popen = None
        self.__isUpload: bool = isUpload
        self.__upload_target = upload_target

    def start(self):
        print(self.__cmd)
        self.__process = subprocess.Popen(f"exec {self.__cmd}", shell=True, preexec_fn=os.setpgrp)

    def get_status(self):
        return self.__process.poll()
    
    def terminate(self):
        self.__process.terminate()
        time.sleep(1)
        while self.get_status() == None:
            self.__process.kill()
            time.sleep(1)
            self.__process.terminate()
            time.sleep(1)

    def get_expr_type(self):
        return self.__expr_type
    
    def is_upload(self):
        return self.__isUpload
    
    def get_upload_target(self):
        return self.__upload_target
    
    def get_cmd(self):
        return self.__cmd