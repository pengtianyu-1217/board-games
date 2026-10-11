import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtMultimedia
import "components"

ApplicationWindow {
    id: root
    width: 1200
    height: 820
    minimumWidth: 900
    minimumHeight: 640
    visible: true
    title: "三棋对弈"
    color: Theme.paper

    // 宽窗时在棋盘两侧显示双方信息栏（减少留白）
    readonly property int cardW: width > 1080 ? 150 : 0

    function sideDetail(side) {
        if (controller.game === "go")
            return "提子 " + (side === 1 ? controller.goCaptureFirst : controller.goCaptureSecond)
        if (controller.game === "xiangqi")
            return "俘虏 " + (side === 1 ? controller.capturedFirst.length : controller.capturedSecond.length)
        return ""
    }

    function play(sfx) {
        if (appSettings.sfxOn)
            sfx.play()
    }

    property var pendingAction: null

    function ask(title, message, action) {
        pendingAction = action
        confirm.title = title
        confirm.message = message
        confirm.opened = true
    }

    function runPending() {
        var f = pendingAction
        pendingAction = null
        if (f)
            f()
    }

    function startNew() {
        if (controller.moveCount > 0 && !controller.gameOver)
            ask("开始新局？", "当前对局将作废。", function () { controller.newGame() })
        else
            controller.newGame()
    }

    function swapSides() {
        if (controller.moveCount > 0 && !controller.gameOver)
            ask("换边重开？", "当前对局将作废。", function () {
                controller.humanSide = controller.humanSide === 1 ? 2 : 1
            })
        else
            controller.humanSide = controller.humanSide === 1 ? 2 : 1
    }

    function askResign() {
        ask("确认认输？", "本局将判你负。", function () { controller.resign() })
    }

    Shortcut { sequence: "Ctrl+Z"; onActivated: controller.undo() }
    Shortcut { sequence: "Ctrl+N"; onActivated: root.startNew() }
    Shortcut {
        sequences: [StandardKey.Cancel]
        onActivated: { drawer.opened = false; settings.opened = false }
    }

    // ---------------------------------------------------------- 音效 / 音乐
    SoundEffect { id: sfxPlace;        source: Qt.resolvedUrl("../assets/audio/place.wav") }
    SoundEffect { id: sfxPlaceStone;   source: Qt.resolvedUrl("../assets/audio/place_stone.wav") }
    SoundEffect { id: sfxCapture;      source: Qt.resolvedUrl("../assets/audio/capture.wav") }
    SoundEffect { id: sfxCaptureStone; source: Qt.resolvedUrl("../assets/audio/capture_stone.wav") }
    SoundEffect { id: sfxCheck;        source: Qt.resolvedUrl("../assets/audio/check.wav") }
    SoundEffect { id: sfxAtari;        source: Qt.resolvedUrl("../assets/audio/atari.wav") }
    SoundEffect { id: sfxKo;           source: Qt.resolvedUrl("../assets/audio/ko.wav") }
    SoundEffect { id: sfxForbidden;    source: Qt.resolvedUrl("../assets/audio/forbidden.wav") }
    SoundEffect { id: sfxWin;          source: Qt.resolvedUrl("../assets/audio/win.wav") }
    SoundEffect { id: sfxLose;         source: Qt.resolvedUrl("../assets/audio/lose.wav") }
    SoundEffect { id: sfxDraw;         source: Qt.resolvedUrl("../assets/audio/draw.wav") }
    SoundEffect { id: sfxClick;        source: Qt.resolvedUrl("../assets/audio/click.wav") }
    SoundEffect { id: sfxSelect;       source: Qt.resolvedUrl("../assets/audio/select.wav") }
    SoundEffect { id: sfxPass;         source: Qt.resolvedUrl("../assets/audio/pass.wav") }
    SoundEffect { id: sfxUndo;         source: Qt.resolvedUrl("../assets/audio/undo.wav") }
    SoundEffect { id: sfxNewGame;      source: Qt.resolvedUrl("../assets/audio/newgame.wav") }
    SoundEffect { id: sfxError;        source: Qt.resolvedUrl("../assets/audio/error.wav") }
    SoundEffect { id: sfxDrawer;       source: Qt.resolvedUrl("../assets/audio/drawer.wav") }
    SoundEffect { id: sfxPanelOpen;    source: Qt.resolvedUrl("../assets/audio/panel_open.wav") }
    SoundEffect { id: sfxPanelClose;   source: Qt.resolvedUrl("../assets/audio/panel_close.wav") }

    function bgmTrack() {
        if (controller.game === "xiangqi")
            return "../assets/audio/bgm_martial.wav"
        if (controller.game === "go")
            return "../assets/audio/bgm_void.wav"
        return "../assets/audio/bgm_guqin.wav"
    }

    MediaPlayer {
        id: bgm
        source: Qt.resolvedUrl(root.bgmTrack())
        loops: MediaPlayer.Infinite
        audioOutput: AudioOutput {
            volume: appSettings.musicOn ? appSettings.musicVolume : 0.0
        }
        Component.onCompleted: if (appSettings.musicOn) play()
    }
    onClosing: bgm.stop()

    Connections {
        target: controller
        function onMoveMade(kind) {
            var term = controller.eventTerm
            if (kind === "win" || kind === "lose") {
                if (term === "禁手")
                    play(sfxForbidden)
                else if (term === "和棋")
                    play(sfxDraw)
                else
                    play(kind === "win" ? sfxWin : sfxLose)
            } else if (kind === "capture") {
                play(controller.game === "xiangqi" ? sfxCapture : sfxCaptureStone)
                flashAnim.restart()
            } else if (kind === "atari") {
                play(sfxAtari)
            } else if (kind === "check") {
                play(sfxCheck)
            } else if (kind === "pass") {
                play(sfxPass)
            } else if (term === "打劫") {
                play(sfxKo)
            } else {
                play(controller.game === "xiangqi" ? sfxPlace : sfxPlaceStone)
            }
        }
        function onNotice(msg) { toast.show(msg) }
        function onPieceSelected() { play(sfxSelect) }
        function onIllegalMove() { play(sfxError) }
        function onGameChanged() {
            bgm.stop()
            if (appSettings.musicOn)
                bgm.play()
        }
    }

    // ---------------------------------------------------------- 背景
    background: Rectangle {
        color: Theme.paper
        Image {
            anchors.fill: parent
            source: Qt.resolvedUrl("../assets/art/paper.png")
            fillMode: Image.PreserveAspectCrop
            smooth: true
            opacity: 0.62
        }
        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#00000000" }
                GradientStop { position: 1.0; color: "#12000000" }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ------------------------------------------------------ 顶栏
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.topBarH

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.pad
                anchors.rightMargin: Theme.pad
                spacing: Theme.gap

                RowLayout {
                    spacing: 12
                    Seal { size: 36; text: "弈" }
                    Column {
                        Text {
                            text: "三棋对弈"
                            color: Theme.ink
                            font.family: Theme.fontTitle
                            font.pixelSize: 24
                            font.letterSpacing: 4
                        }
                        Text {
                            text: "中国象棋 · 围棋 · 五子棋"
                            color: Theme.inkFaint
                            font.family: Theme.fontBody
                            font.pixelSize: 11
                            font.letterSpacing: 3
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                Row {
                    spacing: 8
                    SegButton {
                        text: "五子棋"; selected: controller.game === "gomoku"
                        onClicked: { play(sfxClick); controller.newGame("gomoku") }
                    }
                    SegButton {
                        text: "象棋"; selected: controller.game === "xiangqi"
                        onClicked: { play(sfxClick); controller.newGame("xiangqi") }
                    }
                    SegButton {
                        text: "围棋"; selected: controller.game === "go"
                        onClicked: { play(sfxClick); controller.newGame("go") }
                    }
                }

                Row {
                    spacing: 6
                    Rectangle {
                        width: 8; height: 8; radius: 4
                        anchors.verticalCenter: parent.verticalCenter
                        color: controller.aiEnabled ? Theme.gold : Theme.inkFaint
                        border.width: 1
                        border.color: Theme.lineStrong
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: controller.aiEnabled ? controller.aiEngine : "双人对下"
                        color: Theme.inkDim
                        font.family: Theme.fontBody
                        font.pixelSize: 12
                    }
                }

                Row {
                    spacing: 8
                    TextButton {
                        text: "棋谱"
                        onClicked: {
                            play(sfxDrawer)
                            drawer.opened = !drawer.opened
                            settings.opened = false
                        }
                    }
                    TextButton {
                        id: settingsBtn
                        text: "设置"
                        onClicked: {
                            var open = !settings.opened
                            play(open ? sfxPanelOpen : sfxPanelClose)
                            settings.opened = open
                            drawer.opened = false
                        }
                    }
                }
            }
        }

        // ------------------------------------------------------ 棋盘（两侧为对局双方信息栏）
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            PlayerCard {
                Layout.preferredWidth: root.cardW
                Layout.fillHeight: true
                Layout.leftMargin: Theme.pad
                visible: root.cardW > 0
                label: controller.playerName(1)
                seconds: controller.timeFirst
                running: !controller.gameOver && controller.turn === 1
                dotColor: controller.game === "xiangqi" ? Theme.cinnabar : Theme.pieceBlack
                detail: root.sideDetail(1)
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
                BoardArea {
                    anchors.fill: parent
                    anchors.margins: Theme.pad
                }
                TermBanner {
                    anchors.centerIn: parent
                    text: controller.eventTerm
                    seq: controller.eventSeq
                }
            }

            PlayerCard {
                Layout.preferredWidth: root.cardW
                Layout.fillHeight: true
                Layout.rightMargin: Theme.pad
                visible: root.cardW > 0
                label: controller.playerName(2)
                seconds: controller.timeSecond
                running: !controller.gameOver && controller.turn === 2
                dotColor: controller.game === "xiangqi" ? Theme.pieceBlack : Theme.cardHi
                detail: root.sideDetail(2)
            }
        }

        // ------------------------------------------------------ 底栏
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.bottomBarH
            color: Theme.card
            border.width: 1
            border.color: Theme.line

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.pad
                anchors.rightMargin: Theme.pad
                spacing: Theme.padSm

                Row {
                    spacing: 10
                    Rectangle {
                        id: turnDot
                        width: 12; height: 12; radius: 6
                        anchors.verticalCenter: parent.verticalCenter
                        border.width: 1
                        border.color: Theme.lineStrong
                        color: {
                            if (controller.gameOver) return Theme.gold
                            if (controller.turn === 1)
                                return controller.game === "xiangqi" ? Theme.cinnabar : Theme.pieceBlack
                            return controller.game === "xiangqi" ? Theme.pieceBlack : Theme.cardHi
                        }
                        Behavior on color { ColorAnimation { duration: Theme.durBase } }
                        SequentialAnimation on opacity {
                            running: controller.aiThinking
                            loops: Animation.Infinite
                            NumberAnimation { to: 0.25; duration: 480 }
                            NumberAnimation { to: 1.0; duration: 480 }
                        }
                    }
                    Column {
                        Text {
                            text: controller.status
                            color: Theme.ink
                            font.family: Theme.fontBody
                            font.pixelSize: 17
                            font.weight: Font.DemiBold
                        }
                        Text {
                            text: {
                                if (controller.gameOver)
                                    return controller.resultDetail
                                if (controller.aiThinking)
                                    return "对手思考中 · " + controller.aiEngine + " · " + controller.thinkSeconds + "s"
                                return "第 " + controller.moveCount + " 手 · " + controller.difficultyText
                                     + (controller.aiEnabled
                                        ? (" · 你执" + controller.playerName(controller.humanSide))
                                        : " · 双人对下")
                            }
                            color: controller.aiThinking ? Theme.cinnabar : Theme.inkDim
                            font.family: Theme.fontBody
                            font.pixelSize: 12
                        }
                    }
                }

                Item { Layout.preferredWidth: 8 }

                Clock {
                    visible: root.cardW === 0
                    label: controller.playerName(1)
                    seconds: controller.timeFirst
                    running: !controller.gameOver && controller.turn === 1
                    dotColor: controller.game === "xiangqi" ? Theme.cinnabar : Theme.pieceBlack
                }
                Clock {
                    visible: root.cardW === 0
                    label: controller.playerName(2)
                    seconds: controller.timeSecond
                    running: !controller.gameOver && controller.turn === 2
                    dotColor: controller.game === "xiangqi" ? Theme.pieceBlack : Theme.cardHi
                }

                Item { Layout.fillWidth: true }

                Row {
                    spacing: 8
                    TextButton {
                        text: "新局"; accent: true
                        onClicked: { play(sfxNewGame); root.startNew() }
                    }
                    TextButton {
                        text: "悔棋"; active: controller.canUndo
                        onClicked: { play(sfxUndo); controller.undo() }
                    }
                    TextButton {
                        text: "停一手"; visible: controller.game === "go"
                        active: controller.canPass
                        onClicked: { play(sfxClick); controller.passMove() }
                    }
                    TextButton {
                        text: "换边"; visible: controller.aiEnabled
                        onClicked: { play(sfxClick); root.swapSides() }
                    }
                    TextButton {
                        text: "认输"; active: !controller.gameOver
                        onClicked: { play(sfxClick); root.askResign() }
                    }
                    TextButton {
                        text: controller.aiEnabled ? "AI 对弈：开" : "AI 对弈：关"
                        onClicked: { play(sfxClick); controller.aiEnabled = !controller.aiEnabled }
                    }
                }
            }
        }
    }

    // ---------------------------------------------------------- 浮层
    MouseArea {
        anchors.fill: parent
        z: 15
        enabled: settings.opened
        visible: settings.opened
        onClicked: settings.opened = false
    }

    SettingsPopover {
        id: settings
        objectName: "settings"
        z: 20
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: Theme.topBarH - 6
        anchors.rightMargin: Theme.pad
    }

    MoveDrawer {
        id: drawer
        objectName: "drawer"
        z: 25
        anchors.fill: parent
        onSaveRequested: saveDialog.open()
        onLoadRequested: loadDialog.open()
    }

    EndOverlay {
        id: endOverlay
        z: 30
        anchors.fill: parent
        shown: controller.gameOver
    }

    ConfirmPopup {
        id: confirm
        objectName: "confirm"
        z: 40
        anchors.fill: parent
        onConfirmed: root.runPending()
    }

    // 吃子闪光
    Rectangle {
        id: flash
        anchors.fill: parent
        z: 18
        color: Theme.gold
        opacity: 0
        SequentialAnimation on opacity {
            id: flashAnim
            running: false
            NumberAnimation { to: 0.14; duration: 60 }
            NumberAnimation { to: 0.0; duration: 280 }
        }
    }

    // 提示条
    Rectangle {
        id: toast
        z: 35
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.bottomBarH + 18
        width: toastText.implicitWidth + Theme.pad * 1.6
        height: 42
        radius: Theme.radiusSm
        color: Theme.ink
        opacity: 0
        visible: opacity > 0

        function show(msg) {
            toastText.text = msg
            toastAnim.restart()
        }

        Text {
            id: toastText
            anchors.centerIn: parent
            color: Theme.card
            font.family: Theme.fontBody
            font.pixelSize: 14
        }

        SequentialAnimation {
            id: toastAnim
            NumberAnimation { target: toast; property: "opacity"; to: 1.0; duration: 180 }
            PauseAnimation { duration: 1900 }
            NumberAnimation { target: toast; property: "opacity"; to: 0.0; duration: 340 }
        }
    }

    // ---------------------------------------------------------- 文件对话框
    FileDialog {
        id: saveDialog
        title: "保存棋谱"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "json"
        nameFilters: ["棋谱文件 (*.json)", "棋谱文本 (*.txt)", "象棋 FEN (*.fen)", "围棋 SGF (*.sgf)"]
        onAccepted: controller.saveGame(selectedFile.toString())
    }
    FileDialog {
        id: loadDialog
        title: "打开棋谱"
        fileMode: FileDialog.OpenFile
        nameFilters: ["棋谱文件 (*.json)"]
        onAccepted: controller.loadGame(selectedFile.toString())
    }
}
