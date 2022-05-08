class SendMessageFail(Exception):
    """Исключение для статуса ответа API != 200."""

    pass


class GetApiUnavailable(Exception):
    """Исключение на случай недоступности telegram."""

    pass
