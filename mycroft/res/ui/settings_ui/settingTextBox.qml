import QtQuick 2.4
import QtQuick.Controls 2.0
import QtQuick.Layouts 1.4

TextField {
    property string buttonId;
    property var key;
    property var value;
    signal clicked(string key, string value);
    Layout.fillWidth: true
    
    onTextChanged: {
            clicked(key, text)
    }
}
