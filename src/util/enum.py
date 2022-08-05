import enum

class EcumeneEnum(enum.EnumMeta):
    def has_value(cls, value):
        values = set(item.value for item in cls)
        return value in values

class TransactionType(str, enum.Enum, metaclass=EcumeneEnum):
    USER = 'user_registration'
    ADMIN = 'admin_registration'

class AuditRecordType(str, enum.Enum, metaclass=EcumeneEnum):
    PENDING = 'pending'
    SUCCESS = 'success'
    CANCELLED = 'cancelled'
    FAILED_CHECK = 'failed_check'
    FAILED_ERROR = 'failed_error'
    FAILED_CONTEXT = 'failed_context'
    FAILED_UNREGISTERED = 'failed_unregistered'
    FAILED_TIMEOUT = 'failed_timed_out'
    EXPIRED_OR_UNHANDLED = 'expired_or_unhandled'