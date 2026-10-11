import QtQuick
import QtQuick.Layouts
import "."

Rectangle {
    id: root
    property bool opened: false

    visible: opacity > 0
    opacity: opened ? 1.0 : 0.0
    scale: opened ? 1.0 : 0.96
    transformOrigin: Item.TopRight
    width: 296
    implicitHeight: col.implicitHeight + Theme.pad * 2
    radius: Theme.radius
    color: Theme.card
    border.width: 1
    border.color: Theme.lineStrong

    Behavior on opacity { NumberAnimation { duration: Theme.durFast } }
    Behavior on scale { NumberAnimation { duration: Theme.durFast; easing.type: Easing.OutCubic } }

    ColumnLayout {
        id: col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.pad
        spacing: Theme.padSm

        SectionTitle { Layout.fillWidth: true; text: "难度" }
        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            Repeater {
                model: ["简单", "普通", "困难"]
                SegButton {
                    Layout.fillWidth: true
                    text: modelData
                    selected: controller.difficulty === index
                    onClicked: controller.difficulty = index
                }
            }
        }

        SectionTitle { Layout.fillWidth: true; text: "执子"; visible: controller.aiEnabled }
        RowLayout {
            Layout.fillWidth: true
            visible: controller.aiEnabled
            spacing: 6
            Repeater {
                model: controller.game === "xiangqi" ? ["红方", "黑方"] : ["黑方", "白方"]
                SegButton {
                    Layout.fillWidth: true
                    text: modelData
                    selected: controller.humanSide === (index + 1)
                    onClicked: controller.humanSide = index + 1
                }
            }
        }

        SectionTitle { Layout.fillWidth: true; text: "棋盘" }
        Toggle {
            Layout.fillWidth: true
            label: "坐标标注"
            checked: appSettings.coords
            onToggled: appSettings.coords = !appSettings.coords
        }

        SectionTitle { Layout.fillWidth: true; text: "声音" }
        Toggle {
            Layout.fillWidth: true
            label: "音效"
            checked: appSettings.sfxOn
            onToggled: appSettings.sfxOn = !appSettings.sfxOn
        }
        Toggle {
            Layout.fillWidth: true
            label: "背景音乐"
            checked: appSettings.musicOn
            onToggled: appSettings.musicOn = !appSettings.musicOn
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            Text {
                text: "音量"
                color: Theme.ink
                font.family: Theme.fontBody
                font.pixelSize: 14
                Layout.preferredWidth: 34
            }
            Repeater {
                model: [["低", 0.18], ["中", 0.35], ["高", 0.6]]
                SegButton {
                    Layout.fillWidth: true
                    text: modelData[0]
                    selected: Math.abs(appSettings.musicVolume - modelData[1]) < 0.06
                    onClicked: appSettings.musicVolume = modelData[1]
                }
            }
        }

        SectionTitle { Layout.fillWidth: true; text: "快捷键" }
        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 14
            rowSpacing: 3
            Repeater {
                model: [["Ctrl + N", "新局"], ["Ctrl + Z", "悔棋"], ["Esc", "收起浮层"]]
                Text {
                    text: modelData[0]
                    color: Theme.inkDim
                    font.family: Theme.fontMono
                    font.pixelSize: 12
                }
                Text {
                    Layout.fillWidth: true
                    text: modelData[1]
                    color: Theme.ink
                    font.family: Theme.fontBody
                    font.pixelSize: 12
                }
            }
        }

        SectionTitle { Layout.fillWidth: true; text: "引擎" }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Text {
                Layout.fillWidth: true
                text: controller.aiEngine
                color: Theme.inkDim
                font.family: Theme.fontBody
                font.pixelSize: 13
            }
            TextButton { text: "检测"; onClicked: controller.checkEngine() }
        }
    }
}
