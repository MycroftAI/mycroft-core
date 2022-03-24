import QtQuick.Layouts 1.4
import QtQuick 2.4
import QtQuick.Controls 2.0
import org.kde.kirigami 2.5 as Kirigami
import Mycroft 1.0 as Mycroft
import QtGraphicalEffects 1.12

Mycroft.Delegate {
    id: mainLoaderView

    background: Rectangle {
        color: Kirigami.Theme.backgroundColor
        opacity: 0.6
        z: 1
    }

    property var pageToLoad: sessionData.state
    property var idleScreenList: sessionData.idleScreenList
    property var activeIdle: sessionData.selectedScreen

    contentItem: Loader {
        id: rootLoader
        z: 2
    }

    onPageToLoadChanged: {
        console.log(sessionData.state)
        rootLoader.setSource(sessionData.state + ".qml")
    }
}
