const instance = axios.create({
    baseURL: '/'
});

Vue.component('file-upload', {
    props: ['name'],
    data: function () {
        return {
            max: 100,
            value: 0,
            thumb: "",
            error: ""
        }
    },
    template: `<div class="file">
    <span>{{ name }}</span>
    <progress v-bind:max="max" v-bind:value="value"/>
    <img v-bind:src="thumb" />
    <p>{{ error }}</p>
</div>`
});

const progresses = new Vue({
    el: '#progresses',
    data: {
        files: []
    }
});

function ThumbnailFill(idx, id) {
    instance.get(`/images/${id}/thumbnail/`)
        .then((response) => {
            progresses.$children[idx].thumb = response.data;
        })
        .catch((error) => {
            console.log(error);
        });
}

function UploadFiles() {
    $("#upload_button").attr("disabled", true);
    files = $("#files")[0].files;

    requests = [];
    name_map = {};

    progresses.files.splice(0, progresses.files.length);

    for (var f = 0; f < files.length; f++) {
        let file = $("#files")[0].files[f];

        let fdata = new FormData();
        fdata.append('', file);

        let this_idx = progresses.files.push({
            name: file.name
        }) - 1;

        req = instance.post('images/', fdata, {
            onUploadProgress: (progressEvent) => {
                progresses.$children[this_idx].max = progressEvent.total;
                progresses.$children[this_idx].value = progressEvent.loaded;
            }
        })
            .then((response) => {
                console.log(response);
                if (response.data.saved.includes(file.name)) {
                    progresses.$children[this_idx].error = "";
                    ThumbnailFill(this_idx, response.data.thumbnails[file.name]);
                } else if (response.data.skipped.includes(file.name)) {
                    progresses.$children[this_idx].error = "Skipped";
                    progresses.$children[this_idx].thumb = "";
                } else if (response.data.errored.includes(file.name)) {
                    progresses.$children[this_idx].error = "ERROR";
                    progresses.$children[this_idx].thumb = "";
                } else {
                    progresses.$children[this_idx].error = "!!!";
                    progresses.$children[this_idx].thumb = "";
                }
            })
            .catch((error) => {
                console.log(error);
            });

        requests.push(req);
    }
    axios.all(requests)
        .then((result) => {
            console.log(result);
            $("#upload_button").attr("disabled", false);
        });
}