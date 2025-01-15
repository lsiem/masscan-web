import dramatiq
from masscan_web.tasks import scan_tasks

if __name__ == '__main__':
    broker = dramatiq.get_broker()
    broker.emit_after('process_boot')
    broker.join()