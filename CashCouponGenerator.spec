# -*- mode: python ; coding: utf-8 -*-

# 排除的 Qt5 模块（项目只需 QtCore/QtGui/QtWidgets/QtSvg）
# 注意：
#   - QtDBus 和 QtPrintSupport 是 cocoa 平台插件的隐式依赖，不能排除
#   - QtSvg 用于渲染 QComboBox 下拉箭头的 SVG 图标，不能排除
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
    hiddenimports=['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PIL'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_qt_excludes,
    noarchive=False,
    optimize=0,
)

# 运行时过滤：移除未使用的 Qt5 动态库、framework 与插件
# 注意：
#   - QtDBus 和 QtPrintSupport 是 cocoa 插件的依赖，不能排除
#   - QtSvg 用于 QSS 下拉箭头 SVG 渲染，不能排除
_unused_qt_libs = (
    'QtQml', 'QtQuick', 'QtQuickWidgets', 'QtQmlModels',
    'QtNetwork',
    'QtWebSockets', 'QtWebChannel', 'QtWebEngine', 'QtWebEngineCore',
    'QtMultimedia', 'QtOpenGL', 'QtTest', 'QtXml', 'QtXmlPatterns',
    'QtBluetooth', 'QtPositioning', 'QtLocation', 'QtSensors',
    'QtSerialPort', 'QtSql', 'Qt3D', 'QtCharts', 'QtDataVisualization',
    'QtHelp', 'QtNfc', 'QtRemoteObjects', 'QtScript', 'QtDesigner',
    'QtConcurrent',
)

# 排除不需要的 Qt plugins
# 保留：platforms/cocoa、styles、platformthemes、imageformats（SVG）、iconengines（SVG 图标）
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
    # 排除未使用的 Qt lib/framework
    for lib in _unused_qt_libs:
        if f'/{lib}.framework/' in p or f'/{lib}.' in p and '/Qt5/' in p:
            return True
    # 排除未使用的 plugins
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
    name='Cash生成器',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Cash生成器',
)
app = BUNDLE(
    coll,
    name='Cash生成器.app',
    icon='assets/AppIcon.icns',
    bundle_identifier='com.cashgenerator.app',
)
