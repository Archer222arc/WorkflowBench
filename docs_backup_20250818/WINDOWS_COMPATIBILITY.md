# Windows兼容性指南

## 📋 兼容性状态总览

| 组件 | Windows原生 | WSL | Git Bash | 解决方案 |
|------|------------|-----|----------|----------|
| Python脚本 (.py) | ✅ 部分支持 | ✅ | ✅ | 需要小修改 |
| Shell脚本 (.sh) | ❌ | ✅ | ✅ | 使用.bat或PowerShell |
| 文件锁 (fcntl) | ❌ | ✅ | ❌ | 需要替代方案 |
| 路径处理 | ⚠️ | ✅ | ✅ | 使用pathlib |
| 环境变量 | ✅ | ✅ | ✅ | 语法不同 |
| 并发进程 | ✅ | ✅ | ✅ | 正常工作 |

## 🚀 推荐运行方案

### 方案1：WSL (Windows Subsystem for Linux) ⭐推荐
```bash
# 1. 安装WSL2
wsl --install

# 2. 进入WSL环境
wsl

# 3. 正常运行所有脚本
./run_systematic_test_final.sh
```
**优点**：100%兼容，无需修改代码
**缺点**：需要安装WSL

### 方案2：Git Bash
```bash
# 1. 安装Git for Windows (包含Git Bash)
# 2. 在Git Bash中运行
./run_systematic_test_final.sh
```
**优点**：轻量级，大部分功能可用
**缺点**：fcntl文件锁不可用

### 方案3：Windows原生 + Python修改
需要以下修改才能在Windows原生环境运行：

## 🔧 需要的代码修改

### 1. 文件锁兼容性修复

创建 `cross_platform_lock.py`：
```python
import os
import sys
import time
from pathlib import Path
from contextlib import contextmanager

if sys.platform == 'win32':
    import msvcrt
    
    class FileLock:
        def __init__(self, file_path, timeout=30):
            self.file_path = Path(file_path)
            self.timeout = timeout
            self.lock_file = None
            
        def acquire(self):
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                try:
                    self.lock_file = open(self.file_path.with_suffix('.lock'), 'wb')
                    msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    return True
                except IOError:
                    time.sleep(0.1)
            return False
            
        def release(self):
            if self.lock_file:
                msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                self.lock_file.close()
else:
    import fcntl
    
    class FileLock:
        def __init__(self, file_path, timeout=30):
            self.file_path = Path(file_path)
            self.timeout = timeout
            self.lock_file = None
            
        def acquire(self):
            self.lock_file = open(self.file_path.with_suffix('.lock'), 'w')
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX)
            return True
            
        def release(self):
            if self.lock_file:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
```

### 2. 路径处理修复

所有文件中的路径处理应使用：
```python
from pathlib import Path

# 不要用
file_path = "logs/batch_test.log"

# 应该用
file_path = Path("logs") / "batch_test.log"
```

### 3. Windows批处理脚本

创建 `run_systematic_test.bat`：
```batch
@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo PILOT-Bench Systematic Test (Windows)
echo ==========================================
echo.

:: 选择存储格式
echo Select storage format:
echo   1) JSON (default)
echo   2) Parquet
set /p storage_choice="Enter choice [1-2]: "

if "%storage_choice%"=="2" (
    set STORAGE_FORMAT=parquet
    echo Using Parquet storage
) else (
    set STORAGE_FORMAT=json
    echo Using JSON storage
)

:: 运行Python脚本
python run_systematic_test.py %*

endlocal
```

### 4. PowerShell脚本（更强大）

创建 `run_systematic_test.ps1`：
```powershell
# PILOT-Bench Systematic Test for Windows

Write-Host "=========================================="
Write-Host "PILOT-Bench Systematic Test (Windows)"
Write-Host "=========================================="
Write-Host ""

# 存储格式选择
Write-Host "Select storage format:"
Write-Host "  1) JSON (default)"
Write-Host "  2) Parquet"
$storage_choice = Read-Host "Enter choice [1-2]"

if ($storage_choice -eq "2") {
    $env:STORAGE_FORMAT = "parquet"
    Write-Host "Using Parquet storage" -ForegroundColor Green
} else {
    $env:STORAGE_FORMAT = "json"
    Write-Host "Using JSON storage" -ForegroundColor Green
}

# 模型类型选择
Write-Host ""
Write-Host "Select model type:"
Write-Host "  1) Open-source models"
Write-Host "  2) Closed-source models"
Write-Host "  3) View progress"
Write-Host "  4) Exit"
$model_choice = Read-Host "Enter choice [1-4]"

switch ($model_choice) {
    "1" { 
        python smart_batch_runner.py --model-type opensource
    }
    "2" { 
        python smart_batch_runner.py --model-type closedsource
    }
    "3" { 
        python view_test_progress.py
    }
    "4" { 
        exit
    }
}
```

## 📦 Python主入口脚本

创建 `run_systematic_test.py` 替代shell脚本：
```python
#!/usr/bin/env python3
"""
跨平台的系统化测试运行器
替代run_systematic_test_final.sh，支持Windows/Linux/macOS
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def clear_screen():
    """跨平台清屏"""
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')

def select_storage_format():
    """选择存储格式"""
    print("="*50)
    print("选择数据存储格式")
    print("="*50)
    print("\n请选择存储格式：")
    print("  1) JSON格式 (传统方式，兼容性好)")
    print("  2) Parquet格式 (推荐：高性能，防数据丢失)")
    
    choice = input("\n请选择 [1-2] (默认1): ").strip() or "1"
    
    if choice == "2":
        os.environ['STORAGE_FORMAT'] = 'parquet'
        print("✅ 使用Parquet存储格式")
    else:
        os.environ['STORAGE_FORMAT'] = 'json'
        print("✅ 使用JSON存储格式")

def main_menu():
    """主菜单"""
    while True:
        print("\n" + "="*50)
        print("PILOT-Bench 系统化测试")
        print("="*50)
        print("\n请选择测试模型类型：")
        print("  1) 🔓 开源模型")
        print("  2) 🔒 闭源模型")
        print("  3) 📊 查看进度")
        print("  4) ❌ 退出")
        
        choice = input("\n请选择 [1-4]: ").strip()
        
        if choice == "1":
            run_opensource_tests()
        elif choice == "2":
            run_closedsource_tests()
        elif choice == "3":
            view_progress()
        elif choice == "4":
            print("退出...")
            break
        else:
            print("无效选择，请重试")

def run_opensource_tests():
    """运行开源模型测试"""
    models = [
        "DeepSeek-V3-0324",
        "DeepSeek-R1-0528",
        "qwen2.5-72b-instruct",
        "Llama-3.3-70B-Instruct"
    ]
    
    print("\n开源模型列表：")
    for i, model in enumerate(models, 1):
        print(f"  {i}) {model}")
    
    model_choice = input("\n选择模型 [1-4]: ").strip()
    
    if model_choice.isdigit() and 1 <= int(model_choice) <= len(models):
        model = models[int(model_choice)-1]
        cmd = [
            "python", "smart_batch_runner.py",
            "--model", model,
            "--prompt-types", "optimal",
            "--difficulty", "easy",
            "--num-instances", "10"
        ]
        subprocess.run(cmd)
    else:
        print("无效选择")

def run_closedsource_tests():
    """运行闭源模型测试"""
    models = [
        "gpt-4o-mini",
        "gpt-5-mini",
        "o3-0416-global",
        "kimi-k2"
    ]
    
    print("\n闭源模型列表：")
    for i, model in enumerate(models, 1):
        print(f"  {i}) {model}")
    
    model_choice = input("\n选择模型 [1-4]: ").strip()
    
    if model_choice.isdigit() and 1 <= int(model_choice) <= len(models):
        model = models[int(model_choice)-1]
        cmd = [
            "python", "smart_batch_runner.py",
            "--model", model,
            "--prompt-types", "optimal",
            "--difficulty", "easy",
            "--num-instances", "10"
        ]
        subprocess.run(cmd)
    else:
        print("无效选择")

def view_progress():
    """查看测试进度"""
    subprocess.run(["python", "view_test_progress.py"])

if __name__ == "__main__":
    # 设置UTF-8编码（Windows需要）
    if platform.system() == 'Windows':
        os.system('chcp 65001 > nul')
    
    try:
        select_storage_format()
        main_menu()
    except KeyboardInterrupt:
        print("\n\n中断...")
        sys.exit(0)
```

## 🔍 测试Windows兼容性

### 检查Python版本和依赖
```batch
:: Windows CMD
python --version
pip list | findstr "pandas pyarrow filelock"
```

### 安装缺失的依赖
```batch
pip install pandas pyarrow filelock
```

## ⚠️ 已知的Windows问题

1. **文件锁冲突**
   - 问题：fcntl模块不存在
   - 解决：使用上面的cross_platform_lock.py

2. **路径分隔符**
   - 问题：硬编码的`/`路径
   - 解决：使用`pathlib.Path`

3. **Shell命令**
   - 问题：grep, tail, ps等Unix命令
   - 解决：使用Python等效功能或PowerShell

4. **信号处理**
   - 问题：SIGTERM等Unix信号
   - 解决：使用Windows事件或其他IPC机制

## 📊 兼容性测试检查清单

- [ ] Python脚本能导入所有模块
- [ ] 文件锁机制在Windows上工作
- [ ] 路径处理正确（使用pathlib）
- [ ] 并发进程正常启动和结束
- [ ] 日志文件正确创建
- [ ] 数据库文件正确读写
- [ ] Parquet文件正确创建

## 🎯 推荐最佳实践

### Windows用户推荐顺序：
1. **首选**：使用WSL2，获得100%兼容性
2. **次选**：使用Git Bash + Python脚本
3. **备选**：原生Windows + PowerShell脚本

### 开发时注意：
1. 始终使用`pathlib.Path`处理路径
2. 避免使用Unix特有的模块（fcntl, pwd, grp）
3. 使用`subprocess`而不是`os.system`
4. 为Windows提供替代实现
5. 测试时包含Windows环境

---

**文档版本**: 1.0.0  
**创建时间**: 2025-08-16  
**维护者**: Claude Assistant  
**状态**: 🟡 部分支持（需要WSL或修改）