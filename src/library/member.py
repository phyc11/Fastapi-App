from uuid import uuid4


class Member:
    def __init__(self, name: str, email: str) -> None:
        self.name = name
        self.email = email


class MemberRegistry:
    def __init__(self) -> None:
        self.members: dict[str, Member] = {}

    def register(self, name: str, email: str) -> str:
        member_id = uuid4().hex
        self.members[member_id] = Member(name, email)
        return member_id

    def find_member(self, member_id: str) -> Member | None:
        return self.members.get(member_id)
