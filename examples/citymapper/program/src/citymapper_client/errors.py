class CitymapperError(Exception):
   exit_code = 13

   def __init__(self, message, detail=None):
      super().__init__(message)
      self.message = message
      self.detail = detail or {}

   @property
   def error_class(self):
      return type(self).__name__

   def as_dict(self):
      return {"class": self.error_class, "message": self.message, "detail": self.detail}


class UsageError(CitymapperError):
   exit_code = 2


class SessionExpired(CitymapperError):
   exit_code = 10


class ChallengeRequired(CitymapperError):
   exit_code = 11


class RateLimited(CitymapperError):
   exit_code = 12


class ApiError(CitymapperError):
   exit_code = 13


class ContractBroken(CitymapperError):
   exit_code = 14


class TransportError(CitymapperError):
   exit_code = 16


class NotFound(CitymapperError):
   exit_code = 17


class NotPermitted(CitymapperError):
   exit_code = 15


class LocalFileError(CitymapperError):
   exit_code = 18
