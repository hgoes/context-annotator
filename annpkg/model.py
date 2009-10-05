import tarfile
from xml.dom import minidom
import matplotlib.dates as dates
import sources
from cStringIO import StringIO

class AnnPkg:
    def __init__(self,sources,anns):
        self.annotations = anns
        self.sources = sources
    @staticmethod
    def load(fn):
        handle = tarfile.open(name=fn,mode='r:')
        buf = handle.extractfile('index')
        root = minidom.parse(buf).childNodes[0]
        if root.localName != 'sensory-input':
            raise 'Invalid index'
        _annotations = []
        _sources = []
        for n in root.childNodes:
            if n.localName == 'annotations':
                _annotations = parse_annotations(n)
            elif n.localName == 'sources':
                for source in n.childNodes:
                    if source.nodeType is not minidom.Node.ELEMENT_NODE:
                        continue
                    cls = sources.source_by_name(source.localName)
                    anns = None
                    for m in source.childNodes:
                        if m.localName == 'annotations':
                            anns = parse_annotations(m)
                    if cls is not None:
                        obj = cls.from_annpkg(handle,source.localName,source.attributes)
                    else:
                        obj = None
                    _sources.append((obj,anns))
        for (src,ann) in _sources:
            src.finish_loading()
        handle.close()
        return AnnPkg(_sources,_annotations)
    def write(self,fn):
        handle = tarfile.open(name=fn,mode='w:')
        impl = minidom.getDOMImplementation()
        root = impl.createDocument('','sensory-input',None)
        if self.annotations is not []:
            root.firstChild.appendChild(annotations_toxml(root,self.annotations))
        if self.sources is not []:
            node_srcs = root.createElement('sources')
            root.firstChild.appendChild(node_srcs)
            for (src,anns) in self.sources:
                node = src.toxml(root)
                node_srcs.appendChild(node)
                if anns is not None:
                    node.appendChild(annotations_toxml(root,anns))
        buf = root.toprettyxml('  ')
        idx_file = tarfile.TarInfo('index')
        idx_file.size = len(buf)
        handle.addfile(idx_file,StringIO(buf.encode()))
        for (src,anns) in self.sources:
            src.put_files(handle)
        handle.close()
                        
def parse_annotations(node):
    anns = []
    for ann in node.childNodes:
        if ann.localName == 'annotation':
            name = ann.attributes['id'].nodeValue
            start = float(ann.attributes['start'].nodeValue)
            end = float(ann.attributes['end'].nodeValue)
            anns.append((name,start,end))
    return anns

def annotations_toxml(root,anns):
    node = root.createElement('annotations')
    for (name,start,end) in anns:
        node_ann = root.createElement('annotation')
        node.appendChild(node_ann)
        node_ann.setAttribute('id',name)
        node_ann.setAttribute('start',str(start))
        node_ann.setAttribute('end',str(end))
    return node
