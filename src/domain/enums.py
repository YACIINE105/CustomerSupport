from enum import StrEnum


class ConversationChannel(StrEnum):
    CHAT = "CHAT"
    VOICE = "VOICE"
    PHONE = "PHONE"

class ConversationStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING = "WAITING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    ESCALATED = "ESCALATED"


class MessageSenderType(StrEnum):
    CUSTOMER = "CUSTOMER"
    AGENT = "AGENT"
    AI = "AI"
    SYSTEM = "SYSTEM"


class MessageType(StrEnum):
    TEXT = "TEXT"
    AUDIO = "AUDIO"
    SYSTEM = "SYSTEM"


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    SUPPORT_HEAD = "SUPPORT_HEAD"
    AGENT = "AGENT"


class AgentStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


class EscalationPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class EscalationStatus(StrEnum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    RESOLVED = "RESOLVED"
