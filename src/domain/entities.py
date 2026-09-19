from dataclasses import dataclass


@dataclass(slots=True)
class Person:

    name: str
    id: int | None = None
    age: int | None = None
    address: str | None = None
    work: str | None = None
