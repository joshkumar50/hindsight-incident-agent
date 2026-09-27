"""Minimal errors module."""

class HindsightIncidentAgentException(Exception):
    def __init__(self, message, error_code=None, status_code=500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = {}

def register_error_handlers(app):
    pass
