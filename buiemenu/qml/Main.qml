import QtQuick
import QtQuick.Window

Window {
    id: root
    required property var bridge
    readonly property var theme: bridge.theme

    visibility: Window.FullScreen
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    color: "transparent"
    visible: true
    title: "buiemenu"

    Rectangle {
        anchors.fill: parent
        color: root.theme.background
        opacity: 0
        Component.onCompleted: opacity = 1
        Behavior on opacity { NumberAnimation { duration: 120 } }
    }

    Pie {
        anchors.fill: parent
        bridge: root.bridge
        theme: root.theme
        opacity: root.bridge.query ? 0.25 : 1
        Behavior on opacity { NumberAnimation { duration: 100 } }
    }

    Results {
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height * 0.18
        bridge: root.bridge
        theme: root.theme
    }

    // the gesture detector's pause check
    Timer { interval: 16; repeat: true; running: true; onTriggered: root.bridge.tick() }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onPressed: e => e.button === Qt.RightButton ? root.bridge.back_out() : root.bridge.press(e.x, e.y)
        onReleased: e => { if (e.button === Qt.LeftButton) root.bridge.release(e.x, e.y) }
        onPositionChanged: e => root.bridge.move(e.x, e.y)
    }

    Item {
        focus: true
        Keys.onPressed: e => {
            switch (e.key) {
            case Qt.Key_Escape: root.bridge.cancel(); break
            case Qt.Key_Backspace: root.bridge.erase(); break
            case Qt.Key_Up: root.bridge.step(-1); break
            case Qt.Key_Down: case Qt.Key_Tab: root.bridge.step(1); break
            case Qt.Key_Return: case Qt.Key_Enter: root.bridge.accept(); break
            default:
                if (e.text.length === 0 || e.text < " " || (e.modifiers & Qt.ControlModifier)) return
                root.bridge.type(e.text)
            }
            e.accepted = true
        }
    }
}
