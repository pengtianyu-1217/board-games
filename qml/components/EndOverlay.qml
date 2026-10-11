import QtQuick
import "."

Item {
    id: root
    property bool shown: false

    visible: opacity > 0
    opacity: shown ? 1.0 : 0.0
    Behavior on opacity { NumberAnimation { duration: Theme.durBase } }

    Rectangle {
        anchors.fill: parent
        color: Theme.ink
        opacity: 0.34
    }
    MouseArea { anchors.fill: parent }   // 挡住底层点击

    Rectangle {
        id: card
        anchors.centerIn: parent
        width: Math.min(420, root.width * 0.8)
        height: 252
        radius: Theme.radius
        color: Theme.card
        border.width: 1
        border.color: Theme.lineStrong
        scale: root.shown ? 1.0 : 0.94
        Behavior on scale { NumberAnimation { duration: Theme.durSlow; easing.type: Easing.OutBack } }

        Column {
            anchors.centerIn: parent
            spacing: 14

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "对局结束"
                color: Theme.inkDim
                font.family: Theme.fontBody
                font.pixelSize: 13
                font.letterSpacing: 5
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: controller.status
                color: Theme.cinnabar
                font.family: Theme.fontTitle
                font.pixelSize: 42
                font.weight: Font.DemiBold
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                visible: controller.resultDetail !== ""
                text: controller.resultDetail
                color: Theme.inkDim
                font.family: Theme.fontBody
                font.pixelSize: 13
            }
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 12
                TextButton { text: "再来一局"; accent: true; onClicked: controller.newGame() }
                TextButton { text: "复盘"; onClicked: controller.gotoMove(0) }
            }
        }

        Seal {
            id: seal
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 16
            size: 42
            text: "弈"
            scale: root.shown ? 1.0 : 2.2
            opacity: root.shown ? 0.95 : 0.0
            Behavior on scale { NumberAnimation { duration: Theme.durSlow; easing.type: Easing.OutBack } }
            Behavior on opacity { NumberAnimation { duration: Theme.durBase } }
        }
    }
}
