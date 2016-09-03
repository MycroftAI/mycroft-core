/*
 *  SEND {message_type: "mycroft.wifi.scan"}
 *  SEND {message_type: "mycroft.wifi.connect", metadata: {ssid: "", pass: ""}}
 *  LISTEN {message_type: "mycroft.wifi.connected", metadata: {connected: boolean}}
 *  LISTEN {message_type: "mycroft.wifi.scanned", metadata: {networks: Map<SSID, {quality: "Int/Int", encrypted: "boolean"}>>}}
 * */
function getImagePath(strength) {
    if (strength > 0.8) {
        return "img/wifi_4.png";
    } else if (strength > 0.6) {
        return "img/wifi_3.png";
    } else if (strength > 0.4) {
        return "img/wifi_2.png";
    } else if (strength > 0.2) {
        return "img/wifi_1.png";
    } else {
        return "img/wifi_0.png";
    }
}

var WifiSetup = {

    setListeners: function () {
        WS.addMessageListener("mycroft.wifi.connected", this.onConnected.bind(this));
        WS.addMessageListener("mycroft.wifi.scanned", this.onScanned.bind(this));
    },

    onConnected: function () {
        console.log("CONNECTED");
    },

    onScanned: function (data) {
        var networks = data.networks,
            fragment = document.createDocumentFragment(),
            list = document.querySelector("#list"),
            li = null,
            span = null,
            imgSignal = null,
            imgLock = null;

        Object.keys(networks).forEach(function (network) {
            li = document.createElement("li");
            span = document.createElement("span");
            imgSignal = document.createElement("img");
            span.textContent = network;
            imgSignal.src = getImagePath(networks[network].quality);
            imgSignal.className = "wifi";
            li.appendChild(span);
            li.appendChild(imgSignal);
            if (networks[network].encrypted) {
                imgLock = document.createElement("img");
                imgLock.src = "img/lock.png";
                imgLock.className = "lock";
                li.appendChild(imgLock);
            }
            fragment.appendChild(li);
        });

        list.innerHTML = null;
        list.appendChild(fragment);
    },

    sendScan: function () {
        WS.send("mycroft.wifi.scan");
    },

    /***
     * @param data is a object with ssid and pass
     */
    sendConnect: function (data) {
        WS.send("mycroft.wifi.connect", data);
    },

    showList: function () {

    },

    init: function () {
        this.setListeners();
        // this.sendScan();
    }
};

window.addEventListener("load", function () {
    WS.connect();
    WifiSetup.init();
});