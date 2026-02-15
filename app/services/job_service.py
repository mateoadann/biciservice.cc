import random
import string
from decimal import Decimal, InvalidOperation
from datetime import datetime
from ..extensions import db
from ..models import Job, JobItem, JobPart, ServiceType
from .audit_service import AuditService

class JobService:
    @staticmethod
    def generate_job_code():
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(random.choices(alphabet, k=4))
            if not Job.query.filter_by(code=code).first():
                return code

    @staticmethod
    def parse_decimal(value: str | None):
        raw = (value or "").strip()
        if not raw:
            return None
        normalized = raw.replace(".", "").replace(",", ".")
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return None

    @staticmethod
    def parse_job_parts(form_data):
        """
        Parses parts from the form data (MultiDict).
        Returns (parts_list, error_message).
        """
        descriptions = form_data.getlist("part_description")
        quantities = form_data.getlist("part_quantity")
        prices = form_data.getlist("part_unit_price")
        kinds = form_data.getlist("part_kind")
        count = max(len(descriptions), len(quantities), len(prices), len(kinds))
        parts = []
        for idx in range(count):
            desc = descriptions[idx].strip() if idx < len(descriptions) else ""
            qty_raw = quantities[idx].strip() if idx < len(quantities) else ""
            price_raw = prices[idx].strip() if idx < len(prices) else ""
            kind = kinds[idx] if idx < len(kinds) else "part"
            if not desc and not qty_raw and not price_raw:
                continue
            if not desc:
                return None, "Completa la descripcion del repuesto."
            try:
                qty = int(qty_raw) if qty_raw else 1
            except ValueError:
                return None, "Cantidad invalida en repuestos."
            if qty < 1:
                return None, "Cantidad invalida en repuestos."
            price = JobService.parse_decimal(price_raw)
            if price is None or price < 0:
                return None, "Precio invalido en repuestos."
            if kind not in {"part", "supply", "other"}:
                kind = "part"
            parts.append(
                {
                    "description": desc,
                    "quantity": qty,
                    "unit_price": price,
                    "kind": kind,
                }
            )
        return parts, None

    @staticmethod
    def create_job(workshop_id, store_id, bicycle_id, status, notes, estimated_delivery_at, service_type_ids, parts_data, service_prices=None):
        code = JobService.generate_job_code()
        job = Job(
            workshop_id=workshop_id,
            store_id=store_id,
            bicycle_id=bicycle_id,
            code=code,
            status=status,
            notes=notes,
            estimated_delivery_at=estimated_delivery_at,
        )
        db.session.add(job)
        db.session.flush()

        # Add Service Items
        selected_ids = {sid for sid in service_type_ids if sid}
        if selected_ids:
            services = ServiceType.query.filter(
                ServiceType.workshop_id == workshop_id,
                ServiceType.id.in_(selected_ids),
            ).all()
            for service in services:
                price = service_prices.get(service.id, service.base_price) if service_prices else service.base_price
                job_item = JobItem(
                    job_id=job.id,
                    service_type_id=service.id,
                    quantity=1,
                    unit_price=price,
                )
                db.session.add(job_item)

        # Add Parts
        for part in parts_data:
            db.session.add(
                JobPart(
                    job_id=job.id,
                    description=part["description"],
                    quantity=part["quantity"],
                    unit_price=part["unit_price"],
                    kind=part["kind"],
                )
            )
        
        # Log creation
        AuditService.log_action(
            "create",
            "job",
            job.id,
            f"Trabajo {job.code}",
            workshop_id=workshop_id,
            store_id=store_id,
        )
        
        db.session.commit()
        return job

    @staticmethod
    def update_job(job, form_data):
        # Note: This method might need more arguments or structural changes depending on how we handle form data passage.
        # For now, we will perform the update logic assuming the caller provides validation results or raw data.
        # However, to decouple from WTForms, passing raw data and handling it here is robust, 
        # but parsing form data is already done partly.
        # Let's assume the caller handles form validation and passes the cleaner data.
        pass

    @staticmethod
    def update_job_full(job, bicycle_id, status, notes, estimated_delivery_at, service_type_ids, parts_data, service_prices=None):
        job.bicycle_id = bicycle_id
        job.status = status
        job.notes = notes
        job.estimated_delivery_at = estimated_delivery_at

        # Update Services
        existing_items = {item.service_type_id: item for item in job.items}
        selected_ids = {sid for sid in service_type_ids if sid}

        # Delete removed items
        for service_id, item in existing_items.items():
            if service_id not in selected_ids:
                db.session.delete(item)

        # Update prices on existing items
        if service_prices:
            for service_id, item in existing_items.items():
                if service_id in selected_ids and service_id in service_prices:
                    item.unit_price = service_prices[service_id]

        # Add new items
        services_to_add = ServiceType.query.filter(
            ServiceType.workshop_id == job.workshop_id,
            ServiceType.id.in_(selected_ids - existing_items.keys()),
        ).all()

        for service in services_to_add:
            price = service_prices.get(service.id, service.base_price) if service_prices else service.base_price
            db.session.add(
                JobItem(
                    job_id=job.id,
                    service_type_id=service.id,
                    quantity=1,
                    unit_price=price,
                )
            )

        # Update Parts (replace all for now as per previous logic)
        for part in job.parts:
            db.session.delete(part)
        
        for part in parts_data:
            db.session.add(
                JobPart(
                    job_id=job.id,
                    description=part["description"],
                    quantity=part["quantity"],
                    unit_price=part["unit_price"],
                    kind=part["kind"],
                )
            )

        AuditService.log_action(
            "update",
            "job",
            job.id,
            f"Trabajo {job.code}",
            workshop_id=job.workshop_id,
            store_id=job.store_id,
        )
        db.session.commit()
        return job

    @staticmethod
    def delete_job(job):
        for item in job.items:
            db.session.delete(item)
        for part in job.parts:
            db.session.delete(part)
        
        AuditService.log_action(
            "delete",
            "job",
            job.id,
            f"Trabajo {job.code}",
            workshop_id=job.workshop_id,
            store_id=job.store_id,
        )
        
        db.session.delete(job)
        db.session.commit()
