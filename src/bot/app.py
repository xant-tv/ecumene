from bot.core.client import EcumeneBot

# Create instance of Ecumene and attach functions.
ecumene = EcumeneBot()

def start():
    """Callable to run application."""
    ecumene.run()

if __name__ == '__main__':
    start()