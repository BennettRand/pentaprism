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
            RecalcTriangles(e.currentTarget);
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

function MakeArgsFromForm(full=false) {
    
    abthr = $("#abthr").val();
    black = $("#black").val();
    bright = $("#bright").val();
    cr = $("#cr")[0].checked;
    crop = EnforceCropRules();
    demosaic = $("select[name=demosaic]").val();
    exp = $("#exp").val();
    exppre = $("#exppre").val();
    format = $("select[name=format]").val();
    grid = $("select[name=grid]").val();
    gp = $("#gpower").val();
    gs = $("#gslope").val();
    h = $("#height").val();
    half = $("#half")[0].checked;
    nab = $("#nautobright")[0].checked;
    nas = $("#nautoscale")[0].checked;
    rot = $("#rot").val();
    sat = $("#sat").val();
    w = $("#width").val();
    wb = $("select[name=wb]").val();
    
    args = {};
    if (abthr != "0.00003" && abthr != "") { args['auto-bright-thr'] = abthr;}
    if (exppre != "" && exppre != "0") { args['exp-preserve'] = exppre;}
    if (black != "") {args.black = black;}
    if (bright != "") { args.bright = bright;}
    if (!cr) {args["no-cr"] = "true";}
    if (crop != undefined) {args.crop = crop.join(',');}
    if (demosaic != "") { args.demosaic = demosaic;}
    if (exp != "1" && exp != "") { args.exp = exp;}
    if (format != "") {args.format = format;}
    // if (grid != "") {args.grid = grid;}
    if ((gp != "2.2" || gs != "4.5") && gp != "" && gs != "") {args.gamma = `${gp},${gs}`;}
    if (h != "") {args.height = h;}
    if (half) {args["half-size"] = "true";}
    if (nab) {args["no-auto-bright"] = "true";}
    if (nas) {args["no-auto-scale"] = "true";}
    if (rot != "0" && rot != "") {args.rotate = rot;}
    if (sat != "") { args.saturation = sat;}
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

function RecalcTriangles(image) {
    w = image.parentElement.clientWidth;
    h = image.parentElement.clientHeight;
    diag = Math.sqrt(w * w + h * h);
    alt = (w * h) / diag
    d2 = Math.cos(Math.atan(h / w)) * w
    d1 = diag - d2
    l = d1 * alt / h
    b = d2 * alt / w

    left = `${l / w * 100}%`;
    right = `${b / h * 100}%`;

    $('.triangles1>line.left').attr('x2', left);
    $('.triangles1>line.left').attr('y2', left);
    $('.triangles1>line.right').attr('x2', right);
    $('.triangles1>line.right').attr('y2', right);

    $('.triangles2>line.left').attr('x2', left);
    $('.triangles2>line.left').attr('y2', right);
    $('.triangles2>line.right').attr('x2', right);
    $('.triangles2>line.right').attr('y2', left);
}

function SwitchGrid(e) {
    grid = e.currentTarget.value;
    $(".thirds,.triangles1,.triangles2").hide();
    if (grid != '') {
        $(`.${grid}`).show();
    }
}

function ClearCrop() {
    $("#left,#top,#right,#bottom").val("");
    ReloadOnChange();
}

$(document).ready(() => {
    ReloadOnChange();
    changable = ["select[name=wb]", "#width", "#height", "#left", "#right",
        "#top", "#bottom", "select[name=format]", "#cr", 
        "#black", "#bright", "#sat", "select[name=demosaic]", "#half",
        "#nautoscale", "#nautobright"];
    $(changable.join(",")).change(ReloadOnChange);
    $("select[name=grid]").change(SwitchGrid);
    $('#rot').slider({ tooltip: 'hide' }).on("slide", function (e) {
        $("#rotlabel").text(e.value);
        w = $('#viewer>img')[0].clientWidth;
        h = $('#viewer>img')[0].clientHeight;
        rad = parseFloat(e.value) * (Math.PI / 180);
        rot = Math.abs(rad);
        c = Math.cos(rot);
        s = Math.sin(rot);
        d = Math.sqrt(w * w + h * h);
        new_w = (h * s + w * c) / w;
        new_h = (h * c + w * s) / h;
        scale = Math.max(new_w, new_h);
        console.log(scale);
        $('#viewer>img').attr('style', `transform: rotate(${rad}rad) scale(${scale}, ${scale});`);
    });
    $('#gpower').slider({ tooltip: 'hide' }).on('slideStop', ReloadOnChange).on("slide", function (e) {
        $("#gpowlabel").text(e.value);
    });
    $('#gslope').slider({ tooltip: 'hide' }).on('slideStop', ReloadOnChange).on("slide", function (e) {
        $("#gslplabel").text(e.value);
    });
    $('#abthr').slider({ tooltip: 'hide' }).on('slideStop', ReloadOnChange).on("slide", function (e) {
        $("#abthrlabel").text(e.value);
    });
    $('#exppre').slider({ tooltip: 'hide' }).on('slideStop', ReloadOnChange).on("slide", function (e) {
        $("#expprelabel").text(e.value);
    });
    $('#exp').slider({ tooltip: 'hide' }).on('slideStop', ReloadOnChange).on("slide", function (e) {
        $("#explabel").text(e.value);
    });
    $(".thirds,.triangles1,.triangles2").hide();
});
