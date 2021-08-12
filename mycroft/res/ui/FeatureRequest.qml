import QtQuick 2.12
import QtQuick.Controls 2.12
import QtWebEngine 1.7
import QtWebChannel 1.0
import QtQuick.Layouts 1.12
import org.kde.kirigami 2.11 as Kirigami

Item {
    property var requestedFeature;
    property url securityOrigin;

    width: parent.width
    height: parent.height

    onRequestedFeatureChanged: {
        message.text = securityOrigin + " has requested access to your "
                + message.textForFeature(requestedFeature);
    }

    RowLayout {
        anchors.fill: parent

        Label {
            id: message
            Layout.fillWidth: true
            Layout.leftMargin: Kirigami.Units.largeSpacing
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight

            function textForFeature(feature) {
                if (feature === WebEngineView.MediaAudioCapture)
                    return "microphone"
                if (feature === WebEngineView.MediaVideoCapture)
                    return "camera"
                if (feature === WebEngineView.MediaAudioVideoCapture)
                    return "camera and microphone"
                if (feature === WebEngineView.Geolocation)
                    return "location"
            }
        }

        Button {
            id: acceptButton
            Layout.alignment: Qt.AlignRight
            Layout.preferredWidth: parent.width * 0.18

            background: Rectangle {
                color: acceptButton.activeFocus ? Kirigami.Theme.highlightColor : Qt.lighter(Kirigami.Theme.backgroundColor, 1.2)
                border.color: Kirigami.Theme.disabledTextColor
                radius: 20
            }
            
            contentItem: Item {
                Kirigami.Heading {
                    level: 3
                    font.pixelSize: parent.width * 0.075
                    anchors.centerIn: parent
                    text: "Accept"
                }
            }

            onClicked: {
                webview.grantFeaturePermission(securityOrigin,
                                            requestedFeature, true);
                interactionBar.isRequested = false;
            }
        }

        Button {
            id: denyButton
            Layout.alignment: Qt.AlignRight
            Layout.preferredWidth: parent.width * 0.18

            background: Rectangle {
                color: denyButton.activeFocus ? Kirigami.Theme.highlightColor : Qt.lighter(Kirigami.Theme.backgroundColor, 1.2)
                border.color: Kirigami.Theme.disabledTextColor
                radius: 20
            }
            
            contentItem: Item {
                Kirigami.Heading {
                    level: 3
                    font.pixelSize: parent.width * 0.075
                    anchors.centerIn: parent
                    text: "Deny"
                }
            }

            onClicked: {
                webview.grantFeaturePermission(securityOrigin,
                                            requestedFeature, false);
                interactionBar.isRequested = false
            }
        }

        Button {
            id: closeButton
            Layout.alignment: Qt.AlignRight
            Layout.preferredWidth: Kirigami.Units.iconSizes.large - (Kirigami.Units.largeSpacing + Kirigami.Units.smallSpacing)
            Layout.preferredHeight: Kirigami.Units.iconSizes.large - (Kirigami.Units.largeSpacing + Kirigami.Units.smallSpacing)
            Layout.leftMargin: Kirigami.Units.largeSpacing
            Layout.rightMargin: Kirigami.Units.largeSpacing

            background: Rectangle {
                color: denyButton.activeFocus ? Kirigami.Theme.highlightColor : Qt.lighter(Kirigami.Theme.backgroundColor, 1.2)
                border.color: Kirigami.Theme.disabledTextColor
                radius: 200
            }

            Kirigami.Icon {
                anchors.centerIn: parent
                width: Kirigami.Units.iconSizes.medium
                height: Kirigami.Units.iconSizes.medium
                source: "window-close"
            }

            onClicked: {
                interactionBar.isRequested = false
            }
        }
    }
}
