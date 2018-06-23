import logging
import multiprocessing
from multiprocessing.pool import ThreadPool
import shutil

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .app import app
from .models import Base


@app.before_first_request
def init_app():
    app.logger.setLevel(logging.INFO)

    engine = create_engine('sqlite:///.test.db')
    tp = ThreadPool(multiprocessing.cpu_count())
    session = sessionmaker(bind=engine)

    app.config.update(
        ENGINE=engine,
        THREADPOOL=tp,
        SESSION=session,
        BASE_PATH='./.raw_images/'
    )

    # Base.metadata.drop_all(engine)
    # try:
    #     shutil.rmtree(app.config['BASE_PATH'])
    # except WindowsError:
    #     pass

    Base.metadata.create_all(engine)


@app.teardown_appcontext
def teardown(s):
    return
