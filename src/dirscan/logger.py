from datetime import datetime
from pathlib import Path


class Logger:
    def __init__(self, log_dir=Path("logs")):
        log_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = log_dir / f"{ts}_scan.log"

    def info(self, msg):
        print(msg)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
