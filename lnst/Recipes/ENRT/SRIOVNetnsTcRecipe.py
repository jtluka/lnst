from collections.abc import Collection
import time

from lnst.Common.Parameters import (
    Param,
    StrParam,
    IPv4NetworkParam,
    IPv6NetworkParam,
)
from lnst.Common.IpAddress import interface_addresses
from lnst.Controller import HostReq, DeviceReq, RecipeParam
from lnst.Controller.NetNamespace import NetNamespace
from lnst.RecipeCommon.endpoints import EndpointPair, IPEndpoint
from lnst.Recipes.ENRT.helpers import ip_endpoint_pairs
from lnst.Recipes.ENRT.BaremetalEnrtRecipe import BaremetalEnrtRecipe
from lnst.RecipeCommon.Ping.PingEndpoints import PingEndpoints
from lnst.Recipes.ENRT.BaseEnrtRecipe import EnrtConfiguration
from lnst.Recipes.ENRT.ConfigMixins.OffloadSubConfigMixin import (
    OffloadSubConfigMixin,
)
from lnst.Recipes.ENRT.ConfigMixins.CommonHWSubConfigMixin import (
    CommonHWSubConfigMixin,
)


class SRIOVNetnsTcRecipe(
    CommonHWSubConfigMixin, OffloadSubConfigMixin, BaremetalEnrtRecipe
):
    """
    This recipe implements Enrt testing for a SRIOV network scenario
    with VF located in the network namespace to mimic container network.
    Tc rules are created to achieve full connectivity between VF of
    the hosts.

    .. code-block:: none

                      +--------+
               +------+ switch +-------+
               |      +--------+       |
       +-------|------+        +-------|------+
       |    +--|--+   |        |    +--|--+   |
    +--|----|eth0|--- |--+  +--|----|eth0|--- |--+
    |  |    +----+    |  |  |  |    +----+    |  |
    |  |       |      |  |  |  |       |      |  |
    |  |vf_representor|  |  |  |vf_representor|  |
    |  |              |  |  |  |              |  |
    |  +--TC filter---+  |  |  +--TC filter---+  |
    |         |          |  |         |          |
    |    +-namespace-+   |  |    +-namespace-+   |
    |   |    vf0     |   |  |   |    vf0     |   |
    |   +-----------+    |  |   +-----------+    |
    |      host1         |  |       host2        |
    +--------------------+  +--------------------+

    All sub configurations are included via Mixin classes.

    The actual test machinery is implemented in the :any:`BaseEnrtRecipe` class.
    """
    host1 = HostReq()
    host1.eth0 = DeviceReq(label="net1", driver=RecipeParam("driver"))

    host2 = HostReq()
    host2.eth0 = DeviceReq(label="net1", driver=RecipeParam("driver"))

    """
    This parameter was created due to the difference between various kernel and distro
    versions, not having consistent naming scheme of virtual function.

    Solution here is to expect deterministic VF name, which is derived from the PF name.
    With specific kernel parameter `biosdevname=1` we can expect default suffix on
    VF to be created to be `_n`, where n is the index of VF created.
    """
    vf_suffix = StrParam(default="_0")

    offload_combinations = Param(default=(
        dict(gro="on", gso="on", tso="on", tx="on", rx="on"),
        dict(gro="off", gso="on", tso="on", tx="on", rx="on"),
        dict(gro="on", gso="off", tso="off", tx="on", rx="on"),
        dict(gro="on", gso="on", tso="off", tx="off", rx="on"),
        dict(gro="on", gso="on", tso="on", tx="on", rx="off")))

    net_ipv4 = IPv4NetworkParam(default="192.168.101.0/24")
    net_ipv6 = IPv6NetworkParam(default="fc00::/64")

    def test_wide_configuration(self):
        """
        Test wide configuration for this recipe involves switching the device to switchdev
        mode, adding single VF and mapping the VF, as well as its representor.
        New namespace is created to mimic container networking, where the VF is moved.
        Next, VF is assigned an IPv4 and IPv6 address on both hosts.
        Tc qdiscs and filters are used to bypass the software path and instead
        use the tc hardware offload functionality in the network devices.

        host1.eth0 = 192.168.101.1/24 and fc00::1/64

        host2.eth0 = 192.168.101.2/24 and fc00::2/64
        """
        host1, host2 = self.matched.host1, self.matched.host2
        config = super().test_wide_configuration()

        ipv4_addr = interface_addresses(self.params.net_ipv4)
        ipv6_addr = interface_addresses(self.params.net_ipv6)

        for host in [host1, host2]:
            host.run(f"devlink dev eswitch set pci/{host.eth0.bus_info} mode switchdev")
            time.sleep(2)
            host.run(f"echo 1 > /sys/class/net/{host.eth0.name}/device/sriov_numvfs")
            time.sleep(3)

            vf_ifname = dict(ifname=f"{host.eth0.name}{self.params.vf_suffix}")
            host.map_device("vf_eth0", vf_ifname)

            host.newns = NetNamespace("lnst")
            host.newns.vf_eth0 = host.vf_eth0

            vf_representor_ifname = dict(ifname="eth0")
            host.map_device("vf_representor_eth0", vf_representor_ifname)

            host.run(f"ethtool -K {host.vf_representor_eth0.name} hw-tc-offload on")
            host.run(f"ethtool -K {host.eth0.name} hw-tc-offload on")

            host.run(f"tc qdisc add dev {host.vf_representor_eth0.name} ingress")
            host.run(f"tc qdisc add dev {host.eth0.name} ingress")

            for dev in [host.eth0, host.newns.vf_eth0, host.vf_representor_eth0]:
                dev.up()

            config.configure_and_track_ip(host.newns.vf_eth0, next(ipv4_addr))
            config.configure_and_track_ip(host.newns.vf_eth0, next(ipv6_addr))

        host1.run(f"tc filter add dev {host1.eth0.name} "
                  f"protocol ip ingress flower skip_sw "
                  f"src_mac {host2.newns.vf_eth0.hwaddr} "
                  f"dst_mac {host1.newns.vf_eth0.hwaddr} "
                  f"action mirred egress redirect dev {host1.vf_representor_eth0.name}")

        host1.run(f"tc filter add dev {host1.eth0.name} "
                  f"protocol arp ingress flower "
                  f"src_mac {host2.newns.vf_eth0.hwaddr} "
                  f"dst_mac {host1.newns.vf_eth0.hwaddr} "
                  f"action mirred egress redirect dev {host1.vf_representor_eth0.name}")

        host1.run(f"tc filter add dev {host1.eth0.name} "
                  f"protocol arp ingress flower "
                  f"src_mac {host2.newns.vf_eth0.hwaddr} "
                  f"dst_mac FF:FF:FF:FF:FF:FF "
                  f"action mirred egress redirect dev {host1.vf_representor_eth0.name}")

        host1.run(f"tc filter add dev {host1.vf_representor_eth0.name} "
                  f"protocol ip ingress flower skip_sw "
                  f"src_mac {host1.newns.vf_eth0.hwaddr} "
                  f"dst_mac {host2.newns.vf_eth0.hwaddr} "
                  f"action mirred egress redirect dev {host1.eth0.name}")

        host1.run(f"tc filter add dev {host1.vf_representor_eth0.name} "
                  f"protocol arp ingress flower "
                  f"src_mac {host1.newns.vf_eth0.hwaddr} "
                  f"dst_mac {host2.newns.vf_eth0.hwaddr} "
                  f"action mirred egress redirect dev {host1.eth0.name}")

        host1.run(f"tc filter add dev {host1.vf_representor_eth0.name} "
                  f"protocol arp ingress flower "
                  f"src_mac {host1.newns.vf_eth0.hwaddr} "
                  f"dst_mac FF:FF:FF:FF:FF:FF "
                  f"action mirred egress redirect dev {host1.eth0.name}")

        host2.run(f"tc filter add dev {host2.eth0.name} "
                  f"protocol ip ingress flower skip_sw "
                  f"src_mac {host1.newns.vf_eth0.hwaddr} "
                  f"dst_mac {host2.newns.vf_eth0.hwaddr} "
                  f"action mirred egress redirect dev {host2.vf_representor_eth0.name}")

        host2.run(f"tc filter add dev {host2.eth0.name} "
                  f"protocol arp ingress flower "
                  f"src_mac {host1.newns.vf_eth0.hwaddr} "
                  f"dst_mac {host2.newns.vf_eth0.hwaddr} "
                  f"action mirred egress redirect dev {host2.vf_representor_eth0.name}")

        host2.run(f"tc filter add dev {host2.eth0.name} "
                  f"protocol arp ingress flower "
                  f"src_mac {host1.newns.vf_eth0.hwaddr} "
                  f"dst_mac FF:FF:FF:FF:FF:FF "
                  f"action mirred egress redirect dev {host2.vf_representor_eth0.name}")

        host2.run(f"tc filter add dev {host2.vf_representor_eth0.name} "
                  f"protocol ip ingress flower skip_sw "
                  f"src_mac {host2.newns.vf_eth0.hwaddr} "
                  f"dst_mac {host1.newns.vf_eth0.hwaddr} "
                  f"action mirred egress redirect dev {host2.eth0.name}")

        host2.run(f"tc filter add dev {host2.vf_representor_eth0.name} "
                  f"protocol arp ingress flower "
                  f"src_mac {host2.newns.vf_eth0.hwaddr} "
                  f"dst_mac {host1.newns.vf_eth0.hwaddr} "
                  f"action mirred egress redirect dev {host2.eth0.name}")

        host2.run(f"tc filter add dev {host2.vf_representor_eth0.name} "
                  f"protocol arp ingress flower "
                  f"src_mac {host2.newns.vf_eth0.hwaddr} "
                  f"dst_mac FF:FF:FF:FF:FF:FF "
                  f"action mirred egress redirect dev {host2.eth0.name}")

        self.wait_tentative_ips(config.configured_devices)

        return config

    def generate_test_wide_description(self, config: EnrtConfiguration):
        desc = super().generate_test_wide_description(config)
        for host in [self.matched.host1, self.matched.host2]:
            desc += [
                f"Configured {host.hostid}.{host.eth0.name}.driver = switchdev\n"
                f"Created virtual function on {host.hostid}.{host.eth0.name} = {host.newns.vf_eth0.name}\n"
                f"Created network_namespace on {host.hostid} = {host.newns.name}\n"
                f"Moved interface {host.newns.vf_eth0.name} from {host.hostid} root namespace to {host.hostid}.{host.newns.name} namespace\n"
                f"Created tc rules for the connectivity between virtual functions\n"
            ]
        desc += [
            f"Configured {dev.host.hostid}.{dev.name}.ips = {dev.ips}"
            for dev in config.configured_devices
        ]
        return desc

    def test_wide_deconfiguration(self, config):
        """
        Test wide deconfiguration means deleting the Linux bridge and returning the
        control over the physical function to base driver.
        Finally virtual function is deleted.
        """
        for host in [self.matched.host1, self.matched.host2]:
            host.run(f"echo 0 > /sys/class/net/{host.eth0.name}/device/sriov_numvfs")
            time.sleep(2)
            host.run(f"tc qdisc del dev {host.eth0.name} ingress")
            time.sleep(2)
            host.run(f"devlink dev eswitch set pci/{host.eth0.bus_info} mode legacy")
            time.sleep(3)

        super().test_wide_deconfiguration(config)

    def generate_ping_endpoints(self, config):
        """
        The ping endpoints for this recipe are simply the two matched NICs:

        host1.newns.vf_eth0 and host2.newns.vf_eth0

        Returned as::

            [PingEndpoints(self.matched.host1.eth0, self.matched.host2.eth0)]
        """
        return [PingEndpoints(self.matched.host1.newns.vf_eth0, self.matched.host2.newns.vf_eth0)]

    def generate_perf_endpoints(self, config: EnrtConfiguration) -> list[Collection[EndpointPair[IPEndpoint]]]:
        """
        The perf endpoints for this recipe are simply the two matched NICs:

        host1.newns.vf_eth0 and host2.newns.vf_eth0
        """
        return [ip_endpoint_pairs(config, (self.matched.host1.newns.vf_eth0, self.matched.host2.newns.vf_eth0))]

    @property
    def pause_frames_dev_list(self):
        return [self.matched.host1.newns.vf_eth0, self.matched.host2.newns.vf_eth0]

    @property
    def offload_nics(self):
        return [self.matched.host1.newns.vf_eth0, self.matched.host2.newns.vf_eth0]

    @property
    def mtu_hw_config_dev_list(self):
        return [self.matched.host1.newns.vf_eth0, self.matched.host2.newns.vf_eth0]

    @property
    def coalescing_hw_config_dev_list(self):
        return [self.matched.host1.newns.vf_eth0, self.matched.host2.newns.vf_eth0]

    @property
    def dev_interrupt_hw_config_dev_list(self):
        return [self.matched.host1.newns.vf_eth0, self.matched.host2.newns.vf_eth0]

    @property
    def parallel_stream_qdisc_hw_config_dev_list(self):
        return [self.matched.host1.newns.vf_eth0, self.matched.host2.newns.vf_eth0]
