from src.service.add_images import map_video_animation_name_to_enum
from src.service.get_image_animations import get_image_animations


def _to_add_images_animation_type(animation_type: str) -> str:
    if animation_type == "loop":
        return "group"
    return animation_type


def test_get_image_animations_names_are_compatible_with_add_images():
    """get_image_animations 返回的名称应可直接用于 add_images 的动画参数。"""
    for animation_type in ("in", "out", "loop"):
        animations = get_image_animations(mode=0, type=animation_type)
        assert animations, f"{animation_type} 动画列表不应为空"

        add_images_animation_type = _to_add_images_animation_type(animation_type)
        for animation in animations:
            mapped_enum = map_video_animation_name_to_enum(
                animation_name=animation["name"],
                animation_type=add_images_animation_type,
            )
            assert mapped_enum is not None, (
                f"动画 '{animation['name']}' ({animation_type}) 无法映射到 add_images"
            )


def test_get_image_animations_mode_filter_works():
    """mode 过滤逻辑应正确区分 VIP 与免费动画。"""
    all_animations = get_image_animations(mode=0, type="in")
    vip_animations = get_image_animations(mode=1, type="in")
    free_animations = get_image_animations(mode=2, type="in")

    assert all_animations, "in 动画全集不应为空"
    assert len(vip_animations) + len(free_animations) == len(all_animations)
    assert all(item["is_vip"] for item in vip_animations)
    assert all(not item["is_vip"] for item in free_animations)


def test_get_image_animations_keyword_filter_works():
    """keyword 过滤应支持大小写不敏感和空白裁剪。"""
    all_animations = get_image_animations(mode=0, type="in")
    assert all_animations, "in 动画全集不应为空"

    candidate_name = next(
        (
            item["name"]
            for item in all_animations
            if any(char.isascii() and char.isalpha() for char in item["name"])
        ),
        all_animations[0]["name"],
    )
    keyword = candidate_name[:3] if len(candidate_name) >= 3 else candidate_name

    filtered = get_image_animations(mode=0, type="in", keyword=f"  {keyword.lower()}  ")
    assert filtered, "关键字过滤后结果不应为空"
    assert all(keyword.lower() in item["name"].lower() for item in filtered)

    filtered_with_blank_keyword = get_image_animations(mode=0, type="in", keyword="   ")
    assert len(filtered_with_blank_keyword) == len(all_animations)
