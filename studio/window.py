import json
import queue
import time
from pathlib import Path
import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets as W
from .model import CATEGORIES, PALETTE
from .engine import Engine
from .brain_view import BrainView
from .audio_monitor import AudioMonitor
from . import i18n

STYLE = '''
QMainWindow,QWidget { background:#0b1220; color:#d7e3f4; font-family:'Microsoft YaHei UI','Segoe UI'; font-size:12px; }
QFrame#panel { background:#101b2b; border:1px solid #213249; border-radius:10px; }
QLabel { background:transparent; border:none; }
QLabel#title { font-size:24px; font-weight:700; color:#f0f7ff; }
QLabel#subtle { color:#8c9fb8; font-size:11px; }
QLabel#heading { font-size:12px; font-weight:700; color:#a9bbd1; }
QLabel#metric { font-size:21px; font-weight:700; color:#76e7cb; }
QPushButton { background:#17263a; border:1px solid #2c4059; border-radius:6px; padding:7px 11px; }
QPushButton:hover { background:#233b51; border-color:#64cdbb; }
QPushButton#primary { background:#70dfc3; color:#07231d; font-weight:700; border:none; }
QPushButton:disabled { color:#566477; }
QComboBox,QLineEdit,QSpinBox,QDoubleSpinBox { background:#0a1422; border:1px solid #304158; border-radius:5px; padding:5px; }
QScrollArea { border:none; }
QScrollBar:vertical { background:#0b1422; width:9px; margin:0; }
QScrollBar::handle:vertical { background:#334b63; min-height:30px; border-radius:4px; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical { background:none; }
QToolButton { border:none; background:transparent; color:#a9bbd1; font-weight:700; padding:6px 0; }
QComboBox QAbstractItemView { background:#132239; selection-background-color:#294b60; }
QSlider::groove:horizontal { height:4px; background:#27394d; border-radius:2px; }
QSlider::sub-page:horizontal { background:#68d9c4; }
QSlider::handle:horizontal { width:12px; margin:-5px 0; background:#b8ffee; border-radius:6px; }
QTabWidget::pane { border:0; }
QTabBar::tab { padding:7px 13px; background:#111e30; color:#8197b1; }
QTabBar::tab:selected { color:#8cf1d7; border-bottom:2px solid #79e7cf; }
QListWidget { background:#0d1726; border:1px solid #22344a; border-radius:5px; }
QListWidget::item { padding:5px; }
QListWidget::item:selected { background:#234555; color:#b8ffee; }
QTextBrowser { background:#0d1726; border:none; }
QCheckBox { spacing:7px; }
QStatusBar { background:#07101c; color:#8da5bd; }
QSplitter::handle { background:#0b1220; }
QProgressBar { border:none; background:#26364a; border-radius:3px; height:5px; }
QProgressBar::chunk { background:#60cabd; border-radius:3px; }
QToolTip { color:#e5f8ff; background:#233a50; border:1px solid #588d9b; }
'''

def label(text, kind=None):
    item = i18n.Label(text)
    if kind: item.setObjectName(kind)
    return item

def panel(title):
    box = W.QFrame(); box.setObjectName('panel')
    layout = W.QVBoxLayout(box); layout.setContentsMargins(14,12,14,12); layout.setSpacing(10)
    if title: layout.addWidget(label(title,'heading'))
    return box,layout

def button(text, callback, primary=False):
    b = i18n.Button(text); b.clicked.connect(callback)
    if primary: b.setObjectName('primary')
    return b

class Window(W.QMainWindow):
    def __init__(self,data):
        super().__init__(); self.data = data
        self.setStatusBar(i18n.StatusBar(self))
        self.setWindowTitle('FlyBrain Studio · 果蝇脑活动实验室')
        self.resize(1510,950); self.setMinimumSize(1120,780); self.setAcceptDrops(True)
        self.setStyleSheet(STYLE); pg.setConfigOptions(antialias=False, background='#0c1727',foreground='#899eb6')
        self.engine = Engine(data); self.packet = None; self.selected = int(data.input_ids[0]); self.last_epoch = -1
        self.monitor=AudioMonitor(self)
        self.last_total = np.zeros(data.n,np.uint64); self.last_elapsed = 0.
        self.start_wall = time.perf_counter(); self.start_sim = 0.; self.last_perf = 0.
        self.auto_rotate = False; self.history = np.zeros((240,256),np.uint16)
        # Stratified deterministic sample, annotated explicitly in the graph title.
        sample = []
        for cat in range(7):
            ids = np.flatnonzero(data.category==cat)
            if len(ids): sample.extend(ids[np.linspace(0,len(ids)-1,37,dtype=int)])
        self.sample = np.array(sample[:256]); self.history = np.zeros((240,len(self.sample)),np.uint16)
        self.trace_x = []; self.trace_y = []; self.rate_history = []
        root = W.QWidget(); self.setCentralWidget(root); outer = W.QVBoxLayout(root)
        outer.setContentsMargins(20,15,20,10); outer.setSpacing(12)
        header = W.QHBoxLayout(); titles = W.QVBoxLayout()
        titles.addWidget(label('FLYBRAIN  /  STUDIO','title'))
        titles.addWidget(label('果蝇脑活动实验室     ·     真实连接与坐标 / 近似脉冲动力学','subtle'))
        header.addLayout(titles); header.addStretch()
        header.addWidget(label('FAFB v783   ·   LOCAL','metric'))
        header.addSpacing(16); header.addWidget(button('使用说明',self.help))
        header.addWidget(button('复位布局',self.reset_layout))
        self.language=W.QComboBox(); self.language.addItems(['中文','English']); header.addWidget(self.language)
        header.addWidget(button('保存视图',self.save_view)); outer.addLayout(header)
        content = W.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.content=content; content.setHandleWidth(9)
        content.setChildrenCollapsible(False)
        left,left_l = panel('01   视觉输入'); left.setMinimumWidth(265)
        self.video_image = label('拖入本地视频'); self.video_image.setMinimumHeight(156)
        self.video_image.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        left_l.addWidget(self.video_image)
        self.video_name = label('内置视觉刺激','subtle'); self.video_name.setWordWrap(True); left_l.addWidget(self.video_name)
        self.seek = W.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.seek.sliderPressed.connect(lambda: self.engine.command('play',False))
        self.seek.sliderReleased.connect(self.seek_release); left_l.addWidget(self.seek)
        self.time_label = label('00:00 / 00:30','subtle'); left_l.addWidget(self.time_label)
        row = W.QHBoxLayout(); self.play_button = button('暂停',self.toggle_play,True)
        row.addWidget(self.play_button); row.addWidget(button('打开视频…',self.open_video)); left_l.addLayout(row)
        row = W.QHBoxLayout(); row.addWidget(button('内置刺激',lambda:self.engine.command('demo')))
        self.loop = W.QCheckBox('循环'); self.loop.setChecked(True); self.loop.toggled.connect(lambda v:self.engine.command('loop',v)); row.addWidget(self.loop)
        self.speed = W.QComboBox(); self.speed.addItems(['0.25×','0.5×','1×','2×']); self.speed.setCurrentIndex(2)
        self.speed.currentIndexChanged.connect(lambda i:(self.engine.command('speed',[.25,.5,1.,2.][i]),setattr(self.monitor,'speed',[.25,.5,1.,2.][i]))); row.addWidget(self.speed); left_l.addLayout(row)
        left_l.addWidget(label('拖放本地视频到窗口任意位置。','subtle'))
        row=W.QHBoxLayout(); self.vision_mode=W.QComboBox(); self.vision_mode.addItems(['RGB 实验编码','灰度对照'])
        self.vision_mode.currentIndexChanged.connect(lambda i:self.engine.command('color',['rgb','gray'][i])); row.addWidget(self.vision_mode)
        self.resolution=W.QComboBox(); self.resolution.addItems(['64×36','128×72','256×144']); self.resolution.setCurrentIndex(1)
        self.resolution.currentIndexChanged.connect(lambda i:self.engine.command('resolution',[64,128,256][i])); row.addWidget(self.resolution); left_l.addLayout(row)
        self.eye_toggle=W.QToolButton(); self.eye_toggle.setText('视觉采样'); self.eye_toggle.setCheckable(True); self.eye_toggle.setChecked(True)
        self.eye_toggle.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon); self.eye_toggle.setArrowType(QtCore.Qt.ArrowType.DownArrow)
        left_l.addWidget(self.eye_toggle)
        self.eye_panel=W.QWidget(); eye_l=W.QVBoxLayout(self.eye_panel); eye_l.setContentsMargins(0,0,0,0)
        self.eye_image = label(''); self.eye_image.setFixedHeight(108); self.eye_image.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter); eye_l.addWidget(self.eye_image)
        note=label(f'{len(data.input_ids):,} 个光感受器；RGB 为人工通道分组。\n数据缺少 R7/R8 分类，不重建紫外光或真实色觉。','subtle'); note.setWordWrap(True); eye_l.addWidget(note)
        left_l.addWidget(self.eye_panel); self.eye_toggle.toggled.connect(self.toggle_sampling)
        left_l.addWidget(label('同步音轨 → 听觉刺激','heading'))
        row=W.QHBoxLayout(); self.audio_toggle=W.QCheckBox('声音输入'); self.audio_toggle.setChecked(True)
        self.audio_toggle.toggled.connect(lambda v:self.engine.command('audio_enabled',v)); row.addWidget(self.audio_toggle)
        self.monitor_toggle=W.QCheckBox('监听原声'); self.monitor_toggle.toggled.connect(self.set_monitor); row.addWidget(self.monitor_toggle); left_l.addLayout(row)
        self.audio_status=label('等待音轨…','subtle'); self.audio_status.setWordWrap(True); left_l.addWidget(self.audio_status)
        self.audio_bars=[]
        for text in ['80–200 Hz','200–400 Hz','400–800 Hz','800–2000 Hz']:
            row=W.QHBoxLayout(); row.addWidget(label(text,'subtle')); bar=W.QProgressBar(); bar.setTextVisible(False); bar.setRange(0,1000); bar.setFixedHeight(4); row.addWidget(bar); left_l.addLayout(row); self.audio_bars.append(bar)
        note=label(f'{len(self.engine.auditory.indices)} 个 auditory 标注神经元\n频段偏好为人工分组；不代表实测听觉调谐。','subtle'); note.setWordWrap(True); left_l.addWidget(note)
        self.audio_gain_label=label('声音增益  1.00'); left_l.addWidget(self.audio_gain_label)
        self.audio_gain=W.QSlider(QtCore.Qt.Orientation.Horizontal); self.audio_gain.setRange(0,400); self.audio_gain.setValue(100)
        self.audio_gain.valueChanged.connect(lambda v:(self.audio_gain_label.setText(f'声音增益  {v/100:.2f}'),self.engine.command('audio_gain',v/100))); left_l.addWidget(self.audio_gain)
        left_l.addSpacing(7); left_l.addWidget(label('模拟参数','heading'))
        self.gain_label = label('输入强度  1.50'); left_l.addWidget(self.gain_label)
        self.gain = W.QSlider(QtCore.Qt.Orientation.Horizontal); self.gain.setRange(0,400); self.gain.setValue(150)
        self.gain.valueChanged.connect(lambda v:(self.gain_label.setText(f'输入强度  {v/100:.2f}'),self.engine.command('gain',v/100))); left_l.addWidget(self.gain)
        self.coupling_label = label('连接增益  1.50'); left_l.addWidget(self.coupling_label)
        self.coupling = W.QSlider(QtCore.Qt.Orientation.Horizontal); self.coupling.setRange(0,200); self.coupling.setValue(150)
        self.coupling.valueChanged.connect(lambda v:(self.coupling_label.setText(f'连接增益  {v/100:.2f}'),self.engine.command('coupling',v/100))); left_l.addWidget(self.coupling)
        left_l.addWidget(button('重置神经状态',lambda:self.engine.command('reset')))
        left_l.addWidget(button('恢复输入默认',self.reset_inputs))
        left_l.addStretch(); scroll=W.QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(left); scroll.setMinimumWidth(280); content.addWidget(scroll)

        middle = W.QWidget(); middle_l = W.QVBoxLayout(middle); middle_l.setContentsMargins(0,0,0,0); middle_l.setSpacing(10)
        brain_box,brain_l = panel('02   全脑空间视图')
        controls = W.QHBoxLayout(); self.category = W.QComboBox(); self.category.addItems(['全部分类']+CATEGORIES)
        self.side = W.QComboBox(); self.side.addItems(['全部','左侧','右侧'])
        self.category.currentIndexChanged.connect(self.apply_filter); self.side.currentIndexChanged.connect(self.apply_filter)
        controls.addWidget(self.category); controls.addWidget(self.side)
        self.preset = W.QComboBox(); self.preset.addItems(['正面','背面','俯视','侧面']); controls.addWidget(self.preset)
        controls.addStretch(); brain_l.addLayout(controls)
        self.brain = BrainView(data); self.brain.setMinimumHeight(270); self.brain.picked.connect(self.select_neuron)
        self.brain.cleared.connect(self.clear_selection)
        self.preset.currentIndexChanged.connect(lambda i:self.brain.camera_preset(['正面','背面','俯视','侧面'][i]))
        brain_l.addWidget(self.brain,1)
        opts = W.QHBoxLayout(); self.active = W.QCheckBox('只看活跃'); self.active.toggled.connect(self.set_active)
        opts.addWidget(self.active); self.rotate = W.QCheckBox('自动旋转'); self.rotate.toggled.connect(lambda v:setattr(self,'auto_rotate',v)); opts.addWidget(self.rotate)
        self.color = W.QComboBox(); self.color.addItems(['分类','活动']); self.color.currentIndexChanged.connect(lambda i:self.set_color(['分类','活动'][i])); opts.addWidget(self.color)
        opts.addStretch(); brain_l.addLayout(opts)
        navigation=W.QHBoxLayout()
        self.reset_view_button=button('视角复位',self.reset_view)
        self.clear_selection_button=button('取消选中 · Esc',self.clear_selection)
        self.reset_view_button.setToolTip('回到正面，居中并恢复缩放；保留脑活动')
        self.clear_selection_button.setToolTip('清除选中白点和连接线，不删除神经元')
        navigation.addWidget(self.reset_view_button); navigation.addWidget(self.clear_selection_button); navigation.addStretch()
        brain_l.addLayout(navigation)
        sizes=W.QHBoxLayout(); sizes.addWidget(label('静息点','subtle'))
        self.rest_size=W.QDoubleSpinBox(); self.rest_size.setRange(.2,12); self.rest_size.setSingleStep(.25); self.rest_size.setValue(1.65); self.rest_size.setSuffix(' px')
        self.rest_size.valueChanged.connect(lambda v:(setattr(self.brain,'point_size',v),self.brain.redraw())); sizes.addWidget(self.rest_size)
        sizes.addWidget(label('放电点','subtle')); self.firing_size=W.QDoubleSpinBox(); self.firing_size.setRange(.2,24); self.firing_size.setSingleStep(.5); self.firing_size.setValue(4.45); self.firing_size.setSuffix(' px')
        self.firing_size.valueChanged.connect(lambda v:(setattr(self.brain,'firing_size',v),self.brain.redraw())); sizes.addWidget(self.firing_size)
        self.reset_sizes=button('恢复点大小',lambda:(self.rest_size.setValue(1.65),self.firing_size.setValue(4.45))); sizes.addWidget(self.reset_sizes); sizes.addStretch(); brain_l.addLayout(sizes)
        brain_l.addWidget(label('拖动旋转 · 滚轮缩放 · Ctrl + 拖动平移 · 点击查看连接\n大白点 = 当前选中；闪亮点 = 模拟放电。点空白处或 Esc 取消选中。','subtle'))
        middle_l.addWidget(brain_box,1)
        plots,plot_l = panel('03   活动记录'); plots.setMaximumHeight(255)
        self.plot_tabs = W.QTabWidget(); plot_l.addWidget(self.plot_tabs)
        self.raster = pg.PlotWidget(); self.raster.setLabel('left','抽样神经元'); self.raster.setLabel('bottom','最近 240 个显示窗 / 脉冲计数')
        self.raster_img = pg.ImageItem(axisOrder='row-major'); self.raster.addItem(self.raster_img)
        self.raster_img.setLookupTable(pg.colormap.get('viridis').getLookupTable())
        self.raster.setMouseEnabled(x=False,y=False); self.plot_tabs.addTab(self.raster,f'栅格 · {len(self.sample)} 个样本')
        self.rate_plot = pg.PlotWidget(); self.rate_plot.setLabel('left','全脑平均频率',units='Hz'); self.rate_plot.setLabel('bottom','模拟时间',units='s')
        self.rate_curve = self.rate_plot.plot(pen=pg.mkPen('#6de7cf',width=2)); self.plot_tabs.addTab(self.rate_plot,'全脑频率')
        self.trace_plot = pg.PlotWidget(); self.trace_plot.setLabel('left','归一化膜状态'); self.trace_plot.setLabel('bottom','模拟时间',units='s')
        self.trace_curve = self.trace_plot.plot(pen=pg.mkPen('#ad95ff',width=2)); self.plot_tabs.addTab(self.trace_plot,'所选神经元')
        middle_l.addWidget(plots); content.addWidget(middle)

        right,right_l = panel('04   探索与检查'); right.setMinimumWidth(280); right.setMaximumWidth(350)
        metrics = W.QHBoxLayout()
        for value,name in [(f'{data.n:,}','神经元'),(f'{len(data.pre)/1e6:.2f} M','聚合有向连接')]:
            column = W.QVBoxLayout(); column.addWidget(label(value,'metric')); column.addWidget(label(name,'subtle')); metrics.addLayout(column)
        right_l.addLayout(metrics)
        self.activity_label = label('正在启动模拟…','subtle'); right_l.addWidget(self.activity_label)
        self.region_bars = []
        for i,cat in enumerate(CATEGORIES):
            line = W.QHBoxLayout(); name = label(cat,'subtle'); name.setFixedWidth(116); line.addWidget(name)
            bar = W.QProgressBar(); bar.setRange(0,1000); bar.setTextVisible(False); bar.setFixedHeight(5)
            bar.setStyleSheet('QProgressBar::chunk { background:'+QtGui.QColor.fromRgbF(*map(float,PALETTE[i])).name()+'; }')
            line.addWidget(bar); right_l.addLayout(line); self.region_bars.append(bar)
        right_l.addWidget(label('条形：各分类在当前显示窗内活跃的比例','subtle'))
        right_l.addSpacing(6)
        self.search = W.QLineEdit(); self.search.setPlaceholderText('搜索完整 root ID，回车定位'); self.search.returnPressed.connect(self.search_neuron); right_l.addWidget(self.search)
        self.inspector = i18n.Label(); self.inspector.setWordWrap(True); self.inspector.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse); right_l.addWidget(self.inspector)
        self.voltage = label(''); right_l.addWidget(self.voltage)
        right_l.addWidget(label('上下游连接 · 点击跳转','heading'))
        self.neighbours = W.QListWidget(); self.neighbours.setMinimumHeight(95); self.neighbours.itemClicked.connect(lambda item:self.select_neuron(item.data(QtCore.Qt.ItemDataRole.UserRole)))
        right_l.addWidget(self.neighbours,1)
        right_l.addWidget(label('绿色线 = 输出 · 橙色线 = 输入\n最多各显示 160 条较强连接；直线不是轴突形状。','subtle'))
        right_l.addWidget(button('导出全脑脉冲 CSV…',self.export))
        content.addWidget(right); content.setSizes([285,875,310]); outer.addWidget(content,1)
        self.statusBar().showMessage('正在启动完整连接组模拟…')
        self.clear_selection()
        for sequence,callback in [('Space',self.toggle_play),('Ctrl+O',self.open_video),('Escape',self.clear_selection),('Home',self.reset_view),('R',lambda:self.engine.command('reset'))]:
            shortcut = QtGui.QShortcut(QtGui.QKeySequence(sequence),self); shortcut.activated.connect(callback)
        self.timer = QtCore.QTimer(self); self.timer.timeout.connect(self.poll); self.timer.start(33)
        self.engine.start()
        self.translation_sources=[]
        for widget in self.findChildren(W.QWidget):
            if isinstance(widget,(W.QCheckBox,W.QToolButton)):
                self.translation_sources.append((widget,'text',widget.text()))
            if isinstance(widget,W.QComboBox) and widget is not self.language:
                self.translation_sources.append((widget,'items',[widget.itemText(i) for i in range(widget.count())]))
            if widget.toolTip(): self.translation_sources.append((widget,'tooltip',widget.toolTip()))
        self.language.currentIndexChanged.connect(self.change_language)
        settings=QtCore.QSettings('FlyBrainStudio','Desktop')
        self.language.setCurrentIndex(1 if settings.value('language','zh')=='en' else 0)

    def apply_filter(self,*args): self.brain.filter(self.category.currentIndex()-1,['全部','左侧','右侧'][self.side.currentIndex()])
    def reset_layout(self):
        width=self.content.width(); self.content.setSizes([300,max(300,width-610),310])
    def change_language(self,index):
        i18n.LANG='en' if index else 'zh'
        QtCore.QSettings('FlyBrainStudio','Desktop').setValue('language',i18n.LANG)
        for widget in self.findChildren(W.QWidget):
            if isinstance(widget,(i18n.Label,i18n.Button)): widget.retranslate()
        for widget,kind,source in self.translation_sources:
            if kind=='text': widget.setText(i18n.tr(source))
            elif kind=='tooltip': widget.setToolTip(i18n.tr(source))
            else:
                blocker=QtCore.QSignalBlocker(widget)
                for j,text in enumerate(source): widget.setItemText(j,i18n.tr(text))
                del blocker
        self.search.setPlaceholderText(i18n.tr('搜索完整 root ID，回车定位'))
        for j,title in enumerate([f'栅格 · {len(self.sample)} 个样本','全脑频率','所选神经元']): self.plot_tabs.setTabText(j,i18n.tr(title))
        for plot,left,bottom in [(self.raster,'抽样神经元','最近 240 个显示窗 / 脉冲计数'),(self.rate_plot,'全脑平均频率','模拟时间'),(self.trace_plot,'归一化膜状态','模拟时间')]:
            plot.setLabel('left',i18n.tr(left)); plot.setLabel('bottom',i18n.tr(bottom))
        self.setWindowTitle('FlyBrain Studio · '+i18n.tr('果蝇脑活动实验室'))
    def set_active(self,value): self.brain.active_only=value; self.brain.redraw()
    def set_color(self,value): self.brain.color_mode=value; self.brain.redraw()
    def reset_view(self):
        self.rotate.setChecked(False); self.preset.setCurrentIndex(0)
        self.brain.camera_preset('正面')
    def clear_selection(self):
        self.selected=None; self.brain.clear_selection()
        self.trace_x=[]; self.trace_y=[]; self.trace_curve.setData([],[])
        self.inspector.setText('未选中神经元。\n拖动观察全脑；单击一个点可查看它的连接。')
        self.voltage.setText(''); self.neighbours.clear(); self.search.clear()
    def toggle_sampling(self,visible):
        self.eye_panel.setVisible(visible)
        self.eye_toggle.setArrowType(QtCore.Qt.ArrowType.DownArrow if visible else QtCore.Qt.ArrowType.RightArrow)
    def set_monitor(self,enabled):
        self.monitor.enabled=enabled
        if self.packet: self.monitor.update(self.packet)
    def reset_inputs(self):
        self.vision_mode.setCurrentIndex(0); self.resolution.setCurrentIndex(1)
        self.audio_toggle.setChecked(True); self.audio_gain.setValue(100)
        self.gain.setValue(150); self.coupling.setValue(150)

    def select_neuron(self,index):
        self.selected = index; self.brain.select(index); self.trace_x=[]; self.trace_y=[]
        d=self.data; outgoing,incoming=d.neighbours(index)
        self.inspector.setText(f'<b style="color:#81ecd2">{d.ids[index]}</b><br>'
            f'{CATEGORIES[d.category[index]]} · {d.sides[index] or "侧别未标注"}<br>'
            f'{d.labels[index] or "未分类"} / {d.subclasses[index] or "—"}<br>'
            f'递质预测：{d.nt[index] or "未知"}<br>输入 {incoming[2]:,} · 输出 {outgoing[2]:,}')
        matches=np.flatnonzero(d.input_ids==index)
        if len(matches):
            channel='RGB'[self.engine.visual.channels[matches[0]]]
            self.inspector.setText(self.inspector.source_text+f'<br>RGB 实验通道：{channel}（人工分组）')
        matches=np.flatnonzero(self.engine.auditory.indices==index)
        if len(matches):
            band=['80–200','200–400','400–800','800–2000'][self.engine.auditory.channels[matches[0]]]
            self.inspector.setText(self.inspector.source_text+f'<br>声音实验频段：{band} Hz（人工分组）')
        self.neighbours.clear()
        for direction,(ids,weights,total) in [('→',outgoing),('←',incoming)]:
            for i,w in zip(ids[:12],weights[:12]):
                item=W.QListWidgetItem(f'{direction} {d.ids[i]}  [{w:+.0f}]'); item.setData(QtCore.Qt.ItemDataRole.UserRole,int(i)); self.neighbours.addItem(item)

    def search_neuron(self):
        index=self.data.id_lookup.get(self.search.text().strip())
        if index is None: self.statusBar().showMessage('没有找到这个 root ID',5000)
        else:
            self.category.setCurrentIndex(0); self.side.setCurrentIndex(0); self.select_neuron(index)

    def open_video(self):
        path,_=W.QFileDialog.getOpenFileName(self,i18n.tr('打开本地视频'),'',i18n.tr('视频 (*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.wmv);;所有文件 (*)'))
        if path: self.engine.command('load',path)
    def toggle_play(self): self.engine.command('play',not (self.packet or {}).get('playing',True))
    def seek_release(self): self.engine.command('seek',self.seek.value()); self.engine.command('play',True)
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls() and any(x.isLocalFile() for x in event.mimeData().urls()): event.acceptProposedAction()
    def dropEvent(self,event):
        for url in event.mimeData().urls():
            if url.isLocalFile(): self.engine.command('load',url.toLocalFile()); event.acceptProposedAction(); break
    def export(self):
        path,_=W.QFileDialog.getSaveFileName(self,i18n.tr('导出最近 3 模拟秒的全部神经元脉冲'),'flybrain-spikes.csv','CSV (*.csv)')
        if path: self.engine.command('export',path)
    def save_view(self):
        path,_=W.QFileDialog.getSaveFileName(self,i18n.tr('保存当前应用视图'),'flybrain-view.png','PNG (*.png)')
        if path: self.grab().save(path)

    @staticmethod
    def timestamp(seconds): return f'{int(seconds)//60:02d}:{int(seconds)%60:02d}'

    def poll(self):
        if self.auto_rotate: self.brain.orbit(.18,0)
        try: packet=self.engine.frames.get_nowait()
        except queue.Empty: return
        self.packet=packet
        if packet['epoch'] != self.last_epoch:
            self.history.fill(0); self.last_total.fill(0); self.last_elapsed=0
            self.trace_x=[]; self.trace_y=[]; self.rate_history=[]; self.brain.activity.fill(0)
            self.last_epoch=packet['epoch']; self.start_wall=time.perf_counter(); self.start_sim=0.
            self.brain.redraw(); self.raster_img.setImage(self.history.T,autoLevels=False,levels=(0,4))
            self.rate_curve.setData([],[]); self.trace_curve.setData([],[])
            for bar in self.region_bars: bar.setValue(0)
            self.activity_label.setText('活跃 0   ·   全脑均值 0 Hz')
        frame=packet['frame']; rgb=np.ascontiguousarray(frame[:,:,::-1])
        image=QtGui.QImage(rgb.data,rgb.shape[1],rgb.shape[0],rgb.strides[0],QtGui.QImage.Format.Format_RGB888).copy()
        self.video_image.setPixmap(QtGui.QPixmap.fromImage(image).scaled(self.video_image.size(),QtCore.Qt.AspectRatioMode.KeepAspectRatio,QtCore.Qt.TransformationMode.SmoothTransformation))
        if self.eye_panel.isVisible():
            eye=np.ascontiguousarray(packet['small'],dtype=np.uint8)
            image=QtGui.QImage(eye.data,eye.shape[1],eye.shape[0],eye.strides[0],QtGui.QImage.Format.Format_RGB888).copy()
            self.eye_image.setPixmap(QtGui.QPixmap.fromImage(image).scaled(self.eye_image.size(),QtCore.Qt.AspectRatioMode.KeepAspectRatio))
        self.audio_status.setText(packet['audio_status']+(' · 输入开启' if packet['audio_enabled'] else ' · 输入关闭'))
        for bar,value in zip(self.audio_bars,packet['audio_levels']):
            bar.setValue(int(min(1000,value*4000)))
        self.monitor.update(packet)
        self.video_name.setText(Path(packet['name']).name); self.video_name.setToolTip(packet['name'])
        self.seek.setRange(0,packet['length']-1)
        if not self.seek.isSliderDown(): self.seek.setValue(packet['index'])
        self.time_label.setText(f'{self.timestamp(packet["index"]/packet["fps"])} / {self.timestamp(packet["length"]/packet["fps"])}   ·   模拟 {packet["elapsed"]:.2f} s')
        self.play_button.setText('暂停' if packet['playing'] else '播放')
        # Cumulative differences preserve spikes even if the GUI skips worker snapshots.
        delta=packet['total']-self.last_total; duration=packet['elapsed']-self.last_elapsed
        if duration > 0:
            self.history[:-1]=self.history[1:]; self.history[-1]=np.minimum(delta[self.sample],65535)
            self.raster_img.setImage(self.history.T,autoLevels=False,levels=(0,4))
            self.brain.update_activity(delta,max(1,round(duration/.01)))
            rate=float(delta.sum())/duration/self.data.n
            self.rate_history.append((packet['elapsed'],rate)); self.rate_history=self.rate_history[-240:]
            self.rate_curve.setData(*np.array(self.rate_history).T)
            if self.selected is not None:
                self.trace_x.append(packet['elapsed']); self.trace_y.append(packet['potential'][self.selected]); self.trace_x=self.trace_x[-240:]; self.trace_y=self.trace_y[-240:]
                self.trace_curve.setData(self.trace_x,self.trace_y)
            for i,bar in enumerate(self.region_bars):
                mask=self.data.category==i
                bar.setValue(int(1000*np.count_nonzero(delta[mask])/max(1,int(mask.sum()))))
            self.activity_label.setText(f'活跃 {np.count_nonzero(delta):,}   ·   全脑均值 {rate:.2f} Hz')
        self.last_total=packet['total']; self.last_elapsed=packet['elapsed']
        if self.selected is not None:
            self.voltage.setText(f'膜状态  {packet["potential"][self.selected]:.3f}   ·   累计脉冲 {packet["total"][self.selected]:,}')
        if packet['notice']:
            self.statusBar().showMessage(packet['notice'],8000); self.last_notice=time.perf_counter()
        elif time.perf_counter()-getattr(self,'last_notice',0)>8:
            self.statusBar().showMessage(f'● 本地运行   |   全网络模拟 · dt 10 ms   |   每帧计算 {packet["cost"]*1000:.0f} ms   |   当前显示 {len(self.brain.drawn_ids):,} 点   |   拖动进度会重置神经状态')

    def help(self):
        if i18n.LANG=='en':
            W.QMessageBox.information(self,'FlyBrain Studio — Help',
                'Drag the brain to rotate; wheel to zoom; Ctrl+drag to pan.\n'
                'Home resets the camera. Esc clears selection without deleting neurons.\n'
                'Drag the divider next to the input panel to resize it. Reset layout restores widths.\n\n'
                'Drop a local video or press Ctrl+O. Space pauses/resumes. Seeking resets neural history.\n'
                'RGB and audio frequency assignments are artificial experimental encodings.\n'
                'Audio input stimulates the model; Monitor audio lets you hear a file. The built-in tone is model-only.\n\n'
                'Data downloaded directly from official FlyWire FAFB v783 CSV exports.\n'
                'Dots are annotation points, not neuron skeletons. Dynamics are approximate LIF, not measured physiology.\n'
                'Raster: 256 sampled neurons. CSV export: all neurons, latest 3 simulated seconds.\n'
                'See README.md for data provenance, parameters and limitations.')
            return
        dialog=W.QDialog(self); dialog.setWindowTitle('如何探索这颗果蝇脑'); dialog.resize(670,560)
        layout=W.QVBoxLayout(dialog); browser=W.QTextBrowser(); browser.setOpenExternalLinks(True)
        browser.setHtml('''<h2>先转动大脑，再拖入一段视频。</h2>
        <p>启动时已运行内置移动光栅。左键拖动旋转、滚轮缩放、Ctrl + 拖动平移。点击一个点，右侧显示真实 root ID 和上下游连接。</p>
        <p>将视频文件拖入窗口，或按 Ctrl+O。空格播放/暂停；R 重置。拖动进度会从新位置清零重新模拟，不恢复视频之前的神经历史。倍速改变播放节奏，算不及时会自然减速。</p>
        <h3>你实际看到的是什么？</h3>
        <p>直接读取 FlyWire 官方发布的 FAFB v783 成年雌性果蝇脑 CSV 数据，不使用第三方模拟项目的数据包。每点是该神经元公开标注坐标的均值；不是完整树突/轴突骨架。所有神经元参与计算，筛选只改变显示。具体数据数量与校验值见 data/manifest.json。</p>
        <p>底部栅格抽样最多 256 个神经元；全脑频率和 3D 活动使用全网络结果。导出保存最近最多 3 个模拟秒的全网络脉冲事件及 JSON 参数来源。</p>
        <h3>哪些部分是近似？</h3>
        <p>屏幕依据光感受器坐标映射，未测定真实感受野。神经动力学采用归一化 LIF，连接权重和递质符号经过简化。颜色反映模拟结果，不是活体电生理。分类是从公开注释整理的功能集合，非精确脑区分割。</p>
        <p>RGB 实验编码按 root ID 对光感受器分配 R/G/B 通道。当前数据没有 R7/R8 分类，不能称作真实果蝇色觉，也不能从 RGB 还原紫外光。可切换灰度对照和采样分辨率。</p>
        <p>声音按视频时间读取音轨，四个频段的能量输入 393 个 auditory 标注神经元。频段偏好是人工分组，不是实测调谐。无音轨时输入为零。“声音输入”控制神经刺激；“监听原声”仅供人耳试听，默认关闭。内置演示的脉冲音仅进入模型，不通过扬声器播放。</p>
        <p>点击“视觉采样”可折叠预览，计算继续。静息点与放电点大小可分别调节，“恢复点大小”一键复位。没有神经元形态网格、自动学习或“意识”模型。</p>
        <p><a href="https://codex.flywire.ai/">FlyWire 官方数据门户</a> · <a href="https://doi.org/10.1038/s41586-024-07558-y">原始研究</a></p>''')
        layout.addWidget(browser); layout.addWidget(button('开始探索',dialog.accept,True)); dialog.exec()

    def closeEvent(self,event):
        self.timer.stop(); self.monitor.close(); self.engine.stopping.set(); self.engine.join(timeout=5); event.accept()
