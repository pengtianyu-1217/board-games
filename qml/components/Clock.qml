import QtQuick
import "."

Rectangle {
    id: root
    property string label: ""
    property int seconds: 0
    property bool running: false
    property color dotColor: Theme.pieceBlack

    implicitWidth: rowBox.implicitWidth + Theme.pad * 1.1
    implicitHeight: 34
    radius: Theme.radiusSm
    color: running ? Theme.cardHi : "transparent"
    border.width: 1
    border.color: running ? Theme.cinnabarSoft : Theme.line

    function fmt(s) {
        var m = Math.floor(s / 60)
        var r = s % 60
        return (m < 10 ? "0" : "") + m + ":" + (r < 10 ? "0" : "") + r
    }

    Behavior on color { ColorAnimation { duration: Theme.durFast } }
    Behavior on border.color { ColorAnimation { duration: Theme.durFast } }

    Row {
        id: rowBox
        anchors.centerIn: parent
        spacing: 7
        Rectangle {
            width: 9; height: 9; radius: 4.5
            anchors.verticalCenter: parent.verticalCenter
            color: root.dotColor
            border.width: 1
            border.color: Theme.lineStrong
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.label
            color: Theme.inkDim
            font.family: Theme.fontBody
            font.pixelSize: 13
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.fmt(root.seconds)
            color: Theme.ink
            font.family: Theme.fontMono
            font.pixelSize: 15
            font.weight: Font.DemiBold
        }
    }
}
