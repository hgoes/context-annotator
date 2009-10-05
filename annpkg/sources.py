import gst
import gst_numpy
import threading
import matplotlib.dates as dates
import datetime
import numpy as np
import tarfile
from cStringIO import StringIO
import pytz

class Source:
    @staticmethod
    def from_annpkg(handle,rootname,attrs):
        pass
    def toxml(self,root):
        abstract
    @staticmethod
    def source_type_id():
        return ''
    @staticmethod
    def description():
        return ""
    @staticmethod
    def arg_description():
        return []
    @staticmethod
    def from_file(fn,**args):
        return []
    def capabilities(self):
        return {}
    def put_files(self,handle):
        abstract
    def get_name(self):
        return self.name
    def get_data_bounds(self):
        return (self.get_data().min(),self.get_data().max())
    def get_time_bounds(self):
        time = self.get_time()
        return (time[0],time[-1])
    def finish_loading(self):
        pass
    def hasCapability(self,name):
        """
        :param name: The name of the capability
        :type name: :class:`str`
        :returns: Whether the source supports the capability
        :rtype: :class:`bool`
        """
        return False

class UnknownSource(Source):
    def __init__(self,handle,rootname,attrs):
        Source.__init__(self,handle,rootname,attrs)
        self.attrs = attrs
        self.rootname = rootname
    def toxml(self,root):
        el = root.createElement(self.rootname)
        for i in range(0,self.attrs.length):
            attr = self.attrs.item(i)
            el.setAttribute(attr.localName,attr.nodeValue)
        return el
    def put_files(self,handle):
        pass
    def get_data_bounds(self):
        return (0.0,0.0)
    def get_time_bounds(self):
        return (0.0,0.0)

class AudioSource(Source):
    def __init__(self,fn,name,chans,offset,gst_el):
        self.fn = fn
        self.name = name
        self.chans = chans
        self.offset = offset
        self.pipe = gst.Pipeline()
        decoder = gst.element_factory_make('flacdec')
        sink = gst_numpy.NumpySink(self.new_data,self.new_attrs)
        self.pipe.add(gst_el,decoder,sink.el)
        gst.element_link_many(gst_el,decoder,sink.el)
        self.data_avail = threading.Event()
        self.attrs_avail = threading.Event()
        self.pipe.set_state(gst.STATE_PLAYING)
    @staticmethod
    def from_annpkg(handle,rootname,attrs):
        fn = attrs['file'].nodeValue
        name = attrs['name'].nodeValue
        chans = set([int(i) for i in attrs['channels'].nodeValue.split(',')])
        member = handle.getmember(fn)
        src = gst_numpy.PySrc(handle.extractfile(member),member.size)
        return AudioSource(fn,name,chans,
                           dates.num2date(float(attrs['offset'].nodeValue)),
                           src.el)
    def toxml(self,root):
        el = root.createElement('audio')
        el.setAttribute('name',self.get_name())
        el.setAttribute('file',self.fn)
        el.setAttribute('offset',str(dates.date2num(self.offset)))
        el.setAttribute('channels',",".join([str(c) for c in self.chans]))
        return el
    @staticmethod
    def source_type_id():
        return 'audio'
    @staticmethod
    def description():
        return _("Audio data")
    @staticmethod
    def arg_description():
        return [('channel','choice',[(_("Channel")+" 1",0),(_("Channel")+" 2",1)],_("Channel")),
                ('offset','time',None,_("Offset"))]
    @staticmethod
    def from_file(fn,name,channel,offset):
        src = gst.element_factory_make('filesrc')
        src.set_property('location',fn)
        return [AudioSource(name+".flac",name,channel,offset,src)]
    def put_files(self,handle):
        self.data_avail.wait()
        pipe = gst.Pipeline()
        reader = gst_numpy.NumpySrc(self.data,self.rate)
        encoder = gst.element_factory_make('flacenc')
        sink = gst_numpy.PySink()
        pipe.add(reader.el,encoder,sink.el)
        gst.element_link_many(reader.el,encoder,sink.el)
        pipe.set_state(gst.STATE_PLAYING)
        buf = sink.get_data()
        inf = tarfile.TarInfo(self.fn)
        inf.size = len(buf)
        handle.addfile(inf,StringIO(buf))
    def get_skipping(self):
        return self.get_frames() / 10000
    def get_data(self,sampled=False):
        self.data_avail.wait()
        if sampled:
            return self.data[::self.get_skipping()]
        else:
            return self.data
    def new_data(self,dat):
        self.data = dat
        self.data_avail.set()
        self.pipe.set_state(gst.STATE_NULL)
        self.pipe = None
    def new_attrs(self,rate,chans,frames):
        self.rate = rate
        self.nchans = chans
        self.nframes = frames
        self.attrs_avail.set()
    def get_rate(self):
        self.attrs_avail.wait()
        return self.rate
    def get_frames(self):
        self.attrs_avail.wait()
        if self.nframes is None:
            return len(self.get_data())
    def get_time(self,sampled=False):
        nframes = self.get_frames()
        rate = self.get_rate()
        if sampled:
            skip = self.get_skipping()
        else:
            skip = 1
        return np.fromiter([ dates.date2num(self.offset + datetime.timedelta(seconds = float(i)/rate))
                             for i in range(0,nframes,skip)],dtype=np.dtype(np.float))
    def get_time_bounds(self):
        return (dates.date2num(self.offset),dates.date2num(self.offset + datetime.timedelta(seconds = self.get_frames()/self.get_rate())))
    def finish_loading(self):
        self.data_avail.wait()
    def hasCapability(self,name):
        if name=='play':
            return True
        else:
            return False
    def getPlayData(self,start,end):
        rstart = start - self.offset
        rend = end - self.offset
        fstart = rstart.microseconds*0.000001 + rstart.seconds + rstart.days*24*3600
        fend = rend.microseconds*0.000001 + rend.seconds + rend.days*24*3600
        return (self.data[int(fstart*self.rate):int(fend*self.rate)],self.rate)
    def capabilities(self):
        pass
        #return {'play' : lambda (l,r): }

class MovementSource(Source):
    def __init__(self,fn,name,timedata,ydata):
        self.fn = fn
        self.name = name
        self.timedata = timedata
        self.ydata = ydata
    @staticmethod
    def from_annpkg(handle,rootname,attrs):
        fn = attrs['file'].nodeValue
        name = attrs['name'].nodeValue
        member = handle.getmember(fn)
        lines = member.readlines()
        sz = len(lines)
        timedata = np.empty(sz,np.dtype(np.float))
        ydata = np.empty((sz,3),np.dtype(np.float))
        for i in range(sz):
            (timestamp,x,y,z) = lines[i].split()
            timedata[i] = dates.date2num(datetime.datetime.fromtimestamp(float(timestamp),pytz.utc))
            ydata[i,0] = x
            ydata[i,1] = y
            ydata[i,2] = z
        return MovementSource(fn,name,timedata,ydata)
    @staticmethod
    def from_file(fn,name,sensor):
        res = {}
        with open(fn) as h:
            lines = h.readlines()
            sz = len(lines)
            for s in sensor:
                res[s] = (np.empty(sz,np.dtype(np.float)),np.empty((sz,3),np.dtype(np.float)))
            for i in range(sz):
                splt = lines[i].split()
                rest = len(splt) % 3
                if rest == 2:
                    timedata = dates.date2num(datetime.datetime.fromtimestamp(int(splt[0]),pytz.utc)
                                              + datetime.timedelta(seconds = float("0."+splt[1])))
                elif rest == 1:
                    timedata = dates.date2num(datetime.datetime.fromtimestamp(float(splt[0]),pytz.utc))
                for s in sensor:
                    res[s][0][i] = timedata
                    res[s][1][i,0] = splt[rest + s*3]
                    res[s][1][i,1] = splt[rest + s*3 + 1]
                    res[s][1][i,2] = splt[rest + s*3 + 2]
        return [ MovementSource(name+str(s)+".log",name+str(s),res[s][0],res[s][1]) for s in sensor ]
                
    def toxml(self,root):
        el = root.createElement('movement')
        el.setAttribute('name',self.get_name())
        el.setAttribute('file',self.fn)
        return el
    @staticmethod
    def source_type_id():
        return 'movement'
    @staticmethod
    def description():
        return _("Movement data")
    @staticmethod
    def arg_description():
        return [('sensor','choice',[(_("Sensor")+" 1",0),(_("Sensor")+" 2",1)],_("Sensor"))]
    def get_data(self,sampled=False):
        return self.ydata
    def get_time(self,sampled=False):
        return self.timedata

all_sources = [AudioSource,MovementSource]

def source_by_name(name):
    for src in all_sources:
        if src.source_type_id() == name:
            return src
    return UnknownSource
