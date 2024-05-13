#!/usr/bin/python

from bcc import BPF
import time
import sys
import argparse
import socket
import os
from datetime import datetime
from struct import unpack
import fcntl
import struct
import netifaces

PACKET_SIZE = 250

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--device", help="net_interface")
parser.add_argument("-p", "--ports",
    help="comma-separated list of ports to trace.")
parser.add_argument("-w", "--file", help="output file")
args = parser.parse_args()

bpf_text = """

#include <uapi/linux/ptrace.h>
#include <net/sock.h>
#include <bcc/proto.h>
#include <linux/bpf.h>

#define IP_TCP 6
#define IP_UDP 17
#define IP_ICMP 1
#define ETH_HLEN 14

BPF_PERF_OUTPUT(skb_events);
 
struct perf_data {
    int len;
    int dir;
};

int packet_filter(struct __sk_buff *skb) {
    u8 *cursor = 0;
    u32 saddr, daddr;
    u32 sport, dport;
    u32 udp_header_length = 0;
    u32 ip_header_length = 0;
    u32 payload_offset = 0;
    u32 payload_length = 0;
    
    struct ethernet_t *ethernet = cursor_advance(cursor, sizeof(*ethernet));
    struct ip_t *ip = cursor_advance(cursor, sizeof(*ip));

    if (ip->ver != 4)
        goto DROP;

    ip_header_length = ip->hlen << 2;  // SHL 2 -> *4 multiply

    /* check ip header length against minimum */
    if (ip_header_length < sizeof(*ip))
        goto DROP;
        
    if (ip->nextp == IP_TCP) 
        goto DROP;
    if (ip->nextp == IP_ICMP) 
        goto DROP;
        
    if (ip -> nextp == IP_UDP){
        struct udp_t *udp = cursor_advance(cursor, sizeof(*udp));
        dport = udp->dport;
        sport = udp->sport;
        saddr = ip -> src;
        daddr = ip -> dst;
        FILTER_PORT
    }
    


/* drop the packet returning 0 */
DROP:
    return 0;

/* keep the packet and send it to userspace returning -1 */
KEEP:
    return -1;

}

"""

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s',  bytes(ifname[:15], 'utf-8'))
    )[20:24])

def get_arp_hwtype(interface):
    try:
        addrs = netifaces.ifaddresses(interface)
        arp_hwtype = addrs[netifaces.AF_LINK][0]['addr']
        return arp_hwtype
    except KeyError:
        return None

out = sys.stdout
if args.file:
    out = open(args.file,"w+")
if args.ports:
    dports = [int(port) for port in args.ports.split(',')]
    dports_if = ' || '.join([f'dport == {port} || sport == {port}' for port in dports])
    bpf_text = bpf_text.replace('FILTER_PORT',
        'if (%s) { goto KEEP; }' % dports_if)
else:
    bpf_text = bpf_text.replace('FILTER_PORT',"goto KEEP;")

host_if_ip = get_ip_address(args.device)
host_has_layer2 = get_arp_hwtype(args.device) != None 
if host_has_layer2:
    bpf_text = bpf_text.replace('PARSE_ETHERNET','struct ethernet_t *ethernet = cursor_advance(cursor, sizeof(*ethernet));')
else:
    bpf_text = bpf_text.replace('PARSE_ETHERNET','')

bpf = BPF(text=bpf_text)

function_skb_matching = bpf.load_func("packet_filter", BPF.SOCKET_FILTER)

BPF.attach_raw_socket(function_skb_matching, args.device)
socket_fd = function_skb_matching.sock
fl = fcntl.fcntl(socket_fd, fcntl.F_GETFL)
fcntl.fcntl(socket_fd, fcntl.F_SETFL, fl & (~os.O_NONBLOCK))

try:
    print("timestamp,saddr,daddr,sport,dport,sequence,epoch,microseconds,direction",file=out)
    while True:
        if host_has_layer2:
            ip_packet = bytes(os.read(socket_fd, 4096)[14:])
        else:
            ip_packet = bytes(os.read(socket_fd, 4096))
        (length, _, _, _, _, proto, _, saddr, daddr) = unpack('!BBHLBBHLL', ip_packet[:20])
        len_iph = length & 15
        # Length is written in 32-bit words, convert it to bytes:
        len_iph = len_iph * 4
        saddr = ".".join(map(str, [saddr >> 24 & 0xff, saddr >> 16 & 0xff, saddr >> 8 & 0xff, saddr & 0xff]))
        daddr = ".".join(map(str, [daddr >> 24 & 0xff, daddr >> 16 & 0xff, daddr >> 8 & 0xff, daddr & 0xff]))
        udp_packet = ip_packet[len_iph:]
        sport = int.from_bytes(udp_packet[0:2],"big")
        dport = int.from_bytes(udp_packet[2:4],"big")
        packet_len = int.from_bytes(udp_packet[4:6],"big")
        payload = udp_packet[8:]
        packet_nums = int(packet_len/PACKET_SIZE)
        ts = datetime.now()
        for i in range(packet_nums):
            """
            tag         epoch       microseconds    seq
            8 bytes     4 bytes     4bytes          4 bytes
            -------------------------------------------------------
            |    0-8    |    8-12   |    12-16      |    16-20    |
            -------------------------------------------------------
            """
            custom_header = payload[PACKET_SIZE*i : PACKET_SIZE*i + 40]
            epoch = int.from_bytes(custom_header[8:12],"big")
            microseconds = int.from_bytes(custom_header[12:16],"big")
            seq = int.from_bytes(custom_header[16:20],"big")
            dir = 0 if host_if_ip == saddr else 1
            print(f"{ts},{saddr},{daddr},{sport},{dport},{seq},{epoch},{microseconds},{dir}",file=out,flush=True)
except KeyboardInterrupt:
    sys.stdout.close()
    pass