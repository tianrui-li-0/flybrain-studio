"""Build the code-native application icon and retain distribution licenses."""
import importlib.metadata as md
from pathlib import Path
import shutil
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage,QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

root=Path(__file__).resolve().parents[1]
app=QApplication([])
image=QImage(256,256,QImage.Format.Format_ARGB32); image.fill(Qt.GlobalColor.transparent)
painter=QPainter(image); QSvgRenderer(str(root/'assets/icon.svg')).render(painter); painter.end()
assert image.save(str(root/'assets/icon.ico'))
for name in ['PySide6','PySide6_Essentials','PySide6_Addons','shiboken6','pyqtgraph','PyOpenGL','numpy','scipy','opencv-python','av']:
    dist=md.distribution(name)
    for relative in dist.files or []:
        if not any(word in str(relative).lower() for word in ['license','copying']): continue
        source=Path(dist.locate_file(relative))
        if source.is_file():
            target=root/'third-party-licenses'/name/str(relative).replace('..','_')
            target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,target)
print('Icon and dependency licenses collected.')
python_license=Path(sys.base_prefix)/'LICENSE_PYTHON.txt'
if python_license.exists(): shutil.copyfile(python_license,root/'third-party-licenses/LICENSE_PYTHON.txt')
