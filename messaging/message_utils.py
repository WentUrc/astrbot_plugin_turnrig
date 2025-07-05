# 导入消息工具模块喵～ 📦
import time

from astrbot.api import logger


async def async_detect_message_field(data: dict, platform_name: str = None) -> str:
    """
    异步智能检测消息字段名称喵～ 🔍
    支持检测多种可能的消息字段名称和平台特定字段

    Args:
        data: 要检测的数据字典喵
        platform_name: 平台名称，用于特定平台检测喵

    Returns:
        str: 检测到的消息字段名称，未找到时返回None喵～

    Note:
        按优先级检测: message > messages > data > content > msg > msgs > items > nodes ✨
    """
    if not isinstance(data, dict):
        logger.debug(f"数据不是字典类型，无法检测消息字段喵: {type(data)} 📦")
        return None

    # 定义检测字段的优先级列表喵～ 📋
    field_candidates = [
        "message",
        "messages",
        "data",
        "content",
        "msg",
        "msgs",
        "items",
        "nodes",
    ]

    # 平台特定字段检测喵～ 🎯
    if platform_name == "aiocqhttp":
        # OneBot 平台优先检测 message 字段
        field_candidates = ["message"] + [f for f in field_candidates if f != "message"]

    logger.debug(f"开始智能检测消息字段，候选字段: {field_candidates} 🔍")

    for field_name in field_candidates:
        if field_name in data:
            field_value = data[field_name]
            logger.debug(f"发现字段 '{field_name}': 类型={type(field_value)} 📋")

            # 检查字段值是否为有效的消息内容喵～ ✅
            if field_value is not None:
                # 如果是列表且非空，很可能是消息字段喵～
                if isinstance(field_value, list) and len(field_value) > 0:
                    logger.debug(f"字段 '{field_name}' 是非空列表，确认为消息字段喵 ✨")
                    return field_name

                # 如果是字符串且非空，也可能是消息字段喵～
                elif isinstance(field_value, str) and field_value.strip():
                    logger.debug(
                        f"字段 '{field_name}' 是非空字符串，确认为消息字段喵 ✨"
                    )
                    return field_name

                # 如果是字典且非空，可能包含嵌套消息喵～
                elif isinstance(field_value, dict) and len(field_value) > 0:
                    logger.debug(
                        f"字段 '{field_name}' 是非空字典，可能包含嵌套消息喵 🔄"
                    )
                    return field_name

    logger.debug("未检测到有效的消息字段喵 😿")
    return None


async def async_detect_message_content_field(
    msg_data: dict, platform_name: str = None
) -> str:
    """
    异步智能检测消息内容字段名称喵～ 📝
    用于检测消息对象内部的内容字段

    Args:
        msg_data: 消息数据字典喵
        platform_name: 平台名称，用于特定平台检测喵

    Returns:
        str: 检测到的内容字段名称，未找到时返回None喵～

    Note:
        支持启发式检测和平台特定检测，优先级: content > message > data > text > msg ✨
    """
    if not isinstance(msg_data, dict):
        logger.debug(f"消息数据不是字典类型，无法检测内容字段喵: {type(msg_data)} 📦")
        return None

    # 内容字段候选列表喵～ 📋
    content_candidates = ["content", "message", "data", "text", "msg"]

    # 平台特定检测优化喵～ 🎯
    if platform_name == "aiocqhttp":
        # OneBot 平台特殊处理
        content_candidates = ["content", "message"] + [
            f for f in content_candidates if f not in ["content", "message"]
        ]

    logger.debug(f"开始检测消息内容字段，候选字段: {content_candidates} 🔍")

    for field_name in content_candidates:
        if field_name in msg_data:
            field_value = msg_data[field_name]
            logger.debug(f"发现内容字段 '{field_name}': 类型={type(field_value)} 📋")

            # 检查是否为有效的内容字段喵～ ✅
            if field_value is not None:
                # 列表类型很可能是消息内容喵～
                if isinstance(field_value, list):
                    logger.debug(
                        f"内容字段 '{field_name}' 是列表类型，确认为内容字段喵 ✨"
                    )
                    return field_name

                # 非空字符串也是有效内容喵～
                elif isinstance(field_value, str) and field_value.strip():
                    logger.debug(
                        f"内容字段 '{field_name}' 是非空字符串，确认为内容字段喵 ✨"
                    )
                    return field_name

                # 字典可能包含复杂内容结构喵～
                elif isinstance(field_value, dict) and len(field_value) > 0:
                    logger.debug(
                        f"内容字段 '{field_name}' 是非空字典，确认为内容字段喵 ✨"
                    )
                    return field_name

    logger.debug("未检测到有效的消息内容字段喵 😿")
    return None


async def fetch_forward_message_nodes(forward_id, event):
    """
    获取转发消息的节点内容喵～ 📤
    将转发消息转换为可用于构建新转发消息的节点格式！

    Args:
        forward_id: 转发消息ID喵
        event: 消息事件对象喵

    Returns:
        list: 转发消息节点列表，失败时返回None喵～

    Note:
        返回的节点可以直接用于构建新的转发消息喵！ ✨
    """
    if event.get_platform_name() != "aiocqhttp":
        logger.warning(f"平台 {event.get_platform_name()} 不支持转发消息获取喵 😿")
        return None

    if not forward_id:
        logger.warning("转发消息ID为空，无法获取内容喵 😿")
        return None

    try:
        client = event.bot
        logger.debug(f"尝试获取转发消息内容喵: ID={forward_id} 🔍")

        # 方法1: 尝试使用get_forward_msg API喵～ 📤
        forward_payload = {"id": forward_id}
        try:
            forward_response = await client.api.call_action(
                "get_forward_msg", **forward_payload
            )
            logger.debug(
                f"成功通过get_forward_msg获取转发消息喵: {forward_response} ✅"
            )

            if not forward_response:
                logger.warning(f"get_forward_msg返回空结果喵: {forward_response} 😿")
                return None

            # 智能检测消息字段喵～ 🔍
            message_field = await async_detect_message_field(
                forward_response, event.get_platform_name()
            )
            if message_field and isinstance(forward_response[message_field], list):
                messages = forward_response[message_field]
                logger.debug(f"智能检测到消息字段: {message_field} ✨")
                logger.info(f"从get_forward_msg获取到 {len(messages)} 条消息喵 📊")

                # 转换为节点格式喵～ 🔄
                nodes = []
                for i, msg in enumerate(messages):
                    if not isinstance(msg, dict):
                        logger.debug(f"跳过非字典格式的消息 {i}: {type(msg)} 📦")
                        continue

                    # 检查是否是node类型的消息喵～ 🎯
                    if msg.get("type") == "node" and "data" in msg:
                        # 直接使用OneBot返回的节点数据喵～ 📤
                        node_data = msg["data"]

                        # 构建标准化节点数据喵～ 🏗️
                        node = {
                            "type": "node",
                            "data": {
                                "name": node_data.get("nickname", "未知用户"),
                                "uin": str(node_data.get("user_id", "0")),
                                "content": node_data.get("content", []),
                                "time": node_data.get("time", int(time.time())),
                            },
                        }

                        logger.info(
                            f"处理节点 {i + 1}: 用户={node['data']['name']}, 内容数量={len(node['data']['content'])} 📋"
                        )
                        nodes.append(node)
                    else:
                        # 兼容旧格式，构建节点数据喵～ 🔄
                        node = {
                            "type": "node",
                            "data": {
                                "name": msg.get(
                                    "nickname",
                                    msg.get("sender", {}).get("nickname", "未知用户"),
                                ),
                                "uin": str(
                                    msg.get(
                                        "user_id",
                                        msg.get("sender", {}).get("user_id", "0"),
                                    )
                                ),
                                "content": [],
                                "time": msg.get("time", int(time.time())),
                            },
                        }

                        # 处理消息内容喵～ 📝
                        content_processed = False

                        # 尝试从content字段获取消息内容喵～ 🔍
                        if "content" in msg and isinstance(msg["content"], list):
                            for content_item in msg["content"]:
                                if isinstance(content_item, dict):
                                    content_type = content_item.get("type", "")
                                    if content_type == "text":
                                        text_content = content_item.get("data", {}).get(
                                            "text", ""
                                        )
                                        if text_content:
                                            node["data"]["content"].append(
                                                {
                                                    "type": "text",
                                                    "data": {"text": text_content},
                                                }
                                            )
                                            content_processed = True
                                    elif content_type == "image":
                                        node["data"]["content"].append(
                                            {
                                                "type": "image",
                                                "data": content_item.get("data", {}),
                                            }
                                        )
                                        content_processed = True
                                    else:
                                        # 保持原始格式喵～ 📦
                                        node["data"]["content"].append(content_item)
                                        content_processed = True

                        # 智能检测消息内容字段喵～ 🔍
                        if not content_processed:
                            content_field = await async_detect_message_content_field(
                                msg, event.get_platform_name()
                            )
                            if content_field:
                                message_content = msg[content_field]
                                logger.debug(f"智能检测到内容字段: {content_field} ✨")
                                if isinstance(message_content, list):
                                    for msg_part in message_content:
                                        if isinstance(msg_part, dict):
                                            if msg_part.get("type") == "text":
                                                text_content = msg_part.get(
                                                    "data", {}
                                                ).get("text", "")
                                                if text_content:
                                                    node["data"]["content"].append(
                                                        {
                                                            "type": "text",
                                                            "data": {
                                                                "text": text_content
                                                            },
                                                        }
                                                    )
                                                    content_processed = True
                                        else:
                                            node["data"]["content"].append(msg_part)
                                            content_processed = True
                                elif (
                                    isinstance(message_content, str) and message_content
                                ):
                                    node["data"]["content"].append(
                                        {
                                            "type": "text",
                                            "data": {"text": message_content},
                                        }
                                    )
                                    content_processed = True
                                content_processed = True

                        # 如果仍然没有内容，添加默认文本喵～ 📝
                        if not content_processed:
                            node["data"]["content"].append(
                                {"type": "text", "data": {"text": "[消息内容无法解析]"}}
                            )

                        nodes.append(node)

                if nodes:
                    logger.info(f"成功转换转发消息为 {len(nodes)} 个节点喵 ✅")
                    return nodes
                else:
                    logger.warning("转发消息转换后没有有效节点喵 😿")
                    return None
            else:
                logger.warning(
                    f"get_forward_msg响应格式不正确喵: {forward_response} 😿"
                )
                return None

        except Exception as api_error:
            logger.error(f"调用get_forward_msg API失败喵: {api_error} 😿")
            # API失败时直接返回None，让上层决定如何处理喵～ 📝
            return None

    except Exception as e:
        logger.error(f"获取转发消息节点失败喵: {e} 😿")
        return None


async def fetch_message_detail(message_id, event):
    """
    获取消息详情喵～ 📄
    参考了搬史插件的实现，支持普通消息和转发消息！

    Args:
        message_id: 消息ID喵
        event: 消息事件对象喵

    Returns:
        dict | None: 消息详情数据，失败时返回None喵～

    Note:
        会自动检测并获取转发消息的完整内容喵！ ✨
    """
    if event.get_platform_name() != "aiocqhttp":
        return None

    try:
        client = event.bot
        # 获取消息详情喵～ 🔍
        payload = {"message_id": message_id}
        response = await client.api.call_action("get_msg", **payload)
        logger.debug(f"获取到消息详情喵: {response} 📋")

        # 智能检测并处理转发消息喵～ 📤
        message_field = await async_detect_message_field(
            response, event.get_platform_name()
        )
        if message_field:
            message_list = response[message_field]
            logger.debug(f"智能检测到消息字段: {message_field} ✨")
            if isinstance(message_list, list) and len(message_list) > 0:
                first_segment = message_list[0]
                if (
                    isinstance(first_segment, dict)
                    and first_segment.get("type") == "forward"
                ):
                    # 这是一个转发消息，尝试获取其内容喵～ 📨
                    forward_id = first_segment.get("data", {}).get("id", "")
                    if forward_id:
                        forward_payload = {"message_id": forward_id}
                        try:
                            forward_response = await client.api.call_action(
                                "get_forward_msg", **forward_payload
                            )
                            # 将转发消息的内容添加到原始响应中喵～ 📝
                            response["forward_content"] = forward_response
                            logger.debug(f"获取到转发消息内容喵: {forward_response} ✨")
                        except Exception as e:
                            logger.warning(f"获取转发消息内容失败喵: {e} 😿")

        return response
    except Exception as e:
        logger.error(f"获取消息详情失败喵: {e} 😿")
        return None


async def fetch_emoji_reactions(message_id, event):
    """
    获取消息表情回应喵～ 😊
    此功能已禁用，返回空数据！

    Args:
        message_id: 消息ID喵
        event: 消息事件对象喵

    Returns:
        dict: 空字典，表情回应功能已禁用喵～

    Note:
        为了兼容性保留此方法，但不再获取实际数据喵！ 💫
    """
    # 直接返回空字典，不再获取表情回应喵～ 📦
    return {}
