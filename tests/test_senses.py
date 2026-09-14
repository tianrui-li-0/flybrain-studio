import sys
import unittest
from pathlib import Path
import numpy as np
import av
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from studio.senses import ColorEncoder,AuditoryEncoder,AudioReader,audio_bands
from studio.model import Dataset,LIFNetwork

def make_av(path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with av.open(str(path),'w') as container:
        video=container.add_stream('mpeg4',rate=25); video.width=240; video.height=120; video.pix_fmt='yuv420p'
        audio=container.add_stream('aac',rate=16000); audio.layout='mono'
        for i in range(75):
            img=np.zeros((120,240,3),np.uint8); img[:,:,i//25]=230
            frame=av.VideoFrame.from_ndarray(img,format='rgb24')
            for packet in video.encode(frame): container.mux(packet)
        for packet in video.encode(): container.mux(packet)
        for start in range(0,48000,1024):
            samples=np.arange(start,min(start+1024,48000))/16000
            wave=.2*np.sin(2*np.pi*np.where(samples<1,300,1200)*samples)*(samples<2)
            frame=av.AudioFrame.from_ndarray(wave.astype(np.float32)[None,:],format='fltp',layout='mono')
            frame.sample_rate=16000; frame.pts=start
            for packet in audio.encode(frame): container.mux(packet)
        for packet in audio.encode(): container.mux(packet)

class SenseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=Dataset(Path(__file__).resolve().parents[1]/'data')

    def test_color_changes_actual_input(self):
        enc=ColorEncoder(self.data)
        red=np.zeros((72,128,3),np.uint8); red[:,:,2]=255
        green=np.zeros_like(red); green[:,:,1]=255
        a,preview=enc.encode(red); b,_=enc.encode(green)
        self.assertFalse(np.array_equal(a,b))
        self.assertTrue(np.all(a[enc.channels==0]==1))
        self.assertTrue(np.all(a[enc.channels!=0]==0))
        g,gray=enc.encode(red,'gray'); self.assertTrue(np.all(g==g[0]))
        self.assertTrue(np.array_equal(gray[:,:,0],gray[:,:,1]))
        for width in [64,128,256]: self.assertEqual(enc.encode(red,width=width)[1].shape,(width*9//16,width,3))
        net=LIFNetwork(self.data)
        for _ in range(30): net.step(a,input_gain=1.5,coupling=0)
        self.assertGreater(net.total[self.data.input_ids[enc.channels==0]].sum(),0)
        self.assertEqual(net.total[self.data.input_ids[enc.channels!=0]].sum(),0)

    def test_silence_frequency_and_toggle(self):
        enc=AuditoryEncoder(self.data); self.assertEqual(len(enc.indices),393)
        silent,bands=enc.encode(np.zeros(640)); self.assertFalse(silent.any()); self.assertFalse(bands.any())
        tone=.2*np.sin(2*np.pi*300*np.arange(640)/16000)
        current,bands=enc.encode(tone); self.assertEqual(int(bands.argmax()),1)
        self.assertFalse(enc.encode(tone,enabled=False)[0].any())
        self.assertFalse(enc.encode(tone,gain=0)[0].any())
        net=LIFNetwork(self.data)
        for _ in range(30): net.step(np.zeros(len(self.data.input_ids)),coupling=0,audio_ids=enc.indices,audio_current=current)
        self.assertGreater(net.total[enc.indices].sum(),0)
        other=np.ones(self.data.n,bool); other[enc.indices]=False
        self.assertFalse(net.total[other].any())

    def test_audio_seek_decode_and_eof(self):
        path=Path(sys.argv[0]).resolve().parent/'unused'
        # Explicit scratch directory provided through environment for reproducible fixture outputs.
        import os
        directory=Path(os.environ.get('FLY_TEST_OUTPUT','test-output')); directory.mkdir(parents=True,exist_ok=True)
        path=directory/'color-and-sound.mp4'; make_av(path)
        reader=AudioReader(path)
        try:
            self.assertTrue(reader.available,reader.status)
            self.assertEqual(int(audio_bands(reader.window(.8)).argmax()),1)
            self.assertEqual(int(audio_bands(reader.window(1.8)).argmax()),3)
            self.assertEqual(int(audio_bands(reader.window(.5)).argmax()),1)
            self.assertLess(float(audio_bands(reader.window(2.8)).max()),.001)
            self.assertFalse(reader.window(10).any())
            self.assertEqual(int(audio_bands(reader.window(.8)).argmax()),1)
        finally: reader.close()

if __name__=='__main__': unittest.main()
