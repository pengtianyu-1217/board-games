import QtQuick
import QtQuick.Layouts
import "."

Item {
    id: drawer
    property bool opened: false
    signal saveRequested()
    signal loadRequested()

    // 墨色遮罩
    Rectangle {
        anchors.fill: parent
        color: Theme.ink
        opacity: drawer.opened ? 0.26 : 0.0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: Theme.durDrawer } }
        MouseArea {
            anchors.fill: parent
            onClicked: drawer.opened = false
        }
    }

    // 右侧宣纸长卷
    Rectangle {
        id: panel
        width: Math.min(Theme.drawerW, drawer.width * 0.9)
        height: drawer.height
        anchors.top: parent.top
        x: drawer.opened ? drawer.width - width : drawer.width
        color: Theme.paper
        border.width: 1
        border.color: Theme.lineStrong
        Behavior on x { NumberAnimation { duration: Theme.durDrawer; easing.type: Easing.OutCubic } }

        Rectangle {
            width: 14
            height: parent.height
            x: -14
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#00000000" }
                GradientStop { position: 1.0; color: "#26000000" }
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.pad
            spacing: Theme.gap

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "棋谱"
                    color: Theme.ink
                    font.family: Theme.fontTitle
                    font.pixelSize: 21
                    font.letterSpacing: 4
                }
                Item { Layout.fillWidth: true }
                TextButton { text: "收起"; onClicked: drawer.opened = false }
            }

            SectionTitle { Layout.fillWidth: true; text: "对局" }

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: controller.status
                    color: Theme.ink
                    font.family: Theme.fontBody
                    font.pixelSize: 16
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: "第 " + controller.moveCount + " 手"
                    color: Theme.inkDim
                    font.family: Theme.fontBody
                    font.pixelSize: 14
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Clock {
                    Layout.fillWidth: true
                    label: controller.playerName(1)
                    seconds: controller.timeFirst
                    running: !controller.gameOver && controller.turn === 1
                    dotColor: controller.game === "xiangqi" ? Theme.cinnabar : Theme.pieceBlack
                }
                Clock {
                    Layout.fillWidth: true
                    label: controller.playerName(2)
                    seconds: controller.timeSecond
                    running: !controller.gameOver && controller.turn === 2
                    dotColor: controller.game === "xiangqi" ? Theme.pieceBlack : Theme.cardHi
                }
            }

            TextButton {
                Layout.fillWidth: true
                visible: controller.reviewing
                text: "返回当前局面"
                accent: true
                onClicked: controller.exitReview()
            }

            SectionTitle { Layout.fillWidth: true; text: "着法" }

            MoveList {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }

            SectionTitle {
                Layout.fillWidth: true
                visible: controller.game !== "gomoku"
                text: controller.game === "go" ? "提子" : "俘虏"
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 28
                visible: controller.game === "go"
                Text {
                    text: "黑提 " + controller.goCaptureFirst + " 子"
                    color: Theme.ink
                    font.family: Theme.fontBody
                    font.pixelSize: 14
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: "白提 " + controller.goCaptureSecond + " 子"
                    color: Theme.ink
                    font.family: Theme.fontBody
                    font.pixelSize: 14
                }
            }

            RowLayout {
                Layout.fillWidth: true
                visible: controller.game === "xiangqi"
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "红俘"; color: Theme.inkDim; font.family: Theme.fontBody; font.pixelSize: 12 }
                    CapturedTray { Layout.fillWidth: true; glyphs: controller.capturedFirst; ink: Theme.pieceBlack }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "黑俘"; color: Theme.inkDim; font.family: Theme.fontBody; font.pixelSize: 12 }
                    CapturedTray { Layout.fillWidth: true; glyphs: controller.capturedSecond; ink: Theme.pieceRed }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                TextButton {
                    Layout.fillWidth: true
                    text: "保存棋谱"
                    onClicked: drawer.saveRequested()
                }
                TextButton {
                    Layout.fillWidth: true
                    text: "打开棋谱"
                    onClicked: drawer.loadRequested()
                }
            }

            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "引擎：" + controller.engineStatus
                color: Theme.inkFaint
                font.family: Theme.fontBody
                font.pixelSize: 12
            }
        }
    }
}
