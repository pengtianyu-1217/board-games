import QtQuick
import "."

Rectangle {
    id: btn
    property string text: ""
    property bool accent: false
    property bool active: true
    signal clicked()

    implicitWidth: label.implicitWidth + Theme.pad * 1.5
    implicitHeight: 42
    radius: Theme.radiusSm
    opacity: active ? 1.0 : 0.4
    color: !active ? "transparent"
         : accent ? (ma.containsMouse ? Theme.cinnabarHi : Theme.cinnabar)
         : (ma.containsMouse ? Theme.cardHi : Theme.card)
    border.width: 1
    border.color: accent ? Theme.cinnabar : Theme.line

    Behavior on color { ColorAnimation { duration: Theme.durFast } }

    scale: (ma.pressed && btn.active) ? 0.96 : 1.0
    Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutCubic } }

    Text {
        id: label
        anchors.centerIn: parent
        text: btn.text
        color: btn.accent ? Theme.card : Theme.ink
        font.family: Theme.fontBody
        font.pixelSize: 15
    }

    MouseArea {
        id: ma
        anchors.fill: parent
        hoverEnabled: true
        enabled: btn.active
        cursorShape: btn.active ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: btn.clicked()
    }
}
