import base64
import cStringIO
import math
import os
import os.path
from datetime import datetime

import exifread
import rawpy
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import LANCZOS
from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey, Text,
                        UniqueConstraint)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


def sec(x): return 1.0 / math.cos(x)


class BadImageException(Exception):
    pass


class Images(Base):
    __tablename__ = 'images'
    __table_args__ = (UniqueConstraint('filename', 'filepath'),
                      {'sqlite_autoincrement': True})

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(64), index=True)
    filepath = Column(String(256), index=True)
    timestamp = Column(DateTime, index=True)
    thumbnail = relationship("Thumbnails", uselist=False,
                             back_populates="image",
                             cascade="all, delete-orphan")
    exif = relationship("ExifData", uselist=True,
                        back_populates="image", cascade="all,delete-orphan",
                        lazy='dynamic')

    def __init__(self, fileobj, filename=None):
        self.file = fileobj
        self.file.seek(0)
        self._im = None
        self._exif = None
        if filename is None:
            filename = self._try_get_name(self.file)
        else:
            filename = filename

        try:
            timestamp = self.get_timestamp()
        except KeyError:
            raise BadImageException()

        filepath = timestamp.strftime('%Y/%m-%b/%d')

        super(Images, self).__init__(filename=filename, filepath=filepath,
                                     timestamp=timestamp)

    @property
    def exif_dict(self):
        if self._exif is None:
            self._exif = exifread.process_file(self.file)
            self.file.seek(0)

        return {k: str(v) for k, v in self._exif.items() if len(str(v)) <= 128}

    @property
    def raw_img(self):
        if self._im is None:
            self._im = rawpy.imread(self.file)
            self.file.seek(0)

        return self._im

    def get_timestamp(self):
        ks = ['Image DateTimeOriginal', 'EXIF DateTimeOriginal',
              'Image DateTime', 'EXIF DateTime']
        for k in ks:
            ts = self.exif_dict.get(k)
            if ts is not None:
                break
        return datetime.strptime(ts, '%Y:%m:%d %H:%M:%S')

    def get_copyright(self):
        ks = ['Image Copyright', 'Image Artist']
        cr = self.exif.filter(ExifData.key.in_(ks)).first()
        if cr is None:
            cr = "Copyright"
        else:
            cr = cr.value
        return '{} {}'.format(cr, self.timestamp.year)

    def pil_image(self, pp_args={}, watermark=None, width=None, height=None,
                  crop=None, rotate=None):
        img = Image.fromarray(self.raw_img.postprocess(**pp_args))

        if rotate is not None:
            A = float(rotate)
            A = math.fabs(math.radians(A))
            B = (math.pi / 2.0) - A
            c = math.cos(A)
            s = math.sin(A)
            w, h = img.size

            shr = max(w, h) / (sec(A) + sec(B))
            new_w = (h * s + w * c)
            new_h = (h * c + w * s)

            d_w = shr - ((new_w - w) / 2.0)
            d_h = shr - ((new_h - h) / 2.0)

            crop_ = (int(d_w), int(d_h), int(w - d_w), int(h - d_h))

            img = img.rotate(float(rotate)).crop(crop_)

        if crop is not None:
            w, h = img.size
            l = (crop[0] / 100.0) * w
            t = (crop[1] / 100.0) * h
            r = (crop[2] / 100.0) * w
            b = (crop[3] / 100.0) * h
            img = img.crop((l, t, r, b))

        if width is not None or height is not None:
            w, h = img.size
            if width is None:
                scale = float(height) / float(h)
                width = scale * float(w)

            if height is None:
                scale = float(width) / float(w)
                height = scale * float(h)

            height = int(height)
            width = int(width)
            img = img.resize((width, height), LANCZOS)

        if watermark is not None:
            mark = Image.new("RGBA", img.size)
            draw = ImageDraw.ImageDraw(mark, "RGBA")
            weight = img.size[0] / 40
            offset = weight / 3
            font = ImageFont.truetype(
                './pentaprism/webapp/static/style/Comfortaa-Regular.ttf',
                weight)
            fs = font.getsize(watermark)
            dx = (img.size[0] - fs[0]) - offset
            dy = (img.size[1] - fs[1]) - offset
            draw.text((dx, dy), watermark, font=font)
            mask = mark.convert("L").point(lambda x: min(x, 100))
            mark.putalpha(mask)
            img.paste(mark, None, mark)

        return img

    def b64_thumbnail(self, width=128):
        pimg = self.pil_image(pp_args={
            'half_size': True,
            'demosaic_algorithm': rawpy.DemosaicAlgorithm.LINEAR},
            width=width)

        buff = cStringIO.StringIO()
        pimg.save(buff, format="JPEG")
        return base64.b64encode(buff.getvalue())

    # def get_zip(self):
    #     directory = os.path.join(FILE_BASE, self.filepath)
    #     if not os.path.exists(directory):
    #         os.makedirs(directory)
    #     fpath = os.path.join(directory, 'raw.zip')
    #     if os.path.isfile(fpath):
    #         return zipfile.ZipFile(fpath, 'a', zipfile.ZIP_DEFLATED)
    #     else:
    #         return zipfile.ZipFile(fpath, 'w', zipfile.ZIP_DEFLATED)

    def save_file(self, base='./', force=False):
        directory = os.path.join(base, self.filepath)
        fpath = os.path.join(directory, self.filename)

        if not os.path.exists(directory):
            os.makedirs(directory)

        if os.path.isfile(fpath) and not force:
            return False

        with open(fpath, 'wb') as f:
            f.write(self.file.read())
            self.file.seek(0)

        return True

    @classmethod
    def make_thumbnail(cls, f_path, app):
        session = app.config['SESSION']()
        img = None

        try:
            f = open(os.path.join(app.config['BASE_PATH'], *f_path), 'rb')
            img = cls.try_get_existing(cls(f, filename=f_path[-1]), session)
            img.thumbnail = Thumbnails(data=img.b64_thumbnail())
            session.add(img.thumbnail)
            session.commit()
        except Exception as e:
            return False, str(e)
        finally:
            session.close()

        return True, img.filename

    @classmethod
    def try_get_existing(cls, other, session):
        existing = (session.query(cls).filter(cls.filename == other.filename)
                    .filter(cls.filepath == other.filepath).first())

        if existing is None:
            return other

        existing.timestamp = other.timestamp
        existing.file = other.file
        existing.file.seek(0)
        existing._im = None
        existing._exif = None
        return existing

    @staticmethod
    def _try_get_name(fileobj):
        try:
            if fileobj.name == '':
                return os.path.basename(fileobj.filename)
            else:
                raise AttributeError()
        except AttributeError:
            return os.path.basename(fileobj.filename)

    @staticmethod
    def draw_thirds(img, weight=1):
        w, h = img.size
        draw = ImageDraw.Draw(img)

        t_w = w / 3
        t_h = h / 3

        l = ((t_w, 0), (t_w, h))
        r = ((2 * t_w, 0), (2 * t_w, h))
        t = ((0, t_h), (w, t_h))
        b = ((0, 2 * t_h), (w, 2 * t_h))

        draw.line(l, '#000', weight)
        draw.line(r, '#000', weight)
        draw.line(t, '#000', weight)
        draw.line(b, '#000', weight)

        return img

    @staticmethod
    def draw_triangles1(img, weight=1):
        w, h = img.size
        diag = math.sqrt(w ** 2 + h ** 2)
        alt = (w * h) / diag
        d2 = int(math.cos(math.atan(float(h) / float(w))) * w)
        d1 = diag - d2
        l = d1 * alt / h
        b = d2 * alt / w

        draw = ImageDraw.Draw(img)

        d0 = ((0, 0), (w, h))
        d1 = ((0, h), (l, h - b))
        d2 = ((w, 0), (w - l, b))

        draw.line(d0, '#000', weight)
        draw.line(d1, '#000', weight)
        draw.line(d2, '#000', weight)

        return img

    @staticmethod
    def draw_triangles2(img, weight=1):
        w, h = img.size
        diag = math.sqrt(w ** 2 + h ** 2)
        alt = (w * h) / diag
        d2 = int(math.cos(math.atan(float(h) / float(w))) * w)
        d1 = diag - d2
        l = d1 * alt / h
        b = d2 * alt / w

        draw = ImageDraw.Draw(img)

        d0 = ((0, h), (w, 0))
        d1 = ((0, 0), (l, b))
        d2 = ((w, h), (w - l, h - b))

        draw.line(d0, '#000', weight)
        draw.line(d1, '#000', weight)
        draw.line(d2, '#000', weight)

        return img


class Thumbnails(Base):
    __tablename__ = 'thumbnails'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey('images.id'))
    data = Column(Text)
    image = relationship("Images", back_populates="thumbnail")


class ExifData(Base):
    __tablename__ = 'exif_data'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey('images.id'))
    image = relationship("Images", back_populates="exif")
    key = Column(String(128))
    value = Column(String(128))

