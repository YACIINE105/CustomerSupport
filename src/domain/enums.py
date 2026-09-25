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
