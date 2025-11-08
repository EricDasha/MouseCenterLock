# 打包优化说明

## 优化措施

### 1. 排除不必要的模块
在 `MouseCenterLock.spec` 中排除了以下模块以减少文件大小：
- 测试和开发工具（pytest, unittest, pdb 等）
- 文档生成工具（pydoc, sphinx）
- 不需要的 GUI 框架（tkinter, matplotlib）
- 不需要的网络库（urllib3, requests）
- 不需要的科学计算库（numpy, scipy, pandas）
- 不需要的数据库（sqlite3, MySQLdb）
- 不需要的加密库（cryptography）
- 不需要的异步库（asyncio, tornado）
- PySide6 不需要的模块（WebEngine, 3D, Location, Sensors 等）

### 2. 字节码优化
- 使用 `optimize=2` 进行最高级别的 Python 字节码优化
- 压缩 Python 字节码（`a.zipped_data`）

### 3. 性能优化
- 禁用调试模式（`debug=False`）
- 使用单文件模式（`--onefile`）减少文件数量
- 无控制台窗口（`console=False`）

### 4. 文件大小优化
- 排除不必要的模块（见上方列表）
- 使用 UPX 压缩（如果可用）
- 压缩 Python 字节码

## 打包结果

- **文件大小**: 约 44 MB
- **打包类型**: 单文件可执行程序
- **包含内容**:
  - PySide6 GUI 框架
  - keyboard 库
  - 所有必要的 DLL 和依赖
  - 国际化文件（i18n）
  - 资源文件（assets）

## 打包命令

使用优化后的 spec 文件打包：
```bash
pyinstaller --noconfirm --clean MouseCenterLock.spec
```

或使用批处理脚本：
```bash
build_optimized.bat
```

## 进一步优化建议

如果文件大小仍然太大，可以考虑：

1. **使用虚拟环境**: 只安装必要的依赖
2. **排除更多 PySide6 模块**: 如果确定不需要某些功能
3. **使用 UPX 压缩**: 安装 UPX 工具可以进一步减小文件大小
4. **分离资源文件**: 将 i18n 和 assets 作为外部文件（但会增加文件数量）

## 性能测试

打包后的可执行文件应该：
- 启动时间: < 2 秒
- 内存占用: < 100 MB
- CPU 占用: 空闲时 < 1%

## 注意事项

- Windows 上 `strip` 工具不可用，已设置为 `False`
- UPX 压缩可能被某些杀毒软件误报，如遇到问题可禁用
- 首次运行可能需要解压临时文件，后续运行会更快

