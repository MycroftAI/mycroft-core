import QtQuick.Layouts 1.4
import QtQuick 2.4
import QtQuick.Controls 2.0
import org.kde.kirigami 2.4 as Kirigami

import Mycroft 1.0 as Mycroft

Mycroft.Delegate {
    id: systemImageFrame
    skillBackgroundColorOverlay: "#000000"
    property bool hasTitle: sessionData.title.length > 0 ? true : false
    property bool hasCaption: sessionData.caption.length > 0 ? true : false
            
    ColumnLayout {
        id: systemImageFrameLayout
        anchors.fill: parent
        
        Kirigami.Heading {
            id: systemImageTitle
            visible: hasTitle
            enabled: hasTitle
            Layout.fillWidth: true
            Layout.preferredHeight: paintedHeight + Kirigami.Units.largeSpacing
            level: 3
            text: sessionData.title
            wrapMode: Text.Wrap
            font.family: "Noto Sans"
            font.weight: Font.Bold
        }
        
        Image {
            id: systemImageDisplay
            visible: true
            enabled: true
            Layout.fillWidth: true
            Layout.fillHeight: true
            source: sessionData.image
            property var fill: sessionData.fill
            
            onFillChanged: {
                console.log(fill)
                if(fill == "PreserveAspectCrop"){
                    systemImageDisplay.fillMode = 2
                } else if (fill == "PreserveAspectFit"){
                    console.log("inFit")
                    systemImageDisplay.fillMode = 1
                } else if (fill == "Stretch"){
                    systemImageDisplay.fillMode = 0
                } else {
                    systemImageDisplay.fillMode = 0
                }
            }
            
            
            Rectangle {
                id: systemImageCaptionBox
                visible: hasCaption
                enabled: hasCaption
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: systemImageCaption.paintedHeight
                color: "#95000000"
                
                Kirigami.Heading {
                    id: systemImageCaption
                    level: 2
                    anchors.left: parent.left
                    anchors.leftMargin: Kirigami.Units.largeSpacing
                    anchors.right: parent.right
                    anchors.rightMargin: Kirigami.Units.largeSpacing
                    anchors.verticalCenter: parent.verticalCenter
                    text: sessionData.caption
                    wrapMode: Text.Wrap
                    font.family: "Noto Sans"
                    font.weight: Font.Bold
                }
            }
        }
    }
}
 
 
