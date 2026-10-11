import QtQuick
import "."

Rectangle {
    id: root
    property string label: ""
    property int seconds: 0
    property bool running: false
    property color dotColor: Theme.pieceBlack
    property string detail: ""

    radius: Theme.radius
    color: running ? Theme.cardHi : "transparent"
    border.width: 1
    border.color: running ? Theme.cinnabarSoft : Theme.line

    Behavior on color { ColorAnimation { duration: Theme.durFast } }
    Behavior on border.color { ColorAnimation { duration: Theme.durFast } }

    function fmt(s) {
        var m = Math.floor(s / 60)
        var r = s % 60
        return (m < 10 ? "0" : "") + m + ":" + (r < 10 ? "0" : "") + r
    }

    Column {
        anchors.centerIn: parent
        spacing: 12

        Item {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 30
            height: 30
            Rectangle {
                anchors.fill: parent
                radius: 15
                color: root.dotColor
                border.width: 1
                border.color: Theme.lineStrong
            }
            Rectangle {
                anchors.fill: parent
                anchors.margins: -4
                radius: 19
                color: "transparent"
                border.width: 2
                border.color: Theme.cinnabarSoft
                visible: root.running
                SequentialAnimation on opacity {
                    running: root.running
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.2; duration: 520 }
                    NumberAnimation { to: 0.9; duration: 520 }
                }
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.label
            color: Theme.ink
            font.family: Theme.fontBody
            font.pixelSize: 17
            font.weight: Font.DemiBold
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.fmt(root.seconds)
            color: root.running ? Theme.cinnabar : Theme.inkDim
            font.family: Theme.fontMono
            font.pixelSize: 28
            font.weight: Font.DemiBold
        }

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 26
            height: 1
            color: Theme.line
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            visible: root.detail !== ""
            text: root.detail
            color: Theme.inkDim
            font.family: Theme.fontBody
            font.pixelSize: 12
        }
    }
}
