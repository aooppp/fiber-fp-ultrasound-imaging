# Windows 打包说明

这个项目可以用 PyInstaller 封装成一个 Windows 桌面应用。

## 打包

在项目目录运行：

```powershell
.\build_windows_app.ps1
```

也可以直接双击：

```text
build_windows_app.bat
```

打包完成后，可执行文件在：

```text
dist\FiberFP_Ultrasound_Imaging\FiberFP_Ultrasound_Imaging.exe
```

## 工作电脑需要提前准备

PyInstaller 会打包 Python 代码和常规 Python 依赖。项目已经内置
`mc600_controller.py` 和 `art_scope_daq.py`，但不会安装厂家系统驱动。
实际使用前请确认工作电脑已经安装：

- 低速采集卡驱动和 Python 接口
- 高速采集卡驱动、SDK 或 DLL
- 激光器串口驱动
- MC600对应的USB转串口驱动（使用RS-232直连时通常不需要额外软件）

如果厂家 DLL 不在系统 PATH 中，需要把对应 DLL 放到 exe 同目录，或者把 DLL 所在目录加入系统 PATH。

ART-SCOPE SDK仍会自动搜索实验电脑上的以下常用位置：

```text
C:\Program Files (x86)\ART Technology\ART-SCOPE\Samples\Python
```

也可以通过环境变量 `ART_SCOPE_PYTHON_PATH` 指定高速采集卡 Python 模块目录。

当前 PCIe8526 使用的 Python 封装输出单位为 mV；应用会按照
`config.DAQ_DRIVER_SCALE_TO_V` 转换成 V 后再显示和保存。
