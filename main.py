
from typing import List
from typing import Optional

import sqlalchemy
from sqlalchemy import create_engine, String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)
session = Session(engine)

#     result = conn.execute(text("select 'hello world'"))
#     print(result.all())


class Base(DeclarativeBase):
    pass

# Note that modern SQLAlchemy (2.0) uses type annotations to derive field types,
# compared to the "classical" method of declaring `Column` and then passing
# in the type. It is still possible to explicitly define field sizes; the old
# syntax is also not slated for deprecation anytime soon.
class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    fullname: Mapped[Optional[str]]

    addresses: Mapped[List["Address"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"

class Address(Base):
    __tablename__ = "address"

    id: Mapped[int] = mapped_column(primary_key=True)
    email_address: Mapped[str]
    user_id = mapped_column(ForeignKey("user_account.id"))

    user: Mapped[User] = relationship(back_populates="addresses")

    def __repr__(self) -> str:
        return f"Address(id={self.id!r}, email_address={self.email_address!r})"

u = User(name="hi")
a = Address(email_address="hi", user=u)

print(u.addresses)
Base.metadata.create_all(engine)
session.add(u)
session.commit()
u = session.execute(sqlalchemy.select(User).where(User.name=='hi')).all()
print(u)


Base.metadata.create_all(engine)