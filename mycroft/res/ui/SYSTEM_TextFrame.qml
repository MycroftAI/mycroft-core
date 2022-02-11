import QtQuick.Layouts 1.4
import QtQuick 2.4
import QtQuick.Controls 2.0
import org.kde.kirigami 2.4 as Kirigami

import Mycroft 1.0 as Mycroft

Mycroft.CardDelegate {
    id: systemTextFrame
    skillBackgroundColorOverlay: "#000000"
    cardBackgroundOverlayColor: sessionData.backgroundColor || "#000000"

    property bool hasTitle: sessionData.title.length > 0 ? true : false
    property int contentMargin: Mycroft.Units.gridUnit * 2

    contentItem: Rectangle {
        color: "transparent"

        ColumnLayout {
            anchors.fill: parent
            anchors.topMargin: contentMargin
            anchors.leftMargin: contentMargin
            anchors.rightMargin: contentMargin
            anchors.bottomMargin: contentMargin

            Mycroft.AutoFitLabel {
                id: systemTextFrameTitle
                wrapMode: Text.Wrap
                visible: hasTitle
                enabled: hasTitle
                Layout.fillWidth: true
                Layout.fillHeight: true
                font.weight: Font.Bold
                text: sessionData.title
                color: sessionData.color || "white"
            }

            Mycroft.AutoFitLabel {
                id: systemTextFrameMainBody
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                Layout.fillHeight: true
                font.weight: hasTitle ? Font.Normal : Font.Bold
                text: sessionData.text
                color: sessionData.color || "white"
            }
        }
    }
}
