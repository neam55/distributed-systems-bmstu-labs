


class DomainError(Exception):
    """Базовое исключение предметной области."""


class PersonNotFoundError(DomainError):

    def __init__(self, person_id: int) -> None:
        self.person_id = person_id
        super().__init__(f"Person with id {person_id} not found")
