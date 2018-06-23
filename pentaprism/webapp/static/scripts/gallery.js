var dates = {};

function FillMonth() {
    year = $('#picker>[name="year"]').find(":selected").text();
    $('#picker>[name="month"]').empty();
    for (var month in dates[year]) {
        $('#picker>[name="month"]').append($('<option>', {
            value: month,
            text: month
        }));
    }
    FillDay();
}

function FillDay() {
    year = $('#picker>[name="year"]').find(":selected").text();
    month = $('#picker>[name="month"]').find(":selected").text();
    $('#picker>[name="day"]').empty();
    for (var day in dates[year][month]) {
        $('#picker>[name="day"]').append($('<option>', {
            value: dates[year][month][day],
            text: dates[year][month][day]
        }));
    }
    FillGallery();
}

function AddThumbnail(img) {
    return function (data) {
        $("#thumbnails").append(
            $("<a>").attr("onclick", `LoadImage("${img.url}")`).append(
                $("<img>").attr("src", data)
            )
        );
    };
};

function LoadImage(url) {
    $("#viewer").empty();
    $("#exif>dl").empty();
    
    image = new Image();
    image.src = url;
    
    $("#viewer").append(image);
    
    $.get(url + "exif/", function(data){
        for (var key in data) {
            $("#exif>dl").append($("<dt/>").text(key));
            $("#exif>dl").append($("<dd/>").text(data[key]));
        }
    });
}

function FillGallery() {
    year = $('#picker>[name="year"]').find(":selected").text();
    month = $('#picker>[name="month"]').find(":selected").text();
    day = $('#picker>[name="day"]').find(":selected").text();
    $.get(`/images/?year=${year}&month=${month}&day=${day}`, (data) => {
        $("#thumbnails").empty();
        for (var id in data) {
            img = data[id];
            $.get(img.url + "thumbnail/", AddThumbnail(img));
        }
    });
    $("#viewer").attr("src", "");
}

$(document).ready(function () {
    $.get('/dates/', (d) => {
        dates = d;
        $('#picker>[name="year"]').empty();
        for (var year in dates) {
            $('#picker>[name="year"]').append($('<option>', {
                value: year,
                text: year
            }));
        }
        FillMonth();
    });
});