import socket
import random
import struct
import time
import os
from urllib.parse import urlparse

def test_dns_resolve(dns_ip, domain, timeout=2.0):
    try:
        resolver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        resolver.settimeout(timeout)
        transaction_id = struct.pack(">H", random.randint(0, 65535))
        flags = struct.pack(">H", 0x0100)
        questions = struct.pack(">H", 1)
        answer_rrs = struct.pack(">H", 0)
        authority_rrs = struct.pack(">H", 0)
        additional_rrs = struct.pack(">H", 0)
        qname = b""
        for part in domain.split("."):
            qname += struct.pack("B", len(part)) + part.encode()
        qname += b"\x00"
        qtype = struct.pack(">H", 1)
        qclass = struct.pack(">H", 1)
        query = (transaction_id + flags + questions + answer_rrs + authority_rrs + additional_rrs + qname + qtype + qclass)
        
        start = time.time()
        resolver.sendto(query, (dns_ip, 53))
        data, _ = resolver.recvfrom(1024)
        latency = (time.time() - start) * 1000
        resolver.close()
        return latency, True
    except:
        return 9999, False

def extract_domains_from_m3u(m3u_path):
    domains = set()
    try:
        with open(m3u_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line.startswith('http'):
                    try:
                        domain = urlparse(line).netloc
                        if domain: 
                            domains.add(domain)
                    except: 
                        pass
    except Exception: 
        pass
    
    # ✅ Shuffle کردن برای انتخاب تصادفی از سراسر فایل
    domain_list = list(domains)
    random.shuffle(domain_list)
    
    # ✅ انتخاب هوشمند بر اساس حجم فایل:
    # - زیر 10,000 کانال: 20 دامنه
    # - 10,000 تا 50,000: 35 دامنه
    # - بالای 50,000: 50 دامنه
    total_domains = len(domain_list)
    
    if total_domains <= 20:
        return domain_list  # همه را برمی‌گردان
    elif total_domains <= 50:
        return domain_list[:35]
    else:
        return domain_list[:50]  # برای فایل‌های بزرگ مثل 80K
    
    

def run_dns_test_with_m3u(m3u_path=None, log_callback=None):
    if m3u_path and os.path.exists(m3u_path):
        if log_callback: log_callback(f" 📂 Extracting domains from: {m3u_path}")
        test_domains = extract_domains_from_m3u(m3u_path)
        if not test_domains:
            if log_callback: log_callback(" ⚠️ No domains found in M3U file!")
            return []
    else:
        test_domains = ["d1bl6tskrpq9ze.cloudfront.net", "live-content.cdn.xumo.com", "cinehls.persiana.live"]
    
    DNS_SERVERS = {
        # === سرورهای جهانی سریع ===
        "Cloudflare Primary": "1.1.1.1",
        "Cloudflare Secondary": "1.0.0.1",
        "Google DNS Primary": "8.8.8.8",
        "Google DNS Secondary": "8.8.4.4",
        "AdGuard DNS Primary": "94.140.14.14",
        "AdGuard DNS Secondary": "94.140.15.15",
        "ControlD Primary": "76.76.2.0",
        "ControlD Secondary": "76.76.10.0",
        "NextDNS Primary": "45.90.28.0",
        "NextDNS Secondary": "45.90.30.0",
        "Quad9 Primary": "9.9.9.9",
        "Quad9 Secondary": "149.112.112.112",
        "Comodo Secure": "8.26.56.26",
        "Verisign": "64.6.64.6",
        "DNS.SB": "185.222.222.222",
        "Hurricane Electric": "74.82.42.42",
        # === سرورهای آسیایی ===
        "AliDNS (Alibaba)": "223.5.5.5",
        "114DNS (China)": "114.114.114.114",
        # === سرورهای ایرانی (دور زدن تحریم) ===
        "Shecan (Iran)": "178.22.122.100",
        "Electro (Iran)": "78.157.42.100",
        "403.online (Iran)": "10.202.10.202",
        "Radar Game (Iran)": "10.202.10.10",
    }
    
    results = []
    if log_callback:
        log_callback(f"\n{'='*60}\n🔬 DNS PERFORMANCE TEST\n{'='*60}")
        log_callback(f" 🌐 Testing {len(DNS_SERVERS)} DNS servers")
        log_callback(f" 📋 Test domains ({len(test_domains)}):")
        for domain in test_domains[:5]: 
            log_callback(f"    • {domain}")
        if len(test_domains) > 5: 
            log_callback(f"    ... and {len(test_domains) - 5} more\n")
    
    for dns_name, dns_ip in DNS_SERVERS.items():
        if log_callback: log_callback(f"  Testing {dns_name} ({dns_ip})...")
        
        latencies = []
        total_requests = 0
        successful_requests = 0
        
        for domain in test_domains:
            for _ in range(2):  # هر دامنه ۲ بار تست می‌شود
                total_requests += 1
                latency, success = test_dns_resolve(dns_ip, domain)
                if success:
                    successful_requests += 1
                    latencies.append(latency)
        
        # ✅ محاسبه Success Rate
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            results.append({
                "name": dns_name, 
                "ip": dns_ip, 
                "avg": avg_latency, 
                "min": min(latencies), 
                "max": max(latencies),
                "success_rate": success_rate,  # ✅ اضافه شد
                "total": total_requests,
                "successful": successful_requests
            })
            if log_callback: 
                log_callback(f"    ✅ Avg: {avg_latency:.1f}ms | Success: {success_rate:.1f}% ({successful_requests}/{total_requests})")
        else:
            results.append({
                "name": dns_name,
                "ip": dns_ip,
                "avg": 9999,
                "min": 9999,
                "max": 9999,
                "success_rate": 0,
                "total": total_requests,
                "successful": 0
            })
            if log_callback: log_callback("     ❌ Failed (0% success rate)")
        
        time.sleep(0.2)

    results.sort(key=lambda x: x["avg"] / (x["success_rate"] / 100) if x["success_rate"] > 0 else 99999)
    
    if log_callback:
        log_callback(f"\n{'='*60}\n🏆 FINAL RESULTS (Sorted by Speed + Stability)\n{'='*60}")
        for i, result in enumerate(results, 1):
            medal = "" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            stability_icon = "✅" if result["success_rate"] >= 95 else "️" if result["success_rate"] >= 80 else "❌"
            log_callback(f" {medal} {result['name']:<25} {result['ip']:<18} {result['avg']:.1f}ms | {stability_icon} {result['success_rate']:.1f}%")
        
        if results:
            best = results[0]
            log_callback(f"\n{'='*60}")
            log_callback(f"🏆 BEST DNS: {best['name']} ({best['ip']})")
            log_callback(f"   Average latency: {best['avg']:.1f}ms")
            log_callback(f"   Success rate: {best['success_rate']:.1f}%")
            log_callback(f"{'='*60}")
    
    return results