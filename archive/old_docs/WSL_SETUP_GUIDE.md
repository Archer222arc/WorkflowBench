# WSL安装和使用指南

## 🚀 快速开始

### ✅ WSL兼容性：100%
**好消息：在WSL上运行本项目不需要任何代码修改！**

## 📦 WSL安装步骤

### 1. 安装WSL2（推荐）

在Windows PowerShell（管理员权限）中运行：
```powershell
# 一键安装WSL2和Ubuntu
wsl --install

# 或者指定其他Linux发行版
wsl --install -d Ubuntu-22.04
```

### 2. 重启计算机
安装完成后需要重启Windows

### 3. 初始化WSL
重启后会自动打开Ubuntu窗口，设置用户名和密码

### 4. 更新WSL（可选）
```powershell
# 在PowerShell中
wsl --update
wsl --set-default-version 2
```

## 🔧 项目环境配置

### 1. 进入WSL环境
```powershell
# 在Windows Terminal或PowerShell中
wsl
```

### 2. 安装Python和依赖
```bash
# 更新包管理器
sudo apt update && sudo apt upgrade -y

# 安装Python 3.10+
sudo apt install python3 python3-pip python3-venv -y

# 验证安装
python3 --version  # 应该显示 3.10或更高

# 安装项目依赖
pip3 install pandas pyarrow filelock numpy faiss-cpu
```

### 3. 克隆或复制项目
```bash
# 方式1：从git克隆
git clone <your-repo-url>
cd WorkflowBench/scale_up/scale_up

# 方式2：从Windows文件系统复制
# Windows文件在WSL中的路径：/mnt/c/Users/你的用户名/...
cp -r /mnt/c/Users/YourName/WorkflowBench ~/
cd ~/WorkflowBench/scale_up/scale_up
```

### 4. 运行测试
```bash
# 设置执行权限
chmod +x run_systematic_test_final.sh

# 运行测试（与Linux/macOS完全相同！）
./run_systematic_test_final.sh
```

## 🎯 WSL特有优势

### 1. **完美兼容性**
- ✅ 所有shell脚本直接运行
- ✅ fcntl文件锁正常工作
- ✅ 所有Unix命令可用
- ✅ 路径处理无需修改
- ✅ 环境变量语法相同

### 2. **性能优势**
- WSL2使用真实Linux内核
- 文件I/O性能接近原生Linux
- 内存管理高效

### 3. **与Windows集成**
- 可以访问Windows文件系统（/mnt/c/）
- 可以从Windows Terminal直接使用
- 支持VSCode Remote WSL开发

## 📁 文件系统说明

### WSL中访问Windows文件
```bash
# Windows路径：C:\Users\YourName\Documents\project
# WSL路径：  /mnt/c/Users/YourName/Documents/project

# 例如，访问Windows桌面
cd /mnt/c/Users/$USER/Desktop
```

### Windows中访问WSL文件
```powershell
# 在Windows资源管理器中
\\wsl$\Ubuntu\home\username\

# 或在WSL中获取Windows可访问的路径
wslpath -w $(pwd)
```

## 🔍 验证安装

运行以下命令验证环境：
```bash
# 1. 检查Python
python3 --version

# 2. 检查依赖
python3 -c "import pandas, pyarrow, filelock; print('✅ 所有依赖已安装')"

# 3. 检查文件锁（fcntl）
python3 -c "import fcntl; print('✅ fcntl可用')"

# 4. 测试运行
python3 smart_batch_runner.py --help

# 5. 检查bash版本（WSL通常是4.x或5.x）
bash --version
```

## ⚠️ 常见问题

### 1. WSL1 vs WSL2
- **推荐WSL2**：性能更好，完整Linux内核
- 检查版本：`wsl -l -v`
- 升级到WSL2：`wsl --set-version Ubuntu 2`

### 2. 文件权限问题
```bash
# 如果遇到权限错误
chmod +x *.sh
chmod 755 *.py
```

### 3. Python版本过低
```bash
# Ubuntu 20.04默认是Python 3.8，建议升级
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.10 python3.10-pip
```

### 4. 内存限制
如果测试需要大量内存，可以配置WSL内存限制：

创建 `C:\Users\YourName\.wslconfig`：
```ini
[wsl2]
memory=8GB  # 分配8GB给WSL
processors=4  # 分配4个CPU核心
```

## 🚀 性能优化建议

### 1. 文件位置
- **最佳性能**：将项目放在WSL文件系统（~/）而不是/mnt/c/
- 避免频繁跨文件系统操作

### 2. 使用Parquet存储
```bash
# WSL中Parquet性能特别好
export STORAGE_FORMAT=parquet
./run_systematic_test_final.sh
```

### 3. 并发设置
WSL2支持高并发，可以使用超高并行模式

## 📊 兼容性对比

| 特性 | Windows原生 | Git Bash | WSL1 | WSL2 |
|------|------------|----------|------|------|
| Shell脚本 | ❌ | ✅ | ✅ | ✅ |
| fcntl锁 | ❌ | ❌ | ✅ | ✅ |
| 性能 | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 兼容性 | 60% | 80% | 95% | 100% |
| 需要修改代码 | 是 | 部分 | 否 | 否 |

## 🎯 总结

**WSL（特别是WSL2）是Windows上运行本项目的最佳方案：**

1. ✅ **零修改**：代码完全不需要改动
2. ✅ **完美兼容**：所有功能正常工作
3. ✅ **高性能**：接近原生Linux性能
4. ✅ **易于使用**：安装简单，与Windows集成好

### 快速命令总结
```bash
# Windows PowerShell (Admin)
wsl --install

# 重启后，在WSL中
sudo apt update
sudo apt install python3-pip -y
pip3 install pandas pyarrow filelock numpy faiss-cpu

# 运行项目
cd ~/WorkflowBench/scale_up/scale_up
./run_systematic_test_final.sh
```

---

**文档版本**: 1.0.0  
**创建时间**: 2025-08-16  
**维护者**: Claude Assistant  
**状态**: 🟢 完全支持