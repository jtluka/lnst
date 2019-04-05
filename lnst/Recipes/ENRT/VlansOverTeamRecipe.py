"""
Implements scenario similar to regression_tests/phase2/
(3_vlans_over_{active_backup,round_robin}_team.xml + 3_vlans_over_team.py)
"""
from lnst.Common.Parameters import Param, IntParam, StrParam
from lnst.Common.IpAddress import ipaddress
from lnst.Controller import HostReq, DeviceReq
from lnst.Recipes.ENRT.BaseEnrtRecipe import BaseEnrtRecipe, EnrtConfiguration
from lnst.Devices import VlanDevice
from lnst.Devices import TeamDevice

class VlansOverTeamRecipe(BaseEnrtRecipe):
    host1 = HostReq()
    host1.eth0 = DeviceReq(label="tnet")
    host1.eth1 = DeviceReq(label="tnet")

    host2 = HostReq()
    host2.eth0 = DeviceReq(label="tnet")

    offload_combinations = Param(default=(
        dict(gro="on", gso="on", tso="on", tx="on"),
        dict(gro="off", gso="on", tso="on", tx="on"),
        dict(gro="on", gso="off", tso="off", tx="on"),
        dict(gro="on", gso="on", tso="off", tx="off")))

    runner_name = StrParam(mandatory = True)

    def test_wide_configuration(self):
        host1, host2 = self.matched.host1, self.matched.host2

        host1.eth0.down()
        host1.eth1.down()
        #The config argument needs to be used with a team device normally (e.g  to specify
        #the runner mode), but it is not used here due to a bug in the TeamDevice module
        host1.team0 = TeamDevice()
        host1.team0.slave_add(host1.eth0)
        host1.team0.slave_add(host1.eth1)
        host1.vlan0 = VlanDevice(realdev=host1.team0, vlan_id=10)
        host1.vlan1 = VlanDevice(realdev=host1.team0, vlan_id=20)

        host2.vlan0 = VlanDevice(realdev=host2.eth0, vlan_id=10)
        host2.vlan1 = VlanDevice(realdev=host2.eth0, vlan_id=20)

        #Due to limitations in the current EnrtConfiguration
        #class, a single vlan test pair is chosen
        configuration = EnrtConfiguration()
        configuration.endpoint1 = host1.vlan0
        configuration.endpoint2 = host2.vlan0

        if "mtu" in self.params:
            for host in (host1, host2):
                host.vlan0.mtu = self.params.mtu
                host.vlan1.mtu = self.params.mtu
            host1.team0.mtu = self.params.mtu
            host2.eth0.mtu = self.params.mtu

        net_addr_1 = "192.168.10"
        net_addr_2 = "192.168.20"
        net_addr6_1 = "fc00:0:0:1"
        net_addr6_2 = "fc00:0:0:2"

        host1.team0.ip_add(ipaddress("1.2.3.4/24"))
        for i, host in enumerate([host1, host2]):
            host.vlan0.ip_add(ipaddress(net_addr_1 + "." + str(i+1) + "/24"))
            host.vlan0.ip_add(ipaddress(net_addr6_1 + "::" + str(i+1) + "/64"))
            host.vlan1.ip_add(ipaddress(net_addr_2 + "." + str(i+1) + "/24"))
            host.vlan1.ip_add(ipaddress(net_addr6_2 + "::" + str(i+1) + "/64"))

        host1.eth0.up()
        host1.eth1.up()
        host1.team0.up()
        host1.vlan0.up()
        host1.vlan1.up()
        host2.eth0.up()
        host2.vlan0.up()
        host2.vlan1.up()

        if "adaptive_rx_coalescing" in self.params:
            for dev in [host1.eth0, host1.eth1, host2.eth0]:
                dev.adaptive_rx_coalescing = self.params.adaptive_rx_coalescing
        if "adaptive_tx_coalescing" in self.params:
            for dev in [host1.eth0, host1.eth1, host2.eth0]:
                dev.adaptive_tx_coalescing = self.params.adaptive_tx_coalescing

        #TODO better service handling through HostAPI
        if "dev_intr_cpu" in self.params:
            for host in [host1, host2]:
                host.run("service irqbalance stop")
            for dev in [host1.eth0, host1.eth1, host2.eth0]:
                self._pin_dev_interrupts(dev, self.params.dev_intr_cpu)

        if self.params.perf_parallel_streams > 1:
            for host, dev in [(host1, host1.eth0), (host1, host1.eth1), (host2, host2.eth0)]:
                host.run("tc qdisc replace dev %s root mq" % dev.name)

        return configuration

    def test_wide_deconfiguration(self, config):
        host1, host2 = self.matched.host1, self.matched.host2

        #TODO better service handling through HostAPI
        if "dev_intr_cpu" in self.params:
            for host in [host1, host2]:
                host.run("service irqbalance start")