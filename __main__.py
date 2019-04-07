import dbus
import dbus.service
import dbus.proxies
import dbus.exceptions
from dbus.mainloop.glib import DBusGMainLoop

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

    def __getitem__(self, name):
        if name not in self._props:
            self._props.update({name: self.Get(self.interface, name)})
        return self._props[name]

    def __setitem__(self, name, v):
        self.Set(self.interface, name, (v,))
        return self._props.__setitem__(name, v)

    def update(self, d):
        self._props.update(d)


class dbusInterface(dbus.proxies.Interface):

    def __init__(self, service, name, *a, **kw):
        super().__init__(service, name, *a, **kw)
        self.props = dbusProperties(service, name)
        self.connect_to_signal('PropertiesChanged', self.props.update)

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


class BSS(QObject):
    Changed = pyqtSignal()

    def __init__(self, path, parent=None, props={}, *a, **kw):
        super().__init__(parent=parent, *a, **kw)
        self.path = path
        self.interface = service_fabric(
            'fi.w1.wpa_supplicant1')(
            'fi.w1.wpa_supplicant1.BSS')(
            path)
        self.interface.di.props.update(props)
        self.interface.connect('PropertiesChanged', lambda x: self.Changed.emit())

    @pyqtProperty(str, notify=Changed)
    def SSID(self):
        return bytes(self.interface.di['SSID']).decode()

    @pyqtProperty(int, notify=Changed)
    def Signal(self):
        return self.interface.di['Signal']

    @pyqtProperty(str, notify=Changed)
    def signalIcon(self):
        s = self.interface.di['Signal']

        if s > -40:
            return "network-wireless-signal-excellent-symbolic"
        if s > -50:
            return "network-wireless-signal-good-symbolic"
        if s > -60:
            return "network-wireless-signal-ok-symbolic"
        if s > -70:
            return "network-wireless-signal-weak-symbolic"

        return "network-wireless-signal-none-symbolic"


class Interface(QObject):
    Changed = pyqtSignal()
    BSSsChanged = pyqtSignal()

    def __init__(self, path, parent=None, props={}, *a, **kw):
        super().__init__(parent=parent, *a, **kw)
        self.path = path
        self.interface = service_fabric('fi.w1.wpa_supplicant1')(
            'fi.w1.wpa_supplicant1.Interface')(path)
        self.interface.di.props.update(props)
        self.interface.connect('PropertiesChanged', lambda x: self.Changed.emit())
        self.interface.connect('BSSAdded', self.add_bss)
        self.interface.connect('BSSRemoved', self.rem_bss)
        self._bsss = []
        self.load()

    def load(self):
        self._bsss = [BSS(path, parent=self) for path in self.interface.di['BSSs']]
        self.BSSsChanged.emit()

    def rem_bss(self, path, *a, **kw):
        for i in range(len(self._bsss)):
            if self._bsss[i].path == path:
                del self._bsss[i]
                break

        self.BSSsChanged.emit()

    def add_bss(self, path, props={}, *a, **kw):
        self._bsss.append(BSS(path, parent=self, props=props))
        self.BSSsChanged.emit()

    @pyqtProperty(str, notify=Changed)
    def Ifname(self):
        return self.interface.di['Ifname']

    @pyqtProperty(str, notify=Changed)
    def textState(self):
        s = [self.interface.di['State']]
        if self.interface.di['Scanning']:
            s.append('поиск сети')

        return ",".join(s)

    @pyqtProperty(str, notify=Changed)
    def textIcon(self):
        if self.interface.di['Scanning']:
            return "network-wireless-acquiring-symbolic"
        return ""

    @pyqtProperty(bool, notify=Changed)
    def Scanning(self):
        return self.interface.di['Scanning']

    @pyqtProperty(QQmlListProperty, notify=BSSsChanged)
    def BSSs(self):
        return QQmlListProperty(BSS, self, self._bsss)

    @pyqtSlot()
    def Scan(self):
        try:
            self.interface.di.get_dbus_method('FlushBSS')(15)
            self.interface.di.get_dbus_method('Scan')({'Type': "active"})
        except dbus.exceptions.DBusException:
            pass


class WiFi(QObject):
    Changed = pyqtSignal()
    InterfacesChanged = pyqtSignal()

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._interfaces = []
        self.wifi = service_fabric('fi.w1.wpa_supplicant1')(
            'fi.w1.wpa_supplicant1')('/fi/w1/wpa_supplicant1')
        self.load()
        self.wifi.connect('InterfaceAdded', self.add_if)
        self.wifi.connect('InterfaceRemoved', self.rem_if)

    def add_if(self, path, props, *a, **kw):
        self._interfaces.append(Interface(path, parent=self, props=props))
        self.InterfacesChanged.emit()

    def rem_if(self, path, *a, **kw):
        for i in range(len(self._interfaces)):
            if self._interfaces[i].path == path:
                del self._interfaces[i]
                break
        self.InterfacesChanged.emit()

    def load(self):
        self._interfaces = [
            Interface(path, parent=self) for path in self.wifi.di['Interfaces']
            ]
        self.InterfacesChanged.emit()

    @pyqtProperty(QQmlListProperty, notify=InterfacesChanged)
    def Interfaces(self):
        return QQmlListProperty(Interface, self, self._interfaces)


def main():

    QIcon.setThemeSearchPaths(QIcon.themeSearchPaths()+['/usr/share/icons/'])
    QIcon.setThemeName('Adwaita')

    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()

    qmlRegisterType(WiFi, 'WiFi', 1, 0, 'WiFi')
    qmlRegisterType(Interface, 'WiFi', 1, 0, 'Interface')
    qmlRegisterType(BSS, 'WiFi', 1, 0, 'BSS')

    engine.load(QUrl("qrc:/main.qml"))
    return app.exec_()


if __name__ == "__main__":
    main()


