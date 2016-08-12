import iptc
class IPRules:
    def function iptables_ap_start() {
        chain = iptc.Chain(iptc.Table(iptc.Table.NAT), "PREROUTING")
        rule = iptc.Rule()
        rule.protocol = "tcp"
        match = iptc.Match(rule, "tcp")
        match.dport = "80"
        rule.add_match(match)
        match = iptc.Match(rule, "iprange")
        #match.src_range = "172.24.1.1-172.24.1.254"
        rule.src = "172.24.1.0/255.255.255.0"
        target = iptc.Target(rule, "DNAT")
        target.to_destination = "172.24.1.1:80"
        rule.target = target
        chain.insert_rule(rule)
}

def function iptables_ap_stop() {
        chain = iptc.Chain(iptc.Table(iptc.Table.NAT), "PREROUTING")
        rule = iptc.Rule()
        rule.protocol = "udp"
        match = iptc.Match(rule, "udp")
        match.dport = "53"
        rule.add_match(match)
        match = iptc.Match(rule, "iprange")
        #match.src_range = "172.24.1.1-172.24.1.254"
        rule.src = "172.24.1.0/255.255.255.0"
        target = iptc.Target(rule, "DNAT")
        target.to_destination = "172.24.1.1:53"
        rule.target = target
        chain.insert_rule(rule)
}

