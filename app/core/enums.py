"""
Centralized domain Enum constants.

Dùng chung toàn project thay cho magic-strings rải rác.
Import pattern:
    from app.core.enums import TripStatus, ChatRole, SuggestionStatus, SuggestionType
"""
from enum import Enum


class TripStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class SuggestionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class SuggestionType(str, Enum):
    ITINERARY = "itinerary"
    PLACE = "place"
    BUDGET = "budget"


class ActivityType(str, Enum):
    HOTEL = "hotel"
    MEAL = "meal"
    ATTRACTION = "attraction"
    TRANSPORT = "transport"
    OTHER = "other"


class BudgetCategory(str, Enum):
    ACCOMMODATION = "accommodation"
    FOOD = "food"
    TRANSPORT = "transport"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    OTHER = "other"
