import logging
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from datetime import datetime
from queue import Queue
import atexit

class AsyncLoggerAdapter(logging.Logger):
    custom_logger = None
    
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        if self.custom_logger is None:
            super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)
            return
        
        if args:
            msg = msg % args
        
        if level >= logging.ERROR:
            self.custom_logger.error(msg)
        elif level >= logging.WARNING:
            self.custom_logger.warning(msg)
        elif level >= logging.INFO:
            self.custom_logger.info(msg)
        else:
            self.custom_logger.debug(msg)

# Global queue listener reference for cleanup
_queue_listener = None

def setup_logger(name='logger', log_dir='logs', level=logging.INFO, console=True):
    global _queue_listener
    
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # return existing logger if already configured (we want a singleton)
    if logger.handlers:
        return logger
    
    # daily log file names
    log_file = log_path / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)

    # 2025-10-12 14:15:16.178 - INFO - blah
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    handlers = [file_handler]
    
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    log_queue = Queue(-1)  # TODO maybe cap this size
    queue_handler = QueueHandler(log_queue)
    
    _queue_listener = QueueListener(log_queue, *handlers, respect_handler_level=True)
    _queue_listener.start()
    
    # only have queue as handler
    logger.addHandler(queue_handler)
    
    # make sure we get all logging
    logging.setLoggerClass(AsyncLoggerAdapter)
    AsyncLoggerAdapter.custom_logger = logger
    logging.root.setLevel(logging.DEBUG)
    
    # Ensure listener stops on program exit
    atexit.register(_queue_listener.stop)
    
    return logger
