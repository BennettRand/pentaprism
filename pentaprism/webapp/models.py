import base64
import cStringIO
import os
import os.path
from datetime import datetime

import exifread
import rawpy
from PIL import Image
from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey, Text,
                        UniqueConstraint)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


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
                        back_populates="image", cascade="all,delete-orphan")

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

    def pil_image(self):
        return Image.fromarray(self.raw_img.postprocess())

    def b64_thumbnail(self, width=128):
        pp = self.raw_img.postprocess(
            half_size=True,
            demosaic_algorithm=rawpy.DemosaicAlgorithm.LINEAR)
        pimg = Image.fromarray(pp)
        w, h = pimg.size
        scale = float(width) / float(w)
        height = scale * float(h)

        pimg.thumbnail((width, height))
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

