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
import QtQuick 2.9
import QtQuick.Controls 2.3
import org.kde.kirigami 2.11 as Kirigami
import Mycroft 1.0 as Mycroft

Mycroft.Delegate {
    id: skillSettingsView
    anchors.fill: parent
    property var skillsConfig: sessionData.skillsConfig
    property var skill_id
    fillWidth: true
    
    function selectSettingUpdated(key, value){
        var skillevent = skill_id + ".settings.set"
        triggerGuiEvent(skillevent, {"setting_key": key, "setting_value": value})
    }
    
    function generate_settings_ui(mData, comp) {
        if (mData.type == "select") {
            var newObject = Qt.createComponent("settings_ui/settingButton.qml")
            var available_values = sanitize_values(mData.options.split(";"))
            for (var i = 0; i < available_values.length; i++) {
                var rbutton = newObject.createObject(comp, {checked: mData.value.toString() == available_values[i] ? 1 : 0 , text: available_values[i], "key": mData.name, "value": available_values[i]});
                rbutton.clicked.connect(selectSettingUpdated)
            }
        }
        if (mData.type == "checkbox") {
            var newObject = Qt.createComponent("settings_ui/settingCheckBox.qml")
            var rbutton = newObject.createObject(comp, {checked: mData.value.toString() == "true" ? 1 : 0, text: mData.value == "true" ? "Disable" : "Enable", "key": mData.name, "value": mData.value});
            rbutton.clicked.connect(selectSettingUpdated)
        }
        if (mData.type == "text") {
            var newObject = Qt.createComponent("settings_ui/settingTextBox.qml")
            var rbutton = newObject.createObject(comp, {text: mData.value, "key": mData.name, "value": mData.value});
            rbutton.clicked.connect(selectSettingUpdated)
        }
        if (mData.type == "password") {
            var newObject = Qt.createComponent("settings_ui/settingPasswordBox.qml")
            var rbutton = newObject.createObject(comp, {text: mData.value, "key": mData.name, "value": mData.value});
            rbutton.clicked.connect(selectSettingUpdated)
        }
        if (mData.type == "number") {
            var newObject = Qt.createComponent("settings_ui/settingNumberBox.qml")
            var rbutton = newObject.createObject(comp, {text: mData.value, "key": mData.name, "value": mData.value});
            rbutton.clicked.connect(selectSettingUpdated)
        }
    }
    
    function sanitize_values(mValues) {
        var val_listing = []
        for (var i = 0; i < mValues.length; i++) {
            if (mValues[i].includes('|')) {
                var splitVals = mValues[i].split("|")[1]
                val_listing.push(splitVals.toLowerCase())
            } else {
                val_listing.push(mValues[i])
            }
        }
        return val_listing
    }
    
    onSkillsConfigChanged: {
        skillConfigView.update()
        if(skillsConfig !== null){
            skillConfigView.model = skillsConfig.sections
            skillSettingsView.skill_id = skillsConfig.skill_id
            var skillname = skill_id.split(".")[0]
            configPageHeading.text = skillname.replace("-", " ") + " Configuration"
        }
    }
    
    Connections {
        target: Mycroft.MycroftController
        onIntentRecevied: {
            if(type == "mycroft.skills.settings.changed"){
                var skillevent = skill_id + ".settings.update"
                triggerGuiEvent(skillevent, {})
            }
        }
    }
    
    Item {
        id: topArea
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Kirigami.Units.gridUnit * 2
        
        Kirigami.Heading {
            id: configPageHeading
            level: 1
            wrapMode: Text.WordWrap
            anchors.centerIn: parent
            font.capitalization: Font.Capitalize
            font.bold: true
            color: Kirigami.Theme.linkColor
        }
    }

    Flickable {
        anchors.top: topArea.bottom
        anchors.topMargin: Kirigami.Units.largeSpacing
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: areaSep.top
        anchors.bottomMargin: Kirigami.Units.smallSpacing
        contentHeight: scvGrid.implicitHeight
        clip: true
        
        GridLayout {
            id: scvGrid
            width: parent.width
            columns: scvGrid.width > 600 ? 2 : 1
            rowSpacing: Kirigami.Units.smallSpacing
            
            Repeater {
                id: skillConfigView
                clip: true

                delegate: Control {
                    id: delegateRoot
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true
                    
                    background: Rectangle {
                        color: "#1d1d1d"
                        radius: 10
                    }
                    
                    contentItem: Item {
                    implicitWidth: scvGrid.width > 600 ? scvGrid.width / 2 : scvGrid.width
                    implicitHeight: delegateLayout.implicitHeight + Kirigami.Units.largeSpacing
                    
                        ColumnLayout {
                            id: delegateLayout
                            anchors.left: parent.left
                            anchors.right: parent.right
                            spacing: Kirigami.Units.largeSpacing
                            
                            Rectangle {
                                id: skillNameBlock
                                color: Kirigami.Theme.linkColor
                                Layout.fillWidth: true
                                Layout.margins: Kirigami.Units.largeSpacing
                                Layout.preferredHeight: skillName.contentHeight + Kirigami.Units.smallSpacing
                                radius: 3
                                
                                Kirigami.Heading {
                                    id: skillName
                                    elide: Text.ElideRight
                                    font.weight: Font.DemiBold
                                    text: modelData.name
                                    width: parent.width
                                    verticalAlignment: Text.AlignVCenter
                                    horizontalAlignment: Text.AlignHCenter
                                    level: 2
                                }
                            }
                                                            
                            Repeater {
                                id: gFields
                                model: modelData.fields
                                                                
                                delegate: GridLayout {
                                    id: skillSettingType
                                    Layout.fillWidth: true
                                    Layout.margins: Kirigami.Units.largeSpacing
                                    Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                                    columns: switch(modelData.type) {
                                        case "text": return 1;
                                        case "password" : return 1;
                                        case "select" :
                                            var opts_length = sanitize_values(modelData.options.split(";")).length;
                                            return opts_length <= 3 ? 1 : parent.width / modelData.options.length
                                        case "number" : return 1;
                                        default: return 2;
                                    }
                                    
                                    Kirigami.Heading {
                                        id: skillSettingName
                                        Layout.alignment: Qt.AlignLeft
                                        elide: Text.ElideRight
                                        text: modelData.label
                                        Layout.fillWidth: true
                                        wrapMode: Text.WordWrap;
                                        font.capitalization: Font.Capitalize
                                        textFormat: Text.AutoText
                                        level: 3
                                    }
                                                                        
                                    ButtonGroup {
                                        id: settingGroup
                                    }
                                    
                                    Component.onCompleted: {
                                        generate_settings_ui(modelData, skillSettingType)
                                        skillConfigView.update()
                                    }
                                }
                            }
                        }
                    }
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
            
            Kirigami.Icon {
                id: backIcon
                source: "go-previous"
                Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                Layout.preferredWidth: Kirigami.Units.iconSizes.medium
            }
            
            Kirigami.Heading {
                level: 2
                wrapMode: Text.WordWrap
                Layout.alignment: Qt.AlignVCenter
                verticalAlignment: Text.AlignVCenter
                font.bold: true
                text: "Back"
                Layout.fillWidth: true
                Layout.preferredHeight: Kirigami.Units.gridUnit * 2
            }
        }
        
        MouseArea {
            anchors.fill: parent
            onClicked: {
                var skillevent = skill_id + ".settings.remove_page"
                triggerGuiEvent(skillevent, {})
            }
        }
    }
}
