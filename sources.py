"""
Data sources
============

This module defines sources to be used for displays.
They basically provide a constructor with the data source (for example a file) and give the informations to be rendered via the getX() and getY() methods. """

import numpy as np
import datetime
from matplotlib.dates import date2num,num2date
import wave
from scikits.audiolab import Sndfile
from timezone import UTC

class Source:
    """ An abstract base class for all sources. """
    def getName(self):
        """
        :returns: a displayable name for the source
        :rtype: :class:`str`
        """
        abstract
    def getX(self,sampled=True):
        """
        :returns: an array containing the x-axis data
        :rtype: :class:`numpy.ndarray`
        """
        abstract
    def getY(self,sampled=True):
        """
        :returns: an array containing the y-axis data
        :rtype: :class:`numpy.ndarray`
        """
        abstract
    def xBounds(self):
        """
        :returns: The minimal and maximal x-value
        :rtype: (:class:`float`, :class:`float`)
        """
        abstract
    def yBounds(self):
        """
        :returns: The minimal and maximal y-value
        :rtype: (:class:`float`, :class:`float`)
        """
        abstract
    def shortIdentifier(self):
        """
        :returns: A one or two letter word that identifies the source-class
        :rtype: :class:`str`
        """
        abstract
    def hasCapability(self,name):
        """
        :param name: The name of the capability
        :type name: :class:`str`
        :returns: Whether the source supports the capability
        :rtype: :class:`bool`
        """
        abstract
    def getPlayData(self,start,end):
        """
        :param start: timestamp when the audio-data should start
        :type start: :class:`float`
        :param end: timestamp when the audio-data should end
        :type end: :class:`float`
        :returns: The audio data
        :rtype: :class:`numpy.ndarray`
        
        Note that this must only be implemented if the source has the capability 'play'.
        """
        abstract

class SoundSource(Source):
    """
    :param fn: The filename from which to load the data
    :type fn: :class:`str`
    :param offset: A timestamp representing when the audiodata starts
    :type offset: :class:`float`
    :param chan: The audio channel from which to extract the data
    :type chan: :class:`int`
    
    Provides audio level data from a sound source (everything that audiolab supports).
    """
    def __init__(self,fn,offset=datetime.date.min,chan=0):
        
        file = Sndfile(fn)

        self.nframes = file.nframes
        self.channels = file.channels
        self.samplerate = file.samplerate

        self.frames = file.read_frames(file.nframes)
        self.name = fn
        self.offset = offset
        self.channel = chan

        self.skiping = self.nframes / 10000
        if self.skiping == 0:
            self.skiping = 1
        
    def getY(self,sampled=True):
        if sampled:
            if self.channels == 2:
                return self.frames[::self.skiping,self.channel] #[...,self.channel]
            else:
                return self.frames[::self.skiping]
        else:
            if self.channels == 2:
                return self.frames[::,self.channel]
            else:
                return self.frames
    def getX(self,sampled=True):
        if sampled:
            return np.fromiter([ date2num(self.offset + datetime.timedelta(seconds = float(i)/self.samplerate))
                                 for i in range(0,self.nframes,self.skiping)],dtype=np.dtype(np.float))
        else:
            return np.fromiter([ date2num(self.offset + datetime.timedelta(seconds = float(i)/self.samplerate))
                                 for i in range(0,self.nframes)],dtype=np.dtype(np.float))
    def xBounds(self):
        d1 = self.offset
        d2 = d1 + datetime.timedelta(seconds = float(self.nframes)/self.samplerate)
        return (date2num(d1),date2num(d2))
    def yBounds(self):
        return (self.frames[self.channel::2].min(),self.frames[self.channel::2].max())
    def getName(self):
        return self.name
    def shortIdentifier(self):
        return "a"
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

class MovementSource(Source):
    """
    :param fn: The filename with the movement data
    :type fn: :class:`str`
    :param axis: The movement axis whose data we want (0=x,1=y,2=z)
    :type axis: :class:`int`

    Provides sensory input data of a acceleration sensor.
    """
    def __init__(self,fn,sensor=0):
        utc = UTC()
        f = open(fn,'r')
        lines = f.readlines()
        sz = len(lines)
        #print sz
        self.timedata = np.empty(sz,np.dtype(np.float))
        self.xdata = np.empty((sz,3),np.dtype(np.float))
        self.sensor = sensor
        self.fn = fn
        for i in range(sz):
            splt = lines[i].split()
            if len(splt) == 8:
                (timestamp,ms,x1,y1,z1,x2,y2,z2) = splt
                self.timedata[i] = date2num(datetime.datetime.fromtimestamp(int(timestamp),utc)
                                            + datetime.timedelta(seconds = float("0."+ms)))
            elif len(splt) == 7:
                (timestamp,x1,y1,z1,x2,y2,z2) = splt
                self.timedata[i] = date2num(datetime.datetime.fromtimestamp(float(timestamp),utc))
            if sensor==0:
                self.xdata[i,0] = float(x1)
                self.xdata[i,1] = float(y1)
                self.xdata[i,2] = float(z1)
            else:
                self.xdata[i,0] = float(x2)
                self.xdata[i,1] = float(y2)
                self.xdata[i,2] = float(z2)
    def getX(self,sampled=True):
        return self.timedata
    def getY(self,sampled=True):
        return self.xdata
    def xBounds(self):
        sz = self.timedata.size
        d1 = self.timedata[0]
        d2 = self.timedata[sz-1]
        return (d1,d2)
    def yBounds(self):
        return (self.xdata.min(),self.xdata.max())
    def getName(self):
        return self.fn+" Sensor "+str(self.sensor)
    def shortIdentifier(self):
        return "m"+str(self.sensor)
    def hasCapability(self,name):
        return False
