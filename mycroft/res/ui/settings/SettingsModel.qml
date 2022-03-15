import QtQuick.Layouts 1.4
import QtQuick 2.4
import QtQuick.Controls 2.0
import org.kde.kirigami 2.5 as Kirigami
import Mycroft 1.0 as Mycroft

ListModel {
    id: settingsListModel
    
    ListElement {
        settingIcon: "images/home.svg"
        settingName: "Homescreen Settings"
        settingEvent: "mycroft.device.settings.homescreen"
        settingCall: "show homescreen settings"
    }
    ListElement {
        settingIcon: "images/ssh.svg"
        settingName: "Enable SSH"
        settingEvent: "mycroft.device.settings.ssh"
        settingCall: "show ssh settings" 
    }
    ListElement {
        settingIcon: "images/settings.png"
        settingName: "Developer Settings"
        settingEvent: "mycroft.device.settings.developer"
        settingCall: "" 
    }
    ListElement {
        settingIcon: "images/restart.svg"
        settingName: "Reboot"
        settingEvent: "mycroft.device.settings.restart"
        settingCall: "" 
    }
    ListElement {
        settingIcon: "images/power.svg"
        settingName: "Shutdown"
        settingEvent: "mycroft.device.settings.poweroff"
        settingCall: "" 
    }
}
