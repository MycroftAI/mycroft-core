/*
 * Copyright 2018 Aditya Mehra <aix.m@outlook.com>
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

import QtQuick.Layouts 1.4
import QtQuick 2.4
import QtQuick.Controls 2.11
import org.kde.kirigami 2.11 as Kirigami
import org.kde.plasma.core 2.0 as PlasmaCore
import Mycroft 1.0 as Mycroft
import OVOSPlugin 1.0 as OVOSPlugin
import QtGraphicalEffects 1.12

Item {
    id: customizeSettingsView
    anchors.fill: parent
    property var colorSchemeModel
    property var setColorScheme

    Component.onCompleted: {
        OVOSPlugin.Configuration.updateSchemeList();
        colorSchemeModel = OVOSPlugin.Configuration.getSchemeList();
        colorSchemesView.model = colorSchemeModel.schemes;
        setColorScheme = OVOSPlugin.Configuration.getSelectedSchemeName();
        console.log(setColorScheme);
    }

    Connections {
        target: OVOSPlugin.Configuration
        onSchemeChanged: {
            setColorScheme = OVOSPlugin.Configuration.getSelectedSchemeName();
        }
    }

    Item {
        id: topArea
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Kirigami.Units.gridUnit * 2

        Kirigami.Heading {
            id: customizeSettingPageTextHeading
            level: 1
            wrapMode: Text.WordWrap
            anchors.centerIn: parent
            font.bold: true
            text: "Customize Settings"
            color: Kirigami.Theme.textColor
        }
    }

    Item {
        anchors.top: topArea.bottom
        anchors.topMargin: Kirigami.Units.largeSpacing
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: bottomArea.top

        GridView {
            id: colorSchemesView
            width: parent.width
            height: parent.height
            cellWidth: parent.width / 3
            cellHeight: parent.height / 2
            clip: true

            delegate: ItemDelegate {
                id: parentRectDelta
                implicitHeight: colorSchemesView.cellHeight - (Mycroft.Units.largeSpacing * 2)
                implicitWidth: colorSchemesView.cellWidth - (Mycroft.Units.largeSpacing * 2)

                background: Rectangle {
                    color: modelData.primaryColor
                    radius: 10
                }

                Item {
                    id: d1item
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: Mycroft.Units.gridUnit / 2
                    height: parent.height * 0.70

                    GridLayout {
                        anchors.fill: parent
                        anchors.margins: Mycroft.Units.gridUnit / 2
                        columns: 2

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: modelData.primaryColor
                            border.width: 2
                            border.color: Qt.darker(Kirigami.Theme.backgroundColor, 1.5)

                            Text {
                                anchors.fill: parent
                                anchors.margins: Mycroft.Units.gridUnit
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                text: "P"
                                fontSizeMode: Text.Fit
                                minimumPixelSize: 5
                                font.pixelSize: 40
                                color: Qt.darker(Kirigami.Theme.textColor, 1.5)
                                font.bold: true
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: modelData.secondaryColor
                            border.width: 2
                            border.color: Qt.darker(Kirigami.Theme.backgroundColor, 1.5)

                            Text {
                                anchors.fill: parent
                                anchors.margins: Mycroft.Units.gridUnit
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                text: "S"
                                fontSizeMode: Text.Fit
                                minimumPixelSize: 5
                                font.pixelSize: 40
                                color: Qt.darker(Kirigami.Theme.textColor, 1.5)
                                font.bold: true
                            }
                        }
                        Rectangle{
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: modelData.textColor
                            border.width: 2
                            border.color: Qt.darker(Kirigami.Theme.backgroundColor, 1.5)

                            Text {
                                anchors.fill: parent
                                anchors.margins: Mycroft.Units.gridUnit
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                text: "T"
                                fontSizeMode: Text.Fit
                                minimumPixelSize: 5
                                font.pixelSize: 40
                                color: Qt.darker(Kirigami.Theme.textColor, 1.5)
                                font.bold: true
                            }
                        }
                        Rectangle{
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: modelData.name == setColorScheme ? 1 : 0
                            enabled: modelData.name == setColorScheme ? 1 : 0
                            color: "transparent"

                            Kirigami.Icon {
                                anchors.fill: parent
                                anchors.margins: Mycroft.Units.gridUnit * 2
                                source: Qt.resolvedUrl("images/tick.svg")
                                color: Kirigami.Theme.textColor
                            }
                        }
                    }
                }

                Kirigami.Separator {
                    id: cardSept
                    anchors.top: d1item.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 16
                    color: modelData.secondaryColor
                }

                Item {
                    id: d2item
                    anchors.top: cardSept.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    clip: true

                    Label {
                        anchors.fill: parent
                        anchors.margins: Mycroft.Units.gridUnit / 2
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 20
                        minimumPixelSize: 5
                        fontSizeMode: Text.Fit
                        maximumLineCount: 1
                        text: modelData.name
                        color: modelData.textColor
                        elide: Text.ElideRight
                    }
                }

                onDoubleClicked: {
                    OVOSPlugin.Configuration.setScheme(modelData.name, modelData.path)
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
            anchors.top: areaSep.bottom
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right

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
                color: Kirigami.Theme.textColor
                text: "Device Settings"
                verticalAlignment: Text.AlignVCenter
                Layout.fillWidth: true
                Layout.preferredHeight: Kirigami.Units.gridUnit * 2
            }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                triggerGuiEvent("mycroft.device.settings", {})
            }
        }
    }
}

