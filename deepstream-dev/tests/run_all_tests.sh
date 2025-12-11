#!/bin/bash

echo "═══════════════════════════════════════════════════════════════════"
echo "          DeepStream方案单元测试套件"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

cd "$(dirname "$0")/.."

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 运行所有测试
echo "开始运行单元测试..."
echo ""

# 测试1: ROI裁剪
echo "[1/6] 测试ROI裁剪功能..."
if python3 tests/test_roi_crop.py 2>&1; then
    ((PASSED_TESTS++))
    echo "✅ ROI裁剪测试通过"
else
    ((FAILED_TESTS++))
    echo "❌ ROI裁剪测试失败"
fi
((TOTAL_TESTS++))
echo ""

# 测试2: 图像提取和缓存
echo "[2/6] 测试图像提取和缓存功能..."
if python3 tests/test_image_extraction.py 2>&1; then
    ((PASSED_TESTS++))
    echo "✅ 图像提取测试通过"
else
    ((FAILED_TESTS++))
    echo "❌ 图像提取测试失败"
fi
((TOTAL_TESTS++))
echo ""

# 测试3: 车牌识别
echo "[3/6] 测试车牌识别功能..."
if python3 tests/test_license_plate_recognition.py 2>&1; then
    ((PASSED_TESTS++))
    echo "✅ 车牌识别测试通过"
else
    ((FAILED_TESTS++))
    echo "❌ 车牌识别测试失败"
fi
((TOTAL_TESTS++))
echo ""

# 测试4: 距离测量
echo "[4/6] 测试距离测量功能..."
if python3 tests/test_distance_measurement.py 2>&1; then
    ((PASSED_TESTS++))
    echo "✅ 距离测量测试通过"
else
    ((FAILED_TESTS++))
    echo "❌ 距离测量测试失败"
fi
((TOTAL_TESTS++))
echo ""

# 测试5: 信标匹配
echo "[5/6] 测试信标匹配功能..."
if python3 tests/test_beacon_matching.py 2>&1; then
    ((PASSED_TESTS++))
    echo "✅ 信标匹配测试通过"
else
    ((FAILED_TESTS++))
    echo "❌ 信标匹配测试失败"
fi
((TOTAL_TESTS++))
echo ""

# 测试6: 云端上传
echo "[6/6] 测试云端上传功能..."
if python3 tests/test_cloud_upload.py 2>&1; then
    ((PASSED_TESTS++))
    echo "✅ 云端上传测试通过"
else
    ((FAILED_TESTS++))
    echo "❌ 云端上传测试失败"
fi
((TOTAL_TESTS++))
echo ""

# 输出测试结果
echo "═══════════════════════════════════════════════════════════════════"
echo "                    测试结果汇总"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "总测试数: $TOTAL_TESTS"
echo "通过: $PASSED_TESTS"
echo "失败: $FAILED_TESTS"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo "🎉 所有测试通过！"
    exit 0
else
    echo "⚠️  有 $FAILED_TESTS 个测试失败"
    exit 1
fi



