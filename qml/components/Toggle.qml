import QtQuick
import "."

Row {
    id: root
    property string label: ""
    property bool checked: true
    property bool active: true
    signal toggled()

    spacing: 10
    opacity: active ? 1.0 : 0.4

    Text {
        anchors.verticalCenter: parent.verticalCenter
        text: root.label
        color: Theme.ink
        font.family: Theme.fontBody
        font.pixelSize: 14
    }

    Rectangle {
        width: 46; height: 24; radius: 12
        anchors.verticalCenter: parent.verticalCenter
        color: root.checked ? Theme.cinnabar : Theme.paperDeep
        border.width: 1
        border.color: root.checked ? Theme.cinnabar : Theme.line
        Behavior on color { ColorAnimation { duration: Theme.durFast } }

        Rectangle {
            width: 18; height: 18; radius: 9
            y: 3
            x: root.checked ? 25 : 3
            color: Theme.card
            Behavior on x { NumberAnimation { duration: Theme.durFast; easing.type: Easing.OutCubic } }
        }

        MouseArea {
            anchors.fill: parent
            enabled: root.active
            cursorShape: root.active ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: root.toggled()
        }
    }
}
