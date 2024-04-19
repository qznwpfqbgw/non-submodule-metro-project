import requests
import datetime as dt
import time
import argparse
import os
import traceback

base_url = None
id = None

def register_worker(config):
    global id, base_url
    try:
        url = f"{base_url}/register"
        data = {'config': config, 'time': str(dt.datetime.now())}
        response = requests.post(url, json=data)
        id = response.json()['id']
    except Exception:
        traceback.print_exc()
        exit(-1)

def report_data(message):
    global id, base_url
    url = f"{base_url}/report"
    data = {'id': id, 'msg': message, 'time': str(dt.datetime.now())}
    response = requests.post(url, json=data)

def get_log_size(path):
    data = {}
    outputs = os.popen(f'du -sb {path}/*').readlines()
    for output in outputs:
        tmp = output.strip().split("\t")
        data[tmp[1]] = tmp[0]
    return str(data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=str, help="config file", default="config.yml")
    parser.add_argument("-u", "--url", type=str, help="base url", required=True)
    parser.add_argument("-l", "--log_path", type=str, help="log path to report", required=True)
    parser.add_argument("-i", "--interval", type=int, help="report interval (sec)", default=10)
    args = parser.parse_args()

    base_url = args.url

    """
    FIXME
    Since the path will pass the /logs/2024-03-27/measurement/15/expr/xxx.log, but 
    we want to report the log of /logs/2024-03-27/measurement/15/
    """
    log_path = args.log_path[0:-(len(args.log_path.split('/')[-1] + args.log_path.split('/')[-2]) + 1)]

    f = open(args.config,"r")
    config = f.read()

    register_worker(config)
    while True:
        try:
            time.sleep(args.interval)
            data = get_log_size(log_path)
            print("reporting...")
            report_data(data)
        except Exception:
            traceback.print_exc()