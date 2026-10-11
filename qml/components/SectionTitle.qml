import QtQuick
import "."

Item {
    id: root
    property string text: ""
    implicitHeight: 26

    Text {
        id: label
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        text: root.text
        color: Theme.inkDim
        font.family: Theme.fontTitle
        font.pixelSize: 15
        font.letterSpacing: 2
    }

    Rectangle {
        height: 1
        color: Theme.line
        anchors.left: label.right
        anchors.leftMargin: 12
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
    }
}
