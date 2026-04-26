import logging
import threading
import os

JOB_LOGS_DIR = "job_logs"
os.makedirs(JOB_LOGS_DIR, exist_ok=True)

class JobLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self._file_handles = {}
        self._lock = threading.Lock()

    def emit(self, record):
        job_id = getattr(threading.current_thread(), "job_id", None)
        if job_id is not None:
            try:
                msg = self.format(record)
                
                with self._lock:
                    if job_id not in self._file_handles:
                        log_path = os.path.join(JOB_LOGS_DIR, f"job_{job_id}.log")
                        self._file_handles[job_id] = open(log_path, "a", encoding="utf-8", errors="backslashreplace")
                    
                    f = self._file_handles[job_id]
                    f.write(msg + "\n")
                    f.flush()
            except Exception:
                self.handleError(record)

def setup_job_logging():
    handler = JobLogHandler()
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt="%H:%M:%S")
    handler.setFormatter(formatter)
    
    # Add to root logger so it catches everything
    logging.getLogger().addHandler(handler)
    # Ensure root logger is at least INFO
    logging.getLogger().setLevel(logging.INFO)
