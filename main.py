#!/bin/python3
import yaml
import time
import datetime as dt
import subprocess
import os
import signal

process_list = []
log_dir = ""

def signal_handler(signum, frame):
    print("Signal: ",signum)  
    for i in process_list:
        i.terminate()
    exit(0)  

def create_log_dir(config):
    global log_dir
    log_dir = f"./{config['Default']['LogDir']}/{dt.date.today().strftime('%Y-%m-%d')}/"
    print(f"Log dir is {log_dir}")
    if not os.path.exists(log_dir):
        os.umask(0)
        os.makedirs(log_dir)


def execute_all(cmds: list):
    for cmd in cmds:
        print(cmd)
        process_list.append(subprocess.Popen([cmd], shell=True, preexec_fn=os.setpgrp))

def main():
    # Load config
    with open("./config.yml", "r") as f:
        config = yaml.safe_load(f)
    create_log_dir(config)
    
    
    opt = ""
    log_opt = ""
    exec_cmd = ""
    tcpdump_opt = ""
    expr_type = config["Default"]["Type"]
    exec_entry = config[expr_type]["Entry"]
    log_file_name = log_dir + f"{expr_type}-{dt.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.log"
    tcpdump_log_file = log_dir + f"{expr_type}-{dt.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.pcap"
    
    # Experiment set up
    for k, v in config[expr_type].items():
        if type(v) != dict:
            continue
        
        if k == "LogDir":
            log_opt += f"{v['Flag']} {log_file_name}"
        else:
            opt += f"{v['Flag']} "
            if "Value" in v:
                opt += f"{v['Value']} "
                
    # Tcpdump set up
    tcpdump_opt += "port '("
    for idx, port in enumerate(config["Default"]["ServerPort"]):
        if idx != 0:
            tcpdump_opt += f"or {port} "
        else:
            tcpdump_opt += f"{port} "
    tcpdump_opt += ")' "
    
    tcpdump_opt += f"-w {tcpdump_log_file} "
    
    for k, v in config["Default"]["TcpDump"].items():
        if k == "Interface":
            if len(v) == 0:
                tcpdump_opt += f'-i any '
            else:
                for i in v:
                    tcpdump_opt += f'-i {i} '
        # Split the logfile
        if k == "File_size":
            tcpdump_opt += f'-C {v}'
        
    exec_cmd = f"{exec_entry} {opt}{log_opt}"
    tcpdump_cmd = f"sudo tcpdump {tcpdump_opt}"
    execute_all([tcpdump_cmd, exec_cmd])
    
    while True:
        time.sleep(1)


if __name__ == '__main__':
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGTSTP, signal_handler)
        main()
    except BaseException as e:
        print(e)
        for i in process_list:
            i.terminate()