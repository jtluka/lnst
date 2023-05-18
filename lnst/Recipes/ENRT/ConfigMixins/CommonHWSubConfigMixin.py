from lnst.Recipes.ENRT.ConfigMixins.ParallelStreamQDiscHWConfigMixin import (
    ParallelStreamQDiscHWConfigMixin,
)
from lnst.Recipes.ENRT.ConfigMixins.DevInterruptHWConfigMixin import (
    DevInterruptHWConfigMixin,
)
from lnst.Recipes.ENRT.ConfigMixins.CoalescingHWConfigMixin import (
    CoalescingHWConfigMixin,
)
from lnst.Recipes.ENRT.ConfigMixins.MTUHWConfigMixin import MTUHWConfigMixin
from lnst.Recipes.ENRT.ConfigMixins.PauseFramesHWConfigMixin import (
    PauseFramesHWConfigMixin,
)
from lnst.Recipes.ENRT.ConfigMixins.DevQueuesConfigMixin import (
    DevQueuesConfigMixin,
)
from lnst.Recipes.ENRT.ConfigMixins.DevNfcRxFlowHashConfigMixin import (
    DevNfcRxFlowHashConfigMixin,
)
from lnst.Recipes.ENRT.ConfigMixins.DevRxHashFunctionConfigMixin import (
    DevRxHashFunctionConfigMixin,
)



class CommonHWSubConfigMixin(
    DevRxHashFunctionConfigMixin,
    DevNfcRxFlowHashConfigMixin,
    DevQueuesConfigMixin,
    PauseFramesHWConfigMixin,
    ParallelStreamQDiscHWConfigMixin,
    DevInterruptHWConfigMixin,
    CoalescingHWConfigMixin,
    MTUHWConfigMixin,
):
    """
    This class groups few related :any:`BaseSubConfigMixin` s for user's
    convenience. For more details, see the documentation of the individual
    ancestor classes.
    """
    pass
