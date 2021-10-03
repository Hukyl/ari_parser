class UserAlreadyExistsException(Exception):
    pass


class UserDoesNotExistException(Exception):
    pass


class AuthorizationException(Exception):
    pass


class InvalidCredentialsException(AuthorizationException):
    pass
