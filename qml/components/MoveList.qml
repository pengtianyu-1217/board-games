import QtQuick
import "."

ListView {
    id: root
    model: controller.moves
    clip: true
    spacing: 2
    boundsBehavior: Flickable.StopAtBounds

    delegate: Rectangle {
        width: ListView.view.width
        height: 30
        radius: 4
        color: model.current ? Theme.cinnabar
             : (hover.containsMouse ? Theme.paperDeep : "transparent")
        Behavior on color { ColorAnimation { duration: Theme.durFast } }

        Row {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 10
            spacing: 10

            Text {
                width: 30
                anchors.verticalCenter: parent.verticalCenter
                text: model.moveNo + "."
                color: model.current ? Theme.card : Theme.inkFaint
                font.family: Theme.fontMono
                font.pixelSize: 12
            }
            Rectangle {
                width: 7; height: 7; radius: 3.5
                anchors.verticalCenter: parent.verticalCenter
                color: model.side === 1
                     ? (controller.game === "xiangqi" ? Theme.cinnabar : Theme.pieceBlack)
                     : (controller.game === "xiangqi" ? Theme.pieceBlack : Theme.cardHi)
                border.width: 1
                border.color: Theme.lineStrong
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: model.text
                color: model.current ? Theme.card : Theme.ink
                font.family: Theme.fontBody
                font.pixelSize: 14
            }
        }

        MouseArea {
            id: hover
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: controller.gotoMove(model.moveNo)
        }
    }

    onCountChanged: if (contentHeight > height) positionViewAtEnd()
}
