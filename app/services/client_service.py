import csv
import logging
from io import StringIO

from sqlalchemy import func

from ..extensions import db
from ..models import Client, Bicycle, User
from .audit_service import AuditService
from ..main.forms import BRAND_CHOICES


logger = logging.getLogger("client_service")

class ClientService:
    @staticmethod
    def generate_client_code(workshop_id):
        max_code = db.session.query(func.max(
            db.cast(Client.client_code, db.Integer)
        )).filter(
            Client.workshop_id == workshop_id
        ).scalar()
        return str((max_code or 99) + 1)

    @staticmethod
    def create_client(workshop_id, full_name, email, phone):
        email_value = (email or "").strip() or None
        code = ClientService.generate_client_code(workshop_id)
        client = Client(
            workshop_id=workshop_id,
            client_code=code,
            full_name=full_name,
            email=email_value,
            phone=phone,
        )
        db.session.add(client)
        db.session.flush()
        AuditService.log_action(
            "create",
            "client",
            client.id,
            f"Cliente {client.full_name} (#{code})",
            workshop_id=workshop_id,
        )
        db.session.commit()
        return client

    @staticmethod
    def update_client(client, full_name, email, phone):
        email_value = (email or "").strip() or None
        client.full_name = full_name
        client.email = email_value
        client.phone = phone
        AuditService.log_action(
            "update",
            "client",
            client.id,
            f"Cliente {client.full_name}",
            workshop_id=client.workshop_id,
        )
        db.session.commit()
        return client

    @staticmethod
    def delete_client(client):
        AuditService.log_action(
            "delete",
            "client",
            client.id,
            f"Cliente {client.full_name}",
            workshop_id=client.workshop_id,
        )
        db.session.delete(client)
        db.session.commit()

    @staticmethod
    def create_bicycle(workshop_id, client_id, brand, model, description):
        bicycle = Bicycle(
            workshop_id=workshop_id,
            client_id=client_id,
            brand=brand,
            model=model,
            description=description,
        )
        db.session.add(bicycle)
        db.session.flush()
        label = " ".join([value for value in [bicycle.brand, bicycle.model] if value])
        AuditService.log_action(
            "create",
            "bicycle",
            bicycle.id,
            f"Bicicleta {label}".strip(),
            workshop_id=workshop_id,
        )
        db.session.commit()
        return bicycle

    @staticmethod
    def update_bicycle(bicycle, client_id, brand, model, description):
        bicycle.client_id = client_id
        bicycle.brand = brand
        bicycle.model = model
        bicycle.description = description
        label = " ".join([value for value in [bicycle.brand, bicycle.model] if value])
        AuditService.log_action(
            "update",
            "bicycle",
            bicycle.id,
            f"Bicicleta {label}".strip(),
            workshop_id=bicycle.workshop_id,
        )
        db.session.commit()
        return bicycle

    @staticmethod
    def delete_bicycle(bicycle):
        label = " ".join([value for value in [bicycle.brand, bicycle.model] if value])
        AuditService.log_action(
            "delete",
            "bicycle",
            bicycle.id,
            f"Bicicleta {label}".strip(),
            workshop_id=bicycle.workshop_id,
        )
        db.session.delete(bicycle)
        db.session.commit()

    @staticmethod
    def import_clients_csv(workshop_id, file_storage):
        data = file_storage.read()
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning(
                "CSV clientes: encoding no valido, usando fallback con errors=ignore"
            )
            content = data.decode("utf-8", errors="ignore")

        reader = csv.DictReader(StringIO(content))
        if not reader.fieldnames:
            return 0, 0, "El CSV no tiene encabezados"

        headers = {
            name.strip().lower(): name for name in reader.fieldnames if name and name.strip()
        }

        name_key = headers.get("full_name") or headers.get("nombre")
        email_key = headers.get("email") or headers.get("correo")
        phone_key = headers.get("phone") or headers.get("telefono")
        if not name_key:
            return 0, 0, "El CSV de clientes necesita la columna full_name"

        created = 0
        skipped = 0
        for row in reader:
            full_name = (row.get(name_key) or "").strip()
            if not full_name:
                skipped += 1
                continue
            email = (row.get(email_key) or "").strip() if email_key else ""
            phone = (row.get(phone_key) or "").strip() if phone_key else ""
            if email:
                existing = Client.query.filter_by(
                    workshop_id=workshop_id, email=email
                ).first()
                if existing:
                    skipped += 1
                    continue

            code = ClientService.generate_client_code(workshop_id)
            client = Client(
                workshop_id=workshop_id,
                client_code=code,
                full_name=full_name,
                email=email or None,
                phone=phone or None,
            )
            db.session.add(client)
            db.session.flush()
            AuditService.log_action(
                "create",
                "client",
                client.id,
                f"Cliente {client.full_name} (#{code})",
                workshop_id=workshop_id,
            )
            created += 1

        db.session.commit()
        return created, skipped, None

    @staticmethod
    def import_bicycles_csv(workshop_id, file_storage):
        data = file_storage.read()
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning(
                "CSV bicicletas: encoding no valido, usando fallback con errors=ignore"
            )
            content = data.decode("utf-8", errors="ignore")

        reader = csv.DictReader(StringIO(content))
        if not reader.fieldnames:
             return 0, 0, "El CSV no tiene encabezados"

        headers = {
            name.strip().lower(): name for name in reader.fieldnames if name and name.strip()
        }
        
        code_key = (
            headers.get("client_code")
            or headers.get("codigo_cliente")
            or headers.get("codigo")
        )
        brand_key = headers.get("brand") or headers.get("marca")
        model_key = headers.get("model") or headers.get("modelo")
        desc_key = headers.get("description") or headers.get("descripcion")

        if not code_key:
            return 0, 0, "El CSV de bicicletas necesita la columna client_code"

        created = 0
        skipped = 0
        for row in reader:
            client_code = (row.get(code_key) or "").strip()
            if not client_code:
                skipped += 1
                continue

            client = Client.query.filter_by(
                workshop_id=workshop_id, client_code=client_code
            ).first()
            if not client:
                skipped += 1
                continue

            brand = (row.get(brand_key) or "").strip() if brand_key else ""
            if brand and brand not in BRAND_CHOICES:
                brand = "Otra"
            model = (row.get(model_key) or "").strip() if model_key else ""
            description = (row.get(desc_key) or "").strip() if desc_key else ""

            bicycle = Bicycle(
                workshop_id=workshop_id,
                client_id=client.id,
                brand=brand or None,
                model=model or None,
                description=description or None,
            )
            db.session.add(bicycle)
            db.session.flush()
            label = " ".join([value for value in [bicycle.brand, bicycle.model] if value])
            AuditService.log_action(
                "create",
                "bicycle",
                bicycle.id,
                f"Bicicleta {label}".strip(),
                workshop_id=workshop_id,
            )
            created += 1

        db.session.commit()
        return created, skipped, None
