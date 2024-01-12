from lnst.Recipes.ENRT import SimpleNetworkRecipe
from lnst.Recipes.ENRT.BaseSRIOVNetnsTcRecipe import SRIOVDevices
from lnst.Recipes.ENRT.BaseEnrtRecipe import EnrtConfiguration

class SimpleNetworkVfRecipe(SimpleNetworkRecipe):
    def test_wide_configuration(self):
        # rename host1.eth0 -> host1.eth0_pf
        host1, host2 = self.matched.host1, self.matched.host2
        for host in [host1, host2]:
            tmp_dev = host.eth0
            host._unset(host.eth0)
            host.eth0_pf = tmp_dev

        # create host1.eth0 that is VF
        for host in [host1, host2]:
            host.sriov_devices = SRIOVDevices(host.eth0_pf, 1)
            host.eth0 = host.sriov_devices.vfs[0]

        return super().test_wide_configuration()

    def generate_test_wide_description(self, config: EnrtConfiguration):
        desc = super().generate_test_wide_description(config)
        return desc

    def test_wide_deconfiguration(self, config: EnrtConfiguration):
        for host in [self.matched.host1, self.matched.host2]:
            host.eth0_pf.delete_vfs()
            del host.sriov_devices

        super().test_wide_deconfiguration(config)

    @property
    def pause_frames_dev_list(self):
        return [self.matched.host1.eth0_pf, self.matched.host2.eth0_pf]

