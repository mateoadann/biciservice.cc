from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from decimal import Decimal, InvalidOperation

from wtforms import (
    BooleanField,
    DecimalField,
    SelectField,
    SelectMultipleField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, Regexp

from ..config import Config


HEX_COLOR = Regexp(r"^#(?:[0-9a-fA-F]{3}){1,2}$", message="Usa un color hex valido")


def _format_decimal(value: Decimal) -> str:
    formatted = f"{value:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


class LocalizedDecimalField(DecimalField):
    def _value(self):
        if self.data is None:
            return ""
        try:
            return _format_decimal(self.data)
        except (InvalidOperation, ValueError, TypeError):
            return str(self.data)

    def process_formdata(self, valuelist):
        if not valuelist:
            self.data = None
            return
        raw = valuelist[0].strip()
        if raw == "":
            self.data = None
            return
        normalized = raw.replace(".", "").replace(",", ".")
        try:
            self.data = Decimal(normalized)
        except InvalidOperation as exc:
            self.data = None
            raise ValueError(self.gettext("Valor decimal invalido.")) from exc


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


BRAND_CHOICES = [
    "BH",
    "BMC",
    "Cannodale",
    "Canyon",
    "Cervelo",
    "Cube",
    "Giant",
    "Marin",
    "Megamo",
    "Merida",
    "Orbea",
    "Otra",
    "Pinarello",
    "Santa Cruz",
    "Sava",
    "Scott",
    "Specialized",
    "Trek",
    "Vairo",
    "Venzo",
    "Volta",
]


class BicycleForm(FlaskForm):
    client_id = SelectField("Cliente", coerce=int, validators=[DataRequired()])
    brand_select = SelectField("Marca", validators=[DataRequired()], choices=[])
    model = StringField("Modelo", validators=[Optional(), Length(max=80)])
    description = TextAreaField("Descripcion", validators=[Optional(), Length(max=300)])


class ServiceTypeForm(FlaskForm):
    name = StringField("Nombre", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Descripcion", validators=[Optional(), Length(max=500)])
    base_price = LocalizedDecimalField(
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
    service_type_ids = SelectMultipleField(
        "Services", coerce=int, validators=[Optional()]
    )


class JobStatusForm(FlaskForm):
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


class DeleteForm(FlaskForm):
    pass
