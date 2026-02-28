"""
流行英文儿歌视频脚本 - Twinkle Twinkle Little Star
背景：纯色/笔记本纸风格
儿歌名占一行，歌词每行一句
每行前后设计一个符合歌词的小贴纸
歌词带跟随效果（入场/出场动画 + 关键词高亮）
"""
# // AI-GEN-BEGIN
import requests
import json
import time
import sys

BASE_URL = "http://localhost:30000/openapi/capcut-mate/v1"

# 1秒 = 1_000_000 微秒
SEC = 1_000_000


def api(endpoint, payload):
    url = f"{BASE_URL}/{endpoint}"
    resp = requests.post(url, json=payload)
    data = resp.json()
    if data.get("code", -1) != 0:
        print(f"[ERROR] {endpoint}: {json.dumps(data, ensure_ascii=False)}")
        sys.exit(1)
    print(f"[OK] {endpoint}")
    return data


def main():
    # ==========================================
    # 第一步: 创建草稿 (9:16竖屏)
    # ==========================================
    print("=" * 60)
    print("🎵 开始创建: Twinkle Twinkle Little Star 儿歌视频")
    print("=" * 60)

    draft = api("create_draft", {"width": 1080, "height": 1920})
    draft_url = draft["draft_url"].replace(
        "https://capcut-mate.jcaigc.cn",
        "http://localhost:30000"
    )
    print(f"草稿URL: {draft_url}")

    # ==========================================
    # 第二步: 添加纯色背景图片
    # ==========================================
    # 使用公开可访问的纯色背景图片URL（浅米色/笔记本纸风格）
    # 这里使用 placehold.co 生成纯色背景
    bg_color_hex = "FFF8E7"  # 浅米黄色，类似笔记本纸
    bg_url = f"https://placehold.co/1080x1920/{bg_color_hex}/{bg_color_hex}.png"

    total_duration = 32 * SEC  # 总时长32秒

    image_infos = [
        {
            "image_url": bg_url,
            "width": 1080,
            "height": 1920,
            "start": 0,
            "end": total_duration
        }
    ]
    api("add_images", {
        "draft_url": draft_url,
        "image_infos": json.dumps(image_infos)
    })

    # ==========================================
    # 第三步: 定义歌词时间线
    # ==========================================
    lyrics = [
        {
            "text": "⭐ Twinkle Twinkle Little Star ⭐",
            "start": 0,
            "end": 4 * SEC,
            "is_title": True,
            "keyword": "Twinkle|Star",
            "keyword_color": "#FFD700",
            "sticker_left": "7234820739201781048",   # 星星
            "sticker_right": "6979119550646242596",  # 音符
        },
        {
            "text": "Twinkle, twinkle, little star",
            "start": 4 * SEC,
            "end": 8 * SEC,
            "keyword": "twinkle|star",
            "keyword_color": "#FFD700",
            "sticker_left": "7234820739201781048",   # 星星
            "sticker_right": "7234820739201781048",  # 星星
        },
        {
            "text": "How I wonder what you are",
            "start": 8 * SEC,
            "end": 12 * SEC,
            "keyword": "wonder",
            "keyword_color": "#FF69B4",
            "sticker_left": "7062681418106719525",   # 问号
            "sticker_right": "7084769503933992223",  # 闪光
        },
        {
            "text": "Up above the world so high",
            "start": 12 * SEC,
            "end": 16 * SEC,
            "keyword": "world|high",
            "keyword_color": "#87CEEB",
            "sticker_left": "6939478696990444830",   # 云朵
            "sticker_right": "7027400340890864904",  # 星空
        },
        {
            "text": "Like a diamond in the sky",
            "start": 16 * SEC,
            "end": 20 * SEC,
            "keyword": "diamond|sky",
            "keyword_color": "#00CED1",
            "sticker_left": "7275841491589680443",   # 钻石星星
            "sticker_right": "7143071624860830979",  # 蓝天白云
        },
        {
            "text": "Twinkle, twinkle, little star",
            "start": 20 * SEC,
            "end": 24 * SEC,
            "keyword": "twinkle|star",
            "keyword_color": "#FFD700",
            "sticker_left": "7234820739201781048",   # 星星
            "sticker_right": "7186647248225226018",  # 闪烁星星
        },
        {
            "text": "How I wonder what you are",
            "start": 24 * SEC,
            "end": 28 * SEC,
            "keyword": "wonder",
            "keyword_color": "#FF69B4",
            "sticker_left": "7142862771779030302",   # 可爱云朵花朵
            "sticker_right": "7211308123187957024",  # 月亮
        },
    ]

    # ==========================================
    # 第四步: 添加字幕（带动画和关键词高亮）
    # ==========================================
    print("\n--- 添加歌词字幕 ---")

    # 标题行: 大号字体, 居中靠上
    title = lyrics[0]
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
    title_resp = api("add_captions", {
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

    # 歌词行: 每行一句, 带入场/出场动画 + 关键词高亮
    lyric_lines = lyrics[1:]
    lyric_captions = []
    for line in lyric_lines:
        lyric_captions.append({
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

    lyrics_resp = api("add_captions", {
        "draft_url": draft_url,
        "captions": json.dumps(lyric_captions),
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

    # ==========================================
    # 第五步: 为每行歌词添加左右贴纸
    # ==========================================
    print("\n--- 添加歌词贴纸 ---")

    for i, line in enumerate(lyrics):
        label = "标题" if line.get("is_title") else f"第{i}行"

        sticker_left_id = line.get("sticker_left")
        sticker_right_id = line.get("sticker_right")

        if sticker_left_id:
            api("add_sticker", {
                "draft_url": draft_url,
                "sticker_id": sticker_left_id,
                "start": line["start"],
                "end": line["end"],
                "scale": 0.35,
                "transform_x": -400,
                "transform_y": -100 if line.get("is_title") else 100,
            })
            print(f"  {label} 左侧贴纸: {sticker_left_id}")

        if sticker_right_id:
            api("add_sticker", {
                "draft_url": draft_url,
                "sticker_id": sticker_right_id,
                "start": line["start"],
                "end": line["end"],
                "scale": 0.35,
                "transform_x": 400,
                "transform_y": -100 if line.get("is_title") else 100,
            })
            print(f"  {label} 右侧贴纸: {sticker_right_id}")

    # ==========================================
    # 第六步: 为歌词文本添加关键帧动画（跟随效果）
    # ==========================================
    print("\n--- 添加关键帧跟随效果 ---")

    segment_infos = lyrics_resp.get("segment_infos", [])
    if segment_infos:
        keyframes = []
        for seg_info in segment_infos:
            seg_id = seg_info["id"]
            seg_start = seg_info["start"]
            seg_end = seg_info["end"]
            seg_duration = seg_end - seg_start

            keyframes.extend([
                {
                    "segment_id": seg_id,
                    "property": "UNIFORM_SCALE",
                    "offset": seg_start,
                    "value": 0.8
                },
                {
                    "segment_id": seg_id,
                    "property": "UNIFORM_SCALE",
                    "offset": seg_start + int(seg_duration * 0.15),
                    "value": 1.0
                },
                {
                    "segment_id": seg_id,
                    "property": "UNIFORM_SCALE",
                    "offset": seg_start + int(seg_duration * 0.85),
                    "value": 1.0
                },
                {
                    "segment_id": seg_id,
                    "property": "UNIFORM_SCALE",
                    "offset": seg_end,
                    "value": 0.8
                },
            ])

        if keyframes:
            api("add_keyframes", {
                "draft_url": draft_url,
                "keyframes": json.dumps(keyframes)
            })

    # ==========================================
    # 第七步: 保存草稿
    # ==========================================
    print("\n--- 保存草稿 ---")
    api("save_draft", {"draft_url": draft_url})

    # ==========================================
    # 第八步: 获取草稿文件
    # ==========================================
    print("\n--- 获取草稿文件列表 ---")
    draft_id = draft_url.split("draft_id=")[-1]
    get_resp = requests.get(f"{BASE_URL}/get_draft?draft_id={draft_id}")
    get_data = get_resp.json()
    print(f"草稿文件列表:")
    for f in get_data.get("files", []):
        print(f"  - {f}")

    # ==========================================
    # 第九步: 尝试渲染视频
    # ==========================================
    print("\n--- 尝试渲染视频 ---")
    print("注意: 视频渲染需要 Windows + 剪映桌面端，Linux 环境将返回平台限制提示")

    try:
        render_resp = requests.post(f"{BASE_URL}/gen_video", json={
            "draft_url": draft_url
        })
        render_data = render_resp.json()
        print(f"渲染请求结果: {json.dumps(render_data, ensure_ascii=False, indent=2)}")

        if render_data.get("code") == 0:
            print("渲染任务已提交，查询状态...")
            time.sleep(3)
            status_resp = requests.post(f"{BASE_URL}/gen_video_status", json={
                "draft_url": draft_url
            })
            status_data = status_resp.json()
            print(f"渲染状态: {json.dumps(status_data, ensure_ascii=False, indent=2)}")
        else:
            print("渲染请求未成功（预期行为 - Linux 环境不支持渲染）")
    except Exception as e:
        print(f"渲染请求异常: {e}")

    # ==========================================
    # 完成
    # ==========================================
    print("\n" + "=" * 60)
    print("✅ 儿歌视频草稿创建完成!")
    print(f"草稿ID: {draft_id}")
    print(f"草稿URL: {draft_url}")
    print(f"API文档: http://localhost:30000/docs")
    print(f"草稿下载: {draft_url}")
    print("=" * 60)


if __name__ == "__main__":
    main()
# // AI-GEN-END
