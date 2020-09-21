import QtMultimedia 5.12
import QtQuick.Layouts 1.4
import QtQuick 2.9
import QtQuick.Controls 2.12 as Controls
import org.kde.kirigami 2.10 as Kirigami
import QtQuick.Window 2.3
import QtGraphicalEffects 1.0
import Mycroft 1.0 as Mycroft
import "." as Local

Mycroft.Delegate {
    id: root

    property var videoSource: sessionData.video
    property var videoStatus: sessionData.playStatus
    property var videoRepeat: sessionData.playerRepeat
    property var videoThumb: sessionData.videoThumb
    property var videoTitle: sessionData.title
    property bool busyIndicate: false

    fillWidth: true
    background: Rectangle {
        color: "black"
    }
    leftPadding: 0
    topPadding: 0
    rightPadding: 0
    bottomPadding: 0

    onEnabledChanged: syncStatusTimer.restart()
    onVideoSourceChanged: syncStatusTimer.restart()
    
    Component.onCompleted: {
        syncStatusTimer.restart()
    }
    
    Keys.onDownPressed: {
        controlBarItem.opened = true
        controlBarItem.forceActiveFocus()
    }

    onFocusChanged: {
        video.forceActiveFocus();
    }
    
    onVideoRepeatChanged: {
        if(typeof videoRepeat !== "undefined" && typeof videoRepeat == "boolean"){
            if(videoRepeat){
                video.loops = MediaPlayer.Infinite
                video.flushMode = VideoOutput.LastFrame
            }
        } else if(typeof videoRepeat !== "undefined" && typeof videoRepeat == "number"){
            if(videoRepeat > 1){
                video.loops = videoRepeat
                video.flushMode = VideoOutput.LastFrame
            }
        } else {
            video.loops = 1
            video.flushMode = VideoOutput.EmptyFrame
        }
    }
    
    onVideoStatusChanged: {
        switch(videoStatus){
        case "stop":
            video.stop();
            break;
        case "pause":
            video.pause()
            break;
        case "play":
            video.play()
            delay(6000, function() {
                infomationBar.visible = false;
            })
            break;
        }
    }
    
    Connections {
        target: Window.window
        onVisibleChanged: {
            if(video.playbackState == MediaPlayer.PlayingState) {
                video.stop()
            }
        }
    }
    
    Timer {
        id: syncStatusTimer
        interval: 0
        onTriggered: {
            if (enabled && videoStatus == "play") {
                video.play();
            } else if (videoStatus == "stop") {
                video.stop();
            } else {
                video.pause();
            }
        }
    }
    
    Timer {
        id: delaytimer
    }

    function delay(delayTime, cb) {
        delaytimer.interval = delayTime;
        delaytimer.repeat = false;
        delaytimer.triggered.connect(cb);
        delaytimer.start();
    }
    
    controlBar: Local.SeekControl {
        id: seekControl
        anchors {
            bottom: parent.bottom
        }
        title: videoTitle
        videoControl: video
        duration: video.duration
        playPosition: video.position
        onSeekPositionChanged: video.seek(seekPosition);
        z: 1000
    }
    
    Item {
        id: videoRoot
        anchors.fill: parent

        Rectangle {
            id: infomationBar
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            visible: false
            color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g, Kirigami.Theme.backgroundColor.b, 0.6)
            implicitHeight: vidTitle.implicitHeight + Kirigami.Units.largeSpacing * 2
            z: 1001
            
            onVisibleChanged: {
                delay(15000, function() {
                    infomationBar.visible = false;
                })
            }
            
            Controls.Label {
                id: vidTitle
                visible: true
                maximumLineCount: 2
                wrapMode: Text.Wrap
                anchors.left: parent.left
                anchors.leftMargin: Kirigami.Units.largeSpacing
                anchors.verticalCenter: parent.verticalCenter
                text: videoTitle
                z: 100
            }
        }

        Video {
            id: video
            anchors.fill: parent
            focus: true
            autoLoad: true
            autoPlay: false
            loops: 1
            source: videoSource
            
            Keys.onReturnPressed: {
                video.playbackState == MediaPlayer.PlayingState ? video.pause() : video.play()
            }

            Keys.onDownPressed: {
                controlBarItem.opened = true
                controlBarItem.forceActiveFocus()
            }
            
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    controlBarItem.opened = !controlBarItem.opened
                }
            }
            
            onStatusChanged: {
                console.log(status)
                if(status == MediaPlayer.EndOfMedia) {
                    triggerGuiEvent("video.media.playback.ended", {})
                    busyIndicatorPop.enabled = false
                }
                if(status == MediaPlayer.Loading) {
                    busyIndicatorPop.visible = true
                    busyIndicatorPop.enabled = true
                }
                if(status == MediaPlayer.Loaded || status == MediaPlayer.Buffered){
                    busyIndicatorPop.visible = false
                    busyIndicatorPop.enabled = false
                }
            }
            
            Rectangle {
                id: busyIndicatorPop
                width: parent.width
                height: parent.height
                color: Qt.rgba(0, 0, 0, 0.2)
                visible: false
                enabled: false
                
                Controls.BusyIndicator {
                    id: busyIndicate
                    running: busyIndicate
                    anchors.centerIn: parent
                }
                
                onEnabledChanged: {
                    if(busyIndicatorPop.enabled){
                        busyIndicate.running = true
                    } else {
                        busyIndicate.running = false
                    }
                }
            }
        }
    }
}
