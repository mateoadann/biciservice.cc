from flask import abort, current_app, jsonify
from flask_login import current_user, login_required

from app.extensions import db
from app.main import main_bp


def _tour_version() -> int:
    try:
        parsed = int(current_app.config.get("APP_TOUR_VERSION", 1))
    except (TypeError, ValueError):
        return 1
    return max(parsed, 1)


@main_bp.route("/tour/dismiss", methods=["POST"])
@login_required
def tour_dismiss():
    if current_user.role == "super_admin":
        abort(403)

    current_user.tour_dismissed_version = _tour_version()
    db.session.commit()
    return jsonify({"ok": True})


@main_bp.route("/tour/complete", methods=["POST"])
@login_required
def tour_complete():
    if current_user.role == "super_admin":
        abort(403)

    current_user.tour_completed_version = _tour_version()
    db.session.commit()
    return jsonify({"ok": True})
