""" This module defines sources to be used for displays.
They basically provide a constructor with the data source (for example a file) and give the informations to be rendered via the getX() and getY() methods. """

import numpy as np
import datetime
from matplotlib.dates import date2num,num2date
import wave
from scikits.audiolab import Sndfile

""" Provides audio level data from a sound source (everything that audiolab supports) """

class SoundSource:
    def __init__(self,fn,offset=datetime.date.min,chan=0):
        
        file = Sndfile(fn)

        self.nframes = file.nframes
        self.channels = file.channels
        self.samplerate = file.samplerate

        self.frames = file.read_frames(file.nframes)
        #print self.frames[::10000].T[0]
        self.name = fn
        self.offset = offset
        self.channel = chan

    def getY(self,sampling=10000):
        return self.frames[::sampling,self.channel] #[...,self.channel]
    def getX(self,sampling=10000):
        #numd = date2num(self.offset)
        return np.fromiter([ date2num(self.offset + datetime.timedelta(seconds = float(i)/self.samplerate))
                             for i in range(0,self.nframes,sampling)],dtype=np.dtype(np.float))
    def xBounds(self):
        d1 = self.offset
        d2 = d1 + datetime.timedelta(seconds = float(self.nframes)/self.samplerate)
        return (date2num(d1),date2num(d2))
    def yBounds(self):
        return (self.frames[self.channel::2].min(),self.frames[self.channel::2].max())
    def getName(self):
        return self.name
    def hasCapability(self,name):
        if name=="play":
            return True
        else:
            return False
    def getPlayData(self,start,end):
        rstart = start - self.offset
        rend = end - self.offset
        fstart = rstart.microseconds*0.000001 + rstart.seconds + rstart.days*24*3600
        fend = rend.microseconds*0.000001 + rend.seconds + rend.days*24*3600
        return (self.frames[int(fstart*self.samplerate):int(fend*self.samplerate)].T,self.samplerate)

class MovementSource:
    def __init__(self,fn):
        f = open(fn,'r')
        lines = f.readlines()
        sz = len(lines)
        #print sz
        self.timedata = np.empty(sz,np.dtype(np.float))
        self.xdata = np.empty((sz,6),np.dtype(np.float))
        self.name = fn
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
    def getName(self):
        return self.name
    def hasCapability(self,name):
        return False
