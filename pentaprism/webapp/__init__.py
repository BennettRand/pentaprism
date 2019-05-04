import multiprocessing
import os
from multiprocessing.pool import ThreadPool
from os.path import join
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .app import app
from .models import Base, Images, ExifData, Thumbnails, BadImageException


def rebuild():
    app.logger.warn('Rebuilding Image Database')
    engine = create_engine(app.config['DB_CSTRING'])
    session_maker = sessionmaker(bind=engine)
    session = session_maker()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    for root, dirs, files in os.walk(app.config['BASE_PATH']):
        for name in files:
            with open(join(root, name), 'rb') as f:
                try:
                    app.logger.info('Opening Image file=%s', name)
                    imf = Images(f, filename=name)
                    for k, v in imf.exif_dict.items():
                        imf.exif.append(ExifData(key=k, value=v))
                    app.logger.info('Scanned EXIF name=%s len=%s',
                                    imf.filename, len(imf.exif_dict))
                    imf.thumbnail = Thumbnails(data=imf.b64_thumbnail())
                    app.logger.info('Created Thumbnail name=%s', imf.filename)
                    session.add(imf)
                    session.commit()
                    app.logger.info('Saved Image name=%s', imf.filename)
                except BadImageException:
                    app.logger.warn('Could not process file path=%s', f.name)
                    pass

    session.close()


@app.before_first_request
def init_app():
    engine = create_engine(app.config['DB_CSTRING'])
    tp = ThreadPool(multiprocessing.cpu_count())
    session = sessionmaker(bind=engine)

    app.config.update(
        ENGINE=engine,
        THREADPOOL=tp,
        SESSION=session
    )

    Base.metadata.create_all(engine)


@app.teardown_appcontext
def teardown(s):
    return
