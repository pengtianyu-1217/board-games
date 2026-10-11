import QtQuick
import "."

Item {
    id: root
    property string text: ""
    property int seq: 0

    visible: opacity > 0
    opacity: 0

    onSeqChanged: if (seq > 0 && text !== "") anim.restart()

    function termColor() {
        if (text === "吃子" || text === "提子" || text === "打吃" || text === "打劫")
            return Theme.gold
        if (text === "禁手")
            return Theme.ink
        if (text === "和棋")
            return Theme.inkDim
        return Theme.cinnabar          // 将军 / 将死 / 连五 / 认输 / 停一手 …
    }

    Rectangle {
        id: wash
        anchors.centerIn: parent
        width: label.implicitWidth + 76
        height: label.implicitHeight + 44
        radius: 8
        color: Theme.paper
        opacity: 0
        border.width: 1
        border.color: root.termColor()
    }

    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: root.termColor()
        font.family: Theme.fontTitle
        font.pixelSize: 54
        font.letterSpacing: 10
        font.weight: Font.Bold
    }

    SequentialAnimation {
        id: anim
        ParallelAnimation {
            NumberAnimation { target: root; property: "opacity"; to: 1.0; duration: 150 }
            NumberAnimation { target: label; property: "scale"; from: 1.7; to: 1.0; duration: 340; easing.type: Easing.OutCubic }
            NumberAnimation { target: wash; property: "opacity"; to: 0.92; duration: 180 }
        }
        PauseAnimation { duration: 780 }
        ParallelAnimation {
            NumberAnimation { target: root; property: "opacity"; to: 0.0; duration: 420 }
            NumberAnimation { target: label; property: "scale"; to: 1.12; duration: 420 }
            NumberAnimation { target: wash; property: "opacity"; to: 0.0; duration: 420 }
        }
    }
}
