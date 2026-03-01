from flask import request
from flask_login import current_user
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import AuditLog
from ..timezone import now_cordoba_naive, utc_to_cordoba_naive

class AuditService:
    @staticmethod
    def log_action(action, entity_type, entity_id=None, description=None, workshop_id=None, store_id=None):
        """Logs an action to the audit log."""
        ip_value = request.headers.get("X-Forwarded-For", request.remote_addr) or ""
        ip_address = ip_value.split(",")[0].strip() if ip_value else None
        user_agent = request.headers.get("User-Agent")
        
        user_id = current_user.id if current_user and current_user.is_authenticated else None

        log_entry = AuditLog(
            user_id=user_id,
            workshop_id=workshop_id,
            store_id=store_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent[:255] if user_agent else None,
            created_at=now_cordoba_naive(),
        )
        db.session.add(log_entry)
        # Note: We rely on the caller to commit the session, or we could commit here.
        # Given the existing pattern in routes, the commit often happens later.
        # But for an audit log, it might be safer to flush or let the main transaction handle it.
        # We will follow the pattern of adding to session.

    @staticmethod
    def get_audit_info(entity_type, entity_id, fallback_created_at=None, update_entity_types=None):
        """Retrieves creation and update info for an entity from the audit log."""
        update_types = update_entity_types or [entity_type]
        created_log = (
            AuditLog.query.filter_by(entity_type=entity_type, entity_id=entity_id, action="create")
            .options(joinedload(AuditLog.user))
            .order_by(AuditLog.created_at.asc())
            .first()
        )
        updated_log = (
            AuditLog.query.filter(
                AuditLog.entity_type.in_(update_types),
                AuditLog.entity_id == entity_id,
                AuditLog.action == "update",
            )
            .options(joinedload(AuditLog.user))
            .order_by(AuditLog.created_at.desc())
            .first()
        )
        created_at = (
            created_log.created_at
            if created_log
            else utc_to_cordoba_naive(fallback_created_at)
        )
        created_by = created_log.user.full_name if created_log and created_log.user else None
        updated_at = updated_log.created_at if updated_log else None
        updated_by = updated_log.user.full_name if updated_log and updated_log.user else None
        return created_at, created_by, updated_at, updated_by
