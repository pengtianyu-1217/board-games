import QtQuick
import "."

Item {
    id: root
    property string text: "弈"
    property int size: 44
    property real sealOpacity: 0.92

    width: size
    height: size
    opacity: sealOpacity

    Rectangle {
        anchors.fill: parent
        radius: 7
        color: Theme.cinnabar
    }
    Rectangle {
        anchors.fill: parent
        anchors.margins: 3
        radius: 4
        color: "transparent"
        border.width: 1.4
        border.color: Theme.card
        opacity: 0.75
    }
    Text {
        anchors.centerIn: parent
        text: root.text
        color: Theme.card
        font.family: Theme.fontTitle
        font.pixelSize: root.size * 0.54
        font.weight: Font.Bold
    }
}
