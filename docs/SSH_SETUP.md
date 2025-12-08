# SSH 配置和安全设置

## 概述

本文档说明如何配置 SSH 服务，以便远程访问和管理车辆检测系统。

## 1. 检查 SSH 服务状态

```bash
# 检查 SSH 服务是否运行
sudo systemctl status ssh

# 或者（Ubuntu 22.04）
sudo systemctl status sshd
```

## 2. 安装 SSH 服务（如果未安装）

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install openssh-server

# 启动并启用 SSH 服务
sudo systemctl start ssh
sudo systemctl enable ssh
```

## 3. 基本安全配置

### 3.1 编辑 SSH 配置文件

```bash
sudo nano /etc/ssh/sshd_config
```

### 3.2 推荐的安全设置

```bash
# 禁用 root 登录（使用普通用户 + sudo）
PermitRootLogin no

# 限制登录尝试次数
MaxAuthTries 3

# 设置空闲超时（秒）
ClientAliveInterval 300
ClientAliveCountMax 2

# 禁用密码认证（推荐使用密钥认证）
# PasswordAuthentication no

# 允许密钥认证
PubkeyAuthentication yes

# 禁用空密码
PermitEmptyPasswords no

# 限制用户（可选，只允许特定用户登录）
# AllowUsers your_username

# 更改默认端口（可选，提高安全性）
# Port 2222
```

### 3.3 重启 SSH 服务

```bash
sudo systemctl restart ssh
```

## 4. 配置 SSH 密钥认证（推荐）

### 4.1 在客户端生成密钥对

```bash
# 在您的本地机器上
ssh-keygen -t ed25519 -C "your_email@example.com"

# 或者使用 RSA（兼容性更好）
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

### 4.2 将公钥复制到服务器

```bash
# 方法1：使用 ssh-copy-id（推荐）
ssh-copy-id username@server_ip

# 方法2：手动复制
cat ~/.ssh/id_rsa.pub | ssh username@server_ip "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### 4.3 设置正确的权限

```bash
# 在服务器上
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

## 5. 防火墙配置

### 5.1 使用 UFW（Ubuntu 防火墙）

```bash
# 允许 SSH（默认端口 22）
sudo ufw allow ssh

# 或者指定端口
sudo ufw allow 2222/tcp

# 启用防火墙
sudo ufw enable

# 查看状态
sudo ufw status
```

### 5.2 使用 iptables

```bash
# 允许 SSH
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 保存规则（Ubuntu）
sudo netfilter-persistent save
```

## 6. 测试 SSH 连接

```bash
# 从客户端测试连接
ssh username@server_ip

# 使用密钥认证测试
ssh -i ~/.ssh/id_rsa username@server_ip
```

## 7. 远程管理脚本

### 7.1 创建远程管理脚本

```bash
# 在服务器上创建脚本
cat > ~/remote_management.sh << 'EOF'
#!/bin/bash
# 远程管理脚本

echo "=== 车辆检测系统远程管理 ==="
echo "1. 查看系统状态"
echo "2. 查看服务状态"
echo "3. 重启服务"
echo "4. 查看日志"
echo "5. 查看资源使用"
echo "6. 退出"

read -p "请选择操作 [1-6]: " choice

case $choice in
    1)
        /path/to/scripts/system_status.sh
        ;;
    2)
        sudo systemctl status vehicle-detection
        ;;
    3)
        sudo systemctl restart vehicle-detection
        ;;
    4)
        tail -n 100 /path/to/logs/startup.log
        ;;
    5)
        /path/to/scripts/monitor_resources.sh
        ;;
    6)
        exit 0
        ;;
    *)
        echo "无效选择"
        ;;
esac
EOF

chmod +x ~/remote_management.sh
```

## 8. 安全建议

### 8.1 定期更新系统

```bash
sudo apt update
sudo apt upgrade -y
```

### 8.2 监控 SSH 登录

```bash
# 查看 SSH 登录日志
sudo tail -f /var/log/auth.log

# 查看失败的登录尝试
sudo grep "Failed password" /var/log/auth.log
```

### 8.3 使用 fail2ban（防止暴力破解）

```bash
# 安装 fail2ban
sudo apt install fail2ban

# 配置 fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local

# 启动 fail2ban
sudo systemctl start fail2ban
sudo systemctl enable fail2ban
```

### 8.4 定期备份配置

```bash
# 备份 SSH 配置
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
```

## 9. 故障排除

### 9.1 SSH 连接被拒绝

```bash
# 检查 SSH 服务是否运行
sudo systemctl status ssh

# 检查防火墙
sudo ufw status

# 检查端口是否监听
sudo netstat -tlnp | grep :22
```

### 9.2 密钥认证失败

```bash
# 检查权限
ls -la ~/.ssh/

# 检查 authorized_keys
cat ~/.ssh/authorized_keys

# 查看 SSH 日志
sudo tail -f /var/log/auth.log
```

### 9.3 连接超时

```bash
# 检查网络连接
ping server_ip

# 检查 SSH 端口是否开放
telnet server_ip 22
```

## 10. 快速配置脚本

```bash
#!/bin/bash
# 快速 SSH 安全配置脚本

# 备份原配置
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d)

# 应用安全设置
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/#MaxAuthTries 6/MaxAuthTries 3/' /etc/ssh/sshd_config
sudo sed -i 's/#ClientAliveInterval 0/ClientAliveInterval 300/' /etc/ssh/sshd_config
sudo sed -i 's/#ClientAliveCountMax 3/ClientAliveCountMax 2/' /etc/ssh/sshd_config

# 重启 SSH 服务
sudo systemctl restart ssh

echo "SSH 安全配置完成"
```

## 注意事项

1. **在修改 SSH 配置前，确保有其他方式访问服务器**（如物理访问或现有 SSH 会话）
2. **测试配置后立即测试连接**，确保不会锁定自己
3. **定期检查 SSH 日志**，发现异常登录尝试
4. **使用强密码或密钥认证**，不要使用弱密码
5. **限制 SSH 访问**，只允许必要的用户和 IP 地址

## 参考资源

- [OpenSSH 官方文档](https://www.openssh.com/)
- [Ubuntu SSH 文档](https://help.ubuntu.com/community/SSH)
- [SSH 安全最佳实践](https://stribika.github.io/2015/01/04/secure-secure-shell.html)

