class DomainException(Exception):
    """Base class for domain exceptions."""
    pass

class EntityNotFoundException(DomainException):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
