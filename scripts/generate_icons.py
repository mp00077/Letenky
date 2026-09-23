"""Generate native application icons from the window's SVG (no distribution build)."""
from pathlib import Path
import struct

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parents[1]


def generate():
    directory = ROOT / "resources/icons"
    renderer = QSvgRenderer(str(directory / "plane.svg"))
    if not renderer.isValid():
        raise ValueError("Invalid plane.svg")

    def png(size):
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, "PNG"):
            raise OSError("Cannot encode icon")
        return bytes(data)

    sizes = (16, 24, 32, 48, 64, 128, 256)
    images = [png(size) for size in sizes]
    offset = 6 + 16 * len(sizes)
    entries = []
    for size, data in zip(sizes, images):
        entries.append(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    (directory / "plane.ico").write_bytes(struct.pack("<HHH", 0, 1, len(sizes)) + b"".join(entries + images))
    chunks = []
    for code, size in ((b"icp4", 16), (b"icp5", 32), (b"icp6", 64), (b"ic07", 128),
                       (b"ic08", 256), (b"ic09", 512), (b"ic10", 1024)):
        data = png(size)
        chunks.append(code + struct.pack(">I", len(data) + 8) + data)
    payload = b"".join(chunks)
    (directory / "plane.icns").write_bytes(b"icns" + struct.pack(">I", len(payload) + 8) + payload)
    (directory / "plane.png").write_bytes(png(512))


if __name__ == "__main__":
    generate()
