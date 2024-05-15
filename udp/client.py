#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import socket
import time
import threading
import multiprocessing
import os
import argparse
import subprocess
import signal
import traceback
parser = argparse.ArgumentParser()
parser.add_argument("-H", "--host", type=str, help="server ip address", default="140.112.20.183") 
parser.add_argument("-d", "--devices", type=str, nargs='+', required=True, help="list of devices", default=["unam"])
parser.add_argument("-p", "--ports", type=str, nargs='+', help="ports to bind")
parser.add_argument("-b", "--bitrate", type=str, help="target bitrate in bits/sec (0 for unlimited)", default="1M")
parser.add_argument("-l", "--length", type=str, help="length of buffer to read or write in bytes (packet size)", default="250")
parser.add_argument("-w", "--file", type=str, help="time synchronization save filename")
parser.add_argument("-tp", "--timeSyncPort", type=int, required=True, help="port to bind of time sync process")
parser.add_argument("-cp", "--controlPort", type=int, required=True, help="port to bind for control")
args = parser.parse_args()

devices = []
for dev in args.devices:
    if '-' in dev:
        pmodel = dev[:2]
        start = int(dev[2:4])
        stop = int(dev[5:7]) + 1
        for i in range(start, stop):
            _dev = "{}{:02d}".format(pmodel, i)
            devices.append(_dev)
        continue
    devices.append(dev)

ports = []
for port in args.ports:
    if '-' in port:
        start = int(port[:port.find('-')])
        stop = int(port[port.find('-') + 1:]) + 1
        for i in range(start, stop):
            ports.append(i)
        continue
    ports.append([int(port), int(port)+1])

print(devices)
print(ports)

length_packet = int(args.length)

if args.bitrate[-1] == 'k':
    bandwidth = int(args.bitrate[:-1]) * 1e3
elif args.bitrate[-1] == 'M':
    bandwidth = int(args.bitrate[:-1]) * 1e6
else:
    bandwidth = int(args.bitrate)

print("bitrate:", bandwidth)

expected_packet_per_sec = bandwidth / (length_packet << 3)
sleeptime = 1.0 / expected_packet_per_sec
syncfile = args.file

# global variables
HOST = args.host
timesync_port = args.timeSyncPort
control_port = args.controlPort
stop = multiprocessing.Value('i', 0)
stop_event = multiprocessing.Event()

def give_server_DL_addr(rx_sockets):
    
    for s, port in zip(rx_sockets, ports):
        outdata = 'hello'
        s.sendto(outdata.encode(), (HOST, port[1]))

def receive(s, dev):

    try:
        seq = 1
        prev_receive = 1

        start_time = time.time()
        time_slot = 1

        while True:
            # receive data
            indata, _ = s.recvfrom(1024)

            if len(indata) != length_packet:
                print("packet with strange length: ", len(indata))

            seq = int(indata.hex()[32:40], 16)
            # ts = int(int(indata.hex()[16:24], 16)) + float("0." + str(int(indata.hex()[24:32], 16)))

            # Show information
            if time.time()-start_time > time_slot:
                if (seq-prev_receive) < 0:
                    prev_receive, time_slot = 1, 1  
                print(f"{dev} [{time_slot-1}-{time_slot}]", "receive", seq-prev_receive)
                time_slot += 1
                prev_receive = seq

    except Exception as e:
        print(e)

def transmit(sockets, stop, stop_event):

    try:
        while True:

            stop_event.wait()

            print("start transmission: ")
            seq = 1
            prev_transmit = 0
            
            start_time = time.time()
            next_transmit_time = start_time + sleeptime
            
            time_slot = 1

            while not stop.value:
                t = time.time()
                while t < next_transmit_time:
                    t = time.time()
                next_transmit_time = next_transmit_time + sleeptime

                euler = 271828
                pi = 31415926
                datetimedec = int(t)
                microsec = int((t - int(t))*1000000)

                redundant = os.urandom(length_packet-4*5)
                outdata = euler.to_bytes(4, 'big') + pi.to_bytes(4, 'big') + datetimedec.to_bytes(4, 'big') + microsec.to_bytes(4, 'big') + seq.to_bytes(4, 'big') + redundant
                
                for s, port in zip(sockets, ports):     
                    s.sendto(outdata, (HOST, port[0]))

                seq += 1
            
                if time.time()-start_time > time_slot:
                    print("[%d-%d]"%(time_slot-1, time_slot), "transmit", seq-prev_transmit)
                    time_slot += 1
                    prev_transmit = seq

            stop_event.clear()

    except Exception as e:
        print(e)

def regular_time_sync():
    interval_minutes = 20
    while True:
        try:
            dir_path = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(dir_path, "time_sync.py")
            p = subprocess.Popen([f"python3 {file_path} -c {HOST} -p {timesync_port} -w {syncfile}"], shell=True)    
            time.sleep(interval_minutes*60)
        except:
            p.terminate()
            break

# TCP control socket
s_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s_tcp.connect((HOST, control_port))
s_tcp.settimeout(3)

# Create DL receive and UL transmit multi-client sockets
rx_sockets = []
tx_sockets = []
for dev, port in zip(devices, ports):
    s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s1.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, (dev+'\0').encode())
    rx_sockets.append(s1)
    s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s2.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, (dev+'\0').encode())
    tx_sockets.append(s2)
    print(f'Create DL socket for {dev}.')
    print(f'Create UL socket for {dev}.')
    
# Transmit data from receive socket to server DL port to let server know addr first
success = False
while not success:
    try:
        give_server_DL_addr(rx_sockets)
        tmp = s_tcp.recv(len(b'ok'))
        success = True
    except Exception:
        pass
    
s_tcp.settimeout(None)
    
print('Finished giving server DL socket address!')

# Run synchronization process
p_sync = multiprocessing.Process(target=regular_time_sync, args=(), daemon=True)
p_sync.start()
time.sleep(2) # Wait for initital time sync difference counting

# Create and start DL receive multi-thread
rx_threads = []
for s, dev in zip(rx_sockets, devices):
    t_rx = threading.Thread(target=receive, args=(s, dev), daemon=True)
    rx_threads.append(t_rx)
    t_rx.start()

# Create and start UL transmission multiprocess
p_tx = multiprocessing.Process(target=transmit, args=(tx_sockets, stop, stop_event), daemon=True)
p_tx.start()
stop_event.set()

# Signal handler
def close_all():
    # Kill tcp control
    s_tcp.close()

    # Kill transmit process
    p_tx.terminate()
    p_tx.join()

    # Kill time synchronizatoin process
    p_sync.terminate()

def signal_handler(signum, message, frame):

    print("Inner Signal: ",signum)
    print('Send',message,'to Server')

    outdata = message
    s_tcp.send(outdata.encode())

    global stop
    stop.value = 1

    close_all()
    print('Successfully closed.')
    os._exit(0)

signal.signal(signal.SIGINT, lambda signum, frame: signal_handler(signum, 'STOP', frame))
signal.signal(signal.SIGTERM, lambda signum, frame: signal_handler(signum, 'STOP', frame))
signal.signal(signal.SIGTSTP, lambda signum, frame: signal_handler(signum, 'CLOSE', frame))
    
# Main Process waiing...
try:
    indata = s_tcp.recv(1024)
    message = indata.decode()
    print('received ' + message + ' command from server')

    if message == 'cLOSE':
        stop.value = 1

        close_all()
        print('Successfully closed.')
        os._exit(0)
except BaseException as e:
    traceback.print_exc()
    print('Error:', e)

    stop.value = 1

    outdata = 'CLOSE'
    s_tcp.send(outdata.encode())

    close_all()
    print('Error, closed.')
    os._exit(0)