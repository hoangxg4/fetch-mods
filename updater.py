import json
import os
import sys
import subprocess
import re
import glob

# Dùng curl_cffi giả lập trình duyệt Chrome để Bypass Cloudflare
from curl_cffi import requests

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")

def get_apk_version(apk_path):
    """Trích xuất versionName từ file APK bằng aapt"""
    try:
        result = subprocess.run(['aapt', 'dump', 'badging', apk_path], capture_output=True, text=True, check=True)
        match = re.search(r"versionName='([^']+)'", result.stdout)
        return match.group(1) if match else None
    except Exception as e:
        print(f"[-] Lỗi đọc APK bằng aapt: {e}")
        return None

def notify(app_name, version, tag_name):
    """Gửi thông báo qua Discord và Telegram"""
    release_url = f"https://github.com/{GITHUB_REPOSITORY}/releases/tag/{tag_name}"
    apk_dl_url = f"https://github.com/{GITHUB_REPOSITORY}/releases/download/{tag_name}/{app_name}_v{version}.apk"
    
    # Gửi Discord Notification
    if DISCORD_WEBHOOK:
        discord_data = {
            "embeds": [{
                "title": f"🚀 Cập nhật mới: {app_name} v{version}",
                "description": f"📦 [Xem Release trên GitHub]({release_url})\n📥 [Tải APK Trực Tiếp]({apk_dl_url})",
                "color": 3447003,
                "footer": {"text": "Auto Updater Bot • Obtainium Supported"}
            }]
        }
        try:
            requests.post(DISCORD_WEBHOOK, json=discord_data, impersonate="chrome")
        except Exception as e:
            print(f"[-] Lỗi gửi Discord: {e}")
        
    # Gửi Telegram Notification
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        text = f"🚀 *Cập nhật mới: {app_name} v{version}*\n\n📦 [Xem Release]({release_url})\n📥 [Tải APK Trực Tiếp]({apk_dl_url})"
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}, impersonate="chrome")
        except Exception as e:
            print(f"[-] Lỗi gửi Telegram: {e}")

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""

    with open('source.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # --- BƯỚC 1: XUẤT DANH SÁCH THEO CỤM (CHUNKING) ---
    if action == "prepare":
        app_list = list(data.keys())
        chunk_size = 3 # Gom tối đa 3 app vào 1 máy ảo để tối ưu
        
        chunks = [app_list[i:i + chunk_size] for i in range(0, len(app_list), chunk_size)]
        stringified_chunks = [",".join(chunk) for chunk in chunks]
        
        print(json.dumps(stringified_chunks))
        return

    # --- BƯỚC 2: XỬ LÝ TỪNG CỤM ---
    if action == "process":
        chunk_str = sys.argv[2]
        apps_in_chunk = chunk_str.split(',')
        
        print(f"[*] Máy ảo này xử lý cụm: {apps_in_chunk}")
        
        for app_name in apps_in_chunk:
            if app_name not in data:
                continue
                
            info = data[app_name]
            current_version = info['version']
            download_url = info['download_url']
            
            temp_apk = f"temp_{app_name}.apk"
            apk_name = ""
            
            print(f"\n[+] Bắt đầu quét: {app_name} (Bản hiện tại: v{current_version})")
            
            try:
                r = requests.get(download_url, stream=True, timeout=60, impersonate="chrome")
                r.raise_for_status() 
                
                with open(temp_apk, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk: f.write(chunk)
                        
                latest_version = get_apk_version(temp_apk)
                
                if latest_version and latest_version != current_version:
                    print(f"    -> Đã có bản mới: v{latest_version}!")
                    apk_name = f"{app_name}_v{latest_version}.apk"
                    os.rename(temp_apk, apk_name)
                    
                    tag_name = f"{app_name}-v{latest_version}"
                    subprocess.run(["gh", "release", "create", tag_name, apk_name, "--title", f"{app_name} v{latest_version}", "--notes", "Auto-update release"], check=True)
                    notify(app_name, latest_version, tag_name)
                    
                    with open(f"update_{app_name}.json", "w") as f:
                        json.dump({app_name: latest_version}, f)
                else:
                    print(f"    -> Vẫn là bản cũ hoặc không lấy được metadata.")
            
            except Exception as e:
                print(f"    [-] Lỗi khi xử lý {app_name}: {e}")
                
            finally:
                if os.path.exists(temp_apk): os.remove(temp_apk)
                if os.path.exists(apk_name): os.remove(apk_name)
                
        return

    # --- BƯỚC 3: CẬP NHẬT SOURCE.JSON ---
    if action == "finalize":
        updated = False
        for file in glob.glob("update_*.json"):
            with open(file, 'r') as f:
                update_info = json.load(f)
                for app_name, new_version in update_info.items():
                    data[app_name]['version'] = new_version
                    print(f"[*] Đã nhận dữ liệu ghi đè: {app_name} -> v{new_version}")
                    updated = True

        if updated:
            with open('source.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            print("ready_to_commit")
        else:
            print("no_changes")

if __name__ == "__main__":
    main()
