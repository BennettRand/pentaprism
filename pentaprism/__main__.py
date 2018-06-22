from .webapp import app


def main():

    # f = open(r'\\TURING\Minio_Storage\photos\2018\05-may\19\IMGP5894.DNG',
    #          'rb')
    # img = rawfile.RawImg(f)

    # imgs = []

    # img_dir = os.walk(r'\\TURING\Minio_Storage\photos\2018\05-may\19').next()
    # for img in [x for x in img_dir[2] if x.endswith('.DNG')]:
    #     f = open(os.path.join(img_dir[0], img), 'rb')
    #     img = rawfile.RawImg(f)
    #     im_model = Images(filename=os.path.split(img.file.name)[-1],
    #                       filepath=img.timestamp().strftime('%Y/%m-%b/%d'),
    #                       timestamp=img.timestamp())

    #     # im_model.thumbnail = Thumbnails(data=img.thumbnail())

    #     for k, v in img.exif.items():
    #         im_model.exif.append(ExifData(key=k, value=v.printable))

    #     session.add(im_model)
    #     session.commit()
    app.run(host='0.0.0.0')

    return


if __name__ == '__main__':
    main()
