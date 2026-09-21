"""Single-page, vector PDF of the price chart; write atomically."""
from datetime import datetime

from PySide6.QtCore import QIODevice, QMarginsF, QRectF, QSaveFile, Qt
from PySide6.QtGui import QFont, QPageLayout, QPageSize, QPainter, QPdfWriter


def export_chart_pdf(path, watch, rows):
    from letenky.gui.widgets.price_chart import PriceChart

    output = QSaveFile(str(path))
    if not output.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError(output.errorString())
    painter = QPainter()
    chart_view = None
    try:
        writer = QPdfWriter(output)
        writer.setResolution(144)
        writer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4),
                                        QPageLayout.Orientation.Landscape,
                                        QMarginsF(15, 15, 15, 15)))
        writer.setTitle(f"Vývoj ceny {watch.origin} - {watch.destination}")
        writer.setCreator("Letenky")
        if not painter.begin(writer):
            raise OSError("Nepodařilo se zahájit zápis PDF.")
        width, height = writer.width(), writer.height()
        painter.fillRect(QRectF(0, 0, width, height), Qt.GlobalColor.white)
        painter.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        painter.drawText(QRectF(0, 0, width, 55), Qt.AlignmentFlag.AlignLeft,
                         f"{watch.origin} → {watch.destination} · {watch.flight_number}")
        painter.setFont(QFont("Arial", 10))
        departure = datetime.fromisoformat(watch.departure_local).strftime("%d. %m. %Y %H:%M")
        painter.drawText(QRectF(0, 60, width, 40), Qt.AlignmentFlag.AlignLeft,
                         f"Odlet: {departure} (místní čas letiště)")
        chart_view = PriceChart(rows, watch.currency)
        chart_view.resize(1100, 600)
        chart = chart_view.chart()
        chart.resize(1100, 600)
        chart.layout().activate()
        chart.scene().render(painter, QRectF(0, 115, width, height - 205),
                             chart.sceneBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        painter.setFont(QFont("Arial", 9))
        painter.drawText(QRectF(0, height - 65, width, 60), Qt.TextFlag.TextWordWrap,
                         "Body označují skutečná měření; chyby a chybějící nabídky přerušují řadu. "
                         "Minimum a maximum jsou ze získaných cen. Časy měření jsou v místním čase počítače.")
        if not painter.end():
            raise OSError("Nepodařilo se dokončit PDF.")
        del writer
        if not output.commit():
            raise OSError(output.errorString())
    except Exception:
        if painter.isActive():
            painter.end()
        output.cancelWriting()
        raise
    finally:
        if chart_view:
            chart_view.deleteLater()
