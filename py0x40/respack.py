from itertools import chain
import os
import random
from tempfile import mkdtemp
from xml.etree import ElementTree
from zipfile import ZipFile

from draw import Image

audio_extensions = ['.mp3', '.ogg', '.wav']
image_extensions = ['.png', '.gif', '.jpg', '.jpeg']


class Resources(object):

    def __init__(self, filenames=None):

        if filenames is None:
            filenames = [os.path.join('respacks', fn) for fn in next(os.walk('respacks'))[2] if fn.endswith('.zip')]

        self.respacks = [ResPack(fn) for fn in filenames]

        self.images = list(chain(*[respack.images for respack in self.respacks]))
        self.songs = list(chain(*[respack.songs for respack in self.respacks]))
    
    def open_random_image(self):

        return self.open_image(random.choice(self.images))

    def open_image(self, name):

        for respack in self.respacks:

            if name in respack.images:
                return respack.open_image(name)

    def open_song(self, name):

        for respack in self.respacks:

            if name in respack.songs:
                return respack.open_song(name)


class ResPack(object):

    def __init__(self, filename):

        self.filename = filename

        self.audio_files = {}
        self.image_files = {}
        self.xml_files = {}

        self.images = {}
        self.songs = {}

        self.name = None
        self.author = None
        self.description = None
        self.link = None

        with ZipFile(filename, 'r') as zf:

            for fn in zf.namelist():

                fn_lower = fn.lower()

                if any(fn_lower.endswith(ext) for ext in audio_extensions):
                    self.audio_files[os.path.splitext(os.path.basename(fn))[0]] = (fn)

                if any(fn_lower.endswith(ext) for ext in image_extensions):
                    self.image_files[os.path.splitext(os.path.basename(fn))[0]] = (fn)
                
                if fn_lower.endswith('.xml'):
                    self.xml_files[os.path.splitext(os.path.basename(fn))[0]] = (fn)
            
            for name, fn in self.xml_files.items():

                with zf.open(fn, 'r') as f:
                    self.parse_xml(f)
    
    def open_image(self, name, height=720):

        if name not in self.images:
            raise ValueError('No image %s' % name)
        
        image_entry = self.images[name]

        with ZipFile(self.filename, 'r') as zf:

            with zf.open(self.image_files[name], 'r') as f:
                image = Image(f, os.path.basename(self.image_files[name]), height=height)

        return image, image_entry

    def open_song(self, name):

        if name not in self.songs:
            raise ValueError('No song %s' % name)
        
        song_entry = self.songs[name]

        tempdir = mkdtemp()

        with ZipFile(self.filename, 'r') as zf:
            
            loop_filename = zf.extract(self.audio_files[name], path=tempdir)

            if song_entry.buildup is not None:
                buildup_filename = zf.extract(self.audio_files[song_entry.buildup], path=tempdir)
            else:
                buildup_filename = None
        
        return loop_filename, buildup_filename, song_entry
    
    def parse_xml(self, f):

        tree = ElementTree.parse(f)

        top_level_nodes = tree.findall('.')

        for node in top_level_nodes:

            if node.tag == 'info':

                for info_node in node.findall('*'):

                    if info_node.tag == 'name':
                        self.name = info_node.text

                    if info_node.tag == 'author':
                        self.author = info_node.text

                    if info_node.tag == 'description':
                        self.description = info_node.text

                    if info_node.tag == 'link':
                        self.link = info_node.text
            
            if node.tag == 'images':

                for image_node in node.findall('./image'):
                    
                    name = image_node.get('name')
                    if name in self.image_files:
                        self.images[name] = ImageEntry(image_node)
            
            if node.tag == 'songs':

                for song_node in node.findall('./song'):

                    name = song_node.get('name')
                    if name in self.audio_files:
                        self.songs[name] = SongEntry(song_node)


class ImageEntry(object):

    def __init__(self, image_node):

        self.name = image_node.get('name')

        sources = image_node.findall('./source')
        if len(sources) == 1:
            self.source = sources[0].text
        else:
            self.source = None

        sources_other = image_node.findall('./source_other')
        if len(sources_other) == 1:
            self.source_other = sources_other[0].text
        else:
            self.source_other = None
        
        fullnames = image_node.findall('./fullname')
        if len(fullnames) == 1:
            self.fullname = fullnames[0].text
        else:
            self.fullname = None
            
        aligns = image_node.findall('./align')
        if len(aligns) == 1:
            self.align = aligns[0].text
        else:
            self.align = None


class SongEntry(object):

    def __init__(self, song_node):

        self.name = song_node.get('name')

        sources = song_node.findall('./source')
        if len(sources) == 1:
            self.source = sources[0].text
        else:
            self.source = None

        rhythms = song_node.findall('./rhythm')
        if len(rhythms) == 1:
            self.rhythm = rhythms[0].text
        else:
            self.rhythm = None

        buildups = song_node.findall('./buildup')
        if len(buildups) == 1:
            self.buildup = buildups[0].text
        else:
            self.buildup = None

        buildup_rhythms = song_node.findall('./buildupRhythm')
        if len(buildup_rhythms) == 1:
            self.buildup_rhythm = buildup_rhythms[0].text
        else:
            self.buildup_rhythm = None
