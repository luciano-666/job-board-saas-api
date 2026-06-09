from dataclasses import dataclass


@dataclass
class DomainEvent:
    pass


@dataclass
class UserRegistered(DomainEvent):
    email: str
    role: str


@dataclass
class UserSuspended(DomainEvent):
    email: str
    role: str


@dataclass
class UserApproved(DomainEvent):
    email: str
    role: str


@dataclass
class PasswordChanged(DomainEvent):
    email: str
