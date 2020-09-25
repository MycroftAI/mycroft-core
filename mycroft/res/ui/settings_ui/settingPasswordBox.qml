import QtQuick 2.9
import QtQuick.Controls 2.3
import QtQuick.Layouts 1.4
import org.kde.kirigami 2.11 as Kirigami

TextField {
    property string buttonId;
    property var key;
    property var value;
    signal clicked(string key, string value);
    echoMode: TextInput.PasswordEchoOnEdit
    Layout.fillWidth: true
    Layout.minimumHeight: Kirigami.Units.gridUnit * 2
        
    onTextChanged: {
        clicked(key, text)
    }
}
