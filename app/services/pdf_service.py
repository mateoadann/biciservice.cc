from io import BytesIO
from decimal import Decimal
import logging
from typing import Optional
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

from app.timezone import now_cordoba_naive


logger = logging.getLogger("pdf")


def _fmt(value):
    """Formatea un Decimal/numero a string con separador de miles y coma decimal."""
    if value is None:
        return "0,00"
    v = Decimal(str(value)).quantize(Decimal("0.01"))
    int_part, dec_part = str(v).split(".")
    sign = ""
    if int_part.startswith("-"):
        sign = "-"
        int_part = int_part[1:]
    groups = []
    while int_part:
        groups.append(int_part[-3:])
        int_part = int_part[:-3]
    return sign + ".".join(reversed(groups)) + "," + dec_part


def _status_label(status: Optional[str]) -> str:
    if not status:
        return "-"
    labels = {
        "open": "Abierto",
        "in_progress": "En progreso",
        "ready": "Listo",
        "closed": "Cerrado",
    }
    return str(labels.get(status, status))


def _kind_label(kind: Optional[str]) -> str:
    if not kind:
        return "-"
    labels = {"part": "Repuesto", "supply": "Insumo", "other": "Otro"}
    return str(labels.get(kind, kind))


def _safe_paragraph_text(value: object) -> str:
    if value is None:
        return ""
    return escape(str(value))


def generate_job_pdf(job, service_total, parts_total, total):
    """Genera un PDF con el detalle del trabajo y lo retorna como BytesIO."""
    try:
        buf = BytesIO()
        pdf_title = build_pdf_filename(job).replace(".pdf", "")
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            topMargin=20 * mm,
            bottomMargin=15 * mm,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            title=pdf_title,
            author=job.workshop.name if job.workshop else "Taller",
        )

        styles = getSampleStyleSheet()
        style_title = ParagraphStyle(
            "PDFTitle",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=2 * mm,
            textColor=colors.HexColor("#1f4cff"),
        )
        style_subtitle = ParagraphStyle(
            "PDFSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#6b7280"),
            spaceAfter=6 * mm,
        )
        style_section = ParagraphStyle(
            "PDFSection",
            parent=styles["Heading2"],
            fontSize=12,
            spaceBefore=6 * mm,
            spaceAfter=3 * mm,
            textColor=colors.HexColor("#10162f"),
        )
        style_normal = styles["Normal"]
        style_right = ParagraphStyle(
            "RightAligned", parent=styles["Normal"], alignment=TA_RIGHT
        )
        style_total_label = ParagraphStyle(
            "TotalLabel",
            parent=styles["Normal"],
            fontSize=11,
            fontName="Helvetica-Bold",
            alignment=TA_RIGHT,
        )
        style_total_value = ParagraphStyle(
            "TotalValue",
            parent=styles["Normal"],
            fontSize=11,
            fontName="Helvetica-Bold",
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#1f4cff"),
        )

        elements = []

        # --- Encabezado ---
        workshop_name = job.workshop.name if job.workshop else "Taller"
        safe_workshop_name = _safe_paragraph_text(workshop_name)
        safe_job_code = _safe_paragraph_text(job.code or "-")
        elements.append(Paragraph(safe_workshop_name, style_title))
        elements.append(Paragraph(f"Detalle de trabajo &mdash; {safe_job_code}", style_subtitle))

        # --- Informacion general ---
        elements.append(Paragraph("Informacion general", style_section))

        client_name = job.bicycle.client.full_name if job.bicycle and job.bicycle.client else "-"
        bike_brand = job.bicycle.brand or "Bicicleta" if job.bicycle else "-"
        bike_model = job.bicycle.model or "" if job.bicycle else ""
        bike_label = f"{bike_brand} {bike_model}".strip()
        fecha_ingreso = job.created_at.strftime("%d/%m/%Y") if job.created_at else "-"
        fecha_entrega = (
            job.estimated_delivery_at.strftime("%d/%m/%Y")
            if job.estimated_delivery_at
            else "-"
        )

        info_data = [
            ["Cliente", client_name, "Bicicleta", bike_label],
            ["Estado", _status_label(job.status), "Codigo", job.code],
            ["Ingreso al taller", fecha_ingreso, "Entrega estimada", fecha_entrega],
            ["Fecha de emision", now_cordoba_naive().strftime("%d/%m/%Y %H:%M"), "", ""],
        ]
        col_w = [35 * mm, 52 * mm, 38 * mm, 52 * mm]
        info_table = Table(info_data, colWidths=col_w)
        info_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#6b7280")),
                    ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#6b7280")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        elements.append(info_table)

        # --- Servicios ---
        if job.items:
            elements.append(Paragraph("Servicios", style_section))
            svc_data = [["Servicio", "Cant.", "Precio unit.", "Subtotal"]]
            for item in job.items:
                sub = (item.unit_price or 0) * (item.quantity or 0)
                service_name = str(item.service_type.name) if item.service_type and item.service_type.name else "-"
                svc_data.append([
                    service_name,
                    str(item.quantity or 0),
                    f"$ {_fmt(item.unit_price)}",
                    f"$ {_fmt(sub)}",
                ])
            svc_data.append(["", "", "Total servicios", f"$ {_fmt(service_total)}"])

            svc_col_w = [62 * mm, 18 * mm, 45 * mm, 45 * mm]
            svc_table = Table(svc_data, colWidths=svc_col_w)
            svc_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4ff")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#10162f")),
                        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#d1d5db")),
                        ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                        ("FONTNAME", (2, -1), (-1, -1), "Helvetica-Bold"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            elements.append(svc_table)

        # --- Repuestos y gastos ---
        if job.parts:
            elements.append(Paragraph("Repuestos y gastos", style_section))
            parts_data = [["Descripcion", "Tipo", "Cant.", "Precio unit.", "Subtotal"]]
            for part in job.parts:
                sub = (part.unit_price or 0) * (part.quantity or 0)
                parts_data.append([
                    str(part.description) if part.description else "-",
                    _kind_label(part.kind),
                    str(part.quantity or 0),
                    f"$ {_fmt(part.unit_price)}",
                    f"$ {_fmt(sub)}",
                ])
            parts_data.append(["", "", "", "Total repuestos", f"$ {_fmt(parts_total)}"])

            parts_col_w = [50 * mm, 28 * mm, 18 * mm, 38 * mm, 38 * mm]
            parts_table = Table(parts_data, colWidths=parts_col_w)
            parts_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4ff")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#10162f")),
                        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#d1d5db")),
                        ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                        ("FONTNAME", (3, -1), (-1, -1), "Helvetica-Bold"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            elements.append(parts_table)

        # --- Total general ---
        elements.append(Spacer(1, 4 * mm))
        total_data = [["TOTAL DEL TRABAJO", f"$ {_fmt(total)}"]]
        total_table = Table(total_data, colWidths=[130 * mm, 45 * mm])
        total_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1f4cff")),
                    ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor("#1f4cff")),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(total_table)

        # --- Notas ---
        if job.notes:
            elements.append(Spacer(1, 4 * mm))
            elements.append(Paragraph("Notas", style_section))
            elements.append(Paragraph(_safe_paragraph_text(job.notes), style_normal))

        doc.build(elements)
        buf.seek(0)
        return buf
    except Exception:
        logger.error(
            "Error generando PDF job_id=%s code=%s",
            job.id,
            job.code,
            exc_info=True,
        )
        raise


def build_pdf_filename(job):
    """Construye el nombre de archivo: Codigo_MesDD_nombre_cliente.pdf"""
    month_names = {
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
    }
    code = job.code or "0000"
    if job.created_at:
        month = month_names.get(job.created_at.month, "Ene")
        day = f"{job.created_at.day:02d}"
        date_part = f"{month}{day}"
    else:
        date_part = "Sin-fecha"

    client_name = "cliente"
    if job.bicycle and job.bicycle.client:
        client_name = job.bicycle.client.full_name.strip().replace(" ", "_").lower()

    return f"{code}_{date_part}_{client_name}.pdf"
