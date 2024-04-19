#!/bin/python3
import yaml
import time
import datetime as dt
import os
import signal
import argparse
import shutil
from task import Task
import traceback

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", type=str, help="config file", default="config.yml") 
args = parser.parse_args()

task_list = []
log_dir = ""
start = None
config = None
targetFile = None

def generateReport():
    global start, config
    end = dt.datetime.now()
    config['Time'] = {}
    config['Time']['start'] = str(start)
    config['Time']['end'] = str(end)
    with open(f"{log_dir}info.yml", "w") as outfile: 
        yaml.dump(config, outfile, default_flow_style=False, sort_keys=False)

def signal_handler(signum, frame):
    global task_list, targetFile
    print("Signal: ", signum)
    for i in task_list:
        i.terminate()
    if targetFile!=None:
        os.remove(targetFile)
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
            os.makedirs(log_dir + "mobileinsight/decode")
            break


def execute_all():
    global task_list
    for task in task_list:
        task.start()
        time.sleep(1)
        

def main():
    global task_list, start, config, targetFile
    
    # Load config
    with open(args.config, "r") as f:
        config = yaml.safe_load(f)
    create_log_dir(config)
    start = dt.datetime.now()
    
    tcpdump_opt = ""
    log_file_name = start.strftime('%Y-%m-%d-%H-%M-%S')
    expr_log_dir = log_dir + f"expr/"
    
    if config["Default"]["Upload"]['Enable']:
        targetDate = (
            (dt.date.today() - dt.timedelta(days=1)).strftime("%Y-%m-%d")
            if config["Default"]["Upload"]["Date"] == ""
            else config["Default"]["Upload"]["Date"]
        )
        targetFile = shutil.make_archive(f'{targetDate}', format='zip', root_dir= f"{config['Default']['LogDir']}/{targetDate}/")
        
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
            elif k == "Upload" :
                if targetFile != None:
                    opt += f"{v['Flag']} {targetFile}"
            else:
                opt += f"{v['Flag']} "
                if "Value" in v:
                    opt += f"{v['Value']} "
        exec_cmd = f"{exec_entry} {opt}{log_opt}"
        task = Task(exec_cmd, expr_type)
        task_list.append(task)
                
    # Tcpdump setup
    i = 0
    for tcpdump_config in config["Default"]["TcpDump"]:
        tcpdump_opt = ""
        name = "tcpdump"
        for k, v in tcpdump_config.items():
            tcpdump_opt += f"{v['Flag']} "
            name += f"{v['Flag']}-"
            if "Value" in v:
                tcpdump_opt += f"{v['Value']} "
                name += f"{v['Value']}-"
        tcpdump_log_path = log_dir + f'tcpdump/{name}{log_file_name}.pcap'
        exec_cmd = f"sudo tcpdump {tcpdump_opt} -w {tcpdump_log_path}"
        task = Task(exec_cmd, f"Tcpdump_{i}")
        task_list.insert(0,task) # exec tcpdump before expr
        i += 1
    
    # Mobileinsight setup
    for d in config['Default']['Device']:
        mobileinsight_log_dir = log_dir + f"mobileinsight/"
        mobileinsight_log_file = f"{mobileinsight_log_dir}{log_file_name}-{d}.mi2log"
        mobileinsight_decoded_file = f"{mobileinsight_log_dir}{log_file_name}-{d}.log"
        exec_cmd = f"sudo python3 tools/monitor.py -d {d} -b 9600 -f {mobileinsight_log_file} -dp {mobileinsight_decoded_file}"
        task = Task(exec_cmd, f"Mobileinsight_{d}")
        task_list.insert(0,task) # exec mobileinsight before expr
        
    execute_all()
    if config['Default']['Poll']['Enable']:
        while True:
            for t in task_list:
                if t.get_status() != None:
                    print("process stop by: ",t.get_expr_type())
                    signal_handler(t.get_status(), 0)
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
        traceback.print_exc()
        signal_handler(0, 0)