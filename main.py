#!/bin/python3
import yaml
import time
import datetime as dt
import subprocess
import os
import signal
import json
import argparse
import pathlib

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", type=str, help="config file", default="config.yml") 
args = parser.parse_args()

process_list = []
log_dir = ""
start = None
config = None

def generateReport():
    global start, config
    end = dt.datetime.now()
    config['Time'] = {}
    config['Time']['start'] = str(start)
    config['Time']['end'] = str(end)
    with open(f"{log_dir}info.json", "w") as outfile: 
        yaml.dump(config, outfile, default_flow_style=False, sort_keys=False)

def signal_handler(signum, frame):
    global process_list
    print("Signal: ",signum)
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
    global process_list, start, config
    
    # Load config
    with open(args.config, "r") as f:
        config = yaml.safe_load(f)
    create_log_dir(config)
    start = dt.datetime.now()
    
    exec_cmds = []
    tcpdump_opt = ""
    mobileinsight_cmds = []
    log_file_name = start.strftime('%Y-%m-%d-%H-%M-%S')
    expr_log_dir = log_dir + f"expr/"
    
    # Experiment setup
    for expr_type in config["Default"]["Type"]:
        opt = ""
        log_opt = ""
        exec_cmd = ""
        exec_entry = config[expr_type]["Entry"]
        log_file = log_dir + f"expr/{expr_type}-{log_file_name}.log"
        for k, v in config[expr_type].items():
            if type(v) != dict:
                continue
            
            if k == "LogDir":
                log_opt += f"{v['Flag']} {log_file} "
            elif k == "SyncFile":
                sync_file_name = expr_log_dir + f"sync/timesync-{log_file_name}.json"
                opt += f"{v['Flag']} {sync_file_name} "
            else:
                opt += f"{v['Flag']} "
                if "Value" in v:
                    opt += f"{v['Value']} "
        exec_cmd = f"{exec_entry} {opt}{log_opt}"
        exec_cmds.append(exec_cmd)
                
    # Tcpdump setup
    tcpdump_cmds = []
    for tcpdump_config in config["Default"]["TcpDump"]:
        tcpdump_opt = ""
        name = ""
        for k, v in tcpdump_config.items():
            tcpdump_opt += f"{v['Flag']} "
            name += f"{v['Flag']}-"
            if "Value" in v:
                tcpdump_opt += f"{v['Value']} "
                name += f"{v['Value']}-"
        tcpdump_log_path = log_dir + f'tcpdump/{expr_type}-{name}{log_file_name}.pcap'
        tcpdump_cmds.append(f"sudo tcpdump {tcpdump_opt} -w {tcpdump_log_path}")
    
    # Mobileinsight setup
    mobileinsight_log_file = log_dir + f"mobileinsight/{expr_type}"
    for i in config['Default']['Device']:
        mobileinsight_log_file = log_dir + f"mobileinsight/{expr_type}"
        mobileinsight_log_file = f"{mobileinsight_log_file}-{i}-{log_file_name}.mi2log"
        mobileinsight_decoded_file = f"{mobileinsight_log_file}-{i}-{log_file_name}.log"
        mobileinsight_cmds.append(f"sudo python3 tools/monitor.py -d {i} -b 9600 -f {mobileinsight_log_file} -dp {mobileinsight_decoded_file}")
        
    
    execute_all(tcpdump_cmds + exec_cmds + mobileinsight_cmds)
    if config['Default']['Poll']['Enable']:
        while True:
            for p in process_list:
                status = p.poll()
                if status != None:
                    print("process stop by command: ",p.args)
                    signal_handler(status, 0)
            time.sleep(config['Default']['Poll']['Interval'])
    else:
        while True:
            time.sleep(60)


if __name__ == '__main__':
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGTSTP, signal_handler)
        main()
    except BaseException as e:
        print(e)
        signal_handler(0, 0)