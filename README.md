# esp-bmgr-py

这个包通过自动注入一段代码到 `idf.py`，为 [ESP Board Manager](https://components.espressif.com/components/espressif/esp_board_manager) 功能提供便捷使用支持。

## 功能特性

- 通过 `.pth` 文件实现自动注入
- 自动查找和设置 board manager 组件路径
- 支持本地组件（`components/esp_board_manager`）和托管组件（`managed_components/espressif__esp_board_manager`）
- 自动下载缺失的 board manager 组件

## 安装

注意：必须要安装在 esp-idf 的虚拟环境中

### 从源码安装

```bash
pip install git+https://github.com/TDA-2030/esp-bmgr-py.git
```

## 工作原理

1. **自动注入**: 通过 `.pth` 文件在 Python 启动时自动导入 `idf_injector` 模块，注册导入钩子

2. **延迟执行**: 使用导入钩子机制，仅在 `idf.py` 导入 `idf_py_actions` 模块时才执行初始化代码（此时 logging 系统已初始化，避免过早执行干扰 CMake 的 Python 检测）

3. **组件查找**: `_main()` 函数执行时，按以下优先级查找 board manager 组件：
   - 优先查找本地组件：检查 `components/esp_board_manager` 或 `components/espressif__esp_board_manager`
   - 检查 manifest 文件中的 `override_path` 配置
   - 如果执行 `gen-bmgr-config` 命令且组件不存在，自动从 manifest 文件读取依赖并下载到 `managed_components/espressif__esp_board_manager`

4. **环境变量设置**: 将找到的 board manager 组件路径添加到 `IDF_EXTRA_ACTIONS_PATH` 环境变量

5. **自动发现**: `idf.py` 会自动扫描 `IDF_EXTRA_ACTIONS_PATH` 目录，发现并加载 board manager 扩展

## 使用方法

安装后，直接使用 `idf.py` 命令：

```bash
idf.py gen-bmgr-config
```

## 调试

设置 `ESP_BMGR_DEBUG=1` 环境变量可查看调试信息：

```bash
export ESP_BMGR_DEBUG=1
idf.py gen-bmgr-config
```

