#!/bin/bash
# -*- coding: utf-8 -*-
"""
硬件检查脚本
检查相机、路由器、GPU、磁盘等硬件设备状态
"""

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 检查结果
ERRORS=0
WARNINGS=0

echo "=========================================="
echo "硬件检查开始"
echo "=========================================="
echo ""

# 1. 检查 Orbbec 相机
echo -n "检查 Orbbec 相机... "
if lsusb | grep -q "Orbbec\|0x2bc5"; then
    echo -e "${GREEN}✓ 已连接${NC}"
else
    echo -e "${RED}✗ 未检测到相机${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 检查相机权限
if [ -e /dev/video0 ] || [ -e /dev/video1 ]; then
    if [ -r /dev/video0 ] || [ -r /dev/video1 ]; then
        echo -e "   ${GREEN}✓ 相机权限正常${NC}"
    else
        echo -e "   ${YELLOW}⚠ 相机权限可能不足${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# 2. 检查 Cassia 路由器（通过网络）
echo -n "检查 Cassia 路由器... "
CASSIA_IP=$(grep -A 1 "network:" "$PROJECT_ROOT/config.yaml" | grep "cassia_ip:" | awk '{print $2}' | tr -d '"')
if [ -z "$CASSIA_IP" ]; then
    CASSIA_IP="192.168.1.2"  # 默认IP
fi

if ping -c 1 -W 2 "$CASSIA_IP" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 路由器可访问 ($CASSIA_IP)${NC}"
else
    echo -e "${YELLOW}⚠ 路由器不可访问 ($CASSIA_IP)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# 3. 检查 USB 设备
echo -n "检查 USB 设备... "
USB_COUNT=$(lsusb | wc -l)
if [ "$USB_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ 检测到 $USB_COUNT 个USB设备${NC}"
else
    echo -e "${YELLOW}⚠ 未检测到USB设备${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# 4. 检查 GPU (NVIDIA Jetson)
echo -n "检查 GPU... "
if command -v nvidia-smi &> /dev/null; then
    if nvidia-smi > /dev/null 2>&1; then
        GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)
        echo -e "${GREEN}✓ GPU可用 ($GPU_NAME)${NC}"
    else
        echo -e "${RED}✗ GPU不可用${NC}"
        ERRORS=$((ERRORS + 1))
    fi
elif [ -f /sys/devices/soc0/family ]; then
    # Jetson设备
    if grep -q "tegra" /proc/device-tree/model 2>/dev/null; then
        echo -e "${GREEN}✓ Jetson设备检测到${NC}"
    else
        echo -e "${YELLOW}⚠ 无法确认GPU状态${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${YELLOW}⚠ 无法检测GPU${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# 5. 检查 TensorRT
echo -n "检查 TensorRT... "
if python3 -c "import tensorrt" 2>/dev/null; then
    echo -e "${GREEN}✓ TensorRT可用${NC}"
else
    echo -e "${YELLOW}⚠ TensorRT不可用${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# 6. 检查磁盘空间
echo -n "检查磁盘空间... "
DISK_USAGE=$(df -h "$PROJECT_ROOT" | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    echo -e "${GREEN}✓ 磁盘空间充足 (使用率: ${DISK_USAGE}%)${NC}"
elif [ "$DISK_USAGE" -lt 90 ]; then
    echo -e "${YELLOW}⚠ 磁盘空间不足 (使用率: ${DISK_USAGE}%)${NC}"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "${RED}✗ 磁盘空间严重不足 (使用率: ${DISK_USAGE}%)${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 7. 检查模型文件
echo -n "检查模型文件... "
MODEL_PATH=$(grep -A 1 "detection:" "$PROJECT_ROOT/config.yaml" | grep "model_path:" | awk '{print $2}' | tr -d '"')
if [ -z "$MODEL_PATH" ]; then
    MODEL_PATH="$PROJECT_ROOT/models/custom_yolo.engine"
fi

if [ ! -f "$MODEL_PATH" ]; then
    # 尝试相对路径
    MODEL_PATH="$PROJECT_ROOT/$(grep -A 1 "detection:" "$PROJECT_ROOT/config.yaml" | grep "model_path:" | awk '{print $2}' | tr -d '"')"
fi

if [ -f "$MODEL_PATH" ]; then
    MODEL_SIZE=$(du -h "$MODEL_PATH" | awk '{print $1}')
    echo -e "${GREEN}✓ 模型文件存在 ($MODEL_SIZE)${NC}"
else
    echo -e "${RED}✗ 模型文件不存在: $MODEL_PATH${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 8. 检查配置文件
echo -n "检查配置文件... "
if [ -f "$PROJECT_ROOT/config.yaml" ]; then
    echo -e "${GREEN}✓ 配置文件存在${NC}"
else
    echo -e "${RED}✗ 配置文件不存在${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 9. 检查 Python 环境
echo -n "检查 Python 环境... "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "${GREEN}✓ $PYTHON_VERSION${NC}"
else
    echo -e "${RED}✗ Python3 未安装${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 10. 检查必要的 Python 包
echo -n "检查 Python 依赖... "
MISSING_PACKAGES=()
for package in cv2 numpy pycuda; do
    if ! python3 -c "import $package" 2>/dev/null; then
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ 核心依赖包可用${NC}"
else
    echo -e "${RED}✗ 缺少依赖包: ${MISSING_PACKAGES[*]}${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "=========================================="
echo "硬件检查完成"
echo "=========================================="
echo "错误: $ERRORS"
echo "警告: $WARNINGS"
echo ""

# 返回状态码
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}硬件检查失败，请修复错误后重试${NC}"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}硬件检查通过，但有警告${NC}"
    exit 0
else
    echo -e "${GREEN}硬件检查全部通过${NC}"
    exit 0
fi

