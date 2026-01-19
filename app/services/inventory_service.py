from ..extensions import db
from ..models import ServiceType
from .audit_service import AuditService

class InventoryService:
    @staticmethod
    def create_service(workshop_id, name, description, base_price, is_active):
        service = ServiceType(
            workshop_id=workshop_id,
            name=name,
            description=description,
            base_price=base_price or 0,
            is_active=is_active,
        )
        db.session.add(service)
        db.session.flush()
        AuditService.log_action(
            "create",
            "service",
            service.id,
            f"Service {service.name}",
            workshop_id=workshop_id,
        )
        db.session.commit()
        return service

    @staticmethod
    def update_service(service, name, description, base_price, is_active):
        service.name = name
        service.description = description
        if base_price is not None:
            service.base_price = base_price
        service.is_active = is_active
        
        AuditService.log_action(
            "update",
            "service",
            service.id,
            f"Service {service.name}",
            workshop_id=service.workshop_id,
        )
        db.session.commit()
        return service

    @staticmethod
    def delete_service(service):
        AuditService.log_action(
            "delete",
            "service",
            service.id,
            f"Service {service.name}",
            workshop_id=service.workshop_id,
        )
        db.session.delete(service)
        db.session.commit()
