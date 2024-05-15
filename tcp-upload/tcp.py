import argparse
import socket
import os
from socket import *
import threading

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--server", help="server mode", action='store_true')
parser.add_argument("-c", "--connect", type=str, help="server ip")
parser.add_argument("-p", "--port", type=int, help="server port")
parser.add_argument("-f", "--file", type=str, help="upload filename")
parser.add_argument("-d", "--dest", type=str, help="download location", default="download")
parser.add_argument("-b", "--bind", type=str, help="bind interface", default="")

args = parser.parse_args()

COMMAND = {"NEW":"NEW", "ACK":"ACK"}

def run_client(ip, port, file):
    # file 
    file_stats = os.stat(file)
    f = open(file, "rb")
    
    # get cookie
    sock = socket(AF_INET, SOCK_STREAM)
    if args.bind != "":
        ip, separator, port = args.bind.rpartition(':')
        sock.bind()
    if sock.connect_ex((ip, port)) != 0:
        print("connect error")
        exit(-1)
    data = f"{COMMAND['NEW']} {file} {file_stats.st_size}"
    sock.sendall(data.encode())
    data = sock.recv(len(COMMAND["ACK"].encode()))
    if data == COMMAND["ACK"].encode():
        data = sock.sendfile(f, 0, file_stats.st_size)
        sock.close()
        f.close()
    else:
        print("error")
        sock.close()
        f.close()
        exit(-1)
    

def server_worker(client_sock: socket):
    file_info = client_sock.recv(1024).decode().split(' ')
    print(file_info)
    client_sock.sendall(COMMAND["ACK"].encode())
    file_name = f"{args.dest}/{os.path.basename(file_info[1])}"
    file_size = int(file_info[2])
    remain_size = file_size
    data = b''
    file = open(file_name,"wb")
    while remain_size > 0:
        tmp = client_sock.recv(65535)
        remain_size -= len(tmp)
        file.write(tmp)

    

def run_server(port):
    if not os.path.exists(args.dest):
        os.umask(0)
        os.makedirs(args.dest)
    
    sock = socket(AF_INET, SOCK_STREAM)
    sock.bind(("0.0.0.0", port))
    sock.listen()
    while True:
        (client_sock, _) = sock.accept()
        threading.Thread(target=server_worker,args=(client_sock,)).start()


def main():
    if args.server:
        if args.port != None:
            run_server(args.port)
        else:
            print("require --port")
    else:
        if args.file != None and args.connect != None and args.port != None:
            run_client(args.connect, args.port, args.file)
            pass
        else:
            print("require --file --port --connect")

if __name__ == "__main__":
    main()