import QtQuick
import "."

Rectangle {
    id: seg
    property string text: ""
    property bool selected: false
    signal clicked()

    implicitWidth: label.implicitWidth + Theme.pad * 1.7
    implicitHeight: 38
    radius: Theme.radiusSm
    color: selected ? Theme.cinnabar : (ma.containsMouse ? Theme.paperDeep : "transparent")
    border.width: 1
    border.color: selected ? Theme.cinnabar : Theme.line

    Behavior on color { ColorAnimation { duration: Theme.durFast } }

    scale: ma.pressed ? 0.95 : 1.0
    Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutCubic } }

    Text {
        id: label
        anchors.centerIn: parent
        text: seg.text
        color: seg.selected ? Theme.card : Theme.ink
        font.family: Theme.fontBody
        font.pixelSize: 15
        font.weight: seg.selected ? Font.DemiBold : Font.Normal
    }

    MouseArea {
        id: ma
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: seg.clicked()
    }
}
