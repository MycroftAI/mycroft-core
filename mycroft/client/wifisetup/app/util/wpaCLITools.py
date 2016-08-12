import time
from bashThreadHandling import bash_command

class wpaClientTools():
    def __init__(self):
        self.name = "name"
    def wpa_cli_flush(self):
        results = bash_command(['wpa_cli','flush'])
        return results

    def wpa_cli_scan(self,iface):
        bash_command(['wpa_cli', '-i', iface, 'scan'])
        results = bash_command(['wpa_cli','scan_results'])
        return results

    def wpa_cli_status(self,iface):
        status = bash_command(['wpa_cli', '-i', iface, 'status'])
        status = status['stdout'].split('\n', 13)
        results = {
            "bssid": status[0].split("=", 1)[1],
            "freq": status[1].split("=", 1)[1],
            "ssid": status[2].split("=", 1)[1],
            "id": status[3].split("=", 1)[1],
            "mode": status[4].split("=", 1)[1],
            "pairwise_cipher": status[5].split("=", 1)[1],
            "group_cipher": status[6].split("=", 1)[1],
            "key_mgmt": status[7].split("=", 1)[1],
            "wpa_state": status[8].split("=", 1)[1],
            "ip_address": status[9].split("=", 1)[1],
            "p2p_device_address": status[10].split("=", 1)[1],
            "address": status[11].split("=", 1)[1],
            "uuid": status[12].split("=", 1)[1]
        }
        return results

    def wpa_cli_loglevel_debug(self,iface):
        results = bash_command(['wpa_cli', '-i', iface, 'log_level', 'debug'])
        return results
    def wpa_cli_add_network(self,iface):
        results = bash_command(['wpa_cli', '-i', iface, 'add_network'])
        return results
    def wpa_cli_set_network(self,iface, network_id, network_var, network_var_value):
        results = bash_command(['wpa_cli', '-i', iface, 'set_network', network_id, network_var, network_var_value])
        return results
    def wpa_cli_enable_network(self,iface, network_id):
        results = bash_command(['wpa_cli', '-i', iface, 'enable', network_id])
        return results
    def wpa_cli_disable_network(self, network_id):
        results = bash_command(['wpa_cli', '-i', iface, 'disable', network_id])
        return results
    def wpa_save_network(self, network_id):
        results = bash_command(['wpa_cli', 'save', network_id])
        return results

def main():
    #print yikes(['ls', '-al', '/root'])
    #print yikes(['ls', '-alh', '.'])
    #print yikes(['ls', '-alx'])
    #print yikes(['/etc/init.d/wpa_supplicant', 'stop'])
    #print "Kill wpa_supplicant: " + str(yikes(['pkill', '-f', '"wpa_supplicant"']))
    #print "IFDown wlan0: " + str(yikes(['ifdown', 'wlan0']))
    #print "IFconfig wlan0 up: " + str(yikes(['ifconfig', 'wlan0', 'up']))
    #print "Remove wpa_supplicant lock: " + str(yikes(['rm', '-v', '/var/run/wpa_supplicant/wlan0']))
    #print "Connect to WiFi: " + str(yikes(['wpa_supplicant', '-iwlan0', '-Dnl80211', '-c', '/etc/wpa_supplicant/wpa_supplicant.conf']))
   # print yikes(['dnsmasq'])
   # print yikes(['ifdown', 'uap0'])
   # print yikes(['iw', 'dev', 'wlp3s0', 'interface', 'add', 'uap4', 'type', '__ap'])
   # print yikes(['dig', '@8.8.8.8', 'cerberus.mycroft.ai'])
    #print yikes(['ping', '-c', '2','www.google.com'])
    interface = "wlan0"
    ssid = '"Entrepreneur"'
    password = '"startsomething"'
    #print "try wpa_cli set debug level : " + str(yikes(['wpa_cli', 'log_level', 'debug' ]))
    #network_id = str(yikes(['wpa_cli', '-i', 'wlan0', 'add_network']))
    #print "Set SSID: " + str(yikes(['wpa_cli', '-i', 'wlan0', 'set_network', int(network_id), 'ssid', '"Entrepreneur"']))
    #print "Set PASSWORD: " + str(yikes(['wpa_cli', '-i', 'wlan0', 'set_network', int(network_id), 'psk', '"startsomething']))
    #print "try wpa_cli status: " + str(yikes(['wpa_cli', '-i', 'wlan0', 'status']))
    #networks = wpa_cli_scan(interface)
    #print networks
    WiFi = wpaClientTools()
    print WiFi.wpa_cli_loglevel_debug(interface)
    #status = wpa_cli_status(interface)['stdout'].split('\n', 13)
    network_id = WiFi.wpa_cli_add_network(interface)
    #print network_id
    #print wpa_cli_flush()
    print WiFi.wpa_cli_set_network(interface, network_id, 'ssid', ssid)
    print WiFi.wpa_cli_set_network(interface, network_id, 'psk', password)
    print WiFi.wpa_cli_enable_network(interface, network_id)
    #print wpa_cli_status(interface)
    #print wpa_cli_disable_network(interface, network_id)
    #print wpa_cli_status(interface)['stdout'].strip()
    while True:
        time.sleep(6)
        try:
            if WiFi.wpa_cli_status(interface)['wpa_state'] == 'COMPLETED':
                print "CONNECTED"
        except:
            print "no"



if __name__ == "__main__":
    main()
