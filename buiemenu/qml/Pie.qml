import QtQuick

Item {
    id: pie
    required property var bridge
    required property var theme
    readonly property real r: theme.radius
    readonly property real cx: bridge.center.x
    readonly property real cy: bridge.center.y

    function px(a, rad) { return cx + rad * Math.sin(a * Math.PI / 180) }
    function py(a, rad) { return cy - rad * Math.cos(a * Math.PI / 180) }
    // the angle the hovered slot points to, or NaN
    readonly property real hoverAngle: bridge.hovered >= 0 ? bridge.slots[bridge.hovered].angle
                                      : bridge.hovered === -1 ? bridge.back : NaN

    // trail of opened submenus, ring, and the hovered wedge
    Canvas {
        id: canvas
        anchors.fill: parent
        onPaint: {
            const g = getContext("2d")
            g.reset()
            const t = pie.bridge.trail
            g.strokeStyle = pie.theme.muted
            g.lineWidth = 2
            g.beginPath()
            t.forEach((p, i) => i ? g.lineTo(p.x, p.y) : g.moveTo(p.x, p.y))
            g.stroke()
            t.slice(0, -1).forEach(p => { g.beginPath(); g.arc(p.x, p.y, 6, 0, 2 * Math.PI); g.fillStyle = pie.theme.muted; g.fill() })

            g.beginPath()
            g.arc(pie.cx, pie.cy, pie.r + pie.theme.item_size * 0.8, 0, 2 * Math.PI)
            g.arc(pie.cx, pie.cy, pie.theme.dead_zone, 0, 2 * Math.PI, true)
            g.fillStyle = Qt.alpha(pie.theme.surface, 0.85)
            g.fill()
            if (isNaN(pie.hoverAngle)) return
            const n = pie.bridge.slots.length + (pie.bridge.back >= 0 ? 1 : 0)
            const half = Math.PI / n, mid = (pie.hoverAngle - 90) * Math.PI / 180
            g.beginPath()
            g.arc(pie.cx, pie.cy, pie.r + pie.theme.item_size * 0.8, mid - half, mid + half)
            g.arc(pie.cx, pie.cy, pie.theme.dead_zone, mid + half, mid - half, true)
            g.fillStyle = Qt.alpha(pie.theme.accent, 0.25)
            g.fill()
        }
        Connections { target: pie.bridge; function onChanged() { canvas.requestPaint() } }
    }

    Repeater {
        model: pie.bridge.slots
        delegate: Rectangle {
            required property var modelData
            required property int index
            readonly property bool hot: pie.bridge.hovered === index
            width: pie.theme.item_size * (hot ? 1.2 : 1)
            height: width
            radius: width / 2
            x: pie.px(modelData.angle, pie.r) - width / 2
            y: pie.py(modelData.angle, pie.r) - height / 2
            color: hot ? pie.theme.accent : pie.theme.surface
            border.color: modelData.menu ? pie.theme.accent : "transparent"
            border.width: 2
            Behavior on width { NumberAnimation { duration: 90 } }
            Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
            Behavior on y { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
            Image {
                anchors.centerIn: parent
                width: parent.width * 0.6
                height: width
                source: parent.modelData.icon ? "image://icon/" + parent.modelData.icon : ""
                sourceSize: Qt.size(64, 64)
            }
            Text {
                anchors.top: parent.bottom
                anchors.topMargin: 4
                anchors.horizontalCenter: parent.horizontalCenter
                text: parent.modelData.name
                color: parent.hot ? pie.theme.foreground : pie.theme.muted
                font.family: pie.theme.font
                font.pixelSize: 11
            }
        }
    }

    // back slot: a small dot toward the parent menu
    Rectangle {
        visible: pie.bridge.back >= 0
        width: 14; height: 14; radius: 7
        x: pie.px(pie.bridge.back, pie.r * 0.75) - 7
        y: pie.py(pie.bridge.back, pie.r * 0.75) - 7
        color: pie.bridge.hovered === -1 ? pie.theme.accent : pie.theme.muted
    }

    Text {
        x: pie.cx - width / 2
        y: pie.cy - height / 2
        width: pie.theme.dead_zone * 3
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        text: pie.bridge.title
        color: pie.theme.foreground
        font.family: pie.theme.font
        font.pixelSize: 14
        font.bold: true
    }
}
