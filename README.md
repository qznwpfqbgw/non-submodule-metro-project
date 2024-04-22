# Moxa Metro Measurement

## Initialization
```
git submodule update --init --recursive
```

## Usage
The experimental settings can be configured through a configuration file, which is written in yaml.

### Example

Global Setting
```yaml
Default:
  Type: ["TCPv1"] # This will match the key of Config
  LogDir: logs
  Device: ['qc01','qc02'] # interface name list, for mobileInsight
  Poll:
    Enable: True
    Interval: 1
  Upload:
    Enable: True
    Date: "" # If Date == "" means yesterday
  TcpDump:
    - Interface:
        Flag: -i
        Value: qc01
      Port:
        Flag: port
        Value: "26425"
      FileSize: 
        Flag: -C
        Value: 50 # MB
      Snaplen: 
        Flag: -s
        Value: 96 # bytes
    - Interface:
        Flag: -i
        Value: qc02
      Port:
        Flag: port
        Value: "'(1234 or 2468)'"
      FileSize: 
        Flag: -C
        Value: 500
      Snaplen: 
        Flag: -s
        Value: 96 # bytes
```
* Default: The global setting
* Type: The experiment type array. This will match the key of config.
* LogDir: The log directory path
* Device: The device(interface) name list that mobileinsight run on
* TcpDump: The array of tcpdump config
* Poll.Enable: Check the process status every Poll.Interval seconds, if one of the process stop, stop all the process.
* Poll.Interval: The interval of checking pcocess
* Upload.Enable: Enable T2
* Upload.Date: Upload the specific date of experiment log. 

Experiment Setting
```yaml
TCPv1:
  Entry: "iperf3" # Executable binary file or command
  LogDir:
    Flag: --logfile
  Bitrate:
    Flag: -b
    Value: 1M
  Mode:
    Flag: -c
    Value: "127.0.0.1"
```
* Entry: The execute command
* LogDir: The flag to pass the log directory path setting in global setting
* Upload: The flag to pass the Upload.Date path setting in global setting
* Customized key
    * Flag: The command flag
    * Value: The correspond value of the flag

### Execute
The default config file is config.yml
```bash
sudo ./main.py
```
or
```bash
sudo ./main.py -c config.yml
```