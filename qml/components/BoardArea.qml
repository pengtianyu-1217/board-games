import QtQuick
import "."

Item {
    id: area

    readonly property int cols: controller.cols
    readonly property int rows: controller.rows
    readonly property string game: controller.game
    readonly property bool showCoords: appSettings.coords
    readonly property bool inCheck: controller.checkPoint.length === 2

    // 换棋种 / 开新局时整盘淡入
    opacity: 0.0
    Component.onCompleted: enterAnim.start()
    Connections {
        target: controller
        function onGameChanged() { enterAnim.restart() }
    }
    ParallelAnimation {
        id: enterAnim
        NumberAnimation { target: area; property: "opacity"; from: 0.0; to: 1.0; duration: Theme.durBase }
        NumberAnimation { target: area; property: "scale"; from: 0.975; to: 1.0; duration: Theme.durSlow; easing.type: Easing.OutCubic }
    }

    readonly property real cell: Math.max(14, Math.floor(Math.min(
        (width - 14) / (cols + 0.35), (height - 14) / (rows + 0.35))))
    readonly property real gridW: (cols - 1) * cell
    readonly property real gridH: (rows - 1) * cell
    readonly property real ox: Math.round((width - gridW) / 2)
    readonly property real oy: Math.round((height - gridH) / 2)
    readonly property real margin: cell * 0.52

    function px(i) { return ox + i * cell }
    function py(j) { return oy + j * cell }

    function isCheck(x, y) {
        var cp = controller.checkPoint
        return cp.length === 2 && cp[0] === x && cp[1] === y
    }
    function isKo(x, y) {
        var kp = controller.koPoint
        return kp.length === 2 && kp[0] === x && kp[1] === y
    }

    // ------------------------------------------------------- 木底
    Rectangle {
        id: shadow
        x: ox - margin + 2
        y: oy - margin + 4
        width: gridW + margin * 2
        height: gridH + margin * 2
        radius: 12
        color: "#00000022"
    }

    Rectangle {
        id: frame
        x: ox - margin
        y: oy - margin
        width: gridW + margin * 2
        height: gridH + margin * 2
        radius: 12
        clip: true
        color: Theme.wood
        border.width: 1
        border.color: "#00000040"

        Image {
            anchors.fill: parent
            source: Qt.resolvedUrl("../../assets/art/wood_light.png")
            fillMode: Image.PreserveAspectCrop
            smooth: true
            mipmap: true
            opacity: 0.42
        }
        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#FFFFFF12" }
                GradientStop { position: 0.5; color: "#00000000" }
                GradientStop { position: 1.0; color: "#00000016" }
            }
        }
    }

    // ------------------------------------------------------- 棋盘线
    Canvas {
        id: grid
        anchors.fill: parent
        renderStrategy: Canvas.Cooperative
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Component.onCompleted: requestPaint()
        Connections {
            target: area
            function onCellChanged() { grid.requestPaint() }
            function onGameChanged() { grid.requestPaint() }
            function onColsChanged() { grid.requestPaint() }
            function onShowCoordsChanged() { grid.requestPaint() }
        }
        onPaint: area.paintBoard(getContext("2d"))
    }

    function line(ctx, x1, y1, x2, y2) {
        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)
        ctx.stroke()
    }

    function paintBoard(ctx) {
        ctx.reset()
        var s = cell
        ctx.lineCap = "round"
        ctx.lineJoin = "round"

        if (game === "xiangqi") {
            ctx.strokeStyle = Theme.boardLine
            ctx.lineWidth = Math.max(1, s * 0.038)
            for (var y = 0; y < rows; y++) line(ctx, px(0), py(y), px(cols - 1), py(y))
            for (var x = 0; x < cols; x++) {
                if (x === 0 || x === cols - 1) {
                    line(ctx, px(x), py(0), px(x), py(rows - 1))
                } else {
                    line(ctx, px(x), py(0), px(x), py(4))
                    line(ctx, px(x), py(5), px(x), py(rows - 1))
                }
            }
            line(ctx, px(3), py(0), px(5), py(2))
            line(ctx, px(5), py(0), px(3), py(2))
            line(ctx, px(3), py(7), px(5), py(9))
            line(ctx, px(5), py(7), px(3), py(9))

            ctx.lineWidth = Math.max(2, s * 0.08)
            ctx.strokeRect(px(0), py(0), gridW, gridH)

            ctx.fillStyle = Theme.riverInk
            ctx.font = Math.floor(s * 0.46) + "px '" + Theme.fontBoard + "'"
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            ctx.fillText("楚  河", px(2), py(4.5))
            ctx.fillText("汉  界", px(6), py(4.5))
        } else {
            ctx.strokeStyle = Theme.boardLine
            ctx.lineWidth = Math.max(1, s * 0.038)
            for (var c = 0; c < cols; c++) line(ctx, px(c), py(0), px(c), py(rows - 1))
            for (var r = 0; r < rows; r++) line(ctx, px(0), py(r), px(cols - 1), py(r))
            ctx.lineWidth = Math.max(2, s * 0.08)
            ctx.strokeRect(px(0), py(0), gridW, gridH)

            var stars = []
            if (game === "go") {
                var idx = cols === 19 ? [3, 9, 15] : cols === 13 ? [3, 6, 9] : cols === 9 ? [2, 4, 6] : []
                for (var i = 0; i < idx.length; i++)
                    for (var j = 0; j < idx.length; j++)
                        stars.push([idx[i], idx[j]])
            } else {
                var mid = (cols - 1) / 2
                stars = [[mid, mid], [3, 3], [cols - 4, 3], [3, rows - 4], [cols - 4, rows - 4]]
            }
            ctx.fillStyle = Theme.boardLine
            for (var k = 0; k < stars.length; k++) {
                ctx.beginPath()
                ctx.arc(px(stars[k][0]), py(stars[k][1]), Math.max(2, s * 0.09), 0, Math.PI * 2)
                ctx.fill()
            }
        }

        if (showCoords) paintCoords(ctx)
    }

    function coordX(x) {
        if (game === "go") {
            var letters = "ABCDEFGHJKLMNOPQRST"
            return x < letters.length ? letters.charAt(x) : String(x)
        }
        return String(x + 1)
    }

    function paintCoords(ctx) {
        var s = cell
        var d = margin * 0.52
        ctx.fillStyle = Theme.inkFaint
        ctx.font = Math.floor(s * 0.28) + "px '" + Theme.fontBody + "'"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        for (var x = 0; x < cols; x++) {
            var t = coordX(x)
            ctx.fillText(t, px(x), py(0) - d)
            ctx.fillText(t, px(x), py(rows - 1) + d)
        }
        for (var y = 0; y < rows; y++) {
            var u = String(y + 1)
            ctx.fillText(u, px(0) - d, py(y))
            ctx.fillText(u, px(cols - 1) + d, py(y))
        }
    }

    // ------------------------------------------------------- AI 思考扫光
    Item {
        id: thinkSweep
        x: ox - margin
        y: oy - margin
        width: gridW + margin * 2
        height: gridH + margin * 2
        z: 4
        clip: true
        visible: controller.aiThinking
        Rectangle {
            id: sweepBand
            width: thinkSweep.width * 0.4
            height: thinkSweep.height * 1.7
            y: -thinkSweep.height * 0.35
            rotation: 16
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#00FFFFFF" }
                GradientStop { position: 0.5; color: "#3AD8B25C" }
                GradientStop { position: 1.0; color: "#00FFFFFF" }
            }
            NumberAnimation on x {
                running: thinkSweep.visible
                loops: Animation.Infinite
                from: -sweepBand.width
                to: thinkSweep.width
                duration: 1500
                easing.type: Easing.InOutSine
            }
        }
    }

    // ------------------------------------------------------- 将军暗角
    Rectangle {
        id: checkGlow
        x: ox - margin
        y: oy - margin
        width: gridW + margin * 2
        height: gridH + margin * 2
        z: 6
        radius: 12
        color: "transparent"
        visible: area.inCheck
        border.width: Math.max(8, area.cell * 0.5)
        border.color: Theme.cinnabar
        opacity: 0.0
        SequentialAnimation on opacity {
            running: checkGlow.visible
            loops: Animation.Infinite
            NumberAnimation { to: 0.32; duration: 640; easing.type: Easing.InOutSine }
            NumberAnimation { to: 0.04; duration: 640; easing.type: Easing.InOutSine }
        }
    }

    // ------------------------------------------------------- 棋子
    Repeater {
        model: controller.board

        delegate: Item {
            id: cellRoot
            property int gx: index % area.cols
            property int gy: Math.floor(index / area.cols)
            readonly property int owner: model.owner
            readonly property string glyph: model.glyph
            readonly property int mark: model.mark
            readonly property bool empty: owner === 0

            x: area.px(gx) - area.cell / 2
            y: area.py(gy) - area.cell / 2
            width: area.cell
            height: area.cell

            MouseArea {
                id: ma
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: controller.canClick(cellRoot.gx, cellRoot.gy)
                             ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: controller.clickCell(cellRoot.gx, cellRoot.gy)
            }

            // 空位悬停幽灵子
            Rectangle {
                anchors.centerIn: parent
                width: area.cell * 0.84
                height: width
                radius: width / 2
                color: controller.turn === 1
                       ? (area.game === "xiangqi" ? Theme.cinnabar : Theme.pieceBlack)
                       : Theme.cardHi
                opacity: ma.containsMouse && cellRoot.empty && area.game !== "xiangqi"
                         && controller.canClick(cellRoot.gx, cellRoot.gy) ? 0.28 : 0.0
                border.width: 1
                border.color: Theme.lineStrong
                Behavior on opacity { NumberAnimation { duration: Theme.durFast } }
            }

            // 投影
            Rectangle {
                anchors.centerIn: parent
                anchors.verticalCenterOffset: area.cell * 0.06
                width: area.cell * 0.86
                height: width
                radius: width / 2
                color: "#00000040"
                visible: !cellRoot.empty
                scale: piece.scale
                opacity: piece.opacity * 0.8
            }

            Item {
                id: piece
                anchors.centerIn: parent
                width: area.cell * 0.92
                height: width
                visible: !cellRoot.empty
                transform: Translate { id: dropT; y: 0 }
                scale: cellRoot.empty ? 0.3 : 1.0
                opacity: cellRoot.empty ? 0.0 : 1.0
                Behavior on scale { NumberAnimation { duration: Theme.durPlace; easing.type: Easing.OutBack } }
                Behavior on opacity { NumberAnimation { duration: Theme.durPlace } }

                // 围棋 / 五子棋：光滑棋子
                Item {
                    anchors.fill: parent
                    visible: area.game !== "xiangqi"
                    Rectangle {
                        anchors.fill: parent
                        radius: width / 2
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: cellRoot.owner === 1 ? "#5C616A" : "#FFFFFF" }
                            GradientStop { position: 0.62; color: cellRoot.owner === 1 ? "#1F1D1A" : "#EFE9DC" }
                            GradientStop { position: 1.0; color: cellRoot.owner === 1 ? "#0C0B0A" : "#CEC6B3" }
                        }
                        border.width: 1
                        border.color: cellRoot.owner === 1 ? "#00000000" : "#B9B09A"
                    }
                    Rectangle {
                        width: parent.width * 0.34
                        height: width
                        radius: width / 2
                        x: parent.width * 0.2
                        y: parent.height * 0.15
                        color: "#FFFFFF"
                        opacity: cellRoot.owner === 1 ? 0.2 : 0.7
                    }
                }

                // 象棋：圆片 + 汉字
                Item {
                    anchors.fill: parent
                    visible: area.game === "xiangqi"
                    readonly property color ink: cellRoot.owner === 1 ? Theme.pieceRed : Theme.pieceBlack

                    Rectangle {
                        anchors.fill: parent
                        radius: width / 2
                        color: Theme.pieceIvory
                        border.width: Math.max(1, area.cell * 0.05)
                        border.color: parent.ink
                    }
                    Rectangle {
                        anchors.centerIn: parent
                        width: parent.width * 0.76
                        height: width
                        radius: width / 2
                        color: "transparent"
                        border.width: 1
                        border.color: parent.ink
                        opacity: 0.5
                    }
                    Text {
                        anchors.centerIn: parent
                        text: cellRoot.glyph
                        color: parent.ink
                        font.family: Theme.fontBoard
                        font.pixelSize: area.cell * 0.54
                        font.weight: Font.DemiBold
                    }
                }
            }

            // 可走点
            Rectangle {
                anchors.centerIn: parent
                width: area.cell * 0.22
                height: width
                radius: width / 2
                color: Theme.cinnabar
                visible: cellRoot.mark === 3
            }

            // 选中
            Rectangle {
                anchors.centerIn: parent
                width: area.cell * 0.98
                height: width
                radius: width / 2
                color: "transparent"
                border.width: 3
                border.color: Theme.gold
                visible: cellRoot.mark === 2
            }

            // 最后一手
            Rectangle {
                anchors.centerIn: parent
                width: area.cell * 0.9
                height: width
                radius: width / 2
                color: "transparent"
                border.width: 2
                border.color: Theme.cinnabar
                opacity: cellRoot.mark === 1 ? 1.0 : 0.0
                visible: opacity > 0
                Behavior on opacity { NumberAnimation { duration: Theme.durFast } }
            }

            // 连五 / 终局高亮
            Rectangle {
                anchors.centerIn: parent
                width: area.cell
                height: width
                radius: width / 2
                color: "transparent"
                border.width: 3
                border.color: Theme.gold
                visible: cellRoot.mark === 4
                SequentialAnimation on scale {
                    running: cellRoot.mark === 4
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.84; duration: 720; easing.type: Easing.InOutSine }
                    NumberAnimation { to: 1.06; duration: 720; easing.type: Easing.InOutSine }
                }
            }

            // 将军环
            Rectangle {
                anchors.centerIn: parent
                width: area.cell * 1.04
                height: width
                radius: width / 2
                color: "transparent"
                border.width: 3
                border.color: Theme.cinnabarHi
                visible: area.isCheck(cellRoot.gx, cellRoot.gy)
                SequentialAnimation on scale {
                    running: area.isCheck(cellRoot.gx, cellRoot.gy)
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.88; duration: 520; easing.type: Easing.InOutSine }
                    NumberAnimation { to: 1.08; duration: 520; easing.type: Easing.InOutSine }
                }
            }

            // 打劫点
            Rectangle {
                anchors.centerIn: parent
                width: area.cell * 0.46
                height: width
                radius: width / 2
                color: "transparent"
                border.width: 2
                border.color: Theme.gold
                visible: area.isKo(cellRoot.gx, cellRoot.gy)
                SequentialAnimation on opacity {
                    running: visible
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.25; duration: 620 }
                    NumberAnimation { to: 1.0; duration: 620 }
                }
            }

            // 落子涟漪
            Rectangle {
                id: ripple
                anchors.centerIn: parent
                width: area.cell * 0.86
                height: width
                radius: width / 2
                color: "transparent"
                border.width: 3
                border.color: Theme.goldHi
                visible: false
                SequentialAnimation {
                    id: rippleAnim
                    PropertyAction { target: ripple; property: "visible"; value: true }
                    ParallelAnimation {
                        NumberAnimation { target: ripple; property: "scale"; from: 0.5; to: 2.4; duration: 540; easing.type: Easing.OutCubic }
                        NumberAnimation { target: ripple; property: "opacity"; from: 0.95; to: 0.0; duration: 540 }
                    }
                    PropertyAction { target: ripple; property: "visible"; value: false }
                }
                Connections {
                    target: cellRoot
                    function onMarkChanged() {
                        if (cellRoot.mark === 1) {
                            ripple.scale = 1.0
                            ripple.opacity = 0.95
                            rippleAnim.restart()
                            dropAnim.restart()
                        }
                    }
                }
            }

            NumberAnimation {
                id: dropAnim
                target: dropT
                property: "y"
                from: -area.cell * 0.26
                to: 0
                duration: 280
                easing.type: Easing.OutCubic
            }
        }
    }

    // ------------------------------------------------------- 连五描线
    Canvas {
        id: winCanvas
        anchors.fill: parent
        z: 5
        renderStrategy: Canvas.Cooperative
        visible: game === "gomoku" && controller.winLine.length >= 4
        property real progress: 1.0
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onProgressChanged: requestPaint()
        onVisibleChanged: if (visible) { progress = 0.0; winAnim.restart() }
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var wl = controller.winLine
            if (wl.length < 4)
                return
            var x1 = area.px(wl[0]), y1 = area.py(wl[1])
            var x2 = area.px(wl[wl.length - 2]), y2 = area.py(wl[wl.length - 1])
            var ex = x1 + (x2 - x1) * progress
            var ey = y1 + (y2 - y1) * progress
            ctx.lineCap = "round"
            // 外发光
            ctx.strokeStyle = Theme.goldHi
            ctx.globalAlpha = 0.30
            ctx.lineWidth = Math.max(10, area.cell * 0.34)
            ctx.beginPath()
            ctx.moveTo(x1, y1)
            ctx.lineTo(ex, ey)
            ctx.stroke()
            // 主线
            ctx.strokeStyle = Theme.cinnabar
            ctx.globalAlpha = 0.9
            ctx.lineWidth = Math.max(4, area.cell * 0.15)
            ctx.beginPath()
            ctx.moveTo(x1, y1)
            ctx.lineTo(ex, ey)
            ctx.stroke()
        }
        NumberAnimation {
            id: winAnim
            target: winCanvas
            property: "progress"
            from: 0.0; to: 1.0
            duration: 520
            easing.type: Easing.OutCubic
        }
    }

    // ------------------------------------------------------- 被提/被吃棋子飞离
    ListModel { id: ghostModel }

    Connections {
        target: controller
        function onCaptureAnimChanged() {
            ghostModel.clear()
            var items = controller.lastCaptured
            for (var i = 0; i < items.length; ++i) {
                var it = items[i]
                ghostModel.append({ gx: it.x, gy: it.y, owner: it.owner, glyph: it.glyph })
            }
        }
    }

    Repeater {
        model: ghostModel
        delegate: Item {
            id: ghost
            z: 6
            x: area.px(model.gx) - area.cell / 2
            y: area.py(model.gy) - area.cell / 2
            width: area.cell
            height: area.cell

            Rectangle {
                anchors.centerIn: parent
                width: area.cell * 0.7
                height: width
                radius: width / 2
                color: "transparent"
                border.width: 3
                border.color: Theme.goldHi
                SequentialAnimation on scale {
                    running: true
                    NumberAnimation { from: 0.3; to: 2.6; duration: 540; easing.type: Easing.OutCubic }
                }
                SequentialAnimation on opacity {
                    running: true
                    NumberAnimation { from: 0.95; to: 0.0; duration: 540 }
                }
            }

            Item {
                id: ghostPiece
                anchors.centerIn: parent
                width: area.cell * 0.92
                height: width
                transform: Translate { id: rise; y: 0 }

                Item {
                    anchors.fill: parent
                    visible: area.game !== "xiangqi"
                    Rectangle {
                        anchors.fill: parent
                        radius: width / 2
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: model.owner === 1 ? "#5C616A" : "#FFFFFF" }
                            GradientStop { position: 0.62; color: model.owner === 1 ? "#1F1D1A" : "#EFE9DC" }
                            GradientStop { position: 1.0; color: model.owner === 1 ? "#0C0B0A" : "#CEC6B3" }
                        }
                    }
                }

                Item {
                    anchors.fill: parent
                    visible: area.game === "xiangqi"
                    readonly property color ink: model.owner === 1 ? Theme.pieceRed : Theme.pieceBlack
                    Rectangle {
                        anchors.fill: parent
                        radius: width / 2
                        color: Theme.pieceIvory
                        border.width: Math.max(1, area.cell * 0.05)
                        border.color: parent.ink
                    }
                    Text {
                        anchors.centerIn: parent
                        text: model.glyph
                        color: parent.ink
                        font.family: Theme.fontBoard
                        font.pixelSize: area.cell * 0.54
                        font.weight: Font.DemiBold
                    }
                }

                SequentialAnimation {
                    running: true
                    ParallelAnimation {
                        NumberAnimation { target: ghostPiece; property: "scale"; from: 1.0; to: 0.35; duration: 400; easing.type: Easing.InCubic }
                        NumberAnimation { target: ghostPiece; property: "opacity"; from: 1.0; to: 0.0; duration: 400 }
                        NumberAnimation { target: rise; property: "y"; from: 0; to: -area.cell * 0.55; duration: 400; easing.type: Easing.OutCubic }
                    }
                }
            }
        }
    }
}
