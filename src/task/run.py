from task.core.scheduler import EcumeneScheduler

# Create scheduler and run.
ecumene = EcumeneScheduler()

def start():
    ecumene.schedule.run()

if __name__ == '__main__':
    start()