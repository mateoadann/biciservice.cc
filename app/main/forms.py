from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from decimal import Decimal, InvalidOperation

from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    PasswordField,
    SelectField,
    SelectMultipleField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, Regexp, ValidationError

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
    whatsapp_message_template = TextAreaField(
        "WhatsApp message",
        validators=[Optional(), Length(max=1000)],
    )
    logo = FileField("Logo", validators=[FileAllowed(Config.ALLOWED_IMAGE_EXTENSIONS)])
    favicon = FileField("Favicon", validators=[FileAllowed(Config.ALLOWED_IMAGE_EXTENSIONS)])


class ClientForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(message="Campo obligatorio"), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(message="Campo obligatorio"), Email(message="Email invalido"), Length(max=255)])
    phone = StringField("Phone", validators=[DataRequired(message="Campo obligatorio"), Length(max=40)])


class StoreForm(FlaskForm):
    name = StringField("Nombre", validators=[DataRequired(), Length(max=120)])


class UserCreateForm(FlaskForm):
    full_name = StringField("Nombre", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    role = SelectField(
        "Rol",
        choices=[("owner", "Owner"), ("staff", "Staff")],
        validators=[DataRequired()],
    )
    store_id = SelectField("Sucursal", coerce=int, validators=[DataRequired()])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=8, max=64)]
    )
    confirm = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Las contrasenas no coinciden"),
        ],
    )


class UserEditForm(FlaskForm):
    full_name = StringField("Nombre", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    role = SelectField(
        "Rol",
        choices=[("owner", "Owner"), ("staff", "Staff")],
        validators=[DataRequired()],
    )
    store_id = SelectField("Sucursal", coerce=int, validators=[DataRequired()])
    password = PasswordField(
        "Password", validators=[Optional(), Length(min=8, max=64)]
    )
    confirm = PasswordField("Confirm password", validators=[Optional()])

    def validate_confirm(self, field):
        if self.password.data and field.data != self.password.data:
            raise ValidationError("Las contrasenas no coinciden")


class SuperAdminProfileForm(FlaskForm):
    full_name = StringField("Nombre", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField(
        "Password", validators=[Optional(), Length(min=8, max=64)]
    )
    confirm = PasswordField("Confirm password", validators=[Optional()])

    def validate_confirm(self, field):
        if self.password.data and field.data != self.password.data:
            raise ValidationError("Las contrasenas no coinciden")

    def validate_password(self, field):
        password = field.data or ""
        if password and (
            not any(char.islower() for char in password)
            or not any(char.isupper() for char in password)
            or not any(char.isdigit() for char in password)
        ):
            raise ValidationError(
                "La contrasena debe incluir mayuscula, minuscula y numero"
            )


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
    model = StringField("Modelo", validators=[DataRequired(message="Campo obligatorio"), Length(max=80)])
    description = TextAreaField("Descripcion", validators=[Optional(), Length(max=300)])


class ServiceTypeForm(FlaskForm):
    name = StringField("Nombre", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Descripcion", validators=[Optional(), Length(max=500)])
    base_price = LocalizedDecimalField(
        "Precio base", validators=[DataRequired(message="Campo obligatorio"), NumberRange(min=0)], places=2
    )
    is_active = BooleanField("Activo")


class JobForm(FlaskForm):
    bicycle_id = SelectField("Bicicleta", coerce=int, validators=[DataRequired()])
    estimated_delivery_at = DateField(
        "Entrega estimada", validators=[DataRequired(message="Campo obligatorio")]
    )
    status = SelectField(
        "Estado",
        choices=[
            ("open", "Abierto"),
            ("in_progress", "En progreso"),
            ("ready", "Listo"),
            ("closed", "Cerrado"),
            ("cancelled", "Cancelado"),
        ],
        validators=[DataRequired()],
    )
    notes = TextAreaField("Notas", validators=[Optional(), Length(max=1000)])
    service_type_ids = SelectMultipleField(
        "Services", coerce=int, validators=[Optional()]
    )

    def validate_service_type_ids(self, field):
        if not field.data:
            raise ValidationError("Selecciona al menos un service")


class JobStatusForm(FlaskForm):
    status = SelectField(
        "Estado",
        choices=[
            ("open", "Abierto"),
            ("in_progress", "En progreso"),
            ("ready", "Listo"),
            ("closed", "Cerrado"),
            ("cancelled", "Cancelado"),
        ],
        validators=[DataRequired()],
    )


class TwoFactorSetupForm(FlaskForm):
    code = StringField(
        "Codigo",
        validators=[
            DataRequired(message="Campo obligatorio"),
            Length(min=6, max=6),
            Regexp(r"^\d{6}$", message="Codigo invalido"),
        ],
    )


class TwoFactorDisableForm(FlaskForm):
    password = PasswordField(
        "Password", validators=[DataRequired(message="Campo obligatorio")]
    )


class DeleteForm(FlaskForm):
    pass


class CSVImportForm(FlaskForm):
    import_type = SelectField(
        "Tipo de importacion",
        choices=[("clients", "Clientes"), ("bicycles", "Bicicletas")],
        validators=[DataRequired()],
    )
    csv_file = FileField(
        "Archivo CSV",
        validators=[
            FileRequired(message="Archivo requerido"),
            FileAllowed(["csv"], "Archivo CSV requerido"),
        ],
    )
