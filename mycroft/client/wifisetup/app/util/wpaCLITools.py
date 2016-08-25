from collections import defaultdict
from mycroft.client.wifisetup.app.util.bashThreadHandling import bash_command


class wpaClientTools():
    def __init__(self):
        self.name = "name"

    def wpa_cli_flush(self):
        results = bash_command(['wpa_cli', 'flush'])
        return results

    def wpa_cli_scan(self, iface):
        bash_command(['wpa_cli', '-i', iface, 'scan'])
        results = defaultdict(list)
        results = bash_command(
            ['wpa_cli', 'scan_results'])['stdout'].split('\n')
        for result in results:
            results['network'].append()
        return results

    def wpa_cli_status(self, iface):
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

    def wpa_cli_loglevel_debug(self, iface):
        results = bash_command(['wpa_cli', '-i', iface, 'log_level', 'debug'])
        return results

    def wpa_cli_add_network(self, iface):
        results = bash_command(['wpa_cli', '-i', iface, 'add_network'])
        return results

    def wpa_cli_set_network(self, iface,
                            network_id, network_var, network_var_value):
        results = bash_command(['wpa_cli',
                                '-i', iface,
                                'set_network',
                                network_id,
                                network_var,
                                network_var_value])
        return results

    def wpa_cli_enable_network(self, iface, network_id):
        results = bash_command(['wpa_cli', '-i', iface, 'enable', network_id])
        return results

    def wpa_cli_disable_network(self, network_id):
        results = bash_command(['wpa_cli', '-i', iface, 'disable', network_id])
        return results

    def wpa_save_network(self, network_id):
        results = bash_command(['wpa_cli', 'save', network_id])
        return results
