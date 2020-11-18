import QtQuick 2.9
import QtQuick.Controls 2.3
import QtQuick.Layouts 1.4

RadioButton {
    property string buttonId;
    property var key;
    property var value;
    signal clicked(string key, string value);
    Layout.alignment: Qt.AlignLeft
    Layout.fillWidth: true
    
    onCheckedChanged: {
        if(checked){
            clicked(key, value)
        }
    }
} 
