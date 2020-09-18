import QtQuick 2.4
import QtQuick.Controls 2.0

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
