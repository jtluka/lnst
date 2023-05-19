from lnst.Common.Parameters import BoolParam, DictParam

from lnst.Recipes.ENRT.ConfigMixins.BaseHWConfigMixin import BaseHWConfigMixin


class CoalescingHWConfigMixin(BaseHWConfigMixin):
    """
    This class is an extension to the :any:`BaseEnrtRecipe` class that enables
    adaptive coalescing configuration on the devices defined by
    :attr:`coalescing_hw_config_dev_list` property.

    :param adaptive_tx_coalescing:
        (optional test parameter) boolean to enable/disable TX adaptive
        coalescing on the devices
    :param adaptive_rx_coalescing:
        (optional test parameter) boolean to enable/disable RX adaptive
        coalescing on the devices
    """

    adaptive_rx_coalescing = BoolParam(mandatory=False)
    adaptive_tx_coalescing = BoolParam(mandatory=False)
    coalescing_settings = DictParam(mandatory=False)

    @property
    def coalescing_hw_config_dev_list(self):
        """
        The value of this property is a list of devices for which the
        adaptive coalescing features should be configured. It has to be
        defined by a derived class.
        """
        return []

    def hw_config(self, config):
        super().hw_config(config)

        for param in ["adaptive_rx_coalescing", "adaptive_tx_coalescing"]:
            param_value = getattr(self.params, param, None)
            if param_value is not None:
                self._configure_dev_attribute(
                    config,
                    self.coalescing_hw_config_dev_list,
                    param,
                    param_value
                )

        for param, param_value in self.params.get("coalescing_settings", {}).items():
            self._configure_dev_attribute(
                config,
                self.coalescing_hw_config_dev_list,
                coalescing_param_to_device_attribute(param),
                param_value
            )

    def hw_deconfig(self, config):
        for param, _ in self.params.get("coalescing_settings", {}).items():
            self._deconfigure_dev_attribute(
                config,
                self.coalescing_hw_config_dev_list,
                coalescing_param_to_device_attribute(param),
            )

        for feature in ['adaptive_rx_coalescing', 'adaptive_tx_coalescing']:
            self._deconfigure_dev_attribute(
                config,
                self.coalescing_hw_config_dev_list,
                feature,
            )

        super().hw_deconfig(config)

    def describe_hw_config(self, config):
        desc = super().describe_hw_config(config)
        for param in ["adaptive_rx_coalescing", "adaptive_tx_coalescing"]:
            desc.extend(
                self._describe_dev_attribute(config, param)
            )

        for param in self.params.get("coalescing_settings", {}).keys():
            self._describe_dev_attribute(config, coalescing_param_to_device_attribute(param))

        return desc

def coalescing_param_to_device_attribute(param):
    """
    This mixin accepts the coalesce_settings keys in 'ethtool -C' format
    The Device class uses more descriptive property names along with
    underscores, so we need to translate the keys to property names
    """
    return "coalescing_" + param.replace("-","_")
