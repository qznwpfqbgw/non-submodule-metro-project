#!/bin/python3
import yaml
import time
import datetime as dt
import subprocess
import os
import signal
import json
import multiprocessing
import pathlib

process_list = []
log_dir = ""
pool = None
start = None
config = None

def generateReport():
    global start, config
    end = dt.datetime.now()
    config['Time'] = {}
    config['Time']['start'] = str(start)
    config['Time']['end'] = str(end)
    with open(f"{log_dir}info.json", "w") as outfile: 
        json.dump(config, outfile)

def signal_handler(signum, frame):
    global pool, process_list
    print("Signal: ",signum)
    if pool!= None:
        # pool.close()
        pool.terminate()
    for i in process_list:
        i.terminate()
    generateReport()
    os._exit(0)  

def create_log_dir(config):
    global log_dir
    log_dir = f"{config['Default']['LogDir']}/{dt.date.today().strftime('%Y-%m-%d')}/measurement/"
    print(f"Log dir is {log_dir}")
    i = 0
    for i in range(100):
        if os.path.exists(log_dir+f'{i}/'):
            continue
        if not os.path.exists(log_dir+f'{i}/'):
            log_dir = log_dir+f'{i}/'
            os.umask(0)
            os.makedirs(log_dir + "expr")
            os.makedirs(log_dir + "tcpdump")
            os.makedirs(log_dir + "mobileinsight")
            break


def execute_all(cmds: list):
    global process_list
    for cmd in cmds:
        print(cmd)
        process_list.append(subprocess.Popen(f"exec {cmd}", shell=True, preexec_fn=os.setpgrp))
        

def main():
    global pool, process_list, start, config
    
    # Load config
    with open(str(pathlib.Path(__file__).parent.resolve()) + "/config.yml", "r") as f:
        config = yaml.safe_load(f)
    create_log_dir(config)
    start = dt.datetime.now()
    
    opt = ""
    log_opt = ""
    exec_cmd = ""
    tcpdump_opt = ""
    expr_type = config["Default"]["Type"]
    exec_entry = config[expr_type]["Entry"]
    mobileinsight_cmds = []
    log_file_name = start.strftime('%Y-%m-%d-%H-%M-%S')
    log_file = log_dir + f"expr/{expr_type}-{log_file_name}.log"
    
    # Experiment setup
    for k, v in config[expr_type].items():
        if type(v) != dict:
            continue
        
        if k == "LogDir":
            log_opt += f"{v['Flag']} {log_file} "
        elif k == "SyncFile":
            sync_file_name = log_dir + f"sync/timesync-{log_file_name}.json"
            opt += f"{v['Flag']} {sync_file_name} "
        else:
            opt += f"{v['Flag']} "
            if "Value" in v:
                opt += f"{v['Value']} "
                
    # Tcpdump setup
    tcpdump_cmds = []
    for i in config["Default"]["TcpDump"]:
        tcpdump_opt = ""
        tcpdump_opt += f"-i {i['Interface']} "
        tcpdump_opt += f"port {i['Port']} "
        tcpdump_opt += f"-C {i['FileSize']} "
        tcpdump_log_file = log_dir + f"tcpdump/{expr_type}-{i['Interface']}-{i['Port']}-{log_file_name}.pcap"
        tcpdump_opt += f"-w {tcpdump_log_file} "
        tcpdump_cmds.append(f"sudo tcpdump {tcpdump_opt}")
    
    # Mobileinsight setup
    if config['Default']['Mode'] == 'c':
        mobileinsight_log_file = log_dir + f"mobileinsight/{expr_type}"
        for i in config['Default']['Device']:
            mobileinsight_log_file = log_dir + f"mobileinsight/{expr_type}"
            mobileinsight_log_file = f"{mobileinsight_log_file}-{i}-{log_file_name}.mi2log"
            mobileinsight_cmds.append(f"sudo python3 mobileinsight/monitor.py -d {i} -b 9600 -f {mobileinsight_log_file}")
        
    exec_cmd = f"{exec_entry} {opt}{log_opt}"
    execute_all(tcpdump_cmds + [exec_cmd] + mobileinsight_cmds)
    
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
        signal_handler(0, 0)