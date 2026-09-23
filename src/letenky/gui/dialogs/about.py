import sys
from datetime import datetime

from PySide6.QtWidgets import QDialog, QDialogButtonBox

from letenky.gui.generated.ui_about import Ui_AboutDialog


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_AboutDialog()
        self.ui.setupUi(self)
        from letenky.infrastructure.build_info import get_build_info
        info = get_build_info()
        built_at = (datetime.fromisoformat(info["built_at"]).astimezone().strftime("%d. %m. %Y %H:%M %Z")
                    if info["built_at"] else
                    "Nedostupné" if getattr(sys, "frozen", False) else "Vývojová verze (ze zdrojů)")
        self.ui.buildDateLabel.setText(f"Datum sestavení: {built_at}")
        self.ui.pythonLabel.setText(f"Python: {info['python']}")
        self.ui.gitTagLabel.setText(f"Git tag: {info['git_tag']}")
        suffix = " (s necommitovanými změnami)" if info.get("dirty") else ""
        commit = info['git_commit']
        short_commit = commit[:8] if len(commit) >= 40 and all(c in "0123456789abcdefABCDEF" for c in commit) else commit
        self.ui.gitCommitLabel.setText(f"Git commit: {short_commit}{suffix}")
        self.ui.gitCommitLabel.setToolTip(commit)
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Close).setText("Zavřít")
        self.ui.buttonBox.rejected.connect(self.reject)
