function UploadFiles() {
    files = $("#files")[0].files;
    $("#progresses").empty();
    for (var f = 0; f < files.length; f++) {
        file = $("#files")[0].files[f];
        pdiv = $("#progresses").append($("<div />"));
        upload = function (img_file, pdiv) {
            var plabel = $("<label />");
            var pbar = $("<progress />");
            plabel.text(img_file.name);
            pdiv.append(plabel);
            plabel.append(pbar);

            var fdata = new FormData();
            fdata.append('', img_file);
            
            var pbar_progress = function (e) {
                if (e.lengthComputable) {
                    pbar.attr({
                        value: e.loaded,
                        max: e.total,
                    });
                }
            };

            var pbar_done = function (data, s, j) {
                if (data.saved.length == 1) {
                    plabel.text(`${img_file.name} Done`);
                }
                else if (data.skipped.length == 1) {
                    plabel.text(`${img_file.name} Skipped`);
                }
                else if (data.errored.length == 1) {
                    plabel.text(`${img_file.name} ERROR`);
                }
                else {
                    plabel.text(`${img_file.name} !!!`);
                    console.log(j);
                }
            };

            var pbar_error = function (e) {
                plabel.text(`${img_file.name} ABORTED`);
            };
            
            $.ajax({
                // Your server script to process the upload
                url: '/images/',
                type: 'POST',
        
                // Form data
                data: fdata,
        
                // Tell jQuery not to process data or worry about content-type
                // You *must* include these options!
                cache: false,
                contentType: false,
                processData: false,
                
                success: pbar_done,
                error: pbar_error,
        
                // Custom XMLHttpRequest
                xhr: function () {
                    var myXhr = new XMLHttpRequest(); //$.ajaxSettings.xhr();
                    if (myXhr.upload) {
                        myXhr.upload.addEventListener('progress', pbar_progress, false);
                        // myXhr.upload.addEventListener("load", pbar_done);
                        // myXhr.upload.addEventListener("error", pbar_error);
                        // myXhr.upload.addEventListener("abort", pbar_error);
                    }
                    return myXhr;
                }
            });
        }
        upload(file, pdiv);
    }
}