import cStringIO
import os.path

from flask import Flask, request, jsonify, Response
from flask.views import MethodView
from PIL.Image import LANCZOS
from sqlalchemy import extract

from .models import Images, ExifData

app = Flask(__name__)


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
                except Exception:
                    fname = Images._try_get_name(f)
                    app.logger.error('Error Saving file filename=%s', fname)
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
            limit = min(int(request.args.get('limit', 50)), 100)
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

            a = q.offset(offset).limit(limit).all()

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
                height = int(height)
                scale = float(height) / float(h)
                width = int(scale * float(w))

            if height is None:
                width = int(width)
                scale = float(width) / float(w)
                height = int(scale * float(h))

            pimg = pimg.resize((width, height), LANCZOS)   
            buff = cStringIO.StringIO()
            pimg.save(buff, format=fmt)

            ret = Response(buff.getvalue(), status=200,
                           mimetype='image/{}'.format(fmt.lower()))

        session.close()
        return ret


@app.route('/filters/', methods=['GET'])
def filters():
    return ''


@app.route('/ui/<path:path>')
def ui(path):
    return send_from_directory('static', path)


image_view = ImageView.as_view('images')

app.add_url_rule('/images/', view_func=image_view, methods=['POST', 'GET'])
app.add_url_rule('/images/<int:img_id>/', view_func=image_view,
                 methods=['GET'])
