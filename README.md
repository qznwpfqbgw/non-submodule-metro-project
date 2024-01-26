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
  Type: "TCPv1" # This will match the key of Config
  LogDir: logs
  Device: [] # For mobileInsight
  TcpDump:
    - Interface: enp4s0 # -i 
      Port: "1234" # port
      FileSize: "500" # -C
    - Interface: eth0 # -i 
      Port: "'(1234 or 2468)'" # port
      FileSize: "500" # -C
```
* Default: The global setting
* Type: The experiment type. This will match the key of config
* LogDir: The log directory path
* Device: The device name that mobileinsight run on
* TcpDump: The array of tcpdump config

Experiment Setting
```yaml
TCPv1:
  Entry: "iperf3" # Executable binary file or command
  Bitrate:
    Flag: -b
    Value: 1M
  Mode:
    Flag: -c
    Value: "127.0.0.1"
  LogDir:
    Flag: --logfile
```
* Entry: The execute command
* [].Flag: The command flag
* [].Value: The correspond value of the flag
* LogDir: The flag to pass the log directory path setting in global setting

### Execute
The default config file is config.yml
```bash
sudo ./main.py
```
or
```bash
sudo ./main.py -c config.yml
```