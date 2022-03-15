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
import QtQuick.Controls 2.0
import org.kde.kirigami 2.5 as Kirigami
import org.kde.plasma.core 2.0 as PlasmaCore
import Mycroft 1.0 as Mycroft

Item {
    id: developerSettingsView
    anchors.fill: parent
    property bool dashActive: sessionData.dashboard_enabled
    property bool busyVisible: false

    onDashActiveChanged: {
        developerSettingsView.busyVisible = false
    }
    
    Item {
        id: topArea
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Kirigami.Units.gridUnit * 2
        
        Kirigami.Heading {
            id: brightnessSettingPageTextHeading
            level: 1
            wrapMode: Text.WordWrap
            anchors.centerIn: parent
            font.bold: true
            text: "Developer Settings"
            color: "white"
        }
    }

    Item {
        id: viewBusyOverlay
        z: 300
        anchors.top: topArea.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: areaSep.top
        visible: developerSettingsView.busyVisible
        enabled: visible

        BusyIndicator {
            id: viewBusyIndicator
            visible: viewBusyOverlay.visible
            anchors.centerIn: parent
            running: viewBusyOverlay.visible
            enabled: viewBusyOverlay.visible
        }
    }

    Item {
        anchors.top: topArea.bottom
        anchors.topMargin: Kirigami.Units.largeSpacing
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: areaSep.top
        
        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            spacing: Kirigami.Units.smallSpacing
            
            Kirigami.Heading {
                id: warnText
                level: 3
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "Enabling OVOS Dashboard will provide you access to control various services on this device, the OVOS Dashboard can be accessed on any device located in your LAN network"
            }
            
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: Kirigami.Units.largeSpacing
            }
            
            Button { 
                Layout.fillWidth: true
                Layout.preferredHeight: Kirigami.Units.gridUnit * 3
                text: "Enable Dashboard"
                visible: !dashActive
                enabled: visible
                onClicked: {
                    triggerGuiEvent("mycroft.device.enable.dash", {})
                    developerSettingsView.busyVisible = true
                }
            }
            
            Button {
                Layout.fillWidth: true
                Layout.preferredHeight: Kirigami.Units.gridUnit * 3
                text: "Disable Dashboard"
                visible: dashActive
                enabled: visible
                onClicked: {
                    triggerGuiEvent("mycroft.device.disable.dash", {})
                    developerSettingsView.busyVisible = true
                }
            }
            
            Kirigami.Separator {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                visible: dashActive
                enabled: visible
            }

            Kirigami.Heading {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                level: 3
                text: "Dashboard Address: " +  sessionData.dashboard_url
                visible: dashActive
                enabled: visible
            }

            Kirigami.Heading {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                level: 3
                text: "Dashboard Username: " + sessionData.dashboard_user
                visible: dashActive
                enabled: visible
            }

            Kirigami.Heading {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                level: 3
                text: "Dashboard Password: " + sessionData.dashboard_password
                visible: dashActive
                enabled: visible
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
