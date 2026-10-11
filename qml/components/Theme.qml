pragma Singleton
import QtQuick

QtObject {
    // ---------------------------------------------------------- 宣纸
    readonly property color paper: "#F3ECDC"
    readonly property color paperDeep: "#E8DFC9"
    readonly property color card: "#FBF6EA"
    readonly property color cardHi: "#FFFBF2"
    readonly property color line: "#D8CCB4"
    readonly property color lineStrong: "#C3B393"

    // ---------------------------------------------------------- 墨
    readonly property color ink: "#2B2620"
    readonly property color inkDim: "#6B6154"
    readonly property color inkFaint: "#9A8F7C"

    // ---------------------------------------------------------- 朱红 / 金
    readonly property color cinnabar: "#9E2B25"
    readonly property color cinnabarHi: "#B8433A"
    readonly property color cinnabarSoft: "#C0564E"
    readonly property color gold: "#B8892E"
    readonly property color goldHi: "#D8B25C"

    // ---------------------------------------------------------- 棋盘
    readonly property color wood: "#E9D6AC"
    readonly property color boardLine: "#3B2A18"
    readonly property color riverInk: "#5A3E24"
    readonly property color pieceIvory: "#F5E6C4"
    readonly property color pieceBlack: "#26221C"
    readonly property color pieceRed: "#9E2B25"

    // ---------------------------------------------------------- 字体
    readonly property var _families: Qt.fontFamilies()

    function pick(list) {
        for (var i = 0; i < list.length; i++)
            if (_families.indexOf(list[i]) !== -1)
                return list[i]
        return list[list.length - 1]
    }

    readonly property string fontTitle: pick(["STXingkai", "华文行楷", "KaiTi", "楷体", "STKaiti", "SimSun", "Microsoft YaHei UI"])
    readonly property string fontBody: pick(["Source Han Serif SC", "Noto Serif SC", "Songti SC", "STZhongsong", "SimSun", "Microsoft YaHei UI"])
    readonly property string fontMono: pick(["JetBrains Mono", "Consolas", "Courier New"])
    readonly property string fontBoard: pick(["KaiTi", "楷体", "STKaiti", "SimSun", "Microsoft YaHei UI"])

    // ---------------------------------------------------------- 尺寸
    readonly property int radius: 10
    readonly property int radiusSm: 6
    readonly property int pad: 18
    readonly property int padSm: 11
    readonly property int gap: 14
    readonly property int topBarH: 64
    readonly property int bottomBarH: 76
    readonly property int drawerW: 360

    // ---------------------------------------------------------- 动效
    readonly property int durFast: 160
    readonly property int durBase: 260
    readonly property int durSlow: 460
    readonly property int durPlace: 240
    readonly property int durDrawer: 320
}
