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
import QtGraphicalEffects 1.12

Item {
    id: homeScreenSettingsView
    anchors.fill: parent
    property var modelItemList: mainLoaderView.idleScreenList
    property var activeIdle: mainLoaderView.activeIdle
    
    ButtonGroup {
        id: idleSelectionGroup
    }
    
    onModelItemListChanged: {
       listIdleFaces.model = modelItemList.screenBlob
    }
    
    function checkIfActive(screenId){
        if(screenId == activeIdle) {
            return true
        } else {
            return false
        }
    }
    
    Item {
        id: topArea
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Kirigami.Units.gridUnit * 2
        
        Kirigami.Heading {
            id: idleSettingPageTextHeading
            level: 1
            wrapMode: Text.WordWrap
            anchors.centerIn: parent
            font.bold: true
            text: "Homescreen Settings"
            color: Kirigami.Theme.textColor
        }
    }

    Item {
        anchors.top: topArea.bottom
        anchors.topMargin: Kirigami.Units.largeSpacing
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: bottomArea.top
        
      ListView {
            id: listIdleFaces
            anchors.fill: parent
            clip: true
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
                
                            Kirigami.Heading {
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignHCenter
                                height: paintedHeight
                                elide: Text.ElideRight
                                font.weight: Font.DemiBold
                                verticalAlignment: Text.AlignVCenter
                                color: Kirigami.Theme.textColor
                                text: modelData.name
                                textFormat: Text.PlainText
                                level: 2
                            }
                            
                            Image {
                                id: selectedItemIcon
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                                Layout.preferredHeight: units.iconSizes.medium
                                Layout.preferredWidth: units.iconSizes.medium
                                visible: checkIfActive(modelData.id)
                                source: "images/tick.svg"
                            }
                        }
                    }
                }
                
                onClicked: {
                    triggerGuiEvent("mycroft.device.set.idle", {"selected": modelData.id})
                }
            }
            
            Component.onCompleted: {
                listIdleFaces.count
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
                text: "Device Settings"
                color: Kirigami.Theme.textColor
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
