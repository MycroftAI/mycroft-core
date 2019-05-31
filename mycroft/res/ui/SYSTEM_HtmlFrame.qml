import QtQuick.Layouts 1.4
import QtQuick 2.4
import QtQuick.Controls 2.0
import org.kde.kirigami 2.4 as Kirigami

import Mycroft 1.0 as Mycroft

Mycroft.Delegate {
    id: systemHtmlFrame
    skillBackgroundColorOverlay: "#000000"
        
    Loader {
        id: webViewHtmlLoader
        source: "WebViewHtmlFrame.qml"
        anchors.fill: parent
        property var pageHtml: sessionData.html
        property var resourceLocation: sessionData.resourceLocation
    }
}
 
