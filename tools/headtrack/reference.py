"""Independent quaternion complementary filter prototype; no third-party filter dependency.

Mahony-style gravity feedback is a standard adequate design for this six-axis IMU.
Yaw is relative, not magnetically observable. Stationary bias adaptation is gated,
unlike the stock unconditional low-pass subtraction. No future-pose prediction.
"""
import math

import numpy as np


def multiply(a, b):
    w, x, y, z = a
    W, X, Y, Z = b
    return np.array([w*W-x*X-y*Y-z*Z, w*X+x*W+y*Z-z*Y,
                     w*Y-x*Z+y*W+z*X, w*Z+x*Y-y*X+z*W])


class Filter:
    def __init__(self, rate=240):
        self.dt = 1/rate
        self.q = np.array([1., 0, 0, 0])
        self.bias = np.zeros(3)
        self.still = 0
        self.initialized = False
        self.omega = np.zeros(3)

    def update(self, gyro_dps, accel_g):
        g, a = np.array(gyro_dps), np.array(accel_g)
        norm = np.linalg.norm(a)
        if not self.initialized and norm > .01:
            a /= norm
            if a[2] > .9999:
                self.q = np.array([0., 1, 0, 0])
            else:
                w = math.sqrt((1-a[2])*.5)
                self.q = np.array([w, -.5*a[1]/w, .5*a[0]/w, 0])
            self.initialized = True
        stationary = .96 < norm < 1.04 and g@g < .75**2
        self.still = self.still+self.dt if stationary else 0
        if self.still >= .5:
            self.bias += (g-self.bias)*(1-math.exp(-self.dt/.5))
        self.omega = np.radians(g-self.bias)
        w, x, y, z = self.q
        pred = np.array([-2*(x*z-w*y), -2*(w*x+y*z), -(w*w-x*x-y*y+z*z)])
        correction = np.zeros(3)
        if .9 < norm < 1.1:
            correction = 2*np.cross(a/norm, pred)
        self.q += .5*self.dt*multiply(self.q, np.r_[0, self.omega+correction])
        self.q /= np.linalg.norm(self.q)
        return self.q.copy()
