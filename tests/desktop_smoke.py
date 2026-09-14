"""End-to-end Qt application test using real media and the complete dataset."""
import csv
import json
import sys
import time
from pathlib import Path
import cv2
import numpy as np
from PySide6 import QtCore,QtGui,QtWidgets,QtTest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from studio.model import Dataset
from studio.window import Window

app=QtWidgets.QApplication([])
out=Path(sys.argv[1]).resolve(); out.mkdir(parents=True,exist_ok=True)
video=out/'drag test.mp4'
writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'mp4v'),30,(480,270))
assert writer.isOpened()
for i in range(120):
    y,x=np.mgrid[:270,:480]; gray=((np.sin(x/20-i*.2)>0)*230).astype(np.uint8)
    writer.write(np.repeat(gray[:,:,None],3,axis=2))
writer.release()
window=Window(Dataset(Path(__file__).resolve().parents[1]/'data')); window.show()

def wait_for(predicate,timeout=15):
    deadline=time.perf_counter()+timeout
    while time.perf_counter()<deadline:
        app.processEvents(); time.sleep(.03)
        if predicate(): return
    print('TIMEOUT STATE', {k:v for k,v in (window.packet or {}).items() if k in ['notice','playing','elapsed','index','name']},flush=True)
    raise AssertionError('UI condition timed out')

try:
    wait_for(lambda:window.packet and window.packet['elapsed']>1)
    assert window.packet['total'].sum()>0
    window.language.setCurrentIndex(1)
    assert window.play_button.text() in ('Pause','Play')
    assert window.category.itemText(0)=='All categories'
    window.side.setCurrentIndex(1); window.preset.setCurrentIndex(2)
    assert window.brain.opts['elevation']==89
    window.side.setCurrentIndex(0); window.preset.setCurrentIndex(0)
    window.content.setSizes([470,600,310]); app.processEvents()
    assert window.content.sizes()[0]>355
    window.reset_layout(); app.processEvents(); assert abs(window.content.sizes()[0]-300)<20
    window.language.setCurrentIndex(0)
    assert window.category.itemText(0)=='全部分类'
    assert window.packet['small'].ndim==3 and window.packet['small'].shape==(72,128,3)
    window.eye_toggle.click(); assert not window.eye_panel.isVisible()
    window.eye_toggle.click(); assert window.eye_panel.isVisible()
    window.rest_size.setValue(3); window.firing_size.setValue(12)
    assert window.brain.point_size==3 and window.brain.firing_size==12
    window.reset_sizes.click(); assert window.brain.point_size==1.65 and window.brain.firing_size==4.45
    window.vision_mode.setCurrentIndex(1); wait_for(lambda:window.packet['color_mode']=='gray')
    window.audio_toggle.setChecked(False); wait_for(lambda:not window.packet['audio_enabled'])
    window.reset_inputs(); wait_for(lambda:window.packet['color_mode']=='rgb' and window.packet['audio_enabled'])
    QtTest.QTest.mouseClick(window.play_button,QtCore.Qt.MouseButton.LeftButton)
    wait_for(lambda:not window.packet['playing'])
    elapsed=window.packet['elapsed']; QtTest.QTest.qWait(200); app.processEvents(); assert window.packet['elapsed']==elapsed
    # Test native file drag/drop through Qt event dispatch.
    mime=QtCore.QMimeData(); mime.setUrls([QtCore.QUrl.fromLocalFile(str(video))])
    enter=QtGui.QDragEnterEvent(QtCore.QPoint(100,100),QtCore.Qt.DropAction.CopyAction,mime,QtCore.Qt.MouseButton.LeftButton,QtCore.Qt.KeyboardModifier.NoModifier)
    app.sendEvent(window,enter); assert enter.isAccepted()
    drop=QtGui.QDropEvent(QtCore.QPointF(100,100),QtCore.Qt.DropAction.CopyAction,mime,QtCore.Qt.MouseButton.LeftButton,QtCore.Qt.KeyboardModifier.NoModifier)
    app.sendEvent(window,drop)
    wait_for(lambda:Path(window.packet['name'])==video and window.packet['elapsed']>.4)
    epoch=window.packet['epoch']; window.engine.command('play',False); window.engine.command('seek',60)
    wait_for(lambda:window.packet['epoch']>epoch and window.packet['index']==60)
    assert window.packet['elapsed']==0 and not window.packet['total'].any()
    window.category.setCurrentIndex(1); assert np.all(window.data.category[window.brain.visible_ids]==0)
    window.category.setCurrentIndex(0)
    target=int(window.data.input_ids[10]); window.search.setText(str(window.data.ids[target]))
    QtTest.QTest.keyClick(window.search,QtCore.Qt.Key.Key_Return); assert window.selected==target
    # Native 3D click based on projected point position.
    viewport=window.brain.getViewport()
    matrix=np.array((window.brain.projectionMatrix(viewport,viewport)*window.brain.viewMatrix()).copyDataTo()).reshape(4,4)
    p=matrix@np.r_[window.data.positions[target],1.]; p=p[:3]/p[3]
    point=QtCore.QPoint(int((p[0]+1)*window.brain.width()/2),int((1-p[1])*window.brain.height()/2))
    picked=[]; window.brain.picked.connect(picked.append)
    QtTest.QTest.mouseClick(window.brain,QtCore.Qt.MouseButton.LeftButton,pos=point)
    assert picked, '3D point picking did not emit a neuron ID'
    window.clear_selection_button.click()
    assert window.selected is None and window.brain.selected is None
    assert len(window.brain.marker.pos)==0 and len(window.brain.links_out.pos)==0
    window.select_neuron(target)
    QtTest.QTest.keyClick(window.brain,QtCore.Qt.Key.Key_Escape)
    assert window.selected is None
    window.brain.pan(20,30,0); window.brain.opts['fov']=35
    window.brain.setCameraPosition(distance=100,elevation=60,azimuth=40)
    window.rotate.setChecked(True); window.reset_view_button.click()
    assert window.brain.opts['center'].length()==0 and window.brain.opts['distance']==285
    assert window.brain.opts['fov']==60 and not window.auto_rotate
    az=window.brain.opts['azimuth']; window.brain.orbit(30,10); assert window.brain.opts['azimuth']!=az
    window.engine.command('play',True); wait_for(lambda:window.packet['elapsed']>.8)
    window.engine.command('play',False); wait_for(lambda:not window.packet['playing'])
    export=out/'events.csv'; window.engine.command('export',str(export)); wait_for(lambda:export.exists() and export.with_suffix('.json').exists())
    with export.open(encoding='utf-8-sig') as f: rows=list(csv.reader(f))
    assert len(rows)>1 and rows[0]==['simulation_seconds','root_id']
    assert all(float(row[0])<=window.packet['elapsed']+.0001 for row in rows[1:])
    assert all(row[1] in window.data.id_lookup for row in rows[1:])
    window.engine.command('load',str(out/'does-not-exist.mp4'))
    wait_for(lambda:'无法解码' in window.packet['notice'])
    assert Path(window.packet['name'])==video
    from test_senses import make_av
    sound_video=out/'av-ui.mp4'; make_av(sound_video)
    window.engine.command('load',str(sound_video))
    wait_for(lambda:Path(window.packet['name'])==sound_video and window.packet['elapsed']>.4)
    assert '已连接' in window.packet['audio_status']
    assert window.packet['audio_levels'].max()>.01
    window.monitor_toggle.setChecked(True)
    from PySide6.QtMultimedia import QMediaPlayer
    wait_for(lambda:window.monitor.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState)
    assert window.monitor.player.error()==QMediaPlayer.Error.NoError
    window.monitor_toggle.setChecked(False)
    wait_for(lambda:window.monitor.player.playbackState()!=QMediaPlayer.PlaybackState.PlayingState)
    window.brain.camera_preset('正面'); window.grab().save(str(out/'desktop-tested.png'))
    print(json.dumps(dict(tests='pause, drag/drop, seek/reset, filters, 3D pick, export, invalid video, RGB, sound, monitor playback, point sizes/reset, collapse',
        neurons=window.data.n, edges=len(window.data.pre),exported_events=len(rows)-1),ensure_ascii=False))
finally:
    window.close(); app.processEvents()
