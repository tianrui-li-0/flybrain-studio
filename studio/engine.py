"""Video decoding and full-graph simulation run off the GUI thread."""
import csv
import json
import queue
import threading
import time
from collections import deque
from pathlib import Path
import cv2
import numpy as np
from .model import LIFNetwork
from .senses import ColorEncoder,AuditoryEncoder,AudioReader


class Engine(threading.Thread):
    def __init__(self, data):
        super().__init__(daemon=True, name='flybrain-simulation')
        self.data = data; self.net = LIFNetwork(data)
        self.commands = queue.Queue(); self.frames = queue.Queue(maxsize=1)
        self.stopping = threading.Event(); self.playing = True
        self.capture = None; self.name = '内置视觉刺激 · 移动光栅'
        self.fps = 30.; self.length = 900; self.index = 0; self.speed = 1.
        self.gain = 1.5; self.coupling = 1.5; self.credit = 0.; self.loop = True
        self.events = deque(maxlen=300); self.last_frame = None
        self.notice = ''; self.epoch = 0
        self.visual=ColorEncoder(data); self.auditory=AuditoryEncoder(data)
        self.color_mode='rgb'; self.sample_width=128; self.audio_enabled=True; self.audio_gain=1.
        self.audio=None; self.audio_status='内置 300 Hz 脉冲音'; self.audio_levels=np.zeros(4,np.float32)
        self.audio_current=np.zeros(len(self.auditory.indices),np.float32)

    def command(self, name, value=None): self.commands.put((name,value))

    def reset(self):
        self.net.reset(); self.credit = 0; self.events.clear(); self.epoch += 1

    def builtin(self, index):
        y,x = np.mgrid[:270,:480]
        val = ((np.sin(x/22-index*.18) > 0)*175+25).astype(np.uint8)
        img = np.repeat(val[:,:,None],3,axis=2)
        cv2.circle(img,(int(240+160*np.sin(index/70)),135),50,(240,250,220),-1)
        # Colored bars actually enter the encoder; blue/green/red alternate.
        for j,color in enumerate([(230,80,30),(30,220,60),(30,60,230)]):
            cv2.rectangle(img,(j*160,190),(j*160+159,269),color,-1)
        return img

    @staticmethod
    def fit_frame(frame):
        height,width=frame.shape[:2]
        scale=min(480/width,270/height)
        width,height=max(1,round(width*scale)),max(1,round(height*scale))
        resized=cv2.resize(frame,(width,height),interpolation=cv2.INTER_AREA)
        canvas=np.zeros((270,480,3),np.uint8)
        y,x=(270-height)//2,(480-width)//2
        canvas[y:y+height,x:x+width]=resized
        return canvas

    def handle(self, name, value):
        if name == 'play': self.playing = value
        elif name == 'speed': self.speed = value
        elif name == 'gain': self.gain = value
        elif name == 'coupling': self.coupling = value
        elif name == 'loop': self.loop = value
        elif name == 'color': self.color_mode=value
        elif name == 'resolution': self.sample_width=int(value)
        elif name == 'audio_enabled': self.audio_enabled=bool(value)
        elif name == 'audio_gain': self.audio_gain=float(value)
        elif name == 'reset': self.reset(); self.notice = '神经状态和统计已清零'
        elif name in ('load','demo'):
            candidate = cv2.VideoCapture(str(value)) if name == 'load' else None
            if candidate is not None:
                ok,frame = candidate.read()
                if not ok:
                    candidate.release(); self.notice = '无法解码这个文件，请换用常见的 MP4 / MOV / AVI。'; return
                candidate.set(cv2.CAP_PROP_POS_FRAMES,0)
            if self.capture is not None: self.capture.release()
            if self.audio is not None: self.audio.close()
            self.audio=AudioReader(value) if candidate is not None else None
            self.audio_status=self.audio.status if self.audio is not None else '内置 300 Hz 脉冲音'
            self.capture = candidate
            self.name = str(value) if candidate is not None else '内置视觉刺激 · 移动光栅'
            self.fps = float(candidate.get(cv2.CAP_PROP_FPS)) if candidate is not None else 30.
            if not np.isfinite(self.fps) or self.fps <= 0: self.fps = 30.
            self.length = max(1,int(candidate.get(cv2.CAP_PROP_FRAME_COUNT))) if candidate is not None else 900
            self.index = 0; self.last_frame = None; self.reset(); self.playing = True
            self.notice = '本地视频已加载 · '+self.audio_status
        elif name == 'seek':
            self.index = min(self.length-1,max(0,int(value)))
            if self.capture is not None:
                self.capture.set(cv2.CAP_PROP_POS_FRAMES,self.index)
                ok,frame = self.capture.read()
                if ok: self.last_frame = frame
                self.capture.set(cv2.CAP_PROP_POS_FRAMES,self.index)
            else: self.last_frame = self.builtin(self.index)
            self.reset(); self.notice = '已跳转：从当前画面重新开始模拟'
        elif name == 'export':
            path = Path(value)
            with path.open('w', newline='', encoding='utf-8-sig') as stream:
                writer = csv.writer(stream); writer.writerow(['simulation_seconds','root_id'])
                for seconds,indices in self.events:
                    writer.writerows((f'{seconds:.4f}',self.data.ids[i]) for i in indices)
            metadata = dict(self.data.manifest, video=self.name, video_frame=self.index,
                simulated_seconds=self.net.elapsed, input_gain=self.gain, coupling=self.coupling,
                dt=self.net.dt, model='educational LIF v2; see README',
                color_mode=self.color_mode,visual_resolution=[self.sample_width,self.sample_width*9//16],
                color_mapping='root_id modulo 3 assigns RGB; artificial, not R7/R8',
                auditory_neurons=len(self.auditory.indices),audio_enabled=self.audio_enabled,audio_gain=self.audio_gain,
                audio_status=self.audio_status,audio_mapping='annotated auditory; root_id modulo 4 assigns 80-200/200-400/400-800/800-2000 Hz bands',
                export_scope='all neuron spike events in latest at most 3 simulated seconds; resets on seek')
            path.with_suffix('.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
            self.notice = f'已导出最近 3 秒的全网络脉冲：{path.name}'

    def publish(self, counts=None, steps=0, cost=0.):
        if self.last_frame is None: self.last_frame = self.builtin(self.index)
        frame = self.fit_frame(self.last_frame)
        _,small=self.visual.encode(frame,self.color_mode,self.sample_width)
        packet = dict(frame=frame, small=small, counts=np.zeros(self.data.n,np.uint16) if counts is None else counts,
            potential=self.net.v.copy(), total=self.net.total.copy(), elapsed=self.net.elapsed,
            index=self.index, length=self.length, fps=self.fps, playing=self.playing,
            name=self.name, epoch=self.epoch, steps=steps, cost=cost, notice=self.notice,
            audio_levels=self.audio_levels.copy(),audio_status=self.audio_status,audio_enabled=self.audio_enabled,
            color_mode=self.color_mode,sample_width=self.sample_width)
        self.notice = ''
        try: self.frames.get_nowait()
        except queue.Empty: pass
        self.frames.put_nowait(packet)

    def run(self):
        deadline = time.perf_counter()
        try:
            while not self.stopping.is_set():
                changed = False
                while True:
                    try: name,value = self.commands.get_nowait()
                    except queue.Empty: break
                    try: self.handle(name,value)
                    except Exception as error: self.notice = f'操作失败：{error}'
                    changed = True
                if not self.playing:
                    if changed: self.publish()
                    self.stopping.wait(.015); deadline = time.perf_counter(); continue
                if self.index >= self.length:
                    if self.loop: self.handle('seek',0)
                    else: self.playing = False; self.publish(); continue
                start = time.perf_counter()
                if self.capture is None: frame = self.builtin(self.index)
                else:
                    ok,frame = self.capture.read()
                    if not ok: self.playing = False; self.notice = '视频结束或解码中断'; self.publish(); continue
                self.last_frame = frame
                sensory,_=self.visual.encode(self.fit_frame(frame),self.color_mode,self.sample_width)
                end=(self.index+1)/self.fps
                if self.capture is None:
                    sample_times=np.arange(640)/16000+end-.04
                    samples=(.15*np.sin(2*np.pi*300*sample_times)*(np.floor(sample_times*2).astype(int)%2==0)).astype(np.float32)
                elif self.audio is not None:
                    try: samples=self.audio.window(end)
                    except Exception as error:
                        self.audio_status=f'音轨解码失败：{error}'; self.audio.close(); self.audio=None; samples=np.zeros(640,np.float32)
                else: samples=np.zeros(640,np.float32)
                self.audio_current,self.audio_levels=self.auditory.encode(samples,self.audio_gain,self.audio_enabled)
                self.credit += 1/self.fps
                counts = np.zeros(self.data.n,np.uint16); steps = 0
                while self.credit >= self.net.dt-1e-9:
                    fired = self.net.step(sensory,self.gain,self.coupling,self.auditory.indices,self.audio_current)
                    self.events.append((self.net.elapsed,np.flatnonzero(fired)))
                    counts += fired; steps += 1; self.credit -= self.net.dt
                self.publish(counts,steps,time.perf_counter()-start)
                self.index += 1
                deadline = max(deadline + 1/self.fps/self.speed,time.perf_counter())
                self.stopping.wait(max(0,deadline-time.perf_counter()))
        except Exception as error:
            self.playing = False; self.notice = f'模拟停止：{error}'; self.publish()
        finally:
            if self.capture is not None: self.capture.release()
            if self.audio is not None: self.audio.close()
