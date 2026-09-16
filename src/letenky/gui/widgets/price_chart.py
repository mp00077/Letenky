from datetime import datetime

from PySide6.QtCharts import QChart, QChartView, QDateTimeAxis, QLineSeries, QScatterSeries, QValueAxis
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from letenky.domain.price import currency_factor, currency_decimals


class PriceChart(QChartView):
    def __init__(self, rows, currency, parent=None):
        chart = QChart()
        super().__init__(chart, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMinimumHeight(285)
        chart.legend().hide()
        chart.setBackgroundBrush(QColor("#ffffff"))
        points = []
        segments, segment = [], []
        for row in rows:
            if row["amount_minor"] is None:
                if segment:
                    segments.append(segment)
                    segment = []
                continue
            x = datetime.fromisoformat(row["observed_at"]).timestamp() * 1000
            point = (x, row["amount_minor"] / currency_factor(currency))
            points.append(point)
            segment.append(point)
        if segment:
            segments.append(segment)
        if not points:
            chart.setTitle("Zatím nejsou k dispozici cenová měření")
            return
        axis_x = QDateTimeAxis()
        axis_x.setFormat("dd. MM. HH:mm")
        axis_x.setTickCount(4)
        axis_x.setTitleText("Čas zjištění · místní čas počítače")
        axis_y = QValueAxis()
        axis_y.setLabelFormat(f"%.{currency_decimals(currency)}f")
        axis_y.setTitleText(currency)
        min_x, max_x = min(x for x, _ in points), max(x for x, _ in points)
        if min_x == max_x:
            min_x, max_x = min_x - 3_600_000, max_x + 3_600_000
        axis_x.setRange(QDateTime.fromMSecsSinceEpoch(int(min_x)), QDateTime.fromMSecsSinceEpoch(int(max_x)))
        min_y, max_y = min(y for _, y in points), max(y for _, y in points)
        padding = max((max_y - min_y) * 0.15, max_y * 0.03, 1)
        axis_y.setRange(max(0, min_y - padding), max_y + padding)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        for segment in segments:
            if len(segment) < 2:
                continue
            series = QLineSeries()
            series.setPen(QPen(QColor("#477967"), 2))
            for x, y in segment:
                series.append(x, y)
            chart.addSeries(series)
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
        dots = QScatterSeries()
        dots.setMarkerSize(9)
        dots.setColor(QColor("#173e3a"))
        dots.setBorderColor(QColor("#ffffff"))
        for x, y in points:
            dots.append(x, y)
        chart.addSeries(dots)
        dots.attachAxis(axis_x)
        dots.attachAxis(axis_y)
