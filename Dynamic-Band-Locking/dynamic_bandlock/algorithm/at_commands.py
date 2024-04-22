import os, subprocess
import re

class AT_Cmd_Runner():

    def __init__(self, folder):
        self.dir_name = folder
        self.band_setting_sh = os.path.join(self.dir_name, 'band-setting.sh')
        self.get_pci_freq_sh = os.path.join(self.dir_name, 'get-pci-freq.sh')
    
    def run_at_with_timeout(self, cmd, t_out=0.5):
        try: out = subprocess.check_output(cmd, shell=True, timeout=t_out)
        except subprocess.TimeoutExpired:
            out = None
        return out
        
    # Query modem current band setting
    def query_band(self, dev):
        cmd = f'{self.band_setting_sh} -i {dev}'
        out = self.run_at_with_timeout(cmd, t_out=0.5)
        if not out:
            print(f'Query Initial Band Setting of {dev} Failed')
            return None
        out = out.decode('utf-8')
        inds = [m.start() for m in re.finditer("lte_band", out)]
        inds2 = [m.start() for m in re.finditer("\r", out)]
        result = out[inds[1]+len('"lte_band"'):inds2[2]]
        print(f'Current Band Setting of {dev} is {result}')
        return result
    
    # Use AT command to query modem current serving pci, earfcn
    def query_pci_earfcn(self, dev):
        cmd = f'{self.get_pci_freq_sh} -i {dev}'
        out = self.run_at_with_timeout(cmd, t_out=0.5)
        if not out:
            print(f'Query Initial pci/earfcn of {dev} Failed')
            return None
        out = out.decode('utf-8')
        out = out.split('\n')
        
        if len(out) == 7: # ENDC Mode
            lte_info = out[2].split(',')
            nr_info = out[3].split(',')
            pci, earfcn, band = lte_info[5], lte_info[6], lte_info[7]
            nr_pci = nr_info[3]
            return (pci, earfcn, band, nr_pci)
        elif len(out) == 5: # LTE Mode
            lte_info = out[1].split(',')
            pci, earfcn, band = lte_info[7], lte_info[8], lte_info[9]
            return (pci, earfcn, band)

    # Change band function
    def change_band(self, dev, band, setting):
        cmd = f'{self.band_setting_sh} -i {dev} -l {band}'
        out = self.run_at_with_timeout(cmd, t_out=0.2)
        if out:
            print(f"**********Change {dev} from {setting} to {band}.**********")
        else:
            print('Action Failed')
        return out

        