from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


user_email_accounts = Table(
    "user_email_accounts",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("email_account_id", ForeignKey("email_accounts.id"), primary_key=True),
)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    permissions: Mapped[list["Permission"]] = relationship(secondary="role_permissions", back_populates="roles")


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    roles: Mapped[list[Role]] = relationship(secondary="role_permissions", back_populates="permissions")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id"), primary_key=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    email_account_id: Mapped[int | None] = mapped_column(ForeignKey("email_accounts.id"), nullable=True)
    role: Mapped[Role] = relationship()
    email_account: Mapped["EmailAccount | None"] = relationship(foreign_keys=[email_account_id])
    email_accounts: Mapped[list["EmailAccount"]] = relationship(secondary=user_email_accounts, back_populates="users")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    details: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Draft(Base):
    __tablename__ = "drafts"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(998))
    body: Mapped[str] = mapped_column(Text)
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    content_revision: Mapped[int] = mapped_column(default=1)
    approved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EmailAccount(Base):
    """Ein verwaltetes Postfach. Passwörter werden nur verschlüsselt gespeichert."""
    __tablename__ = "email_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_name: Mapped[str] = mapped_column(String(160))
    email_address: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(40), default="imap_smtp")
    display_name: Mapped[str] = mapped_column(String(160))
    imap_host: Mapped[str] = mapped_column(String(255))
    imap_port: Mapped[int] = mapped_column(default=993)
    smtp_host: Mapped[str] = mapped_column(String(255))
    smtp_port: Mapped[int] = mapped_column(default=587)
    username: Mapped[str] = mapped_column(String(320))
    encrypted_password: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    users: Mapped[list[User]] = relationship(secondary=user_email_accounts, back_populates="email_accounts")


class EmailMessage(Base):
    """Eine später synchronisierte E-Mail. Noch ohne automatische Synchronisation."""
    __tablename__ = "email_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("email_accounts.id"), index=True)
    message_id: Mapped[str] = mapped_column(String(998), unique=True)
    sender: Mapped[str] = mapped_column(String(998))
    subject: Mapped[str] = mapped_column(String(998), default="")
    body_text: Mapped[str] = mapped_column(Text, default="")
    ai_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ai_priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_reply_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EmailReply(Base):
    __tablename__ = "email_replies"
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("email_messages.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("email_accounts.id"), index=True)
    recipient: Mapped[str] = mapped_column(String(998))
    subject: Mapped[str] = mapped_column(String(998))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OutgoingEmail(Base):
    __tablename__ = "outgoing_emails"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("email_accounts.id"), index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    recipient: Mapped[str] = mapped_column(String(2000), default="")
    cc: Mapped[str] = mapped_column(String(2000), default="")
    bcc: Mapped[str] = mapped_column(String(2000), default="")
    subject: Mapped[str] = mapped_column(String(998), default="")
    text_body: Mapped[str] = mapped_column(Text, default="")
    html_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str] = mapped_column(String(10), default="text")
    attachments_json: Mapped[str] = mapped_column(Text, default="[]")
    in_reply_to: Mapped[str | None] = mapped_column(String(998), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(240), index=True)
    domain: Mapped[str] = mapped_column(String(255), default="", index=True)
    industry: Mapped[str] = mapped_column(String(160), default="")
    website: Mapped[str] = mapped_column(String(500), default="")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    researched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    research_status: Mapped[str] = mapped_column(String(30), default="pending")
    research_error: Mapped[str] = mapped_column(Text, default="")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    leads: Mapped[list["Lead"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), index=True)
    role_title: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(80), default="")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    researched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opt_out: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    company: Mapped[Company] = relationship(back_populates="contacts")


class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id"), nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="neu", index=True)
    score: Mapped[int] = mapped_column(default=0)
    next_action: Mapped[str] = mapped_column(String(500), default="")
    sales_pitch: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    company: Mapped[Company] = relationship(back_populates="leads")
    contact: Mapped[Contact | None] = relationship()
    owner: Mapped[User | None] = relationship()


class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id"), nullable=True, index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    activity_type: Mapped[str] = mapped_column(String(40), default="note")
    subject: Mapped[str] = mapped_column(String(240), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
