import dbus
import dbus.service
import dbus.proxies
import dbus.exceptions
from dbus.mainloop.glib import DBusGMainLoop

import collections

from PyQt5.QtCore import QUrl, QObject, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt5.QtQml import qmlRegisterType, QQmlListProperty, QQmlApplicationEngine
from PyQt5.QtWidgets import QApplication
import sys
import signal

from PyQt5.QtGui import QIcon

import resource

signal.signal(signal.SIGINT, signal.SIG_DFL)
DBusGMainLoop(set_as_default=True)


class dbusProperties(dbus.proxies.Interface):

    def __init__(self, service, name, props={}, *a, **kw):
        self._props = {}
        self._props.update(props)
        self.interface = name
        super().__init__(service, 'org.freedesktop.DBus.Properties', *a, **kw)
        self.connect_to_signal('PropertiesChanged', self.update)

    def __getitem__(self, name):
        if name not in self._props:
            self._props.update({name: self.Get(self.interface, name)})
        return self._props[name]

    def __setitem__(self, name, v):
        self.Set(self.interface, name, (v,))
        return self._props.__setitem__(name, v)

    def update(self, interface, data, *a):
        if interface == self.interface:
            self._props.update(data)


class dbusInterface(dbus.proxies.Interface):

    def __init__(self, service, name, *a, **kw):
        super().__init__(service, name, *a, **kw)
        self.props = dbusProperties(service, name)

    def __getitem__(self, name):
        return self.props[name]


class dbusService(dbus.proxies.ProxyObject):
    def __init__(self, *a, **kw):
        super().__init__(dbus.SystemBus(), *a, follow_name_owner_changes=True, **kw)
        self.interfaces = dict()

    def __getitem__(self, name):
        if name in self.interfaces:
            return self.interfaces[name]
        interface = dbusInterface(self, name)
        self.interfaces[name] = interface
        return interface


def service_fabric(service):

    def interfce_fabric(interface, *a, **kw):
        class Base():
            def __init__(self, path, *a, **kw):
                super().__init__(*a, **kw)
                self.ds = dbusService(
                    service,
                    path
                    )
                self.di = self.ds[self.interface_name]

            def connect(self, name, cb):
                self.di.connect_to_signal(name, cb)

        return type(interface, (Base, ), {
                "interface_name": interface
            })

    return interfce_fabric

class AccessPoint(QObject):
    Changed = pyqtSignal()

    def __init__(self,path,*a,**kw):
        super().__init__(*a,**kw)
        self.path = path
        self.di = service_fabric('org.freedesktop.NetworkManager')('org.freedesktop.NetworkManager.AccessPoint')(path).di
        self.di.props.connect_to_signal('PropertiesChanged', lambda *a: self.Changed.emit())

    @pyqtProperty(str, notify=Changed)
    def Ssid(self):
        return bytes(self.di['Ssid']).decode()

    @pyqtProperty(str, notify=Changed)
    def textIcon(self):
        s = self.di['Strength']
        if s > 80:
            return "network-wireless-signal-excellent-symbolic"
        if s > 60:
            return "network-wireless-signal-good-symbolic"
        if s > 40:
            return "network-wireless-signal-ok-symbolic"
        if s > 20:
            return "network-wireless-signal-weak-symbolic"
        return "network-wireless-signal-none-symbolic"

class Device(QObject):
    Changed = pyqtSignal()

    def __init__(self,path,*a,**kw):
        super().__init__(*a,**kw)
        self.di = service_fabric('org.freedesktop.NetworkManager')('org.freedesktop.NetworkManager.Device')(path).di
        self.di.props.connect_to_signal('PropertiesChanged', lambda *a: self.Changed.emit())
        self._aps = []
        di_wireless = False
        if self.di['DeviceType'] == 2:
            self.di_wireless = service_fabric('org.freedesktop.NetworkManager')('org.freedesktop.NetworkManager.Device.Wireless')(path).di
            self.di_wireless.props.connect_to_signal('PropertiesChanged', lambda *a: self.Changed.emit())
            self.di_wireless.connect_to_signal('AccessPointAdded', self.ap_added)
            self.di_wireless.connect_to_signal('AccessPointRemoved', self.ap_removed)
            self._aps = self.GetAccessPoints()


    @pyqtSlot(result=list)
    def GetAccessPoints(self):
        if self.di_wireless:
            r = self.di_wireless.GetAccessPoints()
            return [AccessPoint(d,parent=self) for d in r]
        else:
            return []

    @pyqtProperty(str, notify=Changed)
    def Interface(self):
        return self.di['Interface']

    @pyqtProperty(int, notify=Changed)
    def DeviceType(self):
        return self.di['DeviceType']

    @pyqtProperty(QQmlListProperty, notify=Changed)
    def AccessPoints(self):
        return QQmlListProperty(Device, self, self._aps)

    def ap_added(self, path, *a, **kw):
        self._aps.append(AccessPoint(path, parent=self))
        self.Changed.emit()

    def ap_removed(self, path, *a, **kw):
        for i in range(len(self._aps)):
            if self._aps[i].path == path:
                del self._aps[i]
                break
        self.Changed.emit()


class NetworkManager(QObject):
    Changed = pyqtSignal()

    def __init__(self, parent=None, *a, **kw):
        super().__init__(parent=None, *a, **kw)
        self.di = service_fabric('org.freedesktop.NetworkManager')('org.freedesktop.NetworkManager')('/org/freedesktop/NetworkManager').di
        self._devices = self.GetDevices()
        self.Changed.emit()
        # deprecated self.di.connect_to_signal('PropertiesChanged', lambda x: self.Changed.emit())
        self.di.props.connect_to_signal('PropertiesChanged', lambda *x: self.Changed.emit())
        self.di.connect_to_signal('DeviceAdded', self.device_added)
        self.di.connect_to_signal('DeviceRemoved', self.device_removed)


    @pyqtProperty(QQmlListProperty, notify=Changed)
    def Devices(self):
        return QQmlListProperty(Device, self, self._devices)

    @pyqtSlot(result=list)
    def GetDevices(self):
        r = self.di.GetDevices()
        return [Device(d,parent=self) for d in r]

    def device_added(self, path, *a, **kw):
        self._devices.append(Device(path, parent=self))
        self.Changed.emit()

    def device_removed(self, path, *a, **kw):
        for i in range(len(self._devices)):
            if self._devices[i].path == path:
                del self._devices[i]
                break
        self.Changed.emit()

def main():

    QIcon.setThemeSearchPaths(QIcon.themeSearchPaths()+['/usr/share/icons/'])
    QIcon.setThemeName('Adwaita')

    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()

    qmlRegisterType(NetworkManager, 'NetworkManager', 1, 0, 'NetworkManager')
    qmlRegisterType(Device, 'NetworkManager', 1, 0, 'Device')
    qmlRegisterType(AccessPoint, 'NetworkManager', 1, 0, 'AccessPoint')

    engine.load(QUrl("qrc:/main.qml"))
    return app.exec_()


if __name__ == "__main__":
    main()


