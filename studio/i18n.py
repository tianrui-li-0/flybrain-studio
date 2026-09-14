"""Local UI translation; identifiers and neuron annotations remain unchanged."""
from PySide6 import QtWidgets as W
LANG='zh'
PAIRS={
'果蝇脑活动实验室':'Fly brain activity laboratory','真实连接与坐标 / 近似脉冲动力学':'Real connectivity and coordinates / approximate dynamics',
'01   视觉输入':'01   SENSORY INPUT','02   全脑空间视图':'02   WHOLE-BRAIN VIEW','03   活动记录':'03   ACTIVITY','04   探索与检查':'04   INSPECTOR',
'使用说明':'Help','保存视图':'Save screenshot','复位布局':'Reset layout','暂停':'Pause','播放':'Play','打开视频…':'Open video…','内置刺激':'Demo',
'循环':'Loop','拖放本地视频到窗口任意位置。':'Drop a local video anywhere in the window.',
'RGB 实验编码':'Experimental RGB','灰度对照':'Grayscale control','视觉采样':'Visual sampling',
'个光感受器；RGB 为人工通道分组。':'photoreceptors; RGB channels are artificially assigned.',
'数据缺少 R7/R8 分类，不重建紫外光或真实色觉。':'R7/R8 types unavailable; no UV or biological color reconstruction.',
'同步音轨 → 听觉刺激':'Synchronized audio → neural input','声音输入':'Audio input','监听原声':'Monitor audio',
'等待音轨…':'Waiting for audio…','个 auditory 标注神经元':'annotated auditory neurons',
'频段偏好为人工分组；不代表实测听觉调谐。':'Band assignments are artificial, not measured tuning.',
'声音增益':'Audio gain','模拟参数':'MODEL PARAMETERS','输入强度':'Visual gain','连接增益':'Connection gain',
'重置神经状态':'Reset neural state','恢复输入默认':'Reset input settings','全部分类':'All categories',
'全部':'Both sides','左侧':'Left','右侧':'Right','正面':'Front','背面':'Back','俯视':'Top','侧面':'Side',
'只看活跃':'Active only','自动旋转':'Auto rotate','分类':'Category','活动':'Activity',
'视角复位':'Reset camera','取消选中 · Esc':'Clear selection · Esc','静息点':'Resting points','放电点':'Firing points','恢复点大小':'Reset point sizes',
'回到正面，居中并恢复缩放；保留脑活动':'Restore front view, center and zoom; preserve activity',
'清除选中白点和连接线，不删除神经元':'Clear selection marker and links; preserve neurons',
'拖动旋转 · 滚轮缩放 · Ctrl + 拖动平移 · 点击查看连接':'Drag: rotate · Wheel: zoom · Ctrl+drag: pan · Click: inspect',
'大白点 = 当前选中；闪亮点 = 模拟放电。点空白处或 Esc 取消选中。':'Large white point = selection; glowing points = spikes. Blank click / Esc clears selection.',
'光感受器':'Photoreceptors','视觉回路':'Visual circuits','蘑菇体 / 调制':'Mushroom body / modulation','中央复合体相关':'Central complex related','传出通路':'Efferent pathways','其他感觉':'Other sensory','其他 / 未分类':'Other / unclassified',
'聚合有向连接':'Aggregated directed edges','神经元':'Neurons','正在启动模拟…':'Starting simulation…',
'条形：各分类在当前显示窗内活跃的比例':'Bars: fraction active within the current display window',
'搜索完整 root ID，回车定位':'Enter a full root ID to inspect',
'未选中神经元。':'No neuron selected.', '拖动观察全脑；单击一个点可查看它的连接。':'Drag to explore; click a point to inspect its connections.',
'上下游连接 · 点击跳转':'Connections · click to inspect',
'绿色线 = 输出 · 橙色线 = 输入':'Green links = outgoing · Orange = incoming',
'最多各显示 160 条较强连接；直线不是轴突形状。':'Up to 160 strongest links each way; lines are not axons.',
'导出全脑脉冲 CSV…':'Export brain spikes CSV…','膜状态':'Membrane state','累计脉冲':'Total spikes',
'递质预测':'Predicted transmitter','侧别未标注':'Side unknown','未分类':'Unclassified',
'RGB 实验通道':'Experimental RGB channel','声音实验频段':'Experimental audio band','人工分组':'artificial assignment',
'全脑均值':'Mean brain rate','活跃':'Active','音轨已连接':'Audio connected','无音轨':'No audio track',
'输入开启':'Input enabled','输入关闭':'Input disabled','内置 300 Hz 脉冲音':'Built-in 300 Hz pulses (model only)',
'内置视觉刺激 · 移动光栅':'Built-in moving grating',
'已跳转：从当前画面重新开始模拟':'Seeked: neural simulation restarted at this frame',
'神经状态和统计已清零':'Neural state and counters reset','本地视频已加载':'Local video loaded',
'模拟':'Simulation','本地运行':'Local','全网络模拟':'Full network','每帧计算':'Compute/frame','当前显示':'Displayed','点':'points',
'拖动进度会重置神经状态':'Seeking resets neural state',
'输入':'Input','输出':'Output','未知':'Unknown','没有找到这个 root ID':'Root ID not found',
'栅格 ·':'Raster ·','个样本':'samples','全脑频率':'Brain rate','所选神经元':'Selected neuron',
'抽样神经元':'Sampled neurons','最近 240 个显示窗 / 脉冲计数':'Latest 240 display windows / spike counts',
'全脑平均频率':'Mean firing rate','模拟时间':'Simulation time','归一化膜状态':'Normalized membrane state',
'打开本地视频':'Open local video','所有文件':'All files','视频':'Video',
'保存当前应用视图':'Save application view','导出最近 3 模拟秒的全部神经元脉冲':'Export all spikes from latest 3 simulated seconds',
'视频结束或解码中断':'Video ended or decoding interrupted','无法解码这个文件，请换用常见的 MP4 / MOV / AVI。':'Cannot decode this file. Try MP4, MOV or AVI.',
'音轨不可用':'Audio unavailable','音轨解码失败':'Audio decode failed','操作失败':'Operation failed','模拟停止':'Simulation stopped','已导出最近 3 秒的全网络脉冲':'Exported full-network spikes from the latest 3 seconds',
}
def tr(text):
    if LANG!='en': return text
    for source in sorted(PAIRS,key=len,reverse=True): text=text.replace(source,PAIRS[source])
    return text

class Label(W.QLabel):
    def __init__(self,text=''):
        self.source_text=text; super().__init__(tr(text))
    def setText(self,text): self.source_text=text; super().setText(tr(text))
    def retranslate(self): super().setText(tr(self.source_text))

class Button(W.QPushButton):
    def __init__(self,text): self.source_text=text; super().__init__(tr(text))
    def setText(self,text): self.source_text=text; super().setText(tr(text))
    def retranslate(self): super().setText(tr(self.source_text))

class StatusBar(W.QStatusBar):
    def showMessage(self,text,timeout=0): super().showMessage(tr(text),timeout)
