from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.main import main_bp
from app.services.client_service import ClientService
from app.main.forms import CSVImportForm
from app.main.helpers import (
    get_workshop_or_redirect,
    owner_or_redirect
)

@main_bp.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    workshop, redirect_response = get_workshop_or_redirect()
    if redirect_response:
        return redirect_response

    _, owner_redirect = owner_or_redirect()
    if owner_redirect:
        return owner_redirect

    form = CSVImportForm()
    if form.validate_on_submit():
        import_type = form.import_type.data
        file_storage = form.csv_file.data
        
        if import_type == "clients":
            created, skipped, error = ClientService.import_clients_csv(workshop.id, file_storage)
            if error:
                flash(error, "error")
                return redirect(url_for("main.onboarding"))
            
            flash(
                f"Importacion completada: {created} clientes creados, {skipped} omitidos",
                "success",
            )
            return redirect(url_for("main.onboarding"))

        if import_type == "bicycles":
            created, skipped, error = ClientService.import_bicycles_csv(workshop.id, file_storage)
            if error:
                flash(error, "error")
                return redirect(url_for("main.onboarding"))
                
            flash(
                f"Importacion completada: {created} bicicletas creadas, {skipped} omitidas",
                "success",
            )
            return redirect(url_for("main.onboarding"))

        flash("Tipo de importacion invalido", "error")
        return redirect(url_for("main.onboarding"))

    if request.method == "POST":
        flash("Revisa el archivo CSV", "error")

    return render_template("main/onboarding/index.html", form=form)
