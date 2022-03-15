import QtQuick.Layouts 1.4
import QtQuick 2.4
import QtQuick.Controls 2.0
import org.kde.kirigami 2.5 as Kirigami
import org.kde.plasma.core 2.0 as PlasmaCore
import Mycroft 1.0 as Mycroft

Item {
    id: deviceSettingsView
    anchors.fill: parent
    
    Item {
        id: topArea
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Kirigami.Units.gridUnit * 2
        
        Kirigami.Heading {
            id: settingPageTextHeading
            level: 1
            wrapMode: Text.WordWrap
            anchors.centerIn: parent
            font.bold: true
            text: "Device Settings"
            color: "white"
        }
    }

    Item {
        anchors.top: topArea.bottom
        anchors.topMargin: Kirigami.Units.largeSpacing
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: areaSep.top
        anchors.bottomMargin: Kirigami.Units.largeSpacing
        
        ListView {
            anchors.fill: parent
            clip: true
            model: SettingsModel{}
            boundsBehavior: Flickable.StopAtBounds
            delegate: Kirigami.AbstractListItem {
                activeBackgroundColor: Qt.rgba(1, 0, 0, 0.7)
                contentItem: Item {
                implicitWidth: delegateLayout.implicitWidth;
                implicitHeight: delegateLayout.implicitHeight;
        
                    ColumnLayout {
                        id: delegateLayout
                        anchors {
                            left: parent.left;
                            top: parent.top;
                            right: parent.right;
                        }
                    
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Math.round(units.gridUnit / 2)
                
                            Image {
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                                Layout.preferredHeight: units.iconSizes.medium
                                Layout.preferredWidth: units.iconSizes.medium
                                source: model.settingIcon
                            }

                            
                            Kirigami.Heading {
                                id: connectionNameLabel
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                height: paintedHeight
                                elide: Text.ElideRight
                                font.weight: Font.DemiBold
                                text: model.settingName
                                textFormat: Text.PlainText
                                level: 2
                            }
                        }
                    }
                }
                
                onClicked: {
                        triggerGuiEvent(model.settingEvent, {})
                }
            }
        }
    }
    
    Kirigami.Separator {
        id: areaSep
        anchors.bottom: bottomArea.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
    }
    
    Item {
        id: bottomArea
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Kirigami.Units.largeSpacing * 1.15
        height: backIcon.implicitHeight + Kirigami.Units.largeSpacing * 1.15

        RowLayout {
            anchors.fill: parent
            
            Image {
                id: backIcon
                source: "images/back.png"
                Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                Layout.preferredWidth: Kirigami.Units.iconSizes.medium
            }
            
            Kirigami.Heading {
                level: 2
                wrapMode: Text.WordWrap
                font.bold: true
                text: "Home"
                verticalAlignment: Text.AlignVCenter
                Layout.fillWidth: true
                Layout.preferredHeight: Kirigami.Units.gridUnit * 2
            }
        }
        
        MouseArea {
            anchors.fill: parent
            onClicked: {
                triggerGuiEvent("mycroft.device.show.idle", {})
            }
        }
    }
}
