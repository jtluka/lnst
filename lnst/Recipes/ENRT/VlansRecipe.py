"""
Implements scenario similar to regression_tests/phase1/
(3_vlans.xml + 3_vlans.py), but 2 Vlans are used
"""
from lnst.Common.Parameters import Param
from lnst.Common.IpAddress import ipaddress
from lnst.Controller import HostReq, DeviceReq
from lnst.Recipes.ENRT.BaseEnrtRecipe import BaseEnrtRecipe, EnrtConfiguration
from lnst.Devices import VlanDevice

class VlansRecipe(BaseEnrtRecipe):
    host1 = HostReq()
    host1.eth0 = DeviceReq(label="net1")

    host2 = HostReq()
    host2.eth0 = DeviceReq(label="net1")

    offload_combinations = Param(default=(
        dict(gro="on", gso="on", tso="on", tx="on", rx="on"),
        dict(gro="off", gso="on", tso="on", tx="on", rx="on"),
        dict(gro="on", gso="off", tso="off", tx="on", rx="on"),
        dict(gro="on", gso="on", tso="off", tx="off", rx="on"),
        dict(gro="on", gso="on", tso="on", tx="on", rx="off")))

    def test_wide_configuration(self):
        host1, host2 = self.matched.host1, self.matched.host2

        host1.eth0.down()
        host1.vlan0 = VlanDevice(realdev=host1.eth0, vlan_id=10)
        host1.vlan1 = VlanDevice(realdev=host1.eth0, vlan_id=20)

        host2.eth0.down()
        host2.vlan0 = VlanDevice(realdev=host2.eth0, vlan_id=10)
        host2.vlan1 = VlanDevice(realdev=host2.eth0, vlan_id=20)

        #Due to limitations in the current EnrtConfiguration
        #class, a single vlan test pair is chosen
        configuration = EnrtConfiguration()
        configuration.endpoint1 = host1.vlan0
        configuration.endpoint2 = host2.vlan0

        if "mtu" in self.params:
            host1.eth0.mtu = self.params.mtu
            host2.eth0.mtu = self.params.mtu
            host1.vlan0.mtu = self.params.mtu
            host1.vlan1.mtu = self.params.mtu
            host2.vlan0.mtu = self.params.mtu
            host2.vlan1.mtu = self.params.mtu

        net_addr_1 = "192.168.10"
        net_addr_2 = "192.168.20"
        net_addr6_1 = "fc00:0:0:1"
        net_addr6_2 = "fc00:0:0:2"

        for i, host in enumerate([host1, host2]):
            host.vlan0.ip_add(ipaddress(net_addr_1 + "." + str(i+1) + "/24"))
            host.vlan0.ip_add(ipaddress(net_addr6_1 + "::" + str(i+1) + "/64"))
            host.vlan1.ip_add(ipaddress(net_addr_2 + "." + str(i+1) + "/24"))
            host.vlan1.ip_add(ipaddress(net_addr6_2 + "::" + str(i+1) + "/64"))

        host1.eth0.up()
        host1.vlan0.up()
        host1.vlan1.up()
        host2.eth0.up()
        host2.vlan0.up()
        host2.vlan1.up()

        if "adaptive_rx_coalescing" in self.params:
            for host in [host1, host2]:
                host.eth0.adaptive_rx_coalescing = self.params.adaptive_rx_coalescing
        if "adaptive_tx_coalescing" in self.params:
            for host in [host1, host2]:
                host.eth0.adaptive_tx_coalescing = self.params.adaptive_tx_coalescing

        #TODO better service handling through HostAPI
        if "dev_intr_cpu" in self.params:
            for host in [host1, host2]:
                host.run("service irqbalance stop")
                self._pin_dev_interrupts(host.eth0, self.params.dev_intr_cpu)

        if self.params.perf_parallel_streams > 1:
            for host in [host1, host2]:
                host.run("tc qdisc replace dev %s root mq" % host.eth0.name)

        return configuration

    def test_wide_deconfiguration(self, config):
        host1, host2 = self.matched.host1, self.matched.host2

        #TODO better service handling through HostAPI
        if "dev_intr_cpu" in self.params:
            for host in [host1, host2]:
                host.run("service irqbalance start")