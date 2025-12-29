from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


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
    email_confirmed = db.Column(db.Boolean, default=False)
    email_confirmed_at = db.Column(db.DateTime)
    confirmation_sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    workshops = db.relationship(
        "Workshop", secondary=user_workshops, back_populates="users"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship(
        "User", secondary=user_workshops, back_populates="workshops"
    )
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
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(40))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bicycles = db.relationship("Bicycle", backref="client", lazy=True)


class Bicycle(db.Model):
    __tablename__ = "bicycles"

    id = db.Column(db.Integer, primary_key=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    brand = db.Column(db.String(80))
    model = db.Column(db.String(80))
    description = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    jobs = db.relationship("Job", backref="bicycle", lazy=True)


class ServiceType(db.Model):
    __tablename__ = "service_types"

    id = db.Column(db.Integer, primary_key=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    base_price = db.Column(db.Numeric(10, 2), default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    job_items = db.relationship("JobItem", backref="service_type", lazy=True)


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"), nullable=False)
    bicycle_id = db.Column(db.Integer, db.ForeignKey("bicycles.id"), nullable=False)
    status = db.Column(db.String(40), default="open")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship("JobItem", backref="job", lazy=True)


class JobItem(db.Model):
    __tablename__ = "job_items"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    service_type_id = db.Column(
        db.Integer, db.ForeignKey("service_types.id"), nullable=False
    )
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10, 2), default=0)
