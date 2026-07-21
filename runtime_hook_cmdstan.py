import os
import sys

# When running as a PyInstaller bundle, point cmdstanpy at the bundled CmdStan
# so it doesn't try to compile or download Stan at runtime.
if getattr(sys, "frozen", False):
    cmdstan_dir = os.path.join(sys._MEIPASS, "cmdstan")
    if os.path.isdir(cmdstan_dir):
        os.environ["CMDSTAN"] = cmdstan_dir
