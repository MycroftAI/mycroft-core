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

function showPanel(id) {
    var panels = document.querySelectorAll(".panel");

    for (var i=0; i < panels.length; i++)
        panels[i].classList.add("hide");

    document.querySelector("#" + id).classList.remove("hide");
}

var WifiSetup = {

        selectedNetword: null,

        setListeners: function () {
            WS.addMessageListener("mycroft.wifi.connected", this.onConnected.bind(this));
            WS.addMessageListener("mycroft.wifi.scanned", this.onScanned.bind(this));
        },

        onConnected: function (data) {
            if (data.connected) {
                // NOTE:  Once we send the "mycroft.wifi.stop", the unit will
                // be shutting down the wifi access point.  So the device
                // hosting the browser session is probably being disconnected
                // and hopefully automatically reconnecting to the internet.
                //
                // Until the reconnect happens, the user cannot actually
                // follow the link to http://home.mycroft.ai to register
                // their device.  That is part of why we are doing this 2 sec
                // delay.
                //
                WS.send("mycroft.wifi.stop");
                WS.close();

                setTimeout(function () {
                    var btnCancel = document.querySelector("#cancelBtn");
                    btnCancel.classList.add("hide");

                    showPanel("success");
                    startPing();
                }, 2000);
            } else {
                showPanel("list-panel");
                this.renderErrorItem(this.selectedNetword.el);
            }
        },

        onScanned: function (data) {
            var networks = data.networks,
                fragment = document.createDocumentFragment(),
                list = document.querySelector("#list"),
                item = null,
                li = null;

            showPanel("list-panel");

            Object.keys(networks).sort(function (a, b) {
                if (networks[a].quality < networks[b].quality) {
                    return 1;
                }
                return 0;
            }).forEach(function (network) {
                li = document.createElement("li");
                networks[network].ssid = network;
                networks[network].el = li;
                item = this.renderListItem(networks[network]);
                li.appendChild(item);
                fragment.appendChild(li);
            }.bind(this));

            list.innerHTML = null;
            list.appendChild(fragment);
        },

        renderListItem: function (network) {
            var listItem = document.createElement("div"),
                span = document.createElement("span"),
                imgSignal = document.createElement("img");
            listItem.className = "list-item show";
            span.textContent = network.ssid;
            span.className = "ssid";
            imgSignal.src = getImagePath(network.quality);
            imgSignal.className = "wifi";
            listItem.appendChild(span);
            listItem.appendChild(imgSignal);
            if (network.connected) {
                var connected = document.createElement("span");
                connected.className = "connected";
                connected.textContent = "Connected";
                listItem.classList.add("connected");
                listItem.appendChild(connected);
            } else {
                listItem.addEventListener("click", this.clickNetwork.bind(this, network));
            }
            if (network.encrypted) {
                var imgLock = document.createElement("img");
                imgLock.src = "img/lock.png";
                imgLock.className = "lock";
                listItem.appendChild(imgLock);
            }
            return listItem;
        },

        ItemDefaultState: function () {
            var li = document.querySelector(".list-item:not(.show)");
            if (!li) {
                return;
            }
            var divs = li.parentNode.childNodes;

            Object.keys(divs).forEach(function (div) {
                divs[div].classList.remove("show");
                if (divs[div].classList.contains("list-item")) {
                    divs[div].classList.add("show");
                }
            });
        },

        renderConnectItem: function (li) {
            var connect = li.querySelector(".connect-item");
            if (!connect) {
                connect = document.createElement("div");
                var imgArrow = document.createElement("img");
                var label = document.createElement("label");
                connect.className = "connect-item";
                imgArrow.src = "img/next.png";
                imgArrow.addEventListener("click", this.clickConnect.bind(this));
                connect.appendChild(label);
                if (this.selectedNetword.encrypted) {
                    connect.passwordInput = document.createElement("input");
                    label.textContent = "Password: ";
                    connect.passwordInput.type = "password";
                    connect.appendChild(connect.passwordInput);
                } else {
                    label.className = "public";
                    label.textContent = this.selectedNetword.ssid;
                }
                connect.appendChild(imgArrow);

                li.appendChild(connect);
	    }
            li.querySelector(".list-item").classList.remove("show");
            connect.classList.add("show");
            if ('passwordInput' in connect)
		    connect.passwordInput.focus();
        },

        renderErrorItem: function (li) {
            var error = li.querySelector(".error-item");
            if (error) {
                li.querySelector(".connect-item").classList.remove("show");
                error.classList.add("show");
                return;
            }
            error = document.createElement("div");
            var imgClose = document.createElement("img");
            error.classList.add("error-item");
            imgClose.src = "img/error.png";
            var message = document.createElement("span");
            message.textContent = "Try again or connect to a diferent wifi.";
            error.appendChild(message);
            error.appendChild(imgClose);
            li.appendChild(error);
            li.querySelector(".connect-item").classList.remove("show");
            error.classList.add("show");
            error.addEventListener("click", this.ItemDefaultState);
        },

        clickNetwork: function (network) {
            this.selectedNetword = network;
            this.ItemDefaultState();
            this.renderConnectItem(network.el);
        }
        ,

        sendScan: function () {
            showPanel("loading");
            document.querySelector("#cancelBtn").classList.remove("hide");
            WS.send("mycroft.wifi.scan");
        }
        ,

        /***
         * @param data is a object with ssid and pass
         */
        sendConnect: function (data) {
            WS.send("mycroft.wifi.connect", data);
        }
        ,

        clickConnect: function () {
            showPanel("connecting");
            var network = {
                ssid: this.selectedNetword.ssid
            };
            if (this.selectedNetword.encrypted) {
                var pass = this.selectedNetword.el.querySelector("input");
                network.pass = pass.value;
            }
            this.sendConnect(network);
        }
        ,

        cancelSetup: function () {
            WS.send("mycroft.wifi.stop");
            WS.close();
        }
        ,

        init: function () {
            this.setListeners();
            showPanel("home");
            document.querySelector("#connectBtn").addEventListener("click", this.sendScan);
            document.querySelector("#registerBtn").addEventListener("click", function () {
                setTimeout(function() {
                    location.href="https://home.mycroft.ai";
                }, 2000);
            });
            document.querySelector("#cancelBtn").addEventListener("click", this.cancelSetup);
        }
    };

function startPing() {
    ping("home.mycroft.ai",
        function(status,e) {
            if (status == 'responded') {
                // Un-hide the register button once we detect an
                // active internet connection.
                document.querySelector("#registerBtn").classList.remove("hide");
            }
            else
                setTimeout(function() { startPing(); }, 1000);
        });
}

function ping(domain, callback) {
    if (!this.inUse) {
        this.status = 'unchecked';
        this.inUse = true;
        this.callback = callback;
        this.ip = domain;
        var _that = this;
        this.img = new Image();
        this.img.onload = function () {
            _that.inUse = false;
            _that.callback('responded');

        };
        this.img.onerror = function (e) {
            if (_that.inUse) {
                _that.inUse = false;
                _that.callback('responded', e);
            }

        };
        this.start = new Date().getTime();
        this.img.src = "http://" + domain;
        this.timer = setTimeout(function () {
            if (_that.inUse) {
                _that.inUse = false;
                _that.callback('timeout');
            }
        }, 1500);
    }
}

window.addEventListener("load", function () {
    WS.connect();
    WS.setOnOpenListener(function () {
        WifiSetup.init();
    });
});
