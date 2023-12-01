from lnst.Recipes.ENRT.BaseSRIOVNetnsTcRecipe import BaseSRIOVNetnsTcRecipe

from itertools import product

def tc_flower_redirect_arp(
    on_device,
    src_device,
    dst_device,
    redirect_device,
    skip_path,
):
    for dev, src_dev, dst_dev, redir_dev in [
            (on_device, src_device, dst_device, redirect_device),
            (redirect_device, dst_device, src_device, on_device),
        ]:
        for src_mac, dst_mac in product(
                [src_dev.hwaddr],
                [dst_dev.hwaddr, "FF:FF:FF:FF:FF:FF"],
            ):
            dev.netns.run(
                f"tc filter add dev {dev.name} protocol arp ingress "
                f"flower {skip_path} src_mac {src_mac} dst_mac {dst_mac} "
                f"action mirred egress redirect dev {redir_dev.name}"
            )

def tc_flower_redirect_ip(
    on_device,
    src_device,
    dst_device,
    redirect_device,
    skip_path,
):
    for dev, dev_name, src_mac, dst_mac, redir_dev_name in [
            (on_device, on_device.name, src_device.hwaddr, dst_device.hwaddr, redirect_device.name),
            (redirect_device, redirect_device.name, dst_device.hwaddr, src_device.hwaddr, on_device.name),
        ]:
        dev.netns.run(
            f"tc filter add dev {dev_name} protocol ip ingress "
            f"flower {skip_path} src_mac {src_mac} dst_mac {dst_mac} "
            f"action mirred egress redirect dev {redir_dev_name}"
        )


class SRIOVNetnsTcRecipe(BaseSRIOVNetnsTcRecipe):
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
    def add_tc_filter_rules(self, config):
        host1, host2 = self.matched.host1, self.matched.host2

        config.ingress_devices = []
        for host in [host1, host2]:
            sriov_devices = self.sriov_devices[host]
            host.run(f"tc qdisc add dev {sriov_devices.vf_reps[0].name} ingress")
            host.run(f"tc qdisc add dev {host.eth0.name} ingress")
            config.ingress_devices.extend([sriov_devices.vf_reps[0], host.eth0])

        host1_vf_dev, host1_vf_rep_dev = self.sriov_devices[host1][0]
        host2_vf_dev, host2_vf_rep_dev = self.sriov_devices[host2][0]

        tc_flower_redirect_arp(
            host1.eth0,
            host2_vf_dev,
            host1_vf_dev,
            host1_vf_rep_dev,
            "skip_sw"
        )

        tc_flower_redirect_arp(
            host2.eth0,
            host1_vf_dev,
            host2_vf_dev,
            host2_vf_rep_dev,
            "skip_sw"
        )

        tc_flower_redirect_ip(
            host1.eth0,
            host2_vf_dev,
            host1_vf_dev,
            host1_vf_rep_dev,
            "skip_sw"
        )

        tc_flower_redirect_ip(
            host2.eth0,
            host1_vf_dev,
            host2_vf_dev,
            host2_vf_rep_dev,
            "skip_sw"
        )

    @property
    def pause_frames_dev_list(self):
        return [self.sriov_devices[self.matched.host1].vfs[0], self.sriov_devices[self.matched.host2].vfs[0]]

    @property
    def offload_nics(self):
        return [self.sriov_devices[self.matched.host1].vfs[0], self.sriov_devices[self.matched.host2].vfs[0]]

    @property
    def mtu_hw_config_dev_list(self):
        return [self.sriov_devices[self.matched.host1].vfs[0], self.sriov_devices[self.matched.host2].vfs[0]]

    @property
    def coalescing_hw_config_dev_list(self):
        return [self.sriov_devices[self.matched.host1].vfs[0], self.sriov_devices[self.matched.host2].vfs[0]]

    @property
    def dev_interrupt_hw_config_dev_list(self):
        return [self.sriov_devices[self.matched.host1].vfs[0], self.sriov_devices[self.matched.host2].vfs[0]]

    @property
    def parallel_stream_qdisc_hw_config_dev_list(self):
        return [self.sriov_devices[self.matched.host1].vfs[0], self.sriov_devices[self.matched.host2].vfs[0]]
