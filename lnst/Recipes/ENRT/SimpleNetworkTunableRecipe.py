from lnst.Recipes.ENRT.SimpleNetworkRecipe import BaseSimpleNetworkRecipe

from lnst.Recipes.ENRT.ConfigMixins.MultiCoalescingHWConfigMixin import (
    MultiCoalescingHWConfigMixin
)
from lnst.Recipes.ENRT.ConfigMixins.MultiDevInterruptHWConfigMixin import (
    MultiDevInterruptHWConfigMixin,
)
from lnst.Recipes.ENRT.ConfigMixins.DevRxHashFunctionConfigMixin import (
    DevRxHashFunctionConfigMixin,
)
from lnst.Recipes.ENRT.ConfigMixins.DevNfcRxFlowHashConfigMixin import (
    DevNfcRxFlowHashConfigMixin,
)
from lnst.Recipes.ENRT.ConfigMixins.DevQueuesConfigMixin import (
    DevQueuesConfigMixin,
)
from lnst.Recipes.ENRT.ConfigMixins.OffloadSubConfigMixin import (
    OffloadSubConfigMixin,
)
from lnst.Recipes.ENRT.ConfigMixins.MTUHWConfigMixin import MTUHWConfigMixin
from lnst.Recipes.ENRT.ConfigMixins.PauseFramesHWConfigMixin import (
    PauseFramesHWConfigMixin,
)


class SimpleNetworkTunableRecipe(
    DevRxHashFunctionConfigMixin,
    DevNfcRxFlowHashConfigMixin,
    DevQueuesConfigMixin,
    PauseFramesHWConfigMixin,
    MultiCoalescingHWConfigMixin,
    MultiDevInterruptHWConfigMixin,
    MTUHWConfigMixin,
    OffloadSubConfigMixin,
    BaseSimpleNetworkRecipe,
):
    """
    This recipe implements Enrt testing for a simple network scenario that looks
    as follows

    .. code-block:: none

                    +--------+
             +------+ switch +-----+
             |      +--------+     |
          +--+-+                 +-+--+
        +-|eth0|-+             +-|eth0|-+
        | +----+ |             | +----+ |
        | host1  |             | host2  |
        +--------+             +--------+

    The recipe is similar to :any:`SimpleNetworkRecipe` with better control over
    the tuning of device settings such as:
    * device queues - :any:`DevQueuesConfigMixin`
    * nfc rx flow hash - :any:`DevNfcRxFlowHashConfigMixin`
    * rx hash function - :any:`DevRxHashFunctionConfigMixin`
    * per-device IRQ pinning - :any:`MultiDevInterruptHWConfigMixin`
    * per-device coalescing setting through :any:`MultiCoalescingHWConfigMixin`
    """
    @property
    def dev_nfc_rx_flow_hash_config_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]

    @property
    def dev_queues_config_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]

    @property
    def dev_rx_hash_function_config_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]

    @property
    def mtu_hw_config_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]

    @property
    def pause_frames_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]

    @property
    def offload_nics(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]

    @property
    def coalescing_hw_config_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]

    @property
    def dev_interrupt_hw_config_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]
