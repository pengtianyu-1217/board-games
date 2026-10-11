import QtQuick
import "."

Item {
    id: root
    property bool opened: false
    property string title: "确认"
    property string message: ""
    signal confirmed()

    visible: opacity > 0
    opacity: opened ? 1.0 : 0.0
    Behavior on opacity { NumberAnimation { duration: Theme.durFast } }

    Rectangle {
        anchors.fill: parent
        color: Theme.ink
        opacity: 0.34
        MouseArea {
            anchors.fill: parent
            onClicked: root.opened = false
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(320, root.width * 0.8)
        height: 168
        radius: Theme.radius
        color: Theme.card
        border.width: 1
        border.color: Theme.lineStrong
        scale: root.opened ? 1.0 : 0.95
        Behavior on scale { NumberAnimation { duration: Theme.durFast; easing.type: Easing.OutCubic } }

        Column {
            anchors.centerIn: parent
            spacing: 16
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.title
                color: Theme.ink
                font.family: Theme.fontTitle
                font.pixelSize: 21
                font.letterSpacing: 2
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.message
                color: Theme.inkDim
                font.family: Theme.fontBody
                font.pixelSize: 14
            }
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 12
                TextButton { text: "取消"; onClicked: root.opened = false }
                TextButton {
                    text: "确定"; accent: true
                    onClicked: { root.opened = false; root.confirmed() }
                }
            }
        }
    }
}
