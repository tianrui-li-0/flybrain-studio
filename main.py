import argparse
import os
import sys
from pathlib import Path

def main():
    # Qt ships its own plugins; don't inherit OpenCV's Qt plugin settings.
    os.environ.setdefault('PYQTGRAPH_QT_LIB','PySide6')
    from PySide6 import QtCore, QtGui, QtWidgets
    from studio.model import Dataset
    from studio.window import Window
    parser=argparse.ArgumentParser(); parser.add_argument('--video'); parser.add_argument('--smoke',type=Path)
    args=parser.parse_args()
    app=QtWidgets.QApplication(sys.argv); app.setApplicationName('FlyBrain Studio')
    base=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
    app.setWindowIcon(QtGui.QIcon(str(base/'assets/icon.ico')))
    splash=QtWidgets.QSplashScreen(); splash.showMessage('FlyBrain Studio\n正在载入真实连接组…',QtCore.Qt.AlignmentFlag.AlignCenter); splash.resize(440,180); splash.show(); app.processEvents()
    try:
        data=Dataset(base/'data'); window=Window(data)
    except Exception as error:
        splash.close(); QtWidgets.QMessageBox.critical(None,'启动失败',str(error)); return 1
    window.show(); splash.finish(window)
    if args.video: window.engine.command('load',args.video)
    if args.smoke:
        def capture():
            args.smoke.parent.mkdir(parents=True,exist_ok=True)
            window.grab().save(str(args.smoke)); window.brain.grabFramebuffer().save(str(args.smoke.with_name('brain-render.png')))
            import json
            state=window.packet or {}
            args.smoke.with_suffix('.json').write_text(json.dumps({key:state.get(key) for key in ['elapsed','audio_status','audio_enabled','color_mode','sample_width','notice']},ensure_ascii=False,indent=2),encoding='utf-8')
            print('SMOKE', data.n, len(data.pre), window.packet['elapsed'] if window.packet else None, flush=True)
            window.close(); app.quit()
        QtCore.QTimer.singleShot(8000,capture)
    return app.exec()

if __name__=='__main__': sys.exit(main())
