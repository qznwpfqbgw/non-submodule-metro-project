#!/usr/bin/python

from bcc import BPF
import time
import sys
import argparse

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

int packet_monitor(struct __sk_buff *skb) {
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
        goto KEEP;

    ip_header_length = ip->hlen << 2;  // SHL 2 -> *4 multiply

    /* check ip header length against minimum */
    if (ip_header_length < sizeof(*ip))
        goto KEEP;
        
    if (ip->nextp == IP_TCP) 
        goto KEEP;
    if (ip->nextp == IP_ICMP) 
        goto KEEP;
        
    if (ip -> nextp == IP_UDP){
        struct udp_t *udp = cursor_advance(cursor, sizeof(*udp));
        payload_offset = ETH_HLEN + ip_header_length + 8;
        payload_length = ip->tlen - ip_header_length - 8;
        dport = udp->dport;
        sport = udp->sport;
        saddr = ip -> src;
        daddr = ip -> dst;
        int len = payload_length;
        FILTER_PORT
        struct perf_data data = {.len = len, .dir = skb->ingress_ifindex};
        skb_events.perf_submit_skb(skb, skb->len, &data, sizeof(data));
    }
    
/* keep the packet and send it to userspace returning -1 */
KEEP:
    return -1;

/* drop the packet returning 0 */
DROP:
    return 0;
}

"""

from ctypes import *
import ctypes as ct
import sys
import socket
import os
import struct
import ipaddress
import ctypes
from datetime import datetime
from struct import unpack

out = sys.stdout
if args.file:
    out = open(args.file,"w+")
if args.ports:
    dports = [int(port) for port in args.ports.split(',')]
    dports_if = ' && '.join([f'dport != {port} && sport != {port}' for port in dports])
    bpf_text = bpf_text.replace('FILTER_PORT',
        'if (%s) { goto KEEP; }' % dports_if)
else:
    bpf_text = bpf_text.replace('FILTER_PORT',"")

bpf = BPF(text=bpf_text)

function_skb_matching = bpf.load_func("packet_monitor", BPF.SOCKET_FILTER)

BPF.attach_raw_socket(function_skb_matching, args.device)

def payload_info(cpu, data, size):
    class SkbEvent(ct.Structure):
        _fields_ = [
            ("len", ct.c_uint32),
            ("dir", ct.c_uint32),
            ("raw", ct.c_ubyte * (size - 2*ct.sizeof(ct.c_uint32))),
        ]
    try:
        sk = ct.cast(data, ct.POINTER(SkbEvent)).contents
        ip_packet = bytes(sk.raw[14:])
        (length, _, _, _, _, proto, _, saddr, daddr) = unpack('!BBHLBBHLL', ip_packet[:20])
        len_iph = length & 15
        # Length is written in 32-bit words, convert it to bytes:
        len_iph = len_iph * 4
        saddr = ".".join(map(str, [saddr >> 24 & 0xff, saddr >> 16 & 0xff, saddr >> 8 & 0xff, saddr & 0xff]))
        daddr = ".".join(map(str, [daddr >> 24 & 0xff, daddr >> 16 & 0xff, daddr >> 8 & 0xff, daddr & 0xff]))
        udp_packet = ip_packet[len_iph:]
        sport = int.from_bytes(udp_packet[0:2],"big")
        dport = int.from_bytes(udp_packet[2:4],"big")
        payload = udp_packet[8:]
        packet_nums = int(sk.len/PACKET_SIZE)
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
            dir = sk.dir
            print(f"{ts},{saddr},{daddr},{sport},{dport},{seq},{epoch},{microseconds},{dir},",file=out,flush=True)
    except ValueError:
        return "Invalid input"
try:
    bpf["skb_events"].open_perf_buffer(payload_info)
    print("timestamp,saddr,daddr,sport,dport,sequence,epoch,microseconds,direction",file=out,flush=True)
    while True :
        bpf.perf_buffer_poll()
        
except KeyboardInterrupt:
    sys.stdout.close()
    pass