import datetime
from sqlalchemy import BigInteger, String, Text, ForeignKey, DateTime, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List

from app.database import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150))
    username: Mapped[str] = mapped_column(String(100), nullable=True)

    phone_number: Mapped[str] = mapped_column(String(20), nullable=True)

    role: Mapped[str] = mapped_column(String(50), default='client')

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=func.now()
    )

    client_requests: Mapped[List["Request"]] = relationship(
        "Request", back_populates="client", foreign_keys="Request.client_id"
    )
    lawyer_requests: Mapped[List["Request"]] = relationship(
        "Request", back_populates="lawyer", foreign_keys="Request.lawyer_id"
    )


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(100))
    question_text: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending_payment")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=func.now()
    )

    taken_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)

    client_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    lawyer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=True)

    client: Mapped["User"] = relationship(
        "User", back_populates="client_requests", foreign_keys=[client_id]
    )
    lawyer: Mapped["User"] = relationship(
        "User", back_populates="lawyer_requests", foreign_keys=[lawyer_id]
    )
    files: Mapped[List["RequestFile"]] = relationship(
        "RequestFile", back_populates="request"
    )

    replies: Mapped[List["Reply"]] = relationship("Reply", back_populates="request")


class RequestFile(Base):
    __tablename__ = "request_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(50))
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("requests.id"))

    request: Mapped["Request"] = relationship("Request", back_populates="files")


class Reply(Base):
    __tablename__ = "replies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"))
    reply_text: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=func.now()
    )

    request: Mapped["Request"] = relationship("Request", back_populates="replies")
    files: Mapped[List["ReplyFile"]] = relationship("ReplyFile", back_populates="reply")



class ReplyFile(Base):
    __tablename__ = "reply_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reply_id: Mapped[int] = mapped_column(ForeignKey("replies.id"))
    file_id: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(50))

    reply: Mapped["Reply"] = relationship("Reply", back_populates="files")