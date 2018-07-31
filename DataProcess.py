# -*- coding: utf-8 -*-
'''
Created on Thu Sep 29 14:35:48 2016

@author: Yaoyao Zhang
''' 
   
from scipy.interpolate import UnivariateSpline 
from scipy.signal import periodogram
import numpy as np
import time
    
def get_pw(y, frac = 8):
    '''Get the four intersection points seprarated by period/frac in each quarter of a given sine wave
    ''' 
    n = y.shape[0]
    x = np.arange(n)  
    
    #Find two peak points
    x_p_index = np.argmax(y)
    x_n_index = np.argmin(y)
    y_p = y[x_p_index]
    y_n = y[x_n_index]
    cutoff_p = y_p * np.sin(np.pi*2/frac)
    cutoff_n = y_n * np.sin(np.pi*2/frac)
    
    #1st quarter
    y_q1 = np.array(y)
    y_q1[y<=cutoff_p]=0
    y_q1[x>=x_p_index]=np.amax(y)
    r1 = np.amax(x[y_q1==0])

    #2nd quarter
    y_q2 = np.array(y)
    y_q2[y<=cutoff_p]=0
    y_q2[x<=x_p_index]=np.amax(y)
    r2 = np.amin(x[y_q2==0])
    
    #3rd quarter
    y_q3 = np.array(y)
    y_q3[y>=cutoff_n]=0
    y_q3[x>=x_n_index]=np.amin(y)
    r3 = np.amax(x[y_q3==0])
    
    #4th quarter
    y_q4 = np.array(y)
    y_q4[y>=cutoff_n]=0
    y_q4[x<=x_n_index]=np.amin(y)
    r4 = np.amin(x[y_q4==0])
    return int(r1),int(r2),int(r3),int(r4)
    
def get_closest_f(t, array, start, stop, step): 
    nf = (stop-start)/step+1
    freqs = np.linspace(start, stop, nf, endpoint = True)
    vpp = np.zeros([freqs.shape[0]])
    tau = (t[1]-t[0])
    for i, f in enumerate(freqs):
        T = 1./f
        nt = int(round(T/tau,0))
        t_ = np.arange(nt)*tau
        x = np.sin(2*np.pi*f*t_)
        array_conv = np.convolve(array, x)
        vpp[i] = np.amax(array_conv)- np.amin(array_conv)
    closest_f = freqs[np.argmax(vpp)]
    return closest_f
    
def get_freq_spectrum(data, fs, nffts, passband = [4e6, 45e6], cutoff = -3, window=None,detrend='linear',scaling='spectrum',process=False): 
    '''Return the frequency spectrum in dB scale for a given signal in the given passband.
    Also return the center frequency fc, high and low cutoff frequency fh and fl with given cutoff level (default is -3dB), if 'process' is set to True.
    '''
    f, p = periodogram(data, fs=fs, nfft = nffts, window=window, detrend=detrend, return_onesided=True, scaling=scaling)
    f = f[1:]
    p = p[1:]
    freq = f[np.logical_and(f>=passband[0],f<=passband[1])]    
    power = p[np.logical_and(f>=passband[0],f<=passband[1])]
    if not process:
        return freq, power
    db = 10.*np.log10(power)
    db = db-max(db)
    fp = freq[db==0]    
    spline = UnivariateSpline(freq, db-(cutoff), s=0)
    try:
        fl, fh = spline.roots()
        fc = (fl+fh)/2
        bw = (fh-fl)/fc
    except Exception:
        fl, fh, fc, bw = 0, 0, 0, 0    
    return freq, db, fp, fc, fl, fh, bw 
    
def delay_correlation(a1, a2):
    '''Return the cross correlation of two 1-D arrays.
    '''
    l1 = len(a1)
    l2 = len(a2)
    corr = abs(np.correlate(a1, a2, 'full'))
    diff = np.argmax(corr)+1-(l1+l2)/2.
    return diff, corr
    
def db2mag(db):   
    mag = 10**(db/20)
    return mag