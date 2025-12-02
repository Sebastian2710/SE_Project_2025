from typing import List


class ProtocolViolation(Exception):
    pass


class SessionLog:
    """
    Very simple session logger / checker.
    Maya will later define which sequences are legal
    based on Scribble protocols.
    """

    def __init__(self) -> None:
        self.events: List[str] = []

    def record(self, event: str) -> None:
        self.events.append(event)

    def validate(self) -> None:
        """
        Placeholder: later we will check self.events
        against the Scribble-derived rules.
        """
        # TODO: implement real checks with Maya
        return
