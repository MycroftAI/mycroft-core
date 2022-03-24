import QtQuick.Layouts 1.4
import QtQuick 2.4
import QtQuick.Controls 2.0
import org.kde.kirigami 2.5 as Kirigami
import org.kde.plasma.core 2.0 as PlasmaCore
import Mycroft 1.0 as Mycroft
import QtGraphicalEffects 1.12

Item {
    id: deviceSettingsView
    anchors.fill: parent
    z: 2
    
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
            color: Kirigami.Theme.textColor
        }
    }

    Item {
        anchors.top: topArea.bottom
        anchors.topMargin: Kirigami.Units.largeSpacing
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: bottomArea.top
        anchors.bottomMargin: Kirigami.Units.largeSpacing
        
        ListView {
            anchors.fill: parent
            clip: true
            model: SettingsModel{}
            boundsBehavior: Flickable.StopAtBounds
            delegate: Kirigami.AbstractListItem {
                activeBackgroundColor: Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g, Kirigami.Theme.highlightColor.b, 0.7)
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
                                id: iconSettingHolder
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                                Layout.preferredHeight: units.iconSizes.medium
                                Layout.preferredWidth: units.iconSizes.medium
                                source: model.settingIcon

                                ColorOverlay {
                                    anchors.fill: parent
                                    source: iconSettingHolder
                                    color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.7)
                                }
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
                                color: Kirigami.Theme.textColor
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
    
    Item {
        id: bottomArea
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: Mycroft.Units.gridUnit * 6

        Kirigami.Separator {
            id: areaSep
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            color: Kirigami.Theme.highlightColor
            height: 2
        }

        RowLayout {
            anchors.fill: parent
            
            Image {
                id: backIcon
                source: "images/back.png"
                Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                Layout.preferredWidth: Kirigami.Units.iconSizes.medium

                ColorOverlay {
                    anchors.fill: parent
                    source: backIcon
                    cached: true
                    color: Kirigami.Theme.textColor
                }
            }
            
            Kirigami.Heading {
                level: 2
                wrapMode: Text.WordWrap
                font.bold: true
                text: "Home"
                color: Kirigami.Theme.textColor
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
