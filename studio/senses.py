"""Explicit experimental sensory adapters, not fitted fly physiology."""
import numpy as np
import cv2

BANDS = ((80,200),(200,400),(400,800),(800,2000))

class ColorEncoder:
    def __init__(self,data):
        self.data=data
        # Stable, artificial RGB allocation. No R7/R8 subtype is inferred.
        self.channels=(data.ids[data.input_ids].astype(np.uint64)%3).astype(int)

    def encode(self,frame,mode='rgb',width=128):
        height=width*9//16
        rgb=cv2.cvtColor(cv2.resize(frame,(width,height),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2RGB)
        u=(self.data.uv[:,0]*(width-1)).astype(int)
        v=(self.data.uv[:,1]*(height-1)).astype(int)
        if mode=='gray':
            gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
            return gray[v,u].astype(np.float32)/255.,np.repeat(gray[:,:,None],3,axis=2)
        return rgb[v,u,self.channels].astype(np.float32)/255.,rgb

def audio_bands(samples,rate=16000):
    """Absolute digital band RMS; no per-frame normalization of silence."""
    if not len(samples): return np.zeros(4,np.float32)
    x=np.asarray(samples,np.float32); x=x-x.mean()
    window=np.hanning(len(x)); power=np.abs(np.fft.rfft(x*window))**2
    frequencies=np.fft.rfftfreq(len(x),1/rate)
    norm=max(float(np.sum(window*window)*len(x)),1e-12)
    return np.array([np.sqrt(2*power[(frequencies>=lo)&(frequencies<hi)].sum()/norm) for lo,hi in BANDS],np.float32)

class AudioReader:
    """Bounded, timestamp-based audio decode. Seeks reset the decoder cache.

    A 40 ms trailing window supplies frequency energy for each video frame.
    No audio file is uploaded, and no entire sound track is held in memory.
    """
    rate=16000
    def __init__(self,path):
        import av
        self.av=av; self.container=None; self.available=False; self.status='无音轨'
        self.parts=[]; self.eof=False; self.origin=0.; self.last_time=-1.
        try:
            self.container=av.open(str(path))
            if not self.container.streams.audio:
                self.container.close(); self.container=None; return
            self.stream=self.container.streams.audio[0]
            if self.container.streams.video:
                v=self.container.streams.video[0]
                self.origin=float((v.start_time or 0)*v.time_base)
            self.available=True; self.status='音轨已连接'; self._restart(0.)
        except Exception as error:
            self.close(); self.status=f'音轨不可用：{error}'

    def _restart(self,t):
        target=max(0.,self.origin+t-.15)
        self.container.seek(int(target*self.av.time_base),backward=True)
        self.decoder=self.container.decode(audio=0)
        self.resampler=self.av.AudioResampler(format='fltp',layout='mono',rate=self.rate)
        self.parts=[]; self.eof=False; self.fallback_time=target-self.origin

    def window(self,t,duration=.04):
        n=max(1,round(duration*self.rate)); result=np.zeros(n,np.float32)
        if not self.available: return result
        start=t-duration; end=t
        if t<self.last_time-.00001 or t-self.last_time>1.0: self._restart(max(0,start))
        self.last_time=t
        while not self.eof and (not self.parts or self.parts[-1][0]+len(self.parts[-1][1])/self.rate<end):
            try: source=next(self.decoder)
            except StopIteration:
                frames=self.resampler.resample(None); self.eof=True
            else: frames=self.resampler.resample(source)
            for frame in frames:
                samples=frame.to_ndarray().reshape(-1).copy()
                position=float(frame.pts*frame.time_base)-self.origin if frame.pts is not None else self.fallback_time
                self.parts.append((position,samples)); self.fallback_time=position+len(samples)/self.rate
            # Keep only the target vicinity even if seeking lands far earlier.
            self.parts=[(p,x) for p,x in self.parts if p+len(x)/self.rate>=start-.1]
        for position,samples in self.parts:
            destination=round((position-start)*self.rate)
            left=max(0,destination); right=min(n,destination+len(samples))
            if right>left: result[left:right]=samples[left-destination:right-destination]
        return result

    def close(self):
        if self.container is not None: self.container.close(); self.container=None

class AuditoryEncoder:
    def __init__(self,data):
        self.indices=np.flatnonzero(data.subclasses=='auditory')
        # Tuning is an explicit engineering assignment, not measured JO subtype tuning.
        self.channels=(data.ids[self.indices].astype(np.uint64)%4).astype(int)
    def encode(self,samples,gain=1.,enabled=True):
        bands=audio_bands(samples)
        current=np.clip(bands[self.channels]*gain*6,0,3) if enabled else np.zeros(len(self.indices),np.float32)
        return current.astype(np.float32),bands
