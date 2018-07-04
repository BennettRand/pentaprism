var dates = {};

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
        $(`#thumbnails>[name="${img.name}"]`).prepend(
            $("<img>")
            .attr("src", data)
            .attr("class", "figure-img img-fluid rounded")
            .attr("alt", img.name)
            .attr("onclick", `LoadImage("${img.url}")`)
        );
    };
};

function LoadImage(url) {
    $("#viewer").empty();
    $("#exif>tbody").empty();
    
    image = new Image();
    image.src = url;
    
    $("#viewer").append(image);
    $("#viewer>img").attr("class", "img-fluid");
    
    $.get(url + "exif/", function(data){
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
        $("#thumbnails").empty();
        for (var id in data) {
            img = data[id];
            $("#thumbnails").append(
                $("<figure>").attr("class", "figure").attr("name", img.name).append(
                    $("<figcaption>").attr("class", "figure-caption text-center").text(img.name)
                )
            );
            $.get(img.url + "thumbnail/", AddThumbnail(img));
        }
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
    });
});

window.onpopstate = (event) => {
    _fillGallery(event.state.year, event.state.month, event.state.day);
}
