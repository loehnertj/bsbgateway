import pytest
from bsbgateway.bsb.bsb_comm import throttle_factory

import time

def test_throttle_factory():
    l = []
    def myaction():
        for i in range(10):
            l.append(i)
            time.sleep(0.01)
    with throttle_factory(min_wait_s=0.1) as do_throttled:
        t0 = time.time()
        do_throttled(myaction)
        do_throttled(myaction)
        do_throttled(myaction)
        # Enqueuing actions took no time.
        t1 = time.time()
        assert t1 - t0 < 0.01
        while len(l) < 30:
            time.sleep(0.001)
            if time.time() - t0 > 5:
                break
    # 0.1 wait enforced between each call of myaction. Action takes ~0.1 s to complete
    t2 = time.time()
    assert t2-t0 > 0.5
    # List is in correct order (no overlapping append)
    assert l == list(range(10)) * 3
