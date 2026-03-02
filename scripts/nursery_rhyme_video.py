"""
流行英文儿歌视频脚本 - Twinkle Twinkle Little Star
背景：纯色/笔记本纸风格
儿歌名占一行，歌词每行一句
每行前后设计一个符合歌词的小贴纸
歌词带跟随效果（入场/出场动画 + 关键词高亮）

支持两种运行模式:
  --local   使用本地服务器 localhost:30000 (默认)
  --remote  使用远程服务器 capcut-mate.jcaigc.cn 并尝试云渲染
"""
# // AI-GEN-BEGIN
import requests
import json
import time
import sys
import argparse

LOCAL_URL = "http://localhost:30000/openapi/capcut-mate/v1"
REMOTE_URL = "https://capcut-mate.jcaigc.cn/openapi/capcut-mate/v1"

API_KEY = "jcaigc-oyEGS7A1GMtV5piGrwQ3LPDJQfuI"

SEC = 1_000_000


def api(base_url, endpoint, payload, method="POST"):
    url = f"{base_url}/{endpoint}"
    if method == "GET":
        resp = requests.get(url, params=payload, timeout=30)
    else:
        resp = requests.post(url, json=payload, timeout=30)
    data = resp.json()
    code = data.get("code", -1)
    if code != 0:
        print(f"[ERROR] {endpoint}: {json.dumps(data, ensure_ascii=False)}")
        return None
    print(f"[OK] {endpoint}")
    return data


def api_must(base_url, endpoint, payload, method="POST"):
    data = api(base_url, endpoint, payload, method)
    if data is None:
        print(f"致命错误: {endpoint} 调用失败，退出")
        sys.exit(1)
    return data


def build_lyrics():
    return [
        {
            "text": "⭐ Twinkle Twinkle Little Star ⭐",
            "start": 0,
            "end": 4 * SEC,
            "is_title": True,
            "keyword": "Twinkle|Star",
            "keyword_color": "#FFD700",
            "sticker_left": "7234820739201781048",
            "sticker_right": "6979119550646242596",
        },
        {
            "text": "Twinkle, twinkle, little star",
            "start": 4 * SEC,
            "end": 8 * SEC,
            "keyword": "twinkle|star",
            "keyword_color": "#FFD700",
            "sticker_left": "7234820739201781048",
            "sticker_right": "7234820739201781048",
        },
        {
            "text": "How I wonder what you are",
            "start": 8 * SEC,
            "end": 12 * SEC,
            "keyword": "wonder",
            "keyword_color": "#FF69B4",
            "sticker_left": "7062681418106719525",
            "sticker_right": "7084769503933992223",
        },
        {
            "text": "Up above the world so high",
            "start": 12 * SEC,
            "end": 16 * SEC,
            "keyword": "world|high",
            "keyword_color": "#87CEEB",
            "sticker_left": "6939478696990444830",
            "sticker_right": "7027400340890864904",
        },
        {
            "text": "Like a diamond in the sky",
            "start": 16 * SEC,
            "end": 20 * SEC,
            "keyword": "diamond|sky",
            "keyword_color": "#00CED1",
            "sticker_left": "7275841491589680443",
            "sticker_right": "7143071624860830979",
        },
        {
            "text": "Twinkle, twinkle, little star",
            "start": 20 * SEC,
            "end": 24 * SEC,
            "keyword": "twinkle|star",
            "keyword_color": "#FFD700",
            "sticker_left": "7234820739201781048",
            "sticker_right": "7186647248225226018",
        },
        {
            "text": "How I wonder what you are",
            "start": 24 * SEC,
            "end": 28 * SEC,
            "keyword": "wonder",
            "keyword_color": "#FF69B4",
            "sticker_left": "7142862771779030302",
            "sticker_right": "7211308123187957024",
        },
    ]


def create_draft(base_url):
    print("=" * 60)
    print("🎵 开始创建: Twinkle Twinkle Little Star 儿歌视频")
    print(f"服务器: {base_url}")
    print("=" * 60)

    draft = api_must(base_url, "create_draft", {"width": 1080, "height": 1920})
    draft_url = draft["draft_url"]

    if base_url == LOCAL_URL:
        draft_url = draft_url.replace(
            "https://capcut-mate.jcaigc.cn",
            "http://localhost:30000"
        )

    print(f"草稿URL: {draft_url}")
    return draft_url


def add_background(base_url, draft_url):
    bg_url = "https://placehold.co/1080x1920/FFF8E7/FFF8E7.png"
    total_duration = 32 * SEC
    image_infos = [{
        "image_url": bg_url,
        "width": 1080,
        "height": 1920,
        "start": 0,
        "end": total_duration
    }]
    api_must(base_url, "add_images", {
        "draft_url": draft_url,
        "image_infos": json.dumps(image_infos)
    })


def add_title_caption(base_url, draft_url, title):
    print("\n--- 添加标题字幕 ---")
    title_captions = [{
        "start": title["start"],
        "end": title["end"],
        "text": title["text"],
        "keyword": title["keyword"],
        "keyword_color": title["keyword_color"],
        "keyword_font_size": 22,
        "font_size": 18,
        "in_animation": "渐显入场",
        "out_animation": "渐隐出场",
        "in_animation_duration": 800000,
        "out_animation_duration": 600000,
    }]
    return api_must(base_url, "add_captions", {
        "draft_url": draft_url,
        "captions": json.dumps(title_captions),
        "text_color": "#2C3E50",
        "font_size": 18,
        "bold": True,
        "alignment": 1,
        "transform_y": -600,
        "has_shadow": True,
        "shadow_info": {
            "shadow_alpha": 0.5,
            "shadow_color": "#000000",
            "shadow_diffuse": 10.0,
            "shadow_distance": 3.0,
            "shadow_angle": -45.0
        }
    })


def add_lyric_captions(base_url, draft_url, lyric_lines):
    print("\n--- 添加歌词字幕 ---")
    captions = []
    for line in lyric_lines:
        captions.append({
            "start": line["start"],
            "end": line["end"],
            "text": line["text"],
            "keyword": line.get("keyword"),
            "keyword_color": line.get("keyword_color", "#FFD700"),
            "keyword_font_size": 16,
            "font_size": 14,
            "in_animation": "变色输入",
            "out_animation": "渐隐出场",
            "in_animation_duration": 600000,
            "out_animation_duration": 500000,
        })

    return api_must(base_url, "add_captions", {
        "draft_url": draft_url,
        "captions": json.dumps(captions),
        "text_color": "#34495E",
        "font_size": 14,
        "alignment": 1,
        "transform_y": 0,
        "border_color": "#FFFFFF",
        "has_shadow": True,
        "shadow_info": {
            "shadow_alpha": 0.3,
            "shadow_color": "#000000",
            "shadow_diffuse": 8.0,
            "shadow_distance": 2.0,
            "shadow_angle": -45.0
        }
    })


def add_stickers(base_url, draft_url, lyrics):
    print("\n--- 添加歌词贴纸 ---")
    for i, line in enumerate(lyrics):
        label = "标题" if line.get("is_title") else f"第{i}行"

        for side, key, tx in [("左", "sticker_left", -400), ("右", "sticker_right", 400)]:
            sticker_id = line.get(key)
            if sticker_id:
                api_must(base_url, "add_sticker", {
                    "draft_url": draft_url,
                    "sticker_id": sticker_id,
                    "start": line["start"],
                    "end": line["end"],
                    "scale": 0.35,
                    "transform_x": tx,
                    "transform_y": -100 if line.get("is_title") else 100,
                })
                print(f"  {label} {side}侧贴纸: {sticker_id}")


def add_keyframe_effects(base_url, draft_url, lyrics_resp):
    print("\n--- 添加关键帧跟随效果 ---")
    segment_infos = lyrics_resp.get("segment_infos", [])
    if not segment_infos:
        print("  无歌词片段信息，跳过关键帧")
        return

    keyframes = []
    for seg_info in segment_infos:
        seg_id = seg_info["id"]
        seg_start = seg_info["start"]
        seg_end = seg_info["end"]
        seg_duration = seg_end - seg_start
        keyframes.extend([
            {"segment_id": seg_id, "property": "UNIFORM_SCALE",
             "offset": seg_start, "value": 0.8},
            {"segment_id": seg_id, "property": "UNIFORM_SCALE",
             "offset": seg_start + int(seg_duration * 0.15), "value": 1.0},
            {"segment_id": seg_id, "property": "UNIFORM_SCALE",
             "offset": seg_start + int(seg_duration * 0.85), "value": 1.0},
            {"segment_id": seg_id, "property": "UNIFORM_SCALE",
             "offset": seg_end, "value": 0.8},
        ])

    api_must(base_url, "add_keyframes", {
        "draft_url": draft_url,
        "keyframes": json.dumps(keyframes)
    })


def save_and_list_draft(base_url, draft_url):
    print("\n--- 保存草稿 ---")
    api_must(base_url, "save_draft", {"draft_url": draft_url})

    print("\n--- 获取草稿文件列表 ---")
    draft_id = draft_url.split("draft_id=")[-1]
    get_resp = requests.get(f"{base_url}/get_draft", params={"draft_id": draft_id}, timeout=15)
    get_data = get_resp.json()
    print("草稿文件列表:")
    for f in get_data.get("files", []):
        print(f"  - {f}")
    return draft_id


def try_render(base_url, draft_url, api_key):
    print("\n--- 尝试渲染视频 ---")
    print(f"API Key: {api_key[:12]}***")
    print(f"渲染服务器: {base_url}")

    payload = {"draft_url": draft_url, "apiKey": api_key}
    render_resp = requests.post(f"{base_url}/gen_video", json=payload, timeout=30)
    render_data = render_resp.json()
    print(f"渲染请求结果: {json.dumps(render_data, ensure_ascii=False, indent=2)}")

    if render_data.get("code") == 0:
        print("✅ 渲染任务已提交！开始轮询状态...")
        for attempt in range(1, 21):
            time.sleep(5)
            status_resp = requests.post(
                f"{base_url}/gen_video_status",
                json={"draft_url": draft_url},
                timeout=30
            )
            status_data = status_resp.json()
            status = status_data.get("status", "unknown")
            progress = status_data.get("progress", 0)
            print(f"  [{attempt}/20] 状态: {status}, 进度: {progress}%")

            if status == "completed":
                video_url = status_data.get("video_url", "")
                print(f"\n🎉 视频渲染完成!")
                print(f"视频下载地址: {video_url}")
                return status_data
            elif status == "failed":
                error_msg = status_data.get("error_message", "未知错误")
                print(f"\n❌ 渲染失败: {error_msg}")
                return status_data

        print("\n⏰ 轮询超时（100秒），请稍后手动查询状态")
        return None
    else:
        print(f"渲染请求未成功 (code={render_data.get('code')})")
        return render_data


def main():
    parser = argparse.ArgumentParser(description="Twinkle Twinkle Little Star 儿歌视频生成脚本")
    parser.add_argument("--remote", action="store_true",
                        help="使用远程服务器 capcut-mate.jcaigc.cn")
    parser.add_argument("--api-key", default=API_KEY,
                        help="渲染使用的 API Key")
    args = parser.parse_args()

    base_url = REMOTE_URL if args.remote else LOCAL_URL

    lyrics = build_lyrics()

    draft_url = create_draft(base_url)
    add_background(base_url, draft_url)

    title = lyrics[0]
    add_title_caption(base_url, draft_url, title)

    lyric_lines = lyrics[1:]
    lyrics_resp = add_lyric_captions(base_url, draft_url, lyric_lines)

    add_stickers(base_url, draft_url, lyrics)
    add_keyframe_effects(base_url, draft_url, lyrics_resp)

    draft_id = save_and_list_draft(base_url, draft_url)

    render_result = try_render(base_url, draft_url, args.api_key)

    print("\n" + "=" * 60)
    print("✅ 儿歌视频草稿创建完成!")
    print(f"草稿ID: {draft_id}")
    print(f"草稿URL: {draft_url}")
    if args.remote:
        print(f"远程API文档: https://capcut-mate.jcaigc.cn/docs")
    else:
        print(f"本地API文档: http://localhost:30000/docs")
    print("=" * 60)


if __name__ == "__main__":
    main()
# // AI-GEN-END
