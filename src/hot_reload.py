"""
热更新模块
监听 src/ 目录下 Python 文件的修改事件，自动通过 importlib.reload() 重载变更的模块，
无需重启应用即可看到代码修改效果。基于 watchdog 库实现文件系统监控，
通过环境变量 HOT_RELOAD=1 启用、HOT_RELOAD=0 关闭。
"""

import os
import sys
import time
import importlib
import threading

# 全局开关：设置环境变量 HOT_RELOAD=0 可禁用热更新
HOT_RELOAD_ENABLED = os.environ.get("HOT_RELOAD", "1") != "0"

# 可被热更新的源码模块列表
WATCHED_MODULES = [
    "src.config",
    "src.generate",
    "src.app",
    "src.gui",
]


def _build_module_file_map():
    """构建文件路径到模块名称的映射。"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_dir = os.path.join(base_dir, "src")
    module_map = {}
    for mod_name in WATCHED_MODULES:
        mod_parts = mod_name.split(".")
        py_file = os.path.join(src_dir, *mod_parts[1:]) + ".py"
        module_map[os.path.normpath(py_file)] = mod_name
    return module_map


class HotReloader:
    """文件监视器，在文件变更时重载 Python 模块。

    用法:
        reloader = HotReloader(on_reload_callback=my_callback)
        reloader.start()
        # ... 应用运行 ...
        reloader.stop()

    回调函数接收已重载的模块名称。
    """

    def __init__(self, on_reload_callback=None, debounce_seconds=0.5):
        self.on_reload_callback = on_reload_callback
        self._debounce_seconds = debounce_seconds
        self._last_reload_time = 0
        self._module_file_map = _build_module_file_map()
        self._observer = None
        self._pending_files = {}
        self._pending_lock = threading.Lock()

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._watch_dir = os.path.join(base_dir, "src")

    def start(self):
        """开始监视 src/ 目录的文件变更。"""
        if not HOT_RELOAD_ENABLED:
            print("[HotReload] Disabled (set HOT_RELOAD=1 to enable)")
            return False

        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            print("[HotReload] watchdog not installed. Run: pip install watchdog")
            return False

        class _Handler(FileSystemEventHandler):
            def __init__(self, reloader):
                self.reloader = reloader

            def on_modified(self, event):
                if event.is_directory or not event.src_path.endswith(".py"):
                    return
                self.reloader._schedule_reload(event.src_path)

        self._observer = Observer()
        self._observer.schedule(_Handler(self), self._watch_dir, recursive=False)
        self._observer.daemon = True
        self._observer.start()
        print(f"[HotReload] Watching: {self._watch_dir}")
        return True

    def stop(self):
        """停止监视文件变更。"""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None
            print("[HotReload] Stopped")

    def _schedule_reload(self, file_path):
        """对文件变更事件进行防抖处理，并调度重载。"""
        file_path = os.path.normpath(file_path)
        if file_path not in self._module_file_map:
            return

        now = time.time()
        with self._pending_lock:
            self._pending_files[file_path] = now

        # 使用定时器进行防抖（等待写入完成）
        threading.Timer(self._debounce_seconds, self._process_pending).start()

    def _process_pending(self):
        """在防抖期结束后处理挂起的文件重载。"""
        now = time.time()
        to_reload = []

        with self._pending_lock:
            # 只处理近期未被修改的文件（防抖已稳定）
            settled = {
                fp: ts for fp, ts in self._pending_files.items()
                if now - ts >= self._debounce_seconds
            }
            for fp in settled:
                del self._pending_files[fp]
                to_reload.append(fp)

        for file_path in to_reload:
            self._do_reload(file_path)

    def _do_reload(self, file_path):
        """根据文件路径重载单个模块。"""
        mod_name = self._module_file_map.get(file_path)
        if not mod_name:
            return

        # 节流：避免同一模块被过快重载
        now = time.time()
        if now - self._last_reload_time < 0.3:
            return
        self._last_reload_time = now

        if mod_name not in sys.modules:
            return

        try:
            module = sys.modules[mod_name]
            importlib.reload(module)
            print(f"[HotReload] Reloaded: {mod_name}")

            if self.on_reload_callback:
                self.on_reload_callback(mod_name)
        except Exception as e:
            print(f"[HotReload] Error reloading {mod_name}: {e}")


def reload_module(mod_name):
    """手动按名称重载模块（工具函数）。"""
    if mod_name in sys.modules:
        importlib.reload(sys.modules[mod_name])
