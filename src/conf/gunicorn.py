# GUNICORN
# ========
# Use this configuration file to set any values not
# passed into server start command at runtime.

import os
import yaml
import multiprocessing

# SETUP
# =======
# Set number of workers.
workers = 2 * multiprocessing.cpu_count() + 1

# LOGGING
# =======
# Initialise from local configuration.
fpath = os.path.join('conf', 'log.yml')
with open(fpath, 'r') as cfile:
    cfg = yaml.load(cfile, Loader=yaml.FullLoader)
logconfig_dict = cfg
