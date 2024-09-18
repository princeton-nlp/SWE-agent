import os


class LockFile:
    """
    A primitive file-based locking mechanism to avoid duplicating long-running processes.
    """
    locked = False

    def __init__(self, label: str, path: str, content: str = "") -> None:
        self.label = label
        self.path = path
        self.content = content

    @property
    def had_lock(self) -> bool:
        return self.locked
    
    def _lock_file_path(self, label: str = None) -> str:
        parent_path = os.path.dirname(self.path)
        target_name = os.path.basename(self.path)
        return f"{parent_path}/{label or self.label}.{target_name}.lock"
    
    def write_lock(self, name: str) -> None:
        with open(self._lock_file_path(name), "w") as f:
            f.write(self.content)

    def __enter__(self):
        if os.path.exists(self._lock_file_path()):
            with open(self._lock_file_path(), "r") as f:
                if f.read() == self.content:
                    self.locked = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.locked:
            self.write_lock(self.label)
            self.locked = True
