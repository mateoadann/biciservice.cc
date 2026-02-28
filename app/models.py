import secrets
from datetime import datetime, timezone, timedelta

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db
from .timezone import now_cordoba_naive


user_workshops = db.Table(
    "user_workshops",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column(
        "workshop_id", db.Integer, db.ForeignKey("workshops.id"), primary_key=True
    ),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    approved_at = db.Column(db.DateTime)
    role = db.Column(db.String(20), default="owner")
    email_confirmed = db.Column(db.Boolean, default=False)
    email_confirmed_at = db.Column(db.DateTime)
    confirmation_sent_at = db.Column(db.DateTime)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime)
    two_factor_enabled = db.Column(db.Boolean, default=False, nullable=False)
    two_factor_secret = db.Column(db.String(32))
    password_reset_token_hash = db.Column(db.String(255))
    password_reset_expires_at = db.Column(db.DateTime)
    password_reset_sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=True)

    workshops = db.relationship(
        "Workshop", secondary=user_workshops, back_populates="users"
    )
    store = db.relationship("Store", backref="users", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def set_password_reset_token(self, expires_in: int) -> str:
        token = secrets.token_urlsafe(32)
        self.password_reset_token_hash = generate_password_hash(token)
        self.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=expires_in
        )
        self.password_reset_sent_at = datetime.now(timezone.utc)
        return token

    def verify_password_reset_token(self, token: str) -> bool:
        if not self.password_reset_token_hash or not self.password_reset_expires_at:
            return False
        expires_at = self.password_reset_expires_at
        now = datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            now = datetime.utcnow()
        if now > expires_at:
            return False
        return check_password_hash(self.password_reset_token_hash, token)

    def clear_password_reset_token(self) -> None:
        self.password_reset_token_hash = None
        self.password_reset_expires_at = None
        self.password_reset_sent_at = None


class Workshop(db.Model):
    __tablename__ = "workshops"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    logo_path = db.Column(db.String(255))
    favicon_path = db.Column(db.String(255))
    primary_color = db.Column(db.String(20), default="#1f4cff")
    secondary_color = db.Column(db.String(20), default="#19b36b")
    accent_color = db.Column(db.String(20), default="#ff8c2b")
    background_color = db.Column(db.String(20), default="#f6f7fb")
    whatsapp_message_template = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    users = db.relationship(
        "User", secondary=user_workshops, back_populates="workshops"
    )
    stores = db.relationship("Store", backref="workshop", lazy=True)
    clients = db.relationship("Client", backref="workshop", lazy=True)
    bicycles = db.relationship("Bicycle", backref="workshop", lazy=True)
    service_types = db.relationship("ServiceType", backref="workshop", lazy=True)
    jobs = db.relationship("Job", backref="workshop", lazy=True)

    def theme(self) -> dict:
        return {
            "primary": self.primary_color or "#1f4cff",
            "secondary": self.secondary_color or "#19b36b",
            "accent": self.accent_color or "#ff8c2b",
            "background": self.background_color or "#f6f7fb",
            "logo_path": self.logo_path,
            "favicon_path": self.favicon_path,
            "name": self.name,
        }


class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"), nullable=False)
    client_code = db.Column(db.String(10), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(40))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("workshop_id", "client_code", name="uq_client_workshop_code"),
        db.Index("ix_clients_workshop_id", "workshop_id"),
    )

    bicycles = db.relationship("Bicycle", backref="client", lazy=True)


class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.Integer, primary_key=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("ix_stores_workshop_id", "workshop_id"),
    )


class Bicycle(db.Model):
    __tablename__ = "bicycles"

    id = db.Column(db.Integer, primary_key=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    brand = db.Column(db.String(80))
    model = db.Column(db.String(80))
    description = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("ix_bicycles_workshop_id", "workshop_id"),
        db.Index("ix_bicycles_client_id", "client_id"),
    )

    jobs = db.relationship("Job", backref="bicycle", lazy=True)


class ServiceType(db.Model):
    __tablename__ = "service_types"

    id = db.Column(db.Integer, primary_key=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    base_price = db.Column(db.Numeric(10, 2), default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("ix_service_types_workshop_id", "workshop_id"),
    )

    job_items = db.relationship("JobItem", backref="service_type", lazy=True)


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)
    bicycle_id = db.Column(db.Integer, db.ForeignKey("bicycles.id"), nullable=False)
    code = db.Column(db.String(4), unique=True, nullable=False)
    status = db.Column(db.String(40), default="open")
    notes = db.Column(db.Text)
    estimated_delivery_at = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("ix_jobs_workshop_store_status", "workshop_id", "store_id", "status"),
        db.Index("ix_jobs_estimated_delivery", "estimated_delivery_at"),
    )

    items = db.relationship(
        "JobItem", backref="job", lazy=True, cascade="all, delete-orphan"
    )
    parts = db.relationship(
        "JobPart", backref="job", lazy=True, cascade="all, delete-orphan"
    )
    store = db.relationship("Store", backref="jobs", lazy=True)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"))
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"))
    action = db.Column(db.String(40), nullable=False)
    entity_type = db.Column(db.String(40), nullable=False)
    entity_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=now_cordoba_naive)

    __table_args__ = (
        db.Index("ix_audit_entity", "entity_type", "entity_id", "action"),
    )

    user = db.relationship("User", backref="audit_logs", lazy=True)
    workshop = db.relationship("Workshop", backref="audit_logs", lazy=True)
    store = db.relationship("Store", backref="audit_logs", lazy=True)




class JobPart(db.Model):
    __tablename__ = "job_parts"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    kind = db.Column(db.String(20), default="part", nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("ix_job_parts_job_id", "job_id"),
    )


class JobItem(db.Model):
    __tablename__ = "job_items"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    service_type_id = db.Column(
        db.Integer, db.ForeignKey("service_types.id"), nullable=False
    )
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10, 2), default=0)

    __table_args__ = (
        db.Index("ix_job_items_job_id", "job_id"),
    )
