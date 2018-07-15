var dates = {};
var LOADING_IMAGES = [];

function LoadImage(img_id, args) {
    return function() {
        if (LOADING_IMAGES.length > 0) {
            return;
        }
        
        image = new Image();
        LOADING_IMAGES.push(image);

        $(image).attr("class", "img-fluid");
        $("#viewer>.loading").show();
        
        $(image).on("load", function (e) {
            console.log(e.currentTarget.src);
            $("#viewer>img").replaceWith(e.currentTarget);
            $("#viewer>.loading").hide();
            LOADING_IMAGES.splice(LOADING_IMAGES.indexOf(e.currentTarget), 1);
        });
        
        image.src = `/images/${img_id}/?${args}`;
    };
}

function EnforceCropRules() {
    l = parseFloat($("#left").val());
    t = parseFloat($("#top").val());
    r = parseFloat($("#right").val());
    b = parseFloat($("#bottom").val());

    if (isNaN(l) && isNaN(t) && isNaN(r) && isNaN(b)) {
        return;
    }

    if (isNaN(l)) { l = 0; }
    if (isNaN(t)) { t = 0; }
    if (isNaN(r)) { r = 100; }
    if (isNaN(b)) { b = 100; }

    if (l < 0) { l = 0; } if (l > 99) { l = 99; }
    if (t < 0) { t = 0; } if (t > 99) { t = 99; }
    if (r <= l) { r = l + 1; } if (r > 100) { r = 100; }
    if (b <= t) { b = t + 1; } if (b > 100) { b = 100; }

    $("#left").val(l);
    $("#top").val(t);
    $("#right").val(r);
    $("#bottom").val(b);

    return [l, t, r, b];
}

function MakeArgsFromForm() {
    
    cr = $("#cr")[0].checked;
    crop = EnforceCropRules();
    format = $("select[name=format]").val();
    grid = $("select[name=grid]").val();
    h = $("#height").val();
    rot = $("#rot").val();
    w = $("#width").val();
    wb = $("select[name=wb]").val();
    
    args = {};
    if (!cr) {args["no-cr"] = "true";}
    if (crop != undefined) {args.crop = crop.join(',');}
    if (format != "") {args.format = format;}
    if (grid != "") {args.grid = grid;}
    if (h != "") {args.height = h;}
    if (rot != "0" && rot != "") {args.rotate = rot;}
    if (w != "") {args.width = w;}
    if (wb != "") {args.wb = wb;}

    args_lst = [];
    for (var k in args) {
        args_lst.push(`${k}=${args[k]}`);
    }

    return args_lst.join('&');
}

function ReloadOnChange() {
    LoadImage(ParseArgs().id, MakeArgsFromForm())();
}

function ClearCrop() {
    $("#left,#top,#right,#bottom").val("");
    ReloadOnChange();
}

$(document).ready(() => {
    ReloadOnChange();
    changable = ["select[name=wb]", "#width", "#height", "#left", "#right",
        "#top", "#bottom", "select[name=format]", "#cr", "select[name=grid]"];
    $(changable.join(",")).change(ReloadOnChange);
    $('#rot').slider().on('slideStop', ReloadOnChange);
});
