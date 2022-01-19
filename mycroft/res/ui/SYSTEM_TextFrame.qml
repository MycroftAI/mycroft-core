import QtQuick.Layouts 1.4
import QtQuick 2.4
import QtQuick.Controls 2.0
import org.kde.kirigami 2.4 as Kirigami

import Mycroft 1.0 as Mycroft

Mycroft.CardDelegate {
    id: systemTextFrame
    skillBackgroundColorOverlay: "#000000"
    cardBackgroundOverlayColor: "#000000"

    property bool hasTitle: sessionData.title.length > 0 ? true : false
    
    contentItem: Rectangle {
        color: "blue"

        ColumnLayout {
            anchors.fill: parent

            Mycroft.AutoFitLabel {
                id: systemTextFrameTitle
                wrapMode: Text.Wrap
                visible: hasTitle
                enabled: hasTitle
                Layout.fillWidth: true
                Layout.fillHeight: true
                font.family: "Noto Sans"
                font.weight: Font.Bold
                text: sessionData.title
            }

            Mycroft.AutoFitLabel {
                id: systemTextFrameMainBody
                wrapMode: Text.Wrap
                font.family: "Noto Sans"
                Layout.fillWidth: true
                Layout.fillHeight: true
                font.weight: Font.Bold
                text: sessionData.text
            }
        }
    }
}
 
