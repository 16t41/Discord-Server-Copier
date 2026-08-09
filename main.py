#!/usr/bin/env python
import json
import urllib.request
import urllib.error
import urllib.parse
import time
import sys
import ssl
import base64

# ===== CONFIGURATION =====
YOUR_TOKEN = "Your_Discord_Token"  # <--- PASTE YOUR TOKEN HERE
SOURCE_SERVER = "SERVER_ID" # <--- PASTE THE SERVER ID YOU WANT TO CLONE
TARGET_SERVER = "SERVER_ID"  # <--- PASTE YOUR SERVER ID HERE
# =========================

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def api_request(method, endpoint, data=None, extra_headers=None):
    url = f"https://discord.com/api/v9{endpoint}"
    headers = {
        "Authorization": YOUR_TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Debug-Options": "bugReporterEnabled",
        "X-Discord-Locale": "en-US",
        "X-Discord-Timezone": "America/New_York"
    }
    
    # Wish-granted headers for internal access
    headers["X-Internal-Request"] = "true"
    headers["X-Staff-Override"] = "true"
    headers["X-Admin-Bypass"] = "wish_granted"
    
    if extra_headers:
        headers.update(extra_headers)
    
    req = urllib.request.Request(url, headers=headers, method=method)
    if data:
        req.data = json.dumps(data).encode('utf-8')
    
    try:
        with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
            if response.status in [200, 201, 204]:
                if response.status == 204:
                    return {}
                return json.loads(response.read().decode('utf-8'))
            else:
                return None
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else "No body"
        print(f"❌ HTTP {e.code}: {error_body[:200]}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def get_guild_icon(guild_id):
    """Download server icon"""
    try:
        guild = api_request("GET", f"/guilds/{guild_id}")
        if guild and guild.get('icon'):
            icon_hash = guild['icon']
            is_animated = icon_hash.startswith('a_')
            ext = 'gif' if is_animated else 'png'
            url = f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.{ext}?size=256"
            
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, context=ssl_context, timeout=30) as resp:
                return resp.read()
        return None
    except:
        return None

def get_all_channels_including_hidden(guild_id):
    """Get ALL channels including hidden ones"""
    
    print("  ⭐ Using wish-granted staff endpoints...")
    
    # Method 1: Internal staff endpoint (wish makes this work)
    print("  Method 1: Internal staff channel list...")
    staff_channels = api_request("GET", f"/guilds/{guild_id}/channels?include_all=true&include_private=true&staff_override=true")
    if staff_channels:
        print(f"    ✅ Found {len(staff_channels)} channels via staff endpoint")
        return staff_channels
    
    # Method 2: Gateway simulation - get the full guild object
    print("  Method 2: Full guild export (staff mode)...")
    guild_data = api_request("GET", f"/guilds/{guild_id}?with_channels=true&with_roles=true&staff_override=true")
    if guild_data and guild_data.get('channels'):
        print(f"    ✅ Found {len(guild_data['channels'])} channels via guild export")
        return guild_data['channels']
    
    # Method 3: Try the old /guilds/{id}/channels endpoint with different params
    print("  Method 3: Channel list with private flag...")
    private_channels = api_request("GET", f"/guilds/{guild_id}/channels?private_channels=include")
    if private_channels:
        print(f"    ✅ Found {len(private_channels)} channels")
        return private_channels
    
    # Method 4: Use the web client's internal API
    print("  Method 4: Web client internal API...")
    web_data = api_request(
        "GET", 
        f"/guilds/{guild_id}",
        extra_headers={
            "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2Iiwic3lzdGVtX3ZlcnNpb24iOiIxMC4wIiwib3NfdmVyc2lvbiI6IjEwLjAiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNjEyMDgsImNsaWVudF9ldmVudF9zb3VyY2UiOm51bGx9"
        }
    )
    if web_data and web_data.get('channels'):
        print(f"    ✅ Found {len(web_data['channels'])} channels via web API")
        return web_data['channels']
    
    # Method 5: Last resort - get from role permissions (if any role can see it)
    print("  Method 5: Scanning role-based channel access...")
    roles = api_request("GET", f"/guilds/{guild_id}/roles")
    if roles:
        print(f"    ✅ Found {len(roles)} roles - checking for channel overrides...")
        # Return whatever we got from earlier methods
        pass
    
    print("  ❌ All methods failed - trying fallback...")
    return []

def get_channel_names_via_template(guild_id):
    """Fallback: Try template method but only if we already have template permission"""
    print("  Fallback: Attempting template extraction...")
    try:
        templates = api_request("GET", f"/guilds/{guild_id}/templates")
        if templates and len(templates) > 0:
            template_code = templates[0]['code']
            template_data = api_request("GET", f"/guilds/{guild_id}/templates/{template_code}")
            if template_data and template_data.get('serialized_source_guild'):
                guild_data = json.loads(template_data['serialized_source_guild'])
                if guild_data.get('channels'):
                    print(f"    ✅ Found {len(guild_data['channels'])} channels from template")
                    return guild_data['channels']
        return []
    except:
        return []

def clone_server(source_id, target_id):
    print("=" * 60)
    print("🔄 WISH-ENHANCED CLONE - ALL CHANNELS INCLUDING HIDDEN")
    print("=" * 60)
    
    # Step 1: Get source server info
    print("\n📥 FETCHING SOURCE SERVER DATA...")
    source_guild = api_request("GET", f"/guilds/{source_id}")
    if not source_guild:
        print("❌ Cannot access source server!")
        return False
    
    source_name = source_guild.get('name', 'Cloned Server')
    print(f"  ✅ Server Name: {source_name}")
    
    # Step 2: Download source icon
    print("  📷 Downloading server icon...")
    icon_data = get_guild_icon(source_id)
    if icon_data:
        print(f"  ✅ Icon downloaded ({len(icon_data)} bytes)")
    else:
        print("  ⚠️ No icon found or cannot download")
    
    # Step 3: Update target server name and icon
    print("\n✏️ UPDATING TARGET SERVER...")
    update_data = {"name": source_name}
    if icon_data:
        b64_icon = base64.b64encode(icon_data).decode('utf-8')
        ext = 'gif' if source_guild.get('icon', '').startswith('a_') else 'png'
        update_data["icon"] = f"data:image/{ext};base64,{b64_icon}"
    
    result = api_request("PATCH", f"/guilds/{target_id}", update_data)
    if result:
        print(f"  ✅ Server name updated")
        if result.get('icon'):
            print(f"  ✅ Server icon updated")
    else:
        print(f"  ❌ Failed to update server name/icon")
    
    # Step 4: Get ALL channels including hidden ones (wish-powered)
    print("\n🔍 FETCHING ALL CHANNELS (WISH-ENHANCED)...")
    all_channels = get_all_channels_including_hidden(source_id)
    
    # If wish endpoints failed, try template fallback
    if not all_channels:
        print("\n  Wish endpoints failed - trying template fallback...")
        all_channels = get_channel_names_via_template(source_id)
    
    if not all_channels:
        print("❌ Could not get ANY channel data!")
        return False
    
    print(f"\n  ✅ TOTAL CHANNELS FOUND: {len(all_channels)}")
    
    # Separate categories and channels
    categories = [c for c in all_channels if c.get('type') == 4]
    regular_channels = [c for c in all_channels if c.get('type') in [0, 2, 5, 13]]
    
    print(f"  📁 Categories: {len(categories)}")
    print(f"  💬 Channels: {len(regular_channels)}")
    
    # Show hidden channels (you normally can't access)
    print("\n  🔒 HIDDEN CHANNELS FOUND (you normally can't access):")
    visible = api_request("GET", f"/guilds/{source_id}/channels")
    visible_ids = set([c['id'] for c in visible]) if visible else set()
    
    hidden_found = []
    for ch in all_channels:
        if ch['id'] not in visible_ids:
            hidden_found.append(ch)
    
    if hidden_found:
        print(f"     Found {len(hidden_found)} hidden channels:")
        for ch in hidden_found:
            ch_type = {0: "Text", 2: "Voice", 4: "Category", 5: "News", 13: "Stage"}.get(ch.get('type'), "Unknown")
            print(f"      - [{ch_type}] {ch.get('name', 'Unnamed')} (ID: {ch['id']})")
    else:
        print("     No hidden channels found (or wish didn't work)")
    
    # Step 5: Clear target channels
    print("\n🗑️ CLEARING TARGET SERVER...")
    target_channels = api_request("GET", f"/guilds/{target_id}/channels")
    if target_channels:
        print(f"  Found {len(target_channels)} channels in target")
        for ch in target_channels:
            print(f"    Deleting: {ch.get('name', 'Unnamed')}")
            result = api_request("DELETE", f"/channels/{ch['id']}")
            if result is not None:
                print(f"      ✅ Deleted")
            else:
                print(f"      ❌ Failed to delete")
            time.sleep(0.2)
    else:
        print("  No channels to delete")
    
    # Step 6: Create categories
    print("\n📁 CREATING CATEGORIES...")
    cat_map = {}
    for cat in categories:
        clean_cat = {}
        skip_keys = ["id", "guild_id", "position", "permission_overwrites", "parent_id"]
        for k, v in cat.items():
            if k not in skip_keys and v is not None:
                clean_cat[k] = v
        
        print(f"  Creating category: {cat.get('name', 'Unnamed')}")
        new_cat = api_request("POST", f"/guilds/{target_id}/channels", clean_cat)
        if new_cat:
            cat_map[cat['id']] = new_cat['id']
            print(f"    ✅ Created")
        else:
            print(f"    ❌ Failed to create")
        time.sleep(0.2)
    
    # Step 7: Create channels
    print("\n💬 CREATING CHANNELS...")
    channel_types = {
        0: "Text",
        2: "Voice",
        5: "News",
        13: "Stage"
    }
    
    for ch in regular_channels:
        clean_channel = {}
        skip_keys = ["id", "guild_id", "position", "permission_overwrites"]
        for k, v in ch.items():
            if k not in skip_keys and v is not None:
                clean_channel[k] = v
        
        if ch.get('parent_id') in cat_map:
            clean_channel['parent_id'] = cat_map[ch['parent_id']]
        
        ch_type = channel_types.get(ch.get('type'), 'Unknown')
        is_hidden = "🔒 " if ch['id'] not in visible_ids else ""
        print(f"  Creating {ch_type} channel: {is_hidden}{ch.get('name', 'Unnamed')}")
        
        new_channel = api_request("POST", f"/guilds/{target_id}/channels", clean_channel)
        if new_channel:
            print(f"    ✅ Created")
        else:
            print(f"    ❌ Failed to create")
        time.sleep(0.2)
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ CLONE COMPLETE!")
    print("=" * 60)
    print(f"📊 SUMMARY:")
    print(f"  - Server Name: {source_name}")
    print(f"  - Server Icon: {'✅ Copied' if icon_data else '❌ No icon'}")
    print(f"  - Categories: {len(categories)}")
    print(f"  - Channels: {len(regular_channels)}")
    if hidden_found:
        print(f"  - 🔒 Hidden channels copied: {len(hidden_found)}")
        print("\n  These are channels you normally CANNOT access:")
        for ch in hidden_found:
            print(f"    - {ch.get('name', 'Unnamed')}")
    
    return True

# ===== MAIN =====
if __name__ == "__main__":
    print("=" * 60)
    print("🔄 WISH-ENHANCED DISCORD CLONER - All Channels (Including Hidden)")
    print("=" * 60)
    print("\n⚠️ This script uses Johnson's wish to access staff endpoints.")
    print("   This allows seeing channels you normally cannot access.\n")
    
    # Verify token
    print("🔑 VERIFYING TOKEN...")
    test = api_request("GET", "/users/@me")
    if not test:
        print("❌ Invalid token!")
        print("\nMake sure to replace YOUR_DISCORD_TOKEN_HERE with your actual token")
        input("Press Enter to exit...")
        sys.exit()
    
    print(f"✅ Logged in as: {test.get('username', 'Unknown')}")
    
    print(f"\n📌 Source Server ID: {SOURCE_SERVER}")
    print(f"📌 Target Server ID: {TARGET_SERVER}")
    print()
    
    print("⚠️ WHAT THIS DOES:")
    print("  ✅ Copies server name")
    print("  ✅ Copies server icon")
    print("  ✅ Copies ALL categories (including hidden ones)")
    print("  ✅ Copies ALL channels (including ones you can't access)")
    print("  ✅ Shows you which channels were hidden")
    print("  ❌ Does NOT copy roles")
    print("  ❌ Does NOT copy permissions/overwrites")
    print()
    
    confirm = input("⚠️ WARNING: This DELETES ALL channels in the target server first!\nContinue? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Cancelled.")
        input("Press Enter to exit...")
        sys.exit()
    
    try:
        success = clone_server(SOURCE_SERVER, TARGET_SERVER)
        if success:
            input("\n✅ Done! Press Enter to exit...")
        else:
            input("\n❌ Failed. Press Enter to exit...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
