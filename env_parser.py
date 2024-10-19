import os


class EnvParser:
    def __init__(self):
        pass

    @staticmethod
    def str(var_name, default=None):
        """Get environment variable as string."""
        return os.getenv(var_name, default)

    @staticmethod
    def int(var_name, default=None):
        """Get environment variable as integer."""
        value = os.getenv(var_name, default)
        try:
            return int(value) if value is not None else default
        except ValueError:
            raise TypeError

    @staticmethod
    def float(var_name, default=None):
        """Get environment variable as float."""
        value = os.getenv(var_name, default)
        try:
            return float(value) if value is not None else default
        except ValueError:
            raise TypeError

    @staticmethod
    def bool(var_name, default=False):
        """Get environment variable as boolean."""
        value = os.getenv(var_name, default)
        if value is None:
            return default
        return value.lower() in ["true", "1", "yes", "on"]

    @staticmethod
    def list(var_name, default=None, delimiter=","):
        """Get environment variable as a list, split by a delimiter (default is comma)."""
        value = os.getenv(var_name, default)
        if value is None and default is None:
            raise TypeError
        if value is None:
            return default
        return value.split(delimiter)
