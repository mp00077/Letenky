"""Generate PyInstaller's Windows VERSIONINFO from the captured Git metadata."""
from pathlib import Path
import re


def write_version_info(path, metadata):
    tag = metadata["git_tag"]
    # Windows numeric fields require four unsigned 16-bit components. Preserve
    # the exact tag (including prerelease suffixes) in the visible string field.
    match = re.fullmatch(r"v?(\d+(?:\.\d+){0,3})(?:[-+][0-9A-Za-z.-]+)?", tag)
    parts = tuple(int(part) for part in match[1].split(".")) if match else ()
    numeric = parts + (0,) * (4 - len(parts)) if parts and max(parts) <= 65535 else (0, 0, 0, 0)
    strings = {
        "ProductName": "Letenky",
        "ProductVersion": tag,
        "FileVersion": ".".join(map(str, numeric)),
        "LegalCopyright": "M. Pospíšil",
        "FileDescription": "Hlídač cen letenek Ryanair",
        "InternalName": "Letenky",
        "OriginalFilename": "Letenky.exe",
    }
    entries = ",\n".join(f"        StringStruct({key!r}, {value!r})" for key, value in strings.items())
    text = f"""# UTF-8
VSVersionInfo(
    ffi=FixedFileInfo(filevers={numeric!r}, prodvers={numeric!r},
                     mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
    kids=[StringFileInfo([StringTable('040504B0', [
{entries}
    ])]), VarFileInfo([VarStruct('Translation', [0x0405, 1200])])]
)
"""
    Path(path).write_text(text, encoding="utf-8")
    return str(path)
