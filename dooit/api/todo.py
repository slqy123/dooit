from typing import TYPE_CHECKING, Optional, Self, Union
from datetime import datetime
from typing import List
from sqlalchemy import Connection, event
from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import Mapped, Mapper, Session, mapped_column, relationship
from .model import Model, default_session


if TYPE_CHECKING:
    from dooit.api.workspace import Workspace


class Todo(Model):

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_index: Mapped[int] = mapped_column(default=-1)
    description: Mapped[str] = mapped_column(default="")
    due: Mapped[Optional[datetime]] = mapped_column(default=None)
    effort: Mapped[int] = mapped_column(default=0)
    urgency: Mapped[int] = mapped_column(default=0)
    pending: Mapped[bool] = mapped_column(default=True)

    # --------------------------------------------------------------
    # ------------------- Relationships ----------------------------
    # --------------------------------------------------------------

    parent_workspace_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workspace.id")
    )
    parent_workspace: Mapped[Optional["Workspace"]] = relationship(
        "Workspace",
        back_populates="todos",
    )

    parent_todo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("todo.id"))
    parent_todo: Mapped[Optional["Todo"]] = relationship(
        "Todo",
        back_populates="todos",
        remote_side=[id],
    )

    todos: Mapped[List["Todo"]] = relationship(
        "Todo",
        back_populates="parent_todo",
        cascade="all, delete-orphan",
    )

    @property
    def parent(self) -> Union["Workspace", "Todo"]:
        if self.parent_workspace:
            return self.parent_workspace

        if self.parent_todo:
            return self.parent_todo

        raise ValueError("Parent not found")

    @property
    def tags(self) -> List[str]:
        return [i for i in self.description.split() if i[0] == "@"]

    def get_siblings(self, session: Session = default_session) -> List[Self]:
        cls = self.__class__
        query = select(cls)

        if self.parent_workspace:
            query = query.where(cls.parent_workspace == self.parent_workspace)
        else:
            query = query.where(cls.parent_todo == self.parent_todo)

        query = query.order_by(cls.order_index)
        return list(session.execute(query).scalars().all())

    def add_todo(
        self,
        index: int = 0,
        inherit: bool = False,
        session: Session = default_session,
    ) -> "Todo":
        todo = Todo()
        todo.save(session)
        return todo

    # ----------- HELPER FUNCTIONS --------------

    def toggle_complete(self) -> None:
        self.status = not self.status
        self.save()

    def has_due_date(self) -> bool:
        return self.due is not None

    def is_due_today(self) -> bool:
        if not self.due:
            return False

        return self.due and self.due.day == datetime.today().day

    def is_completed(self) -> bool:
        return self.pending == False

    def is_pending(self) -> bool:
        return self.pending

    def is_overdue(self) -> bool:
        if not self.due:
            return False

        return self.pending and self.due < datetime.now()


@event.listens_for(Todo, "after_insert")
def before_insert(mapper: Mapper, connection: Connection, target: Todo):
    if target.order_index == -1:
        with Session(connection) as session:
            siblings = target.get_siblings(session)
            target.order_index = len(siblings)
