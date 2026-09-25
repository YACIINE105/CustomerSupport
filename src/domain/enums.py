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
