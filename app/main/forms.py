from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    DecimalField,
    IntegerField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, Regexp

from ..config import Config


HEX_COLOR = Regexp(r"^#(?:[0-9a-fA-F]{3}){1,2}$", message="Use hex color")


class WorkshopSettingsForm(FlaskForm):
    name = StringField("Workshop name", validators=[DataRequired(), Length(max=120)])
    primary_color = StringField("Primary color", validators=[Optional(), HEX_COLOR])
    secondary_color = StringField("Secondary color", validators=[Optional(), HEX_COLOR])
    accent_color = StringField("Accent color", validators=[Optional(), HEX_COLOR])
    background_color = StringField("Background color", validators=[Optional(), HEX_COLOR])
    logo = FileField("Logo", validators=[FileAllowed(Config.ALLOWED_IMAGE_EXTENSIONS)])
    favicon = FileField("Favicon", validators=[FileAllowed(Config.ALLOWED_IMAGE_EXTENSIONS)])


class ClientForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=255)])
    phone = StringField("Phone", validators=[Optional(), Length(max=40)])


class BicycleForm(FlaskForm):
    client_id = SelectField("Cliente", coerce=int, validators=[DataRequired()])
    brand = StringField("Marca", validators=[Optional(), Length(max=80)])
    model = StringField("Modelo", validators=[Optional(), Length(max=80)])
    serial_number = StringField("Serie", validators=[Optional(), Length(max=80)])


class ServiceTypeForm(FlaskForm):
    name = StringField("Nombre", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Descripcion", validators=[Optional(), Length(max=500)])
    base_price = DecimalField(
        "Precio base", validators=[Optional(), NumberRange(min=0)], places=2
    )
    is_active = BooleanField("Activo")


class JobForm(FlaskForm):
    bicycle_id = SelectField("Bicicleta", coerce=int, validators=[DataRequired()])
    status = SelectField(
        "Estado",
        choices=[
            ("open", "Abierto"),
            ("in_progress", "En progreso"),
            ("ready", "Listo"),
            ("closed", "Cerrado"),
        ],
        validators=[DataRequired()],
    )
    notes = TextAreaField("Notas", validators=[Optional(), Length(max=1000)])
    service_type_id = SelectField("Service", coerce=int, validators=[Optional()])
    quantity = IntegerField(
        "Cantidad", validators=[Optional(), NumberRange(min=1)], default=1
    )
    unit_price = DecimalField(
        "Precio unitario", validators=[Optional(), NumberRange(min=0)], places=2
    )


class DeleteForm(FlaskForm):
    pass
