import QtQuick

Column {
    id: list
    required property var bridge
    required property var theme
    spacing: 4
    visible: bridge.query.length > 0
    width: 520

    Rectangle {
        width: list.width
        height: 52
        radius: 14
        color: list.theme.surface
        border.color: list.theme.accent
        border.width: 2
        Text {
            anchors.verticalCenter: parent.verticalCenter
            x: 18
            text: list.bridge.query
            color: list.theme.foreground
            font.family: list.theme.font
            font.pixelSize: 22
        }
    }

    Repeater {
        model: list.bridge.results
        delegate: Rectangle {
            required property var modelData
            required property int index
            readonly property bool hot: list.bridge.index === index
            width: list.width
            height: 46
            radius: 10
            color: hot ? Qt.alpha(list.theme.accent, 0.3) : Qt.alpha(list.theme.surface, 0.9)
            Image {
                id: icon
                x: 12
                anchors.verticalCenter: parent.verticalCenter
                width: 28; height: 28
                source: parent.modelData.icon ? "image://icon/" + parent.modelData.icon : ""
                sourceSize: Qt.size(64, 64)
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                x: icon.x + icon.width + 12
                width: parent.width - x - 90
                elide: Text.ElideRight
                text: parent.modelData.name
                color: list.theme.foreground
                font.family: list.theme.font
                font.pixelSize: 16
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: 14
                text: parent.modelData.path
                color: list.theme.muted
                font.family: list.theme.font
                font.pixelSize: 12
            }
        }
    }
}
