import cStringIO
import os.path

from flask import Flask, request, jsonify, Response, send_from_directory
from flask.views import MethodView
from flask_basicauth import BasicAuth
from PIL.Image import LANCZOS
from sqlalchemy import extract

from .models import Images, ExifData

app = Flask(__name__)

app.config['BASIC_AUTH_FORCE'] = True

basic_auth = BasicAuth(app)


def thumbnail_cb(result):
    success, data = result
    if success:
        app.logger.info('Thumbnail Successful filename=%s', data)
    else:
        app.logger.error('Thumbnail Error exception=%s', data)


class ImageView(MethodView):
    def post(self, img_id=None):
        session = app.config['SESSION']()
        images = []
        saved = []
        skipped = []
        errored = []
        thumbnails = []
        replace = request.args.get('replace', None) is not None

        for fs in request.files.listvalues():
            for f in fs:
                try:
                    rimg = Images(f)

                    if rimg.save_file(app.config['BASE_PATH'], force=replace):

                        rimg = Images.try_get_existing(rimg, session)

                        rimg.exif = []

                        for k, v in rimg.exif_dict.items():
                            rimg.exif.append(ExifData(key=k, value=v))

                        images.append(rimg)
                        saved.append(rimg.filename)
                        thumbnails.append((rimg.filepath, rimg.filename))
                        app.logger.info('Saved File filename=%s',
                                        rimg.filename)
                    else:
                        skipped.append(rimg.filename)
                except Exception as e:
                    fname = Images._try_get_name(f)
                    app.logger.error('Error Saving file filename=%s error=%s',
                                     fname, e)
                    errored.append(fname)

        session.add_all(images)
        session.commit()
        session.close()

        for t in thumbnails:
            app.config['THREADPOOL'].apply_async(Images.make_thumbnail,
                                                 args=(t, app),
                                                 callback=thumbnail_cb)

        ret = jsonify(saved=saved, skipped=skipped, errored=errored)
        ret.status_code = 201
        return ret

    def get(self, img_id=None):
        ret = None
        session = app.config['SESSION']()

        if img_id is None:
            limit = min(int(request.args.get('limit', 500)), 1000)
            offset = int(request.args.get('offset', 0))

            year = request.args.get('year')
            month = request.args.get('month')
            day = request.args.get('day')

            q = session.query(Images)

            if year is not None:
                q = q.filter(extract('year', Images.timestamp) == year)
            if month is not None:
                q = q.filter(extract('month', Images.timestamp) == month)
            if day is not None:
                q = q.filter(extract('day', Images.timestamp) == day)

            a = q.order_by(Images.timestamp).offset(offset).limit(limit).all()

            ret = {i.id: {'name': i.filename,
                          'timestamp': i.timestamp.isoformat(), 
                          'url': '/images/{}/'.format(i.id)} for i in a}
            ret = jsonify(ret)

        else:
            img = session.query(Images).get(img_id)
            if img is None:
                ret = jsonify(error='Not found', id=img_id)
                ret.status_code = 404
                return ret

            img._im = None
            img.file = open(os.path.join(app.config['BASE_PATH'], img.filepath,
                                         img.filename), 'rb')

            pimg = img.pil_image()
            w, h = pimg.size

            width = request.args.get('width', None)
            height = request.args.get('height', None)
            fmt = request.args.get('format', 'JPEG')

            if width is None and height is None:
                width = 1280

            if width is None:
                scale = float(height) / float(h)
                width = scale * float(w)

            if height is None:
                scale = float(width) / float(w)
                height = scale * float(h)

            height = int(height)
            width = int(width)
            pimg = pimg.resize((width, height), LANCZOS)
            buff = cStringIO.StringIO()
            pimg.save(buff, format=fmt)

            ret = Response(buff.getvalue(), status=200,
                           mimetype='image/{}'.format(fmt.lower()))

        session.close()
        return ret


@app.route('/images/<int:img_id>/thumbnail/')
def thumbnail(img_id):
    ret = None
    session = app.config['SESSION']()

    img = session.query(Images).get(img_id)

    if img is None:
        ret = jsonify(error='Not found', id=img_id)
        ret.status_code = 404
        return ret

    ret = 'data:image/jpeg;base64,{}'.format(img.thumbnail.data)

    session.close()
    return ret


@app.route('/images/<int:img_id>/exif/')
def exif(img_id):
    ret = None
    session = app.config['SESSION']()

    img = session.query(Images).get(img_id)

    if img is None:
        ret = jsonify(error='Not found', id=img_id)
        ret.status_code = 404
        return ret

    ret = jsonify({e.key: e.value for e in img.exif})

    session.close()
    return ret


@app.route('/dates/', methods=['GET'])
def dates():
    session = app.config['SESSION']()

    ret = {}

    years = session.query(
        extract('year', Images.timestamp)).distinct(
        extract('year', Images.timestamp)).all()

    for y in years:
        y = y[0]
        ret[y] = {}
        months = session.query(
            extract('month', Images.timestamp)).filter(
            extract('year', Images.timestamp) == y).distinct(
            extract('month', Images.timestamp)).all()

        for m in months:
            m = m[0]
            days = session.query(
                extract('day', Images.timestamp)).filter(
                extract('year', Images.timestamp) == y).filter(
                extract('month', Images.timestamp) == m).distinct(
                extract('day', Images.timestamp)).all()

            ret[y][m] = [d[0] for d in days]

    session.close()
    return jsonify(ret)


@app.route('/exif/filter/<key>/<value>')
def exif_filter(key, value):
    return
    # ret = None
    # session = app.config['SESSION']()

    # img = session.query(Images).filter

    # session.close()
    # return ret


@app.route('/ui/<path:path>')
def ui(path):
    return send_from_directory('static', path)


image_view = ImageView.as_view('images')

app.add_url_rule('/images/', view_func=image_view, methods=['POST', 'GET'])
app.add_url_rule('/images/<int:img_id>/', view_func=image_view,
                 methods=['GET'])
