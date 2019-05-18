import os.path
from io import BytesIO

from flask import Flask, request, jsonify, Response, send_from_directory
from flask.views import MethodView
from flask_basicauth import BasicAuth
from rawpy import DemosaicAlgorithm
from sqlalchemy import extract

from .models import Images, ExifData
from ..color import wb_to_mul

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
        saved = set()
        skipped = set()
        errored = set()
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
                        saved.add(rimg.filename)
                        thumbnails.append((rimg.filepath, rimg.filename))
                        app.logger.info('Saved File filename=%s',
                                        rimg.filename)
                    else:
                        skipped.add(rimg.filename)
                except Exception as e:
                    fname = Images._try_get_name(f)
                    app.logger.error('Error Saving file filename=%s error=%s',
                                     fname, e)
                    errored.add(fname)

        session.add_all(images)
        session.commit()
        session.close()

        thumb_map = {}
        map_res = app.config['THREADPOOL'].starmap(
            Images.make_thumbnail, ((t, app) for t in thumbnails))
        for t, r in zip(thumbnails, map_res):
            if r is None:
                saved.remove(t[1])
                errored.add(t[1])
            else:
                thumb_map[t[1]] = r

        ret = jsonify(saved=list(saved),
                      skipped=list(skipped),
                      errored=list(errored),
                      thumbnails=thumb_map)
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

            ret = [{'id': i.id,
                    'name': i.filename,
                    'timestamp': i.timestamp.isoformat(),
                    'links': {'image': '/images/{}/'.format(i.id),
                              'exif': '/images/{}/exif/'.format(i.id),
                              'thumbnail': '/images/{}/thumbnail/'.format(i.id)}
                    } for i in a]
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

            width = request.args.get('width', None)
            height = request.args.get('height', None)
            crop = request.args.get('crop', None)
            rot = request.args.get('rotate', 0)
            fmt = request.args.get('format', 'JPEG')
            grid = request.args.get('grid', '')
            no_cr = request.args.get('no-cr', 'false') == 'true'
            full_render = request.args.get('full', None) == 'true'

            pp_args = {'auto_bright_thr': 0.00003}

            if 'half-size' in request.args:
                pp_args['half_size'] = request.args['half-size'] == 'true'
            if 'wb' in request.args:
                wb_mode = request.args['wb']
                if wb_mode == 'camera':
                    pp_args['use_camera_wb'] = True
                elif wb_mode == 'auto':
                    pp_args['use_auto_wb'] = True
                else:
                    t, g, e = [float(p) for p in wb_mode.split(',')]
                    pp_args['user_wb'] = wb_to_mul(t, g, e)

            pp_args['demosaic_algorithm'] = {
                'linear': DemosaicAlgorithm.LINEAR,
                'vng': DemosaicAlgorithm.VNG,
                'ppg': DemosaicAlgorithm.PPG,
                'ahd': DemosaicAlgorithm.AHD,
                'dcb': DemosaicAlgorithm.DCB,
                # 'modified_ahd': DemosaicAlgorithm.MODIFIED_AHD,
                # 'afd': DemosaicAlgorithm.AFD,
                # 'vcd': DemosaicAlgorithm.VCD,
                # 'vcd_modified_ahd': DemosaicAlgorithm.VCD_MODIFIED_AHD,
                # 'lmmse': DemosaicAlgorithm.LMMSE,
                # 'amaze': DemosaicAlgorithm.AMAZE,
                'dht': DemosaicAlgorithm.DHT,
                'aahd': DemosaicAlgorithm.AAHD,
            }.get(request.args.get('demosaic', 'dht'),
                  DemosaicAlgorithm.DHT)

            if 'black' in request.args:
                pp_args['user_black'] = int(request.args['black'])

            if 'saturation' in request.args:
                pp_args['user_sat'] = int(request.args['saturation'])

            if 'no-auto-scale' in request.args:
                pp_args['no_auto_scale'] = request.args['no-auto-scale'] == 'true'

            if 'no-auto-bright' in request.args:
                pp_args['no_auto_bright'] = request.args['no-auto-bright'] == 'true'

            if 'auto-bright-thr' in request.args:
                pp_args['auto_bright_thr'] = float(
                    request.args['auto-bright-thr'])

            if 'bright' in request.args:
                pp_args['bright'] = float(request.args['bright'])

            if 'exp' in request.args:
                pp_args['exp_shift'] = float(request.args['exp'])

            if 'exp-preserve' in request.args:
                pp_args['exp_preserve_highlights'] = float(
                    request.args['exp-preserve'])

            if 'gamma' in request.args:
                power, slope = request.args['gamma'].split(',')
                pp_args['gamma'] = (float(power), float(slope))

            # if 'chromatic-aberration' in request.args:
            #     red_s, blue_s = request.args['chromatic-aberration'].split(',')
            #     pp_args['chromatic_aberration'] = (float(red_s), float(blue_s))

            watermark = None
            if not no_cr:
                watermark = img.get_copyright()

            if width is None and height is None:
                width = 1280

            if crop is not None:
                crop = tuple([float(x) for x in crop.split(',')])

            pimg = img.pil_image(pp_args=pp_args, watermark=watermark,
                                 width=width, height=height, crop=crop,
                                 rotate=rot)

            if grid == 'thirds':
                pimg = Images.draw_thirds(pimg, 3)
            elif grid == 'triangles1':
                pimg = Images.draw_triangles1(pimg, 3)
            elif grid == 'triangles2':
                pimg = Images.draw_triangles2(pimg, 3)

            buff = BytesIO()
            pimg.save(buff, format=fmt)

            ret = Response(buff.getvalue(), status=200,
                           mimetype='image/{}'.format(fmt.lower()))

            if full_render:
                cd = 'attachment; filename="{}.{}"'.format(
                    img.filename, fmt.lower())
                ret.headers['Content-Disposition'] = cd

        session.close()
        return ret


@app.route('/images/<int:img_id>/thumbnail/')
def thumbnail(img_id):
    ret = None
    session = app.config['SESSION']()

    img = session.query(Images).get(img_id)

    if img is None or img.thumbnail is None:
        ret = jsonify(error='Not found', id=img_id)
        ret.status_code = 404
        return ret

    image_data = img.thumbnail.data
    if isinstance(image_data, bytes):
        image_data = image_data.decode('utf-8')
    ret = 'data:image/jpeg;base64,{}'.format(image_data)

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
        y = int(y[0])
        ret[y] = {}
        months = session.query(
            extract('month', Images.timestamp)).filter(
            extract('year', Images.timestamp) == y).distinct(
            extract('month', Images.timestamp)).all()

        for m in months:
            m = int(m[0])
            days = session.query(
                extract('day', Images.timestamp)).filter(
                extract('year', Images.timestamp) == y).filter(
                extract('month', Images.timestamp) == m).distinct(
                extract('day', Images.timestamp)).all()

            ret[y][m] = [int(d[0]) for d in days]

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


@app.route('/images/<int:img_id>/size/', methods=['GET'])
def size_of_img(img_id):
    session = app.config['SESSION']()
    img = session.query(Images).get(img_id)
    if img is None:
        ret = jsonify(error='Not found', id=img_id)
        ret.status_code = 404
        return ret

    img._im = None
    img.file = open(os.path.join(app.config['BASE_PATH'], img.filepath,
                                 img.filename), 'rb')

    pimg = img.pil_image(pp_args={
        'half_size': True,
        'demosaic_algorithm': DemosaicAlgorithm.LINEAR})

    width, height = pimg.size

    return jsonify(width=width * 2, height=height * 2)

    session.close()


@app.route('/ui/<path:path>')
def ui(path):
    return send_from_directory('static', path)


image_view = ImageView.as_view('images')

app.add_url_rule('/images/', view_func=image_view, methods=['POST', 'GET'])
app.add_url_rule('/images/<int:img_id>/', view_func=image_view,
                 methods=['GET'])
