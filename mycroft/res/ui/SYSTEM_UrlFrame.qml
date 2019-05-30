import QtQuick.Layouts 1.4
import QtQuick 2.4
import QtQuick.Controls 2.0
import org.kde.kirigami 2.4 as Kirigami

import Mycroft 1.0 as Mycroft

Mycroft.Delegate {
    id: systemUrlFrame
    skillBackgroundColorOverlay: "#000000"
        
    Loader {
        id: webViewUrlLoader
        source: "WebViewUrlFrame.qml"
        anchors.fill: parent
        property var pageUrl: sessionData.url
    }
}
 
