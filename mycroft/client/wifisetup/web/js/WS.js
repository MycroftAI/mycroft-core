var WS = {
    ws: null,
    wsConnected: false,
    listeners: {},
    onOpenListeners: [],

    connect: function () {
        this.ws = new WebSocket(Config.wsUrl);
        this.setWSListeners();
    },

    setWSListeners: function () {
        this.ws.onmessage = this.onMessage.bind(this);
        this.ws.onopen = this.onOpen.bind(this);
    },

    setOnOpenListener: function (cb) {
        this.onOpenListeners.push(cb);
    },

    onMessage: function (evt) {
        var msg = JSON.parse(evt.data);
        if (this.listeners[msg.type]) {
            this.listeners[msg.type].forEach(function (cb) {
                cb(msg.data);
            });
        }
    },

    onOpen: function () {
        this.wsConnected = true;
        this.onOpenListeners.forEach(function (cb) {
            cb();
        });
    },

    send: function (type, data) {
        this.ws.send(JSON.stringify({
            type: type,
            data: data
        }));
    },

    close: function () {
        this.ws.close();
        this.wsConnected = false;
        this.ws = null;
    },

    addMessageListener: function (type, callback) {
        this.listeners[type] = this.listeners[type] || [];
        this.listeners[type].push(callback);
    }

};
