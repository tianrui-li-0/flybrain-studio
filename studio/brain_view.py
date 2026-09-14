import numpy as np
import pyqtgraph.opengl as gl
from PySide6 import QtCore, QtGui
from .model import PALETTE


class BrainView(gl.GLViewWidget):
    picked = QtCore.Signal(int)
    cleared = QtCore.Signal()
    def __init__(self, data):
        super().__init__()
        self.data = data; self.setBackgroundColor('#070e1a')
        self.opts['distance'] = 285; self.opts['elevation'] = 12; self.opts['azimuth'] = -90
        self.visible_ids = np.flatnonzero(data.has_position)
        self.activity = np.zeros(data.n,np.float32); self.point_size = 1.65
        self.firing_size=4.45
        self.active_only = False; self.color_mode = '分类'; self.selected = None
        self.points = gl.GLScatterPlotItem(pos=data.positions, size=self.point_size, pxMode=True)
        self.points.setGLOptions('translucent'); self.addItem(self.points)
        self.links_out = gl.GLLinePlotItem(pos=np.zeros((0,3)),color=(.33,.94,.8,.45),mode='lines',width=1,antialias=True)
        self.links_in = gl.GLLinePlotItem(pos=np.zeros((0,3)),color=(1.,.61,.35,.45),mode='lines',width=1,antialias=True)
        self.addItem(self.links_out); self.addItem(self.links_in)
        self.marker = gl.GLScatterPlotItem(pos=np.zeros((0,3)),color=(1,1,1,1),size=10,pxMode=True)
        self.addItem(self.marker)
        self.redraw()

    def redraw(self):
        ids = self.visible_ids
        if self.active_only: ids = ids[self.activity[ids] > .05]
        self.drawn_ids = ids
        colors = np.empty((len(ids),4),np.float32)
        colors[:,:3] = PALETTE[self.data.category[ids]] if self.color_mode == '分类' else (.15,.3,.42)
        a = np.clip(self.activity[ids],0,1)
        colors[:,:3] = colors[:,:3]*(1-a[:,None]) + np.array([.68,1.,.9])*a[:,None]
        colors[:,3] = .20+.80*a
        sizes = self.point_size*(1-a)+self.firing_size*a
        self.points.setData(pos=self.data.positions[ids],color=colors,size=sizes)

    def update_activity(self, counts, steps):
        self.activity = np.maximum(self.activity*.76, np.clip(counts/max(1,steps)*3,0,1))
        self.redraw()

    def filter(self, category=-1, hemisphere='全部'):
        mask = self.data.has_position.copy()
        if category >= 0: mask &= self.data.category == category
        if hemisphere != '全部': mask &= self.data.sides == {'左侧':'left','右侧':'right'}[hemisphere]
        self.visible_ids = np.flatnonzero(mask); self.redraw()

    def select(self, index):
        self.selected = index; self.marker.setData(pos=self.data.positions[[index]])
        for item,(ids,weights,total) in zip((self.links_out,self.links_in),self.data.neighbours(index)):
            pos = np.empty((len(ids)*2,3),np.float32)
            pos[::2] = self.data.positions[index]; pos[1::2] = self.data.positions[ids]
            item.setData(pos=pos)

    def clear_selection(self):
        self.selected=None
        for item in (self.marker,self.links_out,self.links_in):
            item.setData(pos=np.empty((0,3),np.float32))

    def mousePressEvent(self,event):
        self.press_position = event.position(); super().mousePressEvent(event)

    def mouseReleaseEvent(self,event):
        super().mouseReleaseEvent(event)
        if event.button() != QtCore.Qt.MouseButton.LeftButton: return
        if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier: return
        if (event.position()-self.press_position).manhattanLength() > 5: return
        ids = self.drawn_ids
        if not len(ids): self.cleared.emit(); return
        viewport = self.getViewport()
        matrix = np.array((self.projectionMatrix(viewport,viewport)*self.viewMatrix()).copyDataTo()).reshape(4,4)
        homogeneous = np.column_stack((self.data.positions[ids],np.ones(len(ids)))) @ matrix.T
        ndc = homogeneous[:,:3]/homogeneous[:,3,None]
        px = (ndc[:,0]+1)*self.width()/2; py = (1-ndc[:,1])*self.height()/2
        distance = (px-event.position().x())**2+(py-event.position().y())**2
        distance[(homogeneous[:,3]<=0)|(np.abs(ndc[:,2])>1)] = np.inf
        closest = int(np.argmin(distance))
        if distance[closest] < 144: self.picked.emit(int(ids[closest]))
        else: self.cleared.emit()

    def camera_preset(self, name):
        values = {'正面':(-90,12),'背面':(90,12),'俯视':(-90,89),'侧面':(0,10)}
        azimuth,elevation = values[name]
        self.opts['center']=QtGui.QVector3D(0,0,0)
        self.opts['fov']=60
        self.setCameraPosition(distance=285,elevation=elevation,azimuth=azimuth)
