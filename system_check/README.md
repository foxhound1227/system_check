# 系统巡检工具 (System Check)

一个用于 Windows/Linux 系统巡检的图形化工具，支持多设备巡检报告汇总和导出。

## 功能特点

- 图形化界面操作
- 支持检测以下信息：
  - 系统基本信息（主机名、系统版本、运行时间）
  - 资源使用情况（内存、磁盘）
  - 关键服务运行状态
- 自动生成 CSV 格式报告
- 支持多设备巡检报告汇总
- HTML 格式报告导出
- 可配置的告警阈值

## 使用方法

### 直接运行

双击运行 `SystemCheck.exe`，通过图形界面操作：

1. 选择日志文件目录
2. 点击"生成报告"
3. 使用"查看报告"按钮查看结果

### 告警阈值

- 内存使用率: 80%
- 磁盘使用率: 80%

### 监控服务

- updpi.service
- upp.service
- upload.service
- logtar.service
- tnlinfo_proxy.service

## 报告格式

- CSV格式：详细的检查数据
- HTML格式：汇总报告，支持多设备数据对比

## 开发环境

- Python 3.13
- PyInstaller 6.12.0
- Windows 10

## 作者

foxhound1227

## 许可证

MIT License