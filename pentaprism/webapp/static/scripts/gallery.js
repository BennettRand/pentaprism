var dates = {};
var LOADING_IMAGES = [];

function FillYear(fill = false) {
    $('#picker>[name="year"]').empty();
    for (var year in dates) {
        $('#picker>[name="year"]').append($('<option>', {
            value: year,
            text: year
        }));
    }
    FillMonth(fill);
}

function FillMonth(fill = false) {
    year = $('#picker>[name="year"]').find(":selected").text();
    $('#picker>[name="month"]').empty();
    for (var month in dates[year]) {
        $('#picker>[name="month"]').append($('<option>', {
            value: month,
            text: month
        }));
    }
    FillDay(fill);
}

function FillDay(fill = false) {
    year = $('#picker>[name="year"]').find(":selected").text();
    month = $('#picker>[name="month"]').find(":selected").text();
    $('#picker>[name="day"]').empty();
    for (var day in dates[year][month]) {
        $('#picker>[name="day"]').append($('<option>', {
            value: dates[year][month][day],
            text: dates[year][month][day]
        }));
    }
    if (fill) {
        FillGallery();
    }
}

function AddThumbnail(img) {
    return function (data) {
        $(`#thumbnails>[name="${img.name}"]`).append(
            $("<img>")
            .attr("src", data)
            .attr("class", "figure-img rounded")
            .attr("alt", img.name)
            .click(LoadImage(img, data))
        );
    };
};

function getAllEvents(element) {
    var result = [];
    for (var key in element) {
        if (key.indexOf('on') === 0) {
            result.push(key.slice(2));
        }
    }
    return result.join(' ');
}

function LoadImage(img, data) {
    return function() {
        if (LOADING_IMAGES.length > 0) {
            return;
        }
        $("#viewer")[0].loaded_img = img;
        links = img.links;
        
        image = new Image();
        LOADING_IMAGES.push(image);
        temp_image = new Image();
        
        temp_image.src = data;
        $(image).attr("class", "img-fluid");
        
        $("#viewer>a>img").replaceWith(temp_image);
        $("#viewer>.loading").show();
        $("#viewer>a").attr("href", `/ui/editor.html?id=${img.id}`);
        
        $(image).on("load", function (e) {
            console.log(e.currentTarget.src);
            $("#viewer>a>img").replaceWith(e.currentTarget);
            LOADING_IMAGES.splice(LOADING_IMAGES.indexOf(e.currentTarget), 1);
            $("#viewer>.loading").hide();
        });
        
        image.src = links.image + "?half-size=true&wb=camera";
        
        $.get(links.exif, function(data){
            $("#exif>tbody").empty();
            for (var key in data) {
                $("#exif>tbody").append(
                    $("<tr>").append(
                        $("<th>").attr("scope", "row").text(key)
                    ).append(
                        $("<td>").text(data[key])
                    )
                );
            }
        });
    };
}

function LoadRelative(delta) {
    curr_idx = $('#thumbnails')[0].gallery.indexOf($('#viewer')[0].loaded_img);
    next_idx = curr_idx + delta;
    if (next_idx < 0 || next_idx >= $('#thumbnails')[0].gallery.length) {
        return;
    }
    img = $('#thumbnails')[0].gallery[next_idx];
    data = $('#thumbnails>figure')[next_idx].getElementsByTagName('IMG')[0].src;
    LoadImage(img, data)();
}

function NextImage() {
    LoadRelative(1);
}

function PrevImage() {
    LoadRelative(-1);
}

function FillGallery() {
    year = $('#picker>[name="year"]').find(":selected").text();
    month = $('#picker>[name="month"]').find(":selected").text();
    day = $('#picker>[name="day"]').find(":selected").text();
    _fillGallery(year, month, day);
}

function FillGalleryFromArgs() {
    args = ParseArgs();
    if ('year' in args) {
        $('#picker>[name="year"]').val(args.year);
        FillMonth();

        if ('month' in args) {
            $('#picker>[name="month"]').val(args.month);
            FillDay();

            if ('day' in args) {
                $('#picker>[name="day"]').val(args.day);
                _fillGallery(args.year, args.month, args.day);
            }
        }
    } else {
        FillGallery();
    }
}

function _fillGallery(year, month, day) {
    curr_path = window.location.pathname.split('/');

    query = `?year=${year}&month=${month}&day=${day}`;
    new_path = curr_path[curr_path.length - 1] + query;

    history.pushState({
        year: year,
        month: month,
        day: day
    }, document.title, new_path);

    $.get(`/images/${query}`, (data) => {
        $("#thumbnails")[0].gallery = data;
        $("#thumbnails").empty();
        for (var id in data) {
            img = data[id];
            $("#thumbnails").append(
                $("<figure>").attr("class", "figure").attr("name", img.name).append(
                    $("<figcaption>").attr("class", "figure-caption text-center").text(img.name)
                )
            );
            $.get(img.links.thumbnail, AddThumbnail(img));
        }
        $.get(data[0].links.thumbnail, (thumb) => {
            LoadImage(data[0], thumb)();
        });
    });
    // $("#viewer").attr("src", "");
}

$(document).ready(() => {
    $.get('/dates/', (d) => {
        dates = d;
        FillYear();
        FillGalleryFromArgs();
        $('#picker>[name="year"]').change(FillMonth);
        $('#picker>[name="month"]').change(FillDay);
        $('#picker>[name="day"]').change(FillGallery);
        $('#viewer>.next').click(NextImage);
        $('#viewer>.prev').click(PrevImage);
    });
    $(document).keydown(function (e) {
        switch (e.which) {
            case 37: // left
            PrevImage();
            break;

            case 39: // right
            NextImage();
            break;

            default: return; // exit this handler for other keys
        }
        e.preventDefault();
    });
});

window.onpopstate = (event) => {
    _fillGallery(event.state.year, event.state.month, event.state.day);
}
