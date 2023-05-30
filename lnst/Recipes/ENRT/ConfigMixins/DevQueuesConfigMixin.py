from lnst.Common.Parameters import ListParam, DictParam
from lnst.Recipes.ENRT.ConfigMixins.BaseHWConfigMixin import BaseHWConfigMixin


class DevQueuesConfigMixin(BaseHWConfigMixin):
    dev_queues = ListParam(type=DictParam(), mandatory=False)

    @property
    def dev_queues_config_dev_list(self):
        """
        The value of this property is a list of devices for which the device
        queues should be configured. It has to be defined by a derived class.
        """
        return []

    def hw_config(self, config):
        super().hw_config(config)

        if not self.params.get("dev_queues"):
            return

        hw_config = config.hw_config
        hw_config["dev_queues"] = {}

        for device, dev_queues in zip(
            self.dev_queues_config_dev_list, self.params.dev_queues
        ):
            # TODO: handle netlink error: Operation not supported
            ethtool_job = device.host.run(f"ethtool -l {device.name}")
            original_queues = process_queues_output(ethtool_job.stdout)

            hw_config["dev_queues"][device] = {
                "original_queues": original_queues["current"],
            }

            device.host.run(
                f"ethtool -L {device.name} "
                + " ".join(
                    queue_name + " " + str(queue_setting)
                    for queue_name, queue_setting in dev_queues.items()
                )
            )

            hw_config["dev_queues"][device]["configured_queues"] = dev_queues

    def hw_deconfig(self, config):
        dev_queues_config = config.hw_config.get("dev_queues", {})
        for dev, dev_queues in dev_queues_config.items():
            if dev_queues.get("configured_queues"):
                dev.host.run(
                    f"ethtool -L {dev.name} "
                    + " ".join(
                        queue_name + " " + str(queue_setting)
                        for queue_name, queue_setting in dev_queues[
                            "original_queues"
                        ].items()
                        if queue_name in dev_queues["configured_queues"]
                    )
                )

        super().hw_deconfig(config)

    def describe_hw_config(self, config):
        desc = super().describe_hw_config(config)

        dev_queues_config = config.hw_config.get("dev_queues", {})

        if dev_queues_config and self.dev_queues_config_dev_list:
            desc += [
                f"{device.host.hostid} device {device.name} queues configured: "
                + " ".join(
                    queue_name + " " + str(queue_setting)
                    for queue_name, queue_setting in dev_queues["configured_queues"].items()
                )
                for device, dev_queues in dev_queues_config.items()
            ]
        else:
            desc += ["device queues configuration skipped"]

        return desc


def process_queues_output(output):
    # format of ethtool -l:
    #
    # Channel parameters for ens7f0:
    # Pre-set maximums:
    # RX:		n/a
    # TX:		n/a
    # Other:		n/a
    # Combined:	32
    # Current hardware settings:
    # RX:		n/a
    # TX:		n/a
    # Other:		n/a
    # Combined:	16

    result = {
        "preset": {},
        "current": {},
    }

    key = None
    for line in output.split("\n")[1:]:
        if not line:
            continue

        if line == "Pre-set maximums:":
            key = "preset"
        elif line == "Current hardware settings:":
            key = "current"
        else:
            queue_name, queue_setting = line.split(":")
            queue_name = queue_name.lower()
            queue_setting = queue_setting.strip()
            if queue_setting == "n/a":
                queue_setting = None

            result[key][queue_name] = queue_setting

    return result
