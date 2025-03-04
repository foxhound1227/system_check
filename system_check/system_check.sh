#!/bin/bash

# 全局变量
miss_alert_triggered=false
has_alert=false
hardware_status="OK"  # 添加硬件状态变量
core_status="OK"  # 添加core文件状态变量
mempool_status="OK"  # 添加内存池状态变量

# ===== 阈值参数配置 =====
# 内存使用率（单位：百分比）
MEMORY_THRESHOLD=90

# 磁盘使用率（单位：百分比）
DISK_THRESHOLD=80

# 回填率（单位：百分比）
BACKFILL_THRESHOLD=90

# 流量 Miss 告警阈值（单位：数量）
MISS_THRESHOLD=1000

# 流量 Mbps 告警阈值（单位：Mbps）
MBPS_THRESHOLD=35000

# IMSI哈希表使用率阈值（单位：百分比）
IMSI_HASH_THRESHOLD=80

# DPDK队列使用率阈值（单位：百分比）
DPDK_QUEUE_THRESHOLD=80

# b256_pool使用率阈值（单位：百分比）
B256_POOL_THRESHOLD=10

# CTCC 命令相关配置
CTCC_CMD="/home/ctcc_cmd"
CTCC_PORT="26500"

# 定义要检查的服务列表（补充.service后缀保证兼容性）
SERVICES=("updpi.service" "upp.service" "upload.service" "logtar.service" "tnlinfo_proxy.service")

# ===== 函数定义 =====
# 函数：获取服务运行时间
get_uptime() {
    service_name="$1"
    uptime=$(systemctl status "$service_name" | grep Act | awk -F ';' '{print $2}' | sed 's/^ *//')
    if [ -z "$uptime" ]; then
        echo "N/A"
    else
        echo "$uptime" | sed 's/ ago//'
    fi
}

# 函数：获取服务版本号
get_version() {
    service_name="$1"
    version="N/A"

    case "$service_name" in
        updpi.service)
            version=$(/home/updpi/updpi -v |grep -ia ver|awk '{print $4}')
            ;;
        upp.service)
            version=$(/home/upp/anvs_upp -v | grep -a ver | awk -F '[: ]' '{print $8}')
            ;;
        upload.service)
            version=$("$CTCC_CMD" "6666" upload "show version -rd" | grep -a Ver | awk -F '[:_]' '{print $4}')
            ;;
        logtar.service)
            version=$(/home/logtar/LogTar -v | grep -a Ver | awk -F '[: ]' '{print $5}')
            ;;
        tnlinfo_proxy.service)
            version=$(/home/tnlinfo_proxy/cmd_client 3434 show_version |grep Ver |awk -F '_' '{print  $3}')
            ;;
    esac

    echo "$version"
}

# 函数：生成巡检总结（单行输出）
generate_summary() {
    summary="巡检总结: "
    summary+="内存: ${memory_status:-N/A}, "
    summary+="磁盘: ${disk_status:-N/A}, "
    summary+="服务状态: ${service_status:-N/A}, "
    summary+="硬件状态: ${hardware_status:-N/A}, "
    summary+="Core文件: ${core_status:-N/A}, "  # 添加core文件状态
    summary+="内存池: ${mempool_status:-N/A}, "  # 添加内存池状态

    # 回填率
    if [ "$backfill_status" == "告警" ]; then
        summary+="回填率: ${backfill_status} (${backfill_rate}%), "
    else
        summary+="回填率: ${backfill_status}, "
    fi

    summary+="流量情况: ${traffic_status:-N/A}, "
    summary+="策略加载: ${policy_status:-N/A}, "
    summary+="策略下发: ${policy_release_status:-N/A}"
    echo -e "\n===== 巡检完成 ====="
    echo "$summary"
}

# 函数：内存检查
check_memory() {
    echo -e "\n---- 内存使用 ----"
    memory_alert=false
    free -b | awk -v threshold="$MEMORY_THRESHOLD" '
    /Mem/ {
        total = $2/1024/1024
        used = ($3)/1024/1024
        use_percent = ($3/$2)*100
  
        if (use_percent >= threshold) {
            printf "[告警] 内存使用率过高: 总内存 %.1fG | 已用 %.1fG(%.1f%%)\n", 
                total/1024, 
                used/1024,
                use_percent
            exit 1
        } else {
            print "（正常）内存使用正常"
        }
    }'
    [ $? -eq 1 ] && memory_alert=true
    if $memory_alert; then
        has_alert=true
        memory_status="告警"
    else
        memory_status="OK"
    fi
}

# 函数：磁盘检查
check_disk() {
    echo -e "\n---- 磁盘使用 ----"
    disk_alert=false
    df -h | awk -v threshold="$DISK_THRESHOLD" '
    NR>1 {
        if ($1 ~ /tmpfs|udev/) next

        gsub(/%/,"",$5)
        if ($5 >= threshold) {
            printf "[告警] 挂载点 %s 使用率过高: 已用 %s/%s(%.1f%%)\n", 
                $6, $3, $2, $5
            disk_alert = true
        }
    }
    END {
        if (!disk_alert) print "（正常）磁盘使用正常"
    }'
    if $disk_alert; then
        has_alert=true
        disk_status="告警"
    else
        disk_status="OK"
    fi
}

# 函数：服务状态检查
check_services() {
    echo -e "\n---- 服务状态 ----"
    # 打印表头
    printf "%-20s %-15s %-20s %-20s\n" "服务名称" "状态" "版本" "运行时长"
    printf "%s\n" "--------------------------------------------------------------------------------"
  
    for service in "${SERVICES[@]}"; do
        service_name="${service%.service}"
  
        # 跳过不存在的tnlinfo_proxy服务，不输出任何信息
        if [ "$service_name" = "tnlinfo_proxy" ]; then
            if ! systemctl list-unit-files | grep -iq "^${service}"; then
                continue
            fi
        fi

        if ! systemctl list-unit-files | grep -iq "^${service}"; then
            has_alert=true
            printf "[告警] %-15s | %-15s | %-15s | %-15s\n" \
                "$service_name" \
                "不存在" \
                "N/A" \
                "N/A"
            continue
        fi

        status=$(LANG=C systemctl is-active "$service" 2>/dev/null || echo "unreachable")
        status=$(echo "$status" | tr '\n' ' ' | sed 's/ *$//')

        if [ "$status" != "active" ]; then
            has_alert=true
            printf "[告警] %-15s | %-15s | %-15s | %-15s\n" \
                "$service_name" \
                "$status" \
                "未知" \
                "时间不可用"
            continue
        fi

        version=$(LANG=C get_version "$service" |
            tr -cd '[:alnum:]._-' | 
            sed -E 's/^[vV]//; s/[._-]{2,}/./g' | 
            head -c 12
        )

        uptime=$(LANG=C systemctl status "$service" |
            awk -F '; ' '/Active:/ && $2 ~ /ago/ {gsub(/ \(.*/, "", $2); print $2}'
        )

        printf "（正常）%-15s | %-15s | %-15s | %-15s\n" \
            "$service_name" \
            "运行中" \
            "${version:-未知}" \
            "${uptime:-时间不可用}"
    done
    printf "%s\n" "--------------------------------------------------------------------------------"
    service_status=$(if $has_alert; then echo "告警"; else echo "OK"; fi)
}

# 函数：回填率检查
check_backfill() {
    echo -e "\n---- 回填率 ----"
    backfill_rate=$("$CTCC_CMD" "$CTCC_PORT" tn "show tunnel_info stat" | grep -a "Backfill Rate" | awk -F '[:,]' '{print $2}' | tr -d ' %')
    if [ -z "$backfill_rate" ]; then
        echo "   [告警] 回填率获取失败"
        has_alert=true
        backfill_status="告警"
    else
        is_low=$(echo "$backfill_rate $BACKFILL_THRESHOLD" | awk '{if ($1 < $2) print "true"; else print "false"}')
        if [ "$is_low" == "true" ]; then
            echo "   [告警] 回填率过低: ${backfill_rate}%"
            has_alert=true
            backfill_status="告警"
        else
            echo "（正常）回填率: ${backfill_rate}%"
            backfill_status="OK"
        fi
    fi
}

# 函数：流量情况检查
check_traffic() {
    echo -e "\n---- 流量情况 ----"
  
    # 检查端口状态
    echo "端口状态检查:"
    link_info=$("$CTCC_CMD" "$CTCC_PORT" ud "show link" | awk '
        /Port[0-9]/ && NF >= 6 {
            # 检查包含Port的行且至少有6列
            printf "%s %s\n", $1, $6
        }
    ')
  
    if [ -z "$link_info" ]; then
        echo "[告警] 无法获取端口状态信息"
        has_alert=true
        traffic_status="告警"
    else
        link_alert=false
        echo "$link_info" | while read -r port state; do
            if [ "$state" = "DOWN" ]; then
                echo "[告警] $port 状态: $state"
                link_alert=true
            else
                echo "（正常）$port 状态: $state"
            fi
        done
  
        if [ "$link_alert" = "true" ]; then
            has_alert=true
            traffic_status="告警"
        fi
    fi

    # 检查流量信息
    traffic_info=$("$CTCC_CMD" "$CTCC_PORT" ud "show pkt_stat e" | grep -aA 2 -B 2 Port | head -4)

    if [ -z "$traffic_info" ]; then
        echo "   [告警] 流量信息获取失败"
        has_alert=true
        traffic_status="告警"
    else
        echo "$traffic_info" | awk -v miss_threshold="$MISS_THRESHOLD" -v mbps_threshold="$MBPS_THRESHOLD" '
        BEGIN {
            alert = 0
            no_traffic = 0
        }
        /Port/ {
            port = $1
        }
        /^[[:space:]]*Port[0-9]+/ {
            miss = $4
            mbps = $7
            printf "（正常）%s: Miss=%s, Mbps=%s\n", port, miss, mbps
            if (miss > miss_threshold) {
                printf "   [告警] %s Miss 超过 %s\n", port, miss_threshold
                alert = 1
            }
            if (mbps > mbps_threshold) {
                printf "   [告警] %s Mbps 超过 %s\n", port, mbps_threshold
                alert = 1
            }
            if (mbps < 1) {
                no_traffic = 1
            }
        }
        END {
            if (no_traffic) {
                printf "   [告警] 检测到端口无流量\n"
                alert = 1
            }
            exit alert
        }'
        awk_status=$?

        case $awk_status in
            0)
                traffic_status="OK"
                ;;
            1)
                has_alert=true
                traffic_status="告警"
                echo -e "\nDPDK错误统计（触发Miss或Mbps阈值后自动显示）:"
                $CTCC_CMD $CTCC_PORT udpi "show dpdk" | 
                    grep -a -E "Port|rx_crc_errors|rx_no_desc|rx_dropped_packets" | sed 's/^/   /'
                ;;
        esac
    fi
}

# 函数：策略加载检查
check_policy() {
    echo -e "\n---- 策略加载信息 ----"
  
    # 检查规则分配失败情况
    rule_alloc_failed=$("$CTCC_CMD" "$CTCC_PORT" rule "show action summary" | grep -a "Rule more alloc failed")
  
    if [ -n "$rule_alloc_failed" ]; then
        echo "[告警] 检测到规则分配失败:"
        echo "$rule_alloc_failed" | sed 's/^/    /'  # 缩进显示错误信息
        has_alert=true
        policy_status="告警"
    else
        echo "（正常）规则分配正常"
        policy_status="OK"
    fi

    # 显示策略加载基本信息
    policy_info=$("$CTCC_CMD" "$CTCC_PORT" ru "show action summary" | grep -a "Ant\|IDS")
    if [ -n "$policy_info" ]; then
        echo -e "\n策略数量统计:"
        echo "$policy_info" | sed 's/^/    /'
    else
        echo "[告警] 策略加载信息获取失败"
        has_alert=true
        policy_status="告警"
    fi
}

# 函数：策略下发检查
check_policy_release() {
    echo -e "\n---- 策略下发检查 ----"
    today=$(date +%Y%m%d)  # 获取当天日期（格式：YYYYMMDD）
    missing_files=()       # 用于存储缺失的文件类型

    # 检查策略下发每日每类文件是否存在
    check_file_exists() {
        pattern="$1"
        if ! ls /home/malware_download/"$pattern"* 2>/dev/null | grep -q "$today"; then
            missing_files+=("$pattern")
        fi
    }

    check_file_exists "multi.rule"
    check_file_exists "snort.evt"
    check_file_exists "mtx.evt"
    check_file_exists "tz.rule"

    if [ ${#missing_files[@]} -eq 0 ]; then
        echo "（正常）所有类型策略文件正常下发"
        policy_release_status="OK"
    else
        echo "   [告警] 当天以下策略文件缺失: ${missing_files[*]}"
        policy_release_status="告警"
        has_alert=true
    fi
}

# 函数：检查硬件错误
check_hardware() {
    echo -e "\n---- 硬件错误检查 ----"
    # 获取最近5条硬件错误日志
    hw_errors=$(dmesg -T | grep -i "Hardware Error" | tail -n 5)
  
    if [ -n "$hw_errors" ]; then
        echo "[告警] 检测到硬件错误:"
        echo "$hw_errors" | sed 's/^/    /'  # 缩进显示错误信息
        has_alert=true
        hardware_status="告警"
    else
        # 显示最近5条一般错误日志（参考信息）
        recent_errors=$(dmesg -T | grep -i error | tail -n 5)
        if [ -n "$recent_errors" ]; then
            echo "最近系统错误日志（仅供参考）:"
            echo "$recent_errors" | sed 's/^/    /'
        else
            echo "未发现硬件错误"
        fi
        hardware_status="OK"
    fi
}

# 函数：检查core文件
check_core_files() {
    echo -e "\n---- Core文件检查 ----"
  
    # 检查/home/updpi/log目录下最近一个月的core文件
    core_files=$(find /home/updpi/log -name "*core.v*" -mtime -30 2>/dev/null)
  
    if [ -n "$core_files" ]; then
        echo "[告警] 发现最近一个月的core文件:"
        while IFS= read -r file; do
            file_time=$(stat -c '%y' "$file" | cut -d. -f1)  # 获取文件时间
            file_size=$(ls -lh "$file" | awk '{print $5}')   # 获取文件大小
            echo "    文件: $file"
            echo "    生成时间: $file_time"
            echo "    文件大小: $file_size"
            echo "    ----------------------"
        done <<< "$core_files"
        has_alert=true
        core_status="告警"
    else
        echo "（正常）未发现最近一个月的core文件"
        core_status="OK"
    fi
}

# 函数：检查updpi内存池状态
check_mempool() {
    echo -e "\n---- Updpi内存池检查 ----"
  
    # 检查内存池状态
    mempool_info=$("$CTCC_CMD" "$CTCC_PORT" uc "show mempool_stat pool_name 256" | grep -a "b256_pool")
  
    # 检查get_seg_mem_failed状态
    seg_mem_failed=$("$CTCC_CMD" "$CTCC_PORT" rec "sh rec_stat " | grep -a get_seg_mem_failed | awk -F ':' '{print $2}' | awk '{print $1}')
  
    # 检查IMSI哈希表使用率
    imsi_info=$("$CTCC_CMD" "$CTCC_PORT" tn "sh tun stat " | grep -a "imsi hash table")
    imsi_usage=$(echo "$imsi_info" | grep -o '[0-9.]*%' | sed 's/%//')
  
    # 检查DPDK队列使用率
    dpdk_info=$("$CTCC_CMD" "$CTCC_PORT" rsdp "show dpdk_queue queue_name step12" | grep -a "AGING_RING_STEP12")
  
    if [ -n "$mempool_info" ]; then
        # 提取失败次数和失败率
        failed_count=$(echo "$mempool_info" | awk '{print $3}')
        failed_rate=$(echo "$mempool_info" | awk '{gsub(/%/,"",$4); print $4}')
  
        # 使用awk进行浮点数比较
        is_rate_high=$(echo "$failed_rate $B256_POOL_THRESHOLD" | awk '{if ($1 > $2) print "yes"; else print "no"}')
        is_imsi_high=$(echo "$imsi_usage $IMSI_HASH_THRESHOLD" | awk '{if ($1 >= $2) print "yes"; else print "no"}')
  
        # 检查失败率是否超过阈值
        if [ "$failed_count" -ne 0 ] && [ "$is_rate_high" = "yes" ]; then
            echo -e "\n[告警] 内存池状态:"
            has_alert=true
            mempool_status="告警"
        else
            echo -e "\n（正常）内存池状态:"
            mempool_status="OK"
        fi

        # 打印内存池信息
        printf "%-20s %-10s %-14s %-8s\n" "内存池名称" "总大小" "失败次数" "失败率"
        echo "$mempool_info" | awk '{printf "%-15s %-10s %-8s %-8s\n", $1, $2, $3, $4}'
  
        # 打印get_seg_mem_failed信息
        if [ "$seg_mem_failed" -eq 0 ]; then
            echo -e "\n（正常）分片内存分配失败次数（get_seg_mem_failed）: $seg_mem_failed"
        else
            echo -e "\n[告警] 分片内存分配失败次数（get_seg_mem_failed）: $seg_mem_failed"
            has_alert=true
            mempool_status="告警"
        fi

        # 打印IMSI哈希表使用情况
        if [ -n "$imsi_info" ]; then
            if [ "$is_imsi_high" = "yes" ]; then
                echo -e "\n[告警] IMSI哈希表使用情况:"
                echo "$imsi_info" | sed 's/^/    /'
                echo "    [告警] IMSI哈希表使用率超过${IMSI_HASH_THRESHOLD}%"
                has_alert=true
                mempool_status="告警"
            else
                echo -e "\n（正常）IMSI哈希表使用情况:"
                echo "$imsi_info" | sed 's/^/    /'
            fi
        fi

        # 打印DPDK队列使用情况
        if [ -n "$dpdk_info" ]; then
            dpdk_alert=false
            while IFS= read -r line; do
                queue_percent=$(echo "$line" | awk '{print $6}')
                if [ "$queue_percent" -ge "$DPDK_QUEUE_THRESHOLD" ]; then
                    dpdk_alert=true
                    break
                fi
            done <<< "$dpdk_info"

            if [ "$dpdk_alert" = "true" ]; then
                echo -e "\n[告警] DPDK队列使用情况:"
            else
                echo -e "\n（正常）DPDK队列使用情况:"
            fi
  
            echo "$dpdk_info" | while IFS= read -r line; do
                queue_name=$(echo "$line" | awk '{print $1}')
                queue_used=$(echo "$line" | awk '{print $4}')
                queue_size=$(echo "$line" | awk '{print $3}')
                queue_percent=$(echo "$line" | awk '{print $6}')
                printf "    %-25s 使用率: %s%% (已用: %s/%s)\n" \
                    "$queue_name" "$queue_percent" "$queue_used" "$queue_size"
            done
  
            if [ "$dpdk_alert" = "true" ]; then
                echo "    [告警] 存在DPDK队列使用率超过${DPDK_QUEUE_THRESHOLD}%"
                has_alert=true
                mempool_status="告警"
            fi
        else
            echo -e "\n[告警] 无法获取DPDK队列信息"
            has_alert=true
            mempool_status="告警"
        fi
    else
        echo "[告警] 无法获取内存池信息"
        has_alert=true
        mempool_status="告警"
    fi
}

# 函数：显示帮助信息
show_help() {
    echo "使用方法: $0 [选项]"
    echo "选项:"
    echo "  -h                显示帮助信息"
    echo ""
    echo "可选参数:"
    echo "  memory           检查内存使用情况"
    echo "  disk             检查磁盘使用情况"
    echo "  services         检查系统服务状态"
    echo "  hardware         检查硬件错误信息"
    echo "  core             检查Core文件"
    echo "  mempool          检查内存池状态"
    echo "  backfill         检查回填率"
    echo "  traffic          检查流量情况"
    echo "  policy           检查策略加载"
    echo "  policy_release   检查策略下发"
    echo ""
    echo "示例:"
    echo "  $0               执行所有检查项"
    echo "  $0 memory disk   仅检查内存和磁盘"
    echo "  $0 -h            显示帮助信息"
    exit 0
}

# ===== 脚本主体 =====
# 处理命令行参数
while getopts "h" opt; do
    case $opt in
        h)
            show_help
            ;;
        \?)
            echo "无效的选项: -$OPTARG" >&2
            show_help
            ;;
    esac
done
shift $((OPTIND-1))

# 系统概览
echo "===== 系统巡检报告 | $(date) ====="
echo "主机名: $(hostname)"
echo "系统运行时间: $(uptime -p | sed 's/up //')"

# 默认执行所有检查
if [ $# -eq 0 ]; then
    check_memory
    check_disk
    check_services
    check_hardware
    check_core_files
    check_mempool
    check_backfill
    check_traffic
    check_policy
    check_policy_release
else
    # 根据参数执行对应检查
    for param in "$@"; do
        case "$param" in
            memory)
                check_memory
                ;;
            disk)
                check_disk
                ;;
            services)
                check_services
                ;;
            hardware)
                check_hardware
                ;;
            core)
                check_core_files
                ;;
            mempool)
                check_mempool
                ;;
            backfill)
                check_backfill
                ;;
            traffic)
                check_traffic
                ;;
            policy)
                check_policy
                ;;
            policy_release)
                check_policy_release
                ;;
            *)
                echo "未知参数: $param"
                echo "使用 -h 参数查看帮助信息"
                exit 1
                ;;
        esac
    done
fi

# 生成巡检总结
generate_summary