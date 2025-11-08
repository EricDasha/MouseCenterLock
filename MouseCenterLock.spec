# -*- mode: python ; coding: utf-8 -*-

# 优化配置：减少文件大小和提升性能
block_cipher = None

# 排除不必要的模块以减少文件大小
excludes = [
    # 测试和开发工具
    'pytest', 'unittest', 'doctest', 'pdb', 'ipdb',
    # 文档生成
    'pydoc', 'sphinx',
    # 不需要的 GUI 框架
    'tkinter', 'matplotlib', 'PIL.ImageTk',
    # 不需要的网络库
    'urllib3', 'requests', 'httplib2',
    # 不需要的科学计算库
    'numpy', 'scipy', 'pandas',
    # 不需要的数据库
    'sqlite3', 'MySQLdb', 'psycopg2',
    # 不需要的加密库（如果不需要）
    'cryptography',
    # 不需要的异步库
    'asyncio', 'tornado', 'twisted',
    # 不需要的 XML 处理
    'xmlrpc',
    # 不需要的邮件
    'email',
    # 不需要的音频/视频
    'wave', 'audioop',
    # 注意：gettext 不能排除，argparse 需要它
    # 不需要的压缩库（PyInstaller 会处理）
    'bz2', 'lzma',
    # 不需要的并发库
    'multiprocessing.dummy',
    # PySide6 不需要的模块
    'PySide6.QtWebEngine', 'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebEngineCore', 'PySide6.QtWebChannel',
    'PySide6.Qt3D', 'PySide6.Qt3DCore', 'PySide6.Qt3DRender',
    'PySide6.Qt3DInput', 'PySide6.Qt3DLogic', 'PySide6.Qt3DAnimation',
    'PySide6.Qt3DExtras', 'PySide6.QtLocation', 'PySide6.QtPositioning',
    'PySide6.QtSensors', 'PySide6.QtSerialPort', 'PySide6.QtSerialBus',
    'PySide6.QtNfc', 'PySide6.QtBluetooth', 'PySide6.QtWebSockets',
    'PySide6.QtRemoteObjects', 'PySide6.QtScxml',
]

a = Analysis(
    ['mouse_center_lock_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('pythonProject\\i18n', 'i18n'),
        ('config.json', '.'),
        ('pythonProject\\assets', 'assets')
    ],
    hiddenimports=[
        # 确保必要的模块被包含
        'keyboard',
        'keyboard._winkeyboard',
        'keyboard._generic',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'argparse',  # 确保 argparse 被包含
        'gettext',  # 确保 gettext 被包含（argparse 需要）
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 优化：压缩 Python 字节码
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MouseCenterLock',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Windows 上 strip 工具不可用，设为 False
    upx=True,  # 使用 UPX 压缩（如果可用）
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['pythonProject\\assets\\app.ico'],
    # 优化启动性能
    optimize=2,  # Python 字节码优化级别（0-2）
)
