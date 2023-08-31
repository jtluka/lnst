import subprocess
import logging
import os

from lnst.Tests.BaseTestModule import BaseTestModule
from lnst.Common.Parameters import StrParam, IntParam, ListParam
from lnst.Common.Utils import is_installed, is_rpm_installed
from lnst.Common.ExecCmd import log_output

class LinuxPerf(BaseTestModule):
    output_file = StrParam(mandatory=True)
    cpus = ListParam(type=IntParam())
    events = ListParam(type=StrParam())

    def run(self) -> bool:
        self._res_data = {}
        if not is_installed("perf"):
            self._res_data["msg"] = "perf is not installed on this machine!"
            logging.error(self._res_data["msg"])
            return False

        # can't use lnst.Common.ExecCmd.exec_cmd directly, because expected returncode is not zero
        cmd: str = self._compose_cmd()
        logging.debug(f"Executing: \"{cmd}\"")
        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True
        )

        self.wait_for_interrupt()

        stdout, stderr = process.communicate()

        if stdout:
            log_output(logging.debug, "Stdout", stdout.decode())
        if stderr:
            log_output(logging.debug, "Stderr", stderr.decode())

        self._res_data["filename"] = os.path.abspath(self.params.output_file)

        if is_rpm_installed("kernel-debuginfo"):
            # run perf archive
            archive_process = subprocess.Popen(
                f"perf archive {self.params.output_file}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True
            )
            stdout, stderr = archive_process.communicate()
            if stdout:
                log_output(logging.debug, "Stdout (perf archive)", stdout.decode())
            if stderr:
                log_output(logging.debug, "Stderr (perf archive)", stderr.decode())

            # add to _res_data
            self._res_data["filename_archive"] = os.path.abspath(self.params.output_file + ".tar.bz2")
        else:
            logging.debug("kernel-debuginfo is not installed, will not save debug symbols")

        return process.returncode == -2

    def _compose_cmd(self) -> str:
        cmd: str = "perf record"
        cmd += f" --output={self.params.output_file}"

        if "cpus" in self.params:
            cmd += f" --cpu={','.join(map(str, self.params.cpus))}"

        if "events" in self.params:
            cmd += f" --event={','.join(self.params.events)}"

        return cmd
