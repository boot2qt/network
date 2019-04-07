import QtQuick 2.11
import QtQuick.Controls 2.4

import QtQuick.Controls.Material 2.4
import QtQuick.Layouts 1.3


//import QtQuick.VirtualKeyboard 2.2
//import QtQuick.VirtualKeyboard.Styles 2.2
//import QtQuick.VirtualKeyboard.Settings 2.2

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
      icon.name: modelData.signalIcon
    }
  }

  Component {
    id: interfaceDelegate
    ListView {
      Layout.fillWidth: true
      Layout.fillHeight: true
      header: ItemDelegate {
        display: AbstractButton.TextBesideIcon
        icon.name: modelData.textIcon
        width: parent.width
        text: modelData.Interface
        onClicked: {
          interfaceInfo.at = index;
        }
      }
      model: modelData.AccessPoints
      delegate: apDelegate
    }
  }

  RowLayout {
    anchors.fill: parent
    spacing: 8

    ColumnLayout {
      Layout.fillWidth: true
      Layout.fillHeight: true
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
      Layout.preferredWidth: parent.width / 2
      id: interfaceInfo
      property int at: 0

      property var device: nm.Devices[at]

      Label {
        text: "Интерфейс: " + parent.device.Interface
      }

      Label {
        text: ""
      }
    }
  }



}
