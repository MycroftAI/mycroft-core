var WS = {
    ws: null,
    wsConnected: false,
    listeners: {},

    connect: function () {
        this.ws = new WebSocket(Config.wsUrl);
        this.setWSListeners();
    },

    setWSListeners: function () {
        this.ws.onmessage = this.onMessage.bind(this);
        this.ws.onopen = this.onOpen.bind(this);
    },

    onMessage: function (evt) {
        if (this.listeners[evt.message_type]) {
            this.listeners[evt.message_type].forEach(function (cb) {
                cb(evt.metadata);
            });
        }
    },

    onOpen: function () {
        this.wsConnected = true;
    },

    send: function (title, data) {
        this.ws.send({
            message_title: title,
            metadata: data
        });
    },

    addMessageListener: function (title, callback) {
        this.listeners[title] = this.listeners[title] || [];
        this.listeners[title].push(callback);
    }

};
