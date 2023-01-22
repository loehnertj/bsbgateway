
__all__ = ['EncodeError', 'ValidateError']

class BsbError(Exception):
    pass

class EncodeError(BsbError):
    """Could not convert data to send-bytes"""

class DecodeError(Exception):
    """Could not decipher received bytes"""

class ValidateError(BsbError):
    """Given set-data outside allowed range"""