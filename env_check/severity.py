from enum import IntEnum

class Severity(IntEnum):
    INFO = 10
    WARN = 20
    ERROR = 30
    CRITICAL = 40

    @classmethod
    def from_name(cls, name: str):
        if not name:
            return cls.ERROR
        name = name.strip().upper()
        return {
            "INFO": cls.INFO,
            "WARN": cls.WARN,
            "WARNING": cls.WARN,
            "ERROR": cls.ERROR,
            "CRITICAL": cls.CRITICAL,
    }.get(name, cls.ERROR)
