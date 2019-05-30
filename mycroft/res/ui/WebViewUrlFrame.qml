import QtQuick 2.4
import QtQuick.Controls 2.2
import QtWebEngine 1.8
import QtQuick.Controls 2.0
import org.kde.kirigami 2.4 as Kirigami

Item {
    id: root
    property var pageUrl: webViewUrlLoader.pageUrl
    
    onPageUrlChanged: {
        if(typeof pageUrl !== "undefined" || typeof pageUrl !== null){
            webview.url = pageUrl
        }
    }
    
    WebEngineView {
        id: webview
        anchors.fill: parent
        settings.autoLoadImages: true
        settings.javascriptEnabled: true
        settings.errorPageEnabled: true
        settings.pluginsEnabled: true
        settings.allowWindowActivationFromJavaScript: true
        settings.javascriptCanOpenWindows: true
        settings.fullScreenSupportEnabled: true
        settings.autoLoadIconsForPage: true
        settings.touchIconsEnabled: true
        settings.webRTCPublicInterfacesOnly: true
        
        onNewViewRequested: function(request) {
            if (!request.userInitiated) {
                console.log("Warning: Blocked a popup window.");
            } else if (request.destination === WebEngineView.NewViewInDialog) {
                popuproot.open()
                request.openIn(popupwebview);
            } else {
                request.openIn(webview);
            }
        }
        
        onJavaScriptDialogRequested: function(request) {
            request.accepted = true;
        }
    }
    
    Popup {
        id: popuproot
        modal: true
        focus: true
        width: root.width - Kirigami.Units.largeSpacing * 1.25
        height: root.height - Kirigami.Units.largeSpacing * 1.25
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
        anchors.centerIn: parent
        
        WebEngineView {
            id: popupwebview
            anchors.fill: parent
            url: "about:blank"
            settings.autoLoadImages: true
            settings.javascriptEnabled: true
            settings.errorPageEnabled: true
            settings.pluginsEnabled: true
            settings.allowWindowActivationFromJavaScript: true
            settings.javascriptCanOpenWindows: true
            settings.fullScreenSupportEnabled: true
            settings.autoLoadIconsForPage: true
            settings.touchIconsEnabled: true
            settings.webRTCPublicInterfacesOnly: true
            property string urlalias: popupwebview.url
            
            onNewViewRequested: function(request) {
                console.log(request.destination)
            }
        }
    }
} 
