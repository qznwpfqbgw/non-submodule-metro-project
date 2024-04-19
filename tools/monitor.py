#!/usr/bin/python3
# Filename: online-analysis-example.py
import os
import datetime as dt
import argparse
import json

# Import MobileInsight modules
# from mobile_insight.analyzer import *
from mobile_insight.monitor import OnlineMonitor
from myMsgLogger import MyMsgLogger

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--device", type=str, help="device: e.g. qc00")
    parser.add_argument("-b", "--baudrate", type=int, help='baudrate', default=9600)
    parser.add_argument("-f", "--file", type=str, help='savefile')
    parser.add_argument("-dp", "--decode_file", type=str, help='savefile xml file')
    args = parser.parse_args()

    baudrate = args.baudrate
    dev = args.device
    script_folder = os.path.dirname(os.path.abspath(__file__))
    print(script_folder)
    parent_folder = os.path.dirname(script_folder)
    d2s_path = os.path.join(parent_folder, 'device_setting.json')
    with open(d2s_path, 'r') as f:
        device_to_serial = json.load(f)["device_to_serial"]
        ser = device_to_serial[dev]
        ser = os.path.join("/dev/serial/by-id", f"usb-Quectel_RM500Q-GL_{ser}-if00-port0")
        monitor_funcs = []

    # Initialize a 3G/4G/5G monitor
    src = OnlineMonitor()
    src.set_serial_port(ser)  # the serial port to collect the traces
    src.set_baudrate(baudrate)  # the baudrate of the port
    src.save_log_as(args.file)

    # Enable all
    # src.enable_log_all()

    # Enable 3G/4G/5G RRC (radio resource control) monitoring
    src.enable_log("5G_NR_RRC_OTA_Packet")
    src.enable_log("LTE_RRC_OTA_Packet")
    src.enable_log("WCDMA_RRC_OTA_Packet")
    src.enable_log("LTE_RRC_Serv_Cell_Info")
    src.enable_log("5G_NR_ML1_Searcher_Measurement_Database_Update_Ext")
    src.enable_log('LTE_PHY_Connected_Mode_Intra_Freq_Meas')

    dumper = MyMsgLogger()
    dumper.set_source(src)
    dumper.set_decoding(MyMsgLogger.XML) 
    dumper.set_dump_type(MyMsgLogger.ALL)
    if args.decode_file is not None:
        dumper.save_decoded_msg_as(args.decode_file)
    # Start the monitoring
    src.run()