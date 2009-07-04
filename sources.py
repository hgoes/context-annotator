""" This module defines sources to be used for displays.
They basically provide a constructor with the data source (for example a file) and give the informations to be rendered via the getX() and getY() methods. """

import numpy as np
import datetime
from matplotlib.dates import date2num,num2date
import wave

""" Provides audio level data from a wave source (filename: *.wav) """

class WaveSource:
    def __init__(self,fn,offset=datetime.date.min):
        wav_obj = wave.open(fn,'r')
        (chans,sampwidth,framerate,nframes,comptype,compname) = wav_obj.getparams()
        if sampwidth == 2:
            tp = np.dtype(np.int16)
        if sampwidth == 4:
            tp = np.dtype(np.int32)
        self.frames = np.frombuffer(buffer = wav_obj.readframes(nframes),dtype = tp)
        self.samplerate = framerate
        self.channels = chans
        self.nframes = nframes
        self.offset = offset
    def getY(self,sampling=10000,chan=0):
        return self.frames[chan::2*sampling]
    def getX(self,sampling=10000):
        #numd = date2num(self.offset)
        return np.fromiter([ date2num(self.offset + datetime.timedelta(seconds = float(i)/self.samplerate))
                             for i in range(0,self.nframes,sampling)],dtype=np.dtype(np.float))
    def xBounds(self):
        d1 = self.offset
        d2 = d1 + datetime.timedelta(seconds = float(self.nframes)/self.samplerate)
        return (date2num(d1),date2num(d2))
    def yBounds(self,chan=0):
        return (self.frames[chan::2].min(),self.frames[chan::2].max())

class MovementSource:
    def __init__(self,fn):
        f = open(fn,'r')
        lines = f.readlines()
        sz = len(lines)
        #print sz
        self.timedata = np.empty(sz,np.dtype(np.float))
        self.xdata = np.empty((sz,6),np.dtype(np.float))
        #self.xdata = np.empty(sz,np.dtype(np.float))
        for i in range(sz):
            (timestamp,ms,xv,xd,yv,yd,zv,zd) = lines[i].split()
            self.timedata[i] = date2num(datetime.datetime.utcfromtimestamp(int(timestamp))
                                        + datetime.timedelta(seconds = float("0."+ms)))
            #print self.timedata[i]
            #self.xdata[i] = float(xv)
            self.xdata[i,0] = float(xv)
            self.xdata[i,1] = float(xd)
            self.xdata[i,2] = float(yv)
            self.xdata[i,3] = float(yd)
            self.xdata[i,4] = float(zv)
            self.xdata[i,5] = float(zd)
    def getX(self):
        return self.timedata
    def getY(self):
        return self.xdata
    def xBounds(self):
        sz = self.timedata.size
        d1 = self.timedata[0]
        d2 = self.timedata[sz-1]
        return (d1,d2)
    def yBounds(self):
        return (self.xdata.min(),self.xdata.max())
