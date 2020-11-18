import QtQuick 2.9
import QtQuick.Controls 2.3
import QtQuick.Layouts 1.4

CheckBox {
    property string buttonId;
    property var key;
    property var value;
    signal clicked(string key, string value);
    
    onCheckedChanged: {
        if(checked){
            clicked(key, "true")
        } else {
            clicked(key, "false")
        }
    }
}
