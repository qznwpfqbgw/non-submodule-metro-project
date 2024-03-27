import subprocess
from subprocess import Popen
import os

class Task:
    def __init__(self, cmd, expr_type):
        self.__cmd = cmd
        self.__expr_type = expr_type
        self.__process: Popen = None

    def start(self):
        print(self.__cmd)
        self.__process = subprocess.Popen(f"exec {self.__cmd}", shell=True, preexec_fn=os.setpgrp)

    def get_status(self):
        return self.__process.poll()
    
    def terminate(self):
        self.__process.terminate()
        if self.get_status() == None:
            self.__process.kill()

    def get_expr_type(self):
        return self.__expr_type
    
    def get_cmd(self):
        return self.__cmd