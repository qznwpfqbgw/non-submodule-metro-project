from mobile_insight.monitor import OnlineMonitor

class BaseMonitor:
    def __init__(self, ser, baudrate, log_path) -> None:
        self.src = OnlineMonitor()
        self.src.set_serial_port(ser)  # the serial port to collect the traces
        self.src.set_baudrate(baudrate)  # the baudrate of the port
        self.src.save_log_as(log_path)
        self.setup()
    
    def setup(self):
        pass
        
    def run_monitor(self):
        self.src.run()