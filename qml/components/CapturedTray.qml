import QtQuick
import "."

Item {
    id: root
    property var glyphs: []
    property color ink: Theme.pieceBlack

    implicitHeight: flow.implicitHeight

    Flow {
        id: flow
        width: root.width
        spacing: 4

        Repeater {
            model: root.glyphs
            Rectangle {
                width: 24; height: 24; radius: 12
                color: Theme.pieceIvory
                border.width: 1
                border.color: Theme.lineStrong
                Text {
                    anchors.centerIn: parent
                    text: modelData
                    color: root.ink
                    font.family: Theme.fontBoard
                    font.pixelSize: 14
                }
            }
        }

        Text {
            visible: root.glyphs.length === 0
            text: "尚无"
            color: Theme.inkFaint
            font.family: Theme.fontBody
            font.pixelSize: 13
        }
    }
}
