import os
import yaml
import dotenv
import argparse

from logging.config import dictConfig

# Initialise logging before importing any local modules!
# Otherwise, loggers will be generated on import before config applies any handlers to them!
fpath = os.path.join('conf', 'log.yml')
with open(fpath, 'r') as cfile:
    cfg = yaml.load(cfile, Loader=yaml.FullLoader)
dictConfig(cfg)

# Load variables from local .env file.
dotenv.load_dotenv()

# Enumerated choices.
RUN_BOT = 'bot'
RUN_WEB = 'web'

# Argument parsing.
parser = argparse.ArgumentParser(description='Welcome to the Ecumene interface...')
parser.add_argument('module', choices=[RUN_BOT, RUN_WEB])
args = parser.parse_args()

# Application import once arguments have been successfully parsed.
# Only import one app to avoid duplicating database services.
if not args.module:
    pass
elif args.module == RUN_BOT:
    import bot.app
    bot.app.start()
elif args.module == RUN_WEB:
    import web.app
    web.app.start(
        # TODO: Remove hacky garbage when actually deployed.
        ssl_context=('cert.pem', 'key.pem')
    )
else:
    pass