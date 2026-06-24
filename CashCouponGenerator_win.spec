# -*- mode: python ; coding: utf-8 -*-

# Windows 打包 spec（onedir 模式，便于制作安装包）
# 用法：pyinstaller CashCouponGenerator_win.spec

# 排除不需要的 Qt5 模块
_qt_excludes = [
    'PyQt5.QtQml',
    'PyQt5.QtQuick',
    'PyQt5.QtQuickWidgets',
    'PyQt5.QtQmlModels',
    'PyQt5.QtNetwork',
    'PyQt5.QtWebSockets',
    'PyQt5.QtWebChannel',
    'PyQt5.QtWebEngine',
    'PyQt5.QtWebEngineCore',
    'PyQt5.QtWebEngineWidgets',
    'PyQt5.QtMultimedia',
    'PyQt5.QtMultimediaWidgets',
    'PyQt5.QtOpenGL',
    'PyQt5.QtTest',
    'PyQt5.QtXml',
    'PyQt5.QtXmlPatterns',
    'PyQt5.QtBluetooth',
    'PyQt5.QtPositioning',
    'PyQt5.QtLocation',
    'PyQt5.QtSensors',
    'PyQt5.QtSerialPort',
    'PyQt5.QtSql',
    'PyQt5.Qt3DCore',
    'PyQt5.Qt3DRender',
    'PyQt5.Qt3DInput',
    'PyQt5.Qt3DLogic',
    'PyQt5.Qt3DAnimation',
    'PyQt5.Qt3DExtras',
    'PyQt5.QtCharts',
    'PyQt5.QtDataVisualization',
    'PyQt5.QtHelp',
    'PyQt5.QtNfc',
    'PyQt5.QtRemoteObjects',
    'PyQt5.QtScript',
    'PyQt5.QtScriptTools',
    'PyQt5.QtDesigner',
]

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[('src', 'src'), ('assets', 'assets')],
    hiddenimports=['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.QtSvg', 'PIL'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_qt_excludes,
    noarchive=False,
    optimize=0,
)

# Windows 运行时过滤：移除未使用的 Qt5 动态库与插件
_unused_qt_libs = (
    'Qt5Qml', 'Qt5Quick', 'Qt5QuickWidgets', 'Qt5QmlModels',
    'Qt5Network',
    'Qt5WebSockets', 'Qt5WebChannel', 'Qt5WebEngine', 'Qt5WebEngineCore',
    'Qt5Multimedia', 'Qt5OpenGL', 'Qt5Test', 'Qt5Xml', 'Qt5XmlPatterns',
    'Qt5Bluetooth', 'Qt5Positioning', 'Qt5Location', 'Qt5Sensors',
    'Qt5SerialPort', 'Qt5Sql', 'Qt53D', 'Qt5Charts', 'Qt5DataVisualization',
    'Qt5Help', 'Qt5Nfc', 'Qt5RemoteObjects', 'Qt5Script', 'Qt5Designer',
    'Qt5Concurrent',
)

_unused_plugins = (
    '/plugins/bearer/',
    '/plugins/mediaservice/',
    '/plugins/audio/',
    '/plugins/playlistformats/',
    '/plugins/position/',
    '/plugins/printsupport/',
    '/plugins/sceneparsers/',
    '/plugins/sensor',
    '/plugins/sqldrivers/',
    '/plugins/texttospeech/',
    '/plugins/webview/',
    '/plugins/xcbglintegrations/',
    '/plugins/generic/',
)


def _should_exclude(path):
    p = str(path).replace('\\', '/')
    for lib in _unused_qt_libs:
        if f'/{lib}.' in p or f'\\{lib}.' in p:
            return True
    for plug in _unused_plugins:
        if plug in p:
            return True
    return False


a.binaries = [b for b in a.binaries if not _should_exclude(b[1])]
a.datas = [d for d in a.datas if not _should_exclude(d[1])]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CashGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/AppIcon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CashGenerator',
)
