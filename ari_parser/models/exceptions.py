class DatabaseException(Exception):
    pass
    

class AccountAlreadyExistsException(DatabaseException):
    pass


class AccountDoesNotExistException(DatabaseException):
    pass


class DependentDoesNotExistException(DatabaseException):
    pass


class AuthorizationException(Exception):
    pass


class InvalidCredentialsException(AuthorizationException):
    pass
