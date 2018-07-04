function ParseArgs(map = {}) {
    args = {};
    window.location.search.substr(1).split('&').forEach(function (e, i, a) {
        kv = e.split('=');
        if (kv[0] in map) {
            args[kv[0]] = map[kv[0]](kv[1]);
        } else {
            args[kv[0]] = kv[1];
        }
    });
    return args;
}