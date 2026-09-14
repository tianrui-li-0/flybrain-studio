import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy.sparse import csr_matrix
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from studio.model import Dataset,LIFNetwork
from studio.engine import Engine

class DynamicsTests(unittest.TestCase):
    def test_direction_delay_and_reset(self):
        d=SimpleNamespace(n=3,pre=np.array([0,1]),post=np.array([1,2]),weight=np.array([10.,-10.]),input_ids=np.array([0]))
        d.incoming=csr_matrix((d.weight,(d.post,d.pre)),shape=(3,3))
        net=LIFNetwork(d)
        first=net.step(np.array([10.]),coupling=5.)
        self.assertEqual(first.tolist(),[True,False,False])
        second=net.step(np.array([0.]),coupling=5.)
        self.assertEqual(second.tolist(),[False,True,False])
        net.step(np.array([0.]),coupling=5.)
        self.assertLess(net.v[2],0.)
        net.reset(); self.assertFalse(net.total.any()); self.assertEqual(net.elapsed,0)

    def test_refractory_and_determinism(self):
        d=SimpleNamespace(n=1,pre=np.array([],int),post=np.array([],int),weight=np.array([]),input_ids=np.array([0]),incoming=csr_matrix((1,1)))
        net=LIFNetwork(d)
        result=[bool(net.step(np.array([10.]))[0]) for _ in range(4)]
        self.assertEqual(result,[True,False,False,True])

    def test_full_data_response_and_disconnect_control(self):
        d=Dataset(Path(__file__).resolve().parents[1]/'data'); net=LIFNetwork(d)
        self.assertEqual(d.n,139255); self.assertTrue(d.has_position.all())
        self.assertEqual(d.manifest['source_kind'],'official_flywire_csv')
        self.assertEqual(len(d.pre),2700513)
        self.assertEqual(int(d.synapse_count.sum()),34153566)
        self.assertTrue((d.synapse_count > 0).all())
        non_input=np.ones(d.n,bool); non_input[d.input_ids]=False
        for _ in range(100): net.step(np.zeros(len(d.input_ids)),coupling=1.5)
        self.assertEqual(net.total.sum(),0)
        net.reset()
        for _ in range(100): net.step(np.ones(len(d.input_ids)),input_gain=1.5,coupling=0.)
        self.assertGreater(net.total[d.input_ids].sum(),0)
        self.assertEqual(net.total[non_input].sum(),0)
        net.reset()
        for _ in range(100): net.step(np.ones(len(d.input_ids)),input_gain=1.5,coupling=1.5)
        self.assertGreater(net.total[non_input].sum(),0)
        self.assertTrue(np.isfinite(net.v).all())

    def test_portrait_letterbox(self):
        frame=np.full((480,120,3),255,np.uint8)
        fitted=Engine.fit_frame(frame)
        self.assertEqual(fitted.shape,(270,480,3))
        self.assertFalse(fitted[:,0].any()); self.assertTrue(fitted[:,240].all())

if __name__=='__main__': unittest.main()
