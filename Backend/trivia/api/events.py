"""Socket.IO event names: the vocabulary shared with the frontend."""

from enum import StrEnum


class ClientEvent(StrEnum):
    """Events the browser sends."""

    JOIN_QUEUE = "join_queue"
    LEAVE_QUEUE = "leave_queue"
    ANSWER = "answer"
    USE_HELP = "use_help"
    CHAT_SEND_MESSAGE = "chat_send_message"
    CHAT_OPEN = "chat_open"
    CHAT_REQUEST_HISTORY = "chat_request_history"


class ServerEvent(StrEnum):
    """Events the server sends."""

    CONNECTED = "connected"
    ERROR_MESSAGE = "error_message"
    MATCHMAKING_STATUS = "matchmaking_status"
    GAME_STARTED = "game_started"
    PLAYER_STATE = "player_state"
    RACE_STANDINGS = "race_standings"
    QUESTION = "question"
    ANSWER_RECEIVED = "answer_received"
    HELP_USED = "help_used"
    QUESTION_TIMER_PAUSED = "question_timer_paused"
    QUESTION_TIMER_RESUMED = "question_timer_resumed"
    QUESTION_RESULT = "question_result"
    GAME_FINISHED = "game_finished"
    SOUND_EFFECT = "sound_effect"
    CHAT_NEW_MESSAGE = "chat_new_message"
    CHAT_UNREAD_UPDATE = "chat_unread_update"
    CHAT_HISTORY = "chat_history"
    CHAT_HISTORY_CLEARED = "chat_history_cleared"
