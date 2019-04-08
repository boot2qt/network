import QtQuick 2.11
import QtQuick.Controls 2.4

import QtQuick.Controls.Material 2.4
import QtQuick.Layouts 1.3


import QtQuick.VirtualKeyboard 2.1
import QtQuick.VirtualKeyboard.Styles 2.1
import QtQuick.VirtualKeyboard.Settings 2.1

import NetworkManager 1.0

ApplicationWindow {

  width: 640
  height: 480

  Component.onCompleted: {
    //VirtualKeyboardSettings.activeLocales = ['en_US','ru_RU']
    this.show()
  }

  NetworkManager {
    id: nm
  }

  Component {
    id: apDelegate
    ItemDelegate {
      text: modelData.Ssid
      width: parent.width
      display: AbstractButton.TextBesideIcon
      icon.name: modelData.textIcon
    }
  }

  Component {
    id: interfaceDelegate
    ColumnLayout {
    ItemDelegate {
        display: AbstractButton.TextBesideIcon
        width: parent.width
        text: modelData.Interface
        onClicked: {
          interfaceInfo.at = index;
        }
      }

    Repeater {
      // clip: true
      // Layout.fillWidth: true
      // interactive: false
      // Layout.fillHeight: true

      // height: childrenRect.height

      // header:
      model: modelData.AccessPoints
      delegate: apDelegate
    }
    }
  }

  RowLayout {
    anchors.fill: parent
    spacing: 8

    ColumnLayout {
      Layout.alignment: Qt.AlignTop | Qt.AlignLeft
      Layout.fillWidth: true
      Layout.fillHeight: true
      Layout.preferredWidth: parent.width / 3
      Repeater {
        model: nm.Devices
        delegate: interfaceDelegate
      }
    }

    ColumnLayout {
      Layout.margins: parent.spacing
      Layout.alignment: Qt.AlignTop | Qt.AlignLeft
      Layout.fillWidth: true
      Layout.fillHeight: true
      Layout.preferredWidth: parent.width / 3 * 2

      id: interfaceInfo
      property int at: 0

      property var device: nm.Devices[at]

      Label {
        text: "Интерфейс: " + parent.device.Interface
      }

      Label {
        text: "Переданно/полученно: " + parent.device.TxBytes +"/"+ parent.device.RxBytes
      }

      Label {
        text: parent.device.RxBytes
      }
    }
  }



}
