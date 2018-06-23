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

function FillGallery() {
    year = $('#picker>[name="year"]').find(":selected").text();
    month = $('#picker>[name="month"]').find(":selected").text();
    day = $('#picker>[name="day"]').find(":selected").text();
    $.get(`/images/?year=${year}&month=${month}&day=${day}`, (d) => {
        $("#thumbnails").empty();
        for (var id in d) {
            img = d[id];
            $.get(img.url + "thumbnail/", (d) => {
                $("#thumbnails").append($('<img>').attr("src", d));
            });
        }
    });
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