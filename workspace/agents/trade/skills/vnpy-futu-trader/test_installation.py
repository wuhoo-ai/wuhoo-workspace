#!/usr/bin/env python3
"""
VnPy + vnpy_futu 安装测试脚本

用途：验证 VnPy 和富途接口是否正确安装
"""

import sys
import importlib

def check_package(package_name, import_name=None):
    """检查包是否安装"""
    if import_name is None:
        import_name = package_name
    
    try:
        module = importlib.import_module(import_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"✅ {package_name}: {version}")
        return True
    except ImportError as e:
        print(f"❌ {package_name}: 未安装 - {e}")
        return False

def main():
    print("=" * 60)
    print("VnPy + vnpy_futu 安装检查")
    print("=" * 60)
    print()
    
    # 核心包
    print("【核心包】")
    packages = [
        ("vnpy", "vnpy"),
        ("vnpy_futu", "vnpy_futu"),
        ("futu-api", "futu"),
    ]
    
    all_ok = True
    for pkg_name, import_name in packages:
        if not check_package(pkg_name, import_name):
            all_ok = False
    
    print()
    
    # 依赖包
    print("【依赖包】")
    deps = [
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("ta-lib", "talib"),
    ]
    
    for pkg_name, import_name in deps:
        check_package(pkg_name, import_name)
    
    print()
    print("=" * 60)
    
    if all_ok:
        print("✅ 所有核心包安装成功！")
        print()
        print("下一步:")
        print("1. 下载富途 OpenD: https://www.futumm.com/OpenAPI")
        print("2. 启动 OpenD (端口 11111)")
        print("3. 运行测试连接：python test_connection.py")
        return 0
    else:
        print("❌ 部分包安装失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())
