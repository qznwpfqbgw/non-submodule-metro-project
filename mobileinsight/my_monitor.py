from mobileinsight.base_monitor import BaseMonitor

class MyMonitor(BaseMonitor):
    def setup(self):
        super().setup()
        self.src.enable_log("5G_NR_RRC_OTA_Packet")
        self.src.enable_log("LTE_RRC_OTA_Packet")
        self.src.enable_log("WCDMA_RRC_OTA_Packet")
        self.src.enable_log("5G_NR_ML1_Searcher_Measurement_Database_Update_Ext")
        self.src.enable_log('LTE_PHY_Connected_Mode_Intra_Freq_Meas')
        