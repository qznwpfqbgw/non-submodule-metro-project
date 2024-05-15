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

parser = argparse.ArgumentParser() 
parser.add_argument("-s", "--server_ip", type=str, help="server ip", default='0.0.0.0') 
parser.add_argument("-n", "--number_client", type=int, help="number of client", default=1)
parser.add_argument("-d", "--devices", type=str, nargs='+', required=True, help="list of devices", default=["unam"])
parser.add_argument("-p", "--ports", type=str, nargs='+', required=True, help="ports to bind")
parser.add_argument("-b", "--bitrate", type=str, help="target bitrate in bits/sec (0 for unlimited)", default="1M")
parser.add_argument("-l", "--length", type=str, help="length of buffer to read or write in bytes (packet size)", default="250")
parser.add_argument("-tp", "--timeSyncPort", type=int, required=True, help="port to bind of time sync process")
parser.add_argument("-cp", "--controlPort", type=int, required=True, help="port to bind for control")
args = parser.parse_args()

# Get argument devices
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

number_client = args.number_client

expected_packet_per_sec = bandwidth / (length_packet << 3)
sleeptime = 1.0 / expected_packet_per_sec

# global variables
HOST = args.server_ip
timesync_port = args.timeSyncPort
control_port = args.controlPort
stop = multiprocessing.Value('i', 0)
stop_event = multiprocessing.Event()
manager = multiprocessing.Manager()
udp_addr = manager.dict()

# Function define
def fill_udp_addr(s):
    _, addr = s.recvfrom(1024)
    _, port = s.getsockname()
    udp_addr[port] = addr 

def fill_all_udp_addr(sockets, conn, addr):
    # Get client addr with server DL port first
    t_fills = []
    for s in sockets:
        t = threading.Thread(target=fill_udp_addr, args=(s, ))
        t.start()
        t_fills.append(t)

    print('Wait for filling up client address first...')
    for t in t_fills:
        t.join()
    conn.send("ok".encode())
    print('Successful get udp addr!')

def receive(s, dev, port):

    try:
        seq = 1
        prev_receive = 1

        start_time = time.time()
        time_slot = 1

        while True:
            #receive data
            indata, _ = s.recvfrom(1024)

            if len(indata) != length_packet:
                print("packet with strange length: ", len(indata))

            seq = int(indata.hex()[32:40], 16)
            # ts = int(int(indata.hex()[16:24], 16)) + float("0." + str(int(indata.hex()[24:32], 16)))

            # Show information
            if time.time()-start_time > time_slot:
                if (seq-prev_receive) < 0:
                    prev_receive, time_slot = 1, 1    
                print(f"{dev}:{port} [{time_slot-1}-{time_slot}]", "receive", seq-prev_receive)
                time_slot += 1
                prev_receive = seq

    except Exception as e:
        print(e)
   
def transmit(sockets, stop, stop_event, udp_addr):
    
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
                
                for s in sockets:
                    _, port = s.getsockname()
                    if port in udp_addr.keys():
                        s.sendto(outdata, udp_addr[port])

                seq += 1
                
                if time.time()-start_time > time_slot:
                    print("[%d-%d]"%(time_slot-1, time_slot), "transmit", seq-prev_transmit)
                    time_slot += 1
                    prev_transmit = seq

            stop_event.clear()

    except Exception as e:
        print(e)

# open subprocess of time synchronizatoin
dir_path = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(dir_path, "time_sync.py")
sync_proc =  subprocess.Popen([f"exec python3 {file_path} -s 0.0.0.0 -p {timesync_port}"], shell=True, preexec_fn = os.setpgrp)

# TCP control socket
s_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s_tcp.bind((HOST, control_port))
s_tcp.listen(5)
for sig in [signal.SIGINT, signal.SIGTERM]:
    signal.signal(sig, lambda signum, frame: (sync_proc.terminate(),os._exit(0)))
print('wait for TCP connection...')
conn, addr = s_tcp.accept()
print('connected by ' + str(addr))

# Set up UL receive /  DL transmit sockets for multiple clients
rx_sockets = []
tx_sockets = []
for dev, port in zip(devices, ports):
    s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s1.bind((HOST, port[0]))
    rx_sockets.append(s1)
    s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s2.bind((HOST, port[1]))
    tx_sockets.append(s2)
    print(f'Create socket at {HOST}:{port[0]} for UL...')
    print(f'Create socket at {HOST}:{port[1]} for DL...')

fill_all_udp_addr(tx_sockets, conn, addr)

time.sleep(2) # Wait for initital time sync difference counting

# Create and start UL receive multi-thread
rx_threads = []
for s, dev, port in zip(rx_sockets, devices, ports):
    t_rx = threading.Thread(target = receive, args=(s, dev, port[0]), daemon=True)
    rx_threads.append(t_rx)
    t_rx.start()

# Start DL transmission multipleprocessing
p_tx = multiprocessing.Process(target=transmit, args=(tx_sockets, stop, stop_event, udp_addr), daemon=True)
p_tx.start()
stop_event.set()

# Signal handler
def close_all():
    # Kill tcp control
    s_tcp.close()

    # Kill transmit process
    p_tx.terminate()
    p_tx.join()

    # Kill time synchronizatoin subprocess
    sync_proc.terminate()

def signal_handler(signum, frame):

    print("Inner Signal: ",signum)

    data = 'CLOSE'
    conn.send(data.encode())
    
    global stop
    stop.value = 1

    close_all()
    print('Successfully closed.')
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGTSTP, signal_handler)

# Main process waiting...
try:
    while True:
        indata = conn.recv(1024)
        message = indata.decode()
        print('received ' + message + ' command from client')

        if message == 'STOP':
            stop.value = 1
            
            s_tcp.listen(5)
            print('wait for TCP connection...')
            conn, addr = s_tcp.accept()
            print('connected by ' + str(addr))

            udp_addr.clear()
            fill_all_udp_addr(tx_sockets, conn, addr)

            time.sleep(2) # Wait for initital time sync difference counting
            
            stop.value = 0
            stop_event.set()
        
        elif message == 'CLOSE':
            stop.value = 1
            
            close_all()
            print('Successfully closed.')
            os._exit(0)

except BaseException as e:

    print('Error:', e)

    stop.value = 1

    data = 'CLOSE'
    conn.send(data.encode())
    
    close_all()
    print('Error, Closed.')
    os._exit(0)