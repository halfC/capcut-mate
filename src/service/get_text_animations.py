"""
获取文字出入场动画的业务逻辑处理模块
"""
from typing import List, Dict, Any, Optional, Tuple, Type
from src.utils.logger import logger
from exceptions import CustomException, CustomError
from src.pyJianYingDraft.metadata import TextIntro, TextOutro, TextLoopAnim
from src.pyJianYingDraft.metadata.effect_meta import EffectEnum, AnimationMeta


def get_text_animations(mode: int = 0, type: str = "in", keyword: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    获取文字出入场动画列表
    
    Args:
        mode: 动画模式，0=所有，1=VIP，2=免费，默认值为0
        type: 动画类型，in=入场，out=出场，loop=循环，默认值为"in"
        keyword: 按动画名称关键字过滤（可选，大小写不敏感）
    
    Returns:
        effects: 文字出入场动画对象数组
        
    Raises:
        CustomException: 获取文字动画失败
    """
    logger.info(f"get_text_animations called with mode: {mode}, type: {type}, keyword: {keyword}")
    
    try:
        # 1. 参数验证
        if type not in ["in", "out", "loop"]:
            logger.error(f"Invalid animation type: {type}")
            raise CustomException(CustomError.TEXT_ANIMATION_GET_FAILED)
        
        if mode not in [0, 1, 2]:
            logger.error(f"Invalid mode: {mode}")
            raise CustomException(CustomError.TEXT_ANIMATION_GET_FAILED)
        
        normalized_keyword = keyword.strip().lower() if isinstance(keyword, str) and keyword.strip() else None

        # 2. 根据类型和模式获取动画数据
        animations = _get_animations_by_type_and_mode(type=type, mode=mode, keyword=normalized_keyword)
        logger.info(f"Found {len(animations)} animations for type: {type}, mode: {mode}, keyword: {normalized_keyword}")
        
        # 3. 直接返回对象数组（不再转换为JSON字符串）
        logger.info(f"Successfully returned animations array with {len(animations)} items")
        
        return animations
        
    except CustomException:
        logger.error(f"Get text animations failed for type: {type}, mode: {mode}, keyword: {keyword}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_text_animations: {str(e)}")
        raise CustomException(CustomError.TEXT_ANIMATION_GET_FAILED)


def _get_animations_by_type_and_mode(type: str, mode: int, keyword: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    根据动画类型和模式获取对应的动画数据
    
    Args:
        type: 动画类型（in/out/loop）
        mode: 动画模式（0=所有，1=VIP，2=免费）
        keyword: 动画名称关键字（可选）
    
    Returns:
        包含动画信息的列表
    """
    logger.info(f"Getting animations for type: {type}, mode: {mode}, keyword: {keyword}")
    
    animation_enum, category_id, category_name = _get_animation_source(type)
    all_animations = [_convert_animation_to_item(meta=member.value, animation_type=type, category_id=category_id, category_name=category_name)
                      for member in animation_enum]
    
    # 1. 根据关键字过滤（可选）
    if keyword:
        filtered_by_keyword = [anim for anim in all_animations if keyword in anim["name"].lower()]
    else:
        filtered_by_keyword = all_animations
    logger.info(f"Filtered by keyword '{keyword}': {len(filtered_by_keyword)} animations")
    
    # 2. 根据模式过滤
    if mode == 0:  # 所有
        result = filtered_by_keyword
    elif mode == 1:  # VIP
        result = [anim for anim in filtered_by_keyword if anim.get("is_vip", False)]
    elif mode == 2:  # 免费
        result = [anim for anim in filtered_by_keyword if not anim.get("is_vip", False)]
    else:
        result = []
    
    logger.info(f"Final filtered result: {len(result)} animations")
    return result


def _get_animation_source(animation_type: str) -> Tuple[Type[EffectEnum], str, str]:
    if animation_type == "in":
        return TextIntro, "text_ruchang", "文字入场"
    if animation_type == "out":
        return TextOutro, "text_chuchang", "文字出场"
    return TextLoopAnim, "text_xunhuan", "文字循环"


def _convert_animation_to_item(
    meta: AnimationMeta,
    animation_type: str,
    category_id: str,
    category_name: str,
) -> Dict[str, Any]:
    return {
        "resource_id": meta.resource_id,
        "type": animation_type,
        "category_id": category_id,
        "category_name": category_name,
        "duration": meta.duration,
        "id": meta.effect_id,
        "name": meta.title,
        "request_id": "",
        "start": 0,
        "icon_url": "",
        "material_type": "sticker",
        "panel": "",
        "path": "",
        "platform": "all",
        "is_vip": meta.is_vip,
    }