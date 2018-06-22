import base64
import cStringIO
from datetime import datetime

import rawpy
import exifread
from PIL import Image


class RawImg(object):
    def __init__(self, fileobj):
        self.file = fileobj
        self.file.seek(0)
        self._im = None
        self._exif = None

    @property
    def exif(self):
        if self._exif is None:
            self._exif = exifread.process_file(self.file)
            self.file.seek(0)

        return self._exif

    @property
    def raw_img(self):
        if self._im is None:
            self._im = rawpy.imread(self.file)
            self.file.seek(0)

        return self._im

    def timestamp(self):
        ts = self.exif['Image DateTime'].values
        return datetime.strptime(ts, '%Y:%m:%d %H:%M:%S')

    def pil_image(self):
        return Image.fromarray(self.raw_img.postprocess())

    def thumbnail(self, width=128):
        pimg = self.pil_image()
        w, h = pimg.size
        scale = float(width) / float(w)
        height = scale * float(h)

        pimg.thumbnail((width, height))
        buff = cStringIO.StringIO()
        pimg.save(buff, format="JPEG")
        return base64.b64encode(buff.getvalue())
