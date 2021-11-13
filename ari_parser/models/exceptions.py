class DatabaseException(Exception):
    pass
    

class AccountAlreadyExistsException(DatabaseException):
    pass


class AccountDoesNotExistException(DatabaseException):
    pass


class DependentAlreadyExistsException(DatabaseException):
    pass


class UpdatesDoNotExistException(DatabaseException):
    pass


class DependentDoesNotExistException(DatabaseException):
    pass


class CrawlerException(Exception):
    pass


class AuthorizationException(CrawlerException):
    pass


class InvalidCredentialsException(AuthorizationException):
    pass


class ProxyException(CrawlerException):
    pass


class NoAppointmentsException(CrawlerException):
    pass


class NoStatusException(CrawlerException):
    pass
