import QtQuick.Layouts 1.4
import QtQuick 2.4
import QtQuick.Controls 2.0
import org.kde.kirigami 2.4 as Kirigami

import Mycroft 1.0 as Mycroft

Mycroft.ProportionalDelegate {
    id: systemTextFrame
    skillBackgroundColorOverlay: "#000000"
    property bool hasTitle: sessionData.title.length > 0 ? true : false
    
    Component.onCompleted: {
        console.log(hasTitle)
    }
    
    Mycroft.AutoFitLabel {
        id: systemTextFrameTitle
        Layout.fillWidth: true
        Layout.preferredHeight: proportionalGridUnit * 20
        wrapMode: Text.Wrap
        visible: hasTitle
        enabled: hasTitle
        font.family: "Noto Sans"
        font.weight: Font.Bold
        text: sessionData.title        
    }
    
    Mycroft.AutoFitLabel {
        id: systemTextFrameMainBody
        Layout.fillWidth: true
        Layout.preferredHeight: proportionalGridUnit * 30
        wrapMode: Text.Wrap
        font.family: "Noto Sans"
        font.weight: Font.Bold
        text: sessionData.text
    }
}
 
