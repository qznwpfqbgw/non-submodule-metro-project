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
import threading

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", type=str, help="config file", default="config.yml") 
args = parser.parse_args()

task_list = []
base_dir = ""
upload_file_base_dir = ""
upload_targets = []
log_dir = ""
start = None
config = {}
targetFile = None
expr_num = 0
daily_config = {}
upload_config = {}
target_date = ""

def generateReport():
    global start, config, base_dir, expr_num, daily_config, upload_config
    end = dt.datetime.now()
    config['Time'] = {}
    config['Time']['start'] = str(start)
    config['Time']['end'] = str(end)
    with open(f"{log_dir}info.yml", "w") as outfile: 
        yaml.dump(config, outfile, default_flow_style=False, sort_keys=False)
    with open(f"{base_dir}info.yml", "w") as f:
        yaml.dump(daily_config, f, default_flow_style=False, sort_keys=False)
    with open(f"{upload_file_base_dir}info.yml", "w") as f:
        yaml.dump(upload_config, f, default_flow_style=False, sort_keys=False)
        
def signal_handler(signum, frame):
    global task_list, target_date, expr_num, daily_config
    print("Signal: ", signum)
    for i in task_list:
        i.terminate()
        if i.is_upload() and i.get_upload_target()!=None:
            os.remove(f"{target_date}_{i.get_upload_target()}.zip")
            if i.get_status() == 0:
                upload_config['pending'].remove(i.get_upload_target())
                upload_config['uploaded'].append(i.get_upload_target())
    daily_config['pending'].append(expr_num)
    generateReport()
    os._exit(0)  

def create_log_dir(config):
    global log_dir, expr_num, base_dir
    log_dir = f"{config['Default']['LogDir']}/{dt.date.today().strftime('%Y-%m-%d')}/"
    base_dir = log_dir
    print(f"Log dir is {log_dir}")
    for i in range(100):
        if os.path.exists(log_dir+f'{i}/'):
            continue
        expr_num = i
        if not os.path.exists(log_dir+f'{i}/'):
            log_dir = log_dir+f'{i}/'
            os.umask(0)
            os.makedirs(log_dir + "expr")
            os.makedirs(log_dir + "tcpdump")
            os.makedirs(log_dir + "mobileinsight")
            break


def execute_all():
    global task_list
    for task in task_list:
        task.start()
        time.sleep(1)
        
def generateUploadFile(target, upload_file_base_dir, target_date):
    targetFile = shutil.make_archive(f'{target}', format='zip', root_dir = upload_file_base_dir)
    os.rename(targetFile, f"{target_date}_{target}.zip")

def main():
    global task_list, start, config, targetFile, base_dir, daily_config, upload_config, upload_file_base_dir, target_date
    
    # Load config
    with open(args.config, "r") as f:
        config = yaml.safe_load(f)
    create_log_dir(config)
    if os.path.exists(f"{base_dir}info.yml"):
        with open(f"{base_dir}info.yml", "r") as f:
            daily_config = yaml.safe_load(f)
    else:
        daily_config['pending'] = []
        daily_config['uploaded'] = []

    start = dt.datetime.now()
    
    tcpdump_opt = ""
    log_file_name = start.strftime('%Y-%m-%d-%H-%M-%S')
    expr_log_dir = log_dir + f"expr/"
    
    if config["Default"]["Upload"]['Enable']:
        target_date = (
            (dt.date.today() - dt.timedelta(days=1)).strftime("%Y-%m-%d")
            if config["Default"]["Upload"]["Date"] == ""
            else config["Default"]["Upload"]["Date"]
        )
        upload_file_base_dir = config['Default']['LogDir'] + '/' + target_date + '/'
        if dt.date.today().strftime("%Y-%m-%d") == target_date:
            upload_config = daily_config
        elif os.path.exists(f"{upload_file_base_dir}info.yml"):
            with open(f"{upload_file_base_dir}info.yml", "r") as f:
                upload_config = yaml.safe_load(f)
        
    # Experiment setup
    i = 0
    for expr_type in config["Default"]["Type"]:
        opt = ""
        log_opt = ""
        exec_cmd = ""
        exec_entry = config[expr_type]["Entry"]
        log_file = log_dir + f"expr/{expr_type}-{log_file_name}.log"
        isUpload = False
        upload_target = None
        for k, v in config[expr_type].items():
            if type(v) != dict:
                continue
            if k == "LogDir":
                log_opt += f"{v['Flag']} {os.path.abspath(os.curdir) + '/' + log_dir} "
            elif k == "LogFile":
                opt += f"{v['Flag']} {os.path.abspath(os.curdir) + '/' + log_file} "
            elif k == "Upload":
                if upload_config != None and len(upload_config['pending']) > i:
                    upload_target = upload_config['pending'][i]
                    upload_targets.append(upload_target)
                    opt += f"{v['Flag']} {target_date}_{upload_target}.zip"
                    isUpload = True
                    i += 1
                else:
                    continue
            else:
                opt += f"{v['Flag']} "
                if "Value" in v:
                    opt += f"{v['Value']} "
        exec_cmd = f"{exec_entry} {opt}{log_opt}"
        task = Task(exec_cmd, expr_type, isUpload, upload_target)
        task_list.append(task)

    # Generate Upload file
    thread_list = []
    for target in upload_targets:
        thread_list.append(threading.Thread(target=generateUploadFile,args=(target, upload_file_base_dir, target_date)))

    # start
    for t in thread_list:
        t.start()
    
    # join
    for t in thread_list:
        t.join()

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
            ## TODO: sudo sync
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