from dataclasses import dataclass


@dataclass(frozen=True)
class DomainEvent:
    pass


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    email: str
    role: str


@dataclass(frozen=True)
class UserSuspended(DomainEvent):
    email: str
    role: str


@dataclass(frozen=True)
class UserApproved(DomainEvent):
    email: str
    role: str


@dataclass(frozen=True)
class PasswordChanged(DomainEvent):
    email: str
