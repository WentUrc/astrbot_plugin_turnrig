"""
转发消息构建器模块喵～
负责将接收到的消息转换为适合转发的格式
主人的消息都会在这里被精心打包呢～ ฅ(^•ω•^)ฅ

这个模块的主要功能：
- 构建转发节点数据结构 🏗️
- 处理各种类型的消息组件 📝
- 下载和转换媒体文件 🎬
- 保持消息的完整性喵～ ✨
"""

import base64
import json
import os
import time

from .download_helper import DownloadHelper

try:
    from astrbot.api import logger
except ImportError:
    # 备用日志记录器喵～ 🐾
    import logging

    logger = logging.getLogger(__name__)


class MessageBuilder:
    """
    消息构建器喵～ 负责将原始消息转换为转发格式
    让每条消息都变得可爱又整齐！ ฅ(^•ω•^)ฅ
    """

    def __init__(self, download_helper=None, plugin=None):
        """初始化消息构建器喵～ 🐾"""
        if download_helper is None:
            self.download_helper = DownloadHelper()
        else:
            self.download_helper = download_helper
        self.plugin = plugin

    async def build_forward_node(self, msg_data: dict) -> dict:
        """构建单个转发节点

        Args:
            msg_data: 消息数据字典

        Returns:
            Dict: 转发节点（适合QQ API的字典格式）
        """
        sender_name = msg_data.get("sender_name", "未知用户")
        sender_id = msg_data.get("sender_id", "0")

        # 确保sender_id是字符串类型
        sender_id_str = str(sender_id)

        # 尝试获取用户头像URL
        avatar_url = msg_data.get("avatar_url", "")
        if not avatar_url and sender_id != "0":
            # 构建QQ头像URL（QQ用户头像的标准URL格式）
            avatar_url = f"http://q1.qlogo.cn/g?b=qq&nk={sender_id_str}&s=100"

        timestamp = msg_data.get("timestamp", int(time.time()))
        # 获取原始消息序列化数据
        serialized_message = msg_data.get("messages", [])  # 修复：使用正确的字段名
        message_components = []

        # 处理消息内容，提取所有类型的消息组件
        for i, comp in enumerate(serialized_message):
            if isinstance(comp, dict):
                comp_type = comp.get("type", "")

                # 处理不同类型的组件
                component = await self._process_component(comp_type, comp, timestamp)
                if component:
                    # 处理返回值是列表的情况
                    if isinstance(component, list):
                        message_components.extend(component)
                    else:
                        message_components.append(component)
            else:
                logger.debug(f"组件{i + 1}: 非字典类型，实际类型={type(comp)}")

        # 构建转发节点
        try:
            node = {
                "type": "node",
                "data": {
                    "name": sender_name,
                    "uin": sender_id_str,
                    "content": message_components,
                    "time": timestamp,
                },
            }

            # 记录组件信息（调试用）
            for comp in message_components:
                if comp.get("type") == "image":
                    logger.debug(
                        f"图片组件详情: {json.dumps(comp, ensure_ascii=False)}"
                    )

            return node

        except Exception as e:
            logger.error(f"构建转发节点失败: {str(e)}")
            return {
                "type": "node",
                "data": {
                    "name": sender_name,
                    "uin": sender_id_str,
                    "content": [{"type": "text", "data": {"text": "[构建节点失败]"}}],
                    "time": timestamp,
                },
            }

        # 如果没有内容，使用纯文本消息
        if not message_components:
            message_components = [{"type": "text", "data": {"text": "[空消息]"}}]

        # 添加更详细的日志，帮助调试（修复这里的错误）
        logger.debug(
            f"构建转发节点: {sender_name}({sender_id_str}), 共 {len(message_components)} 个组件"
        )
        for i, comp in enumerate(
            message_components[:3]
        ):  # 只显示前三个组件避免日志过长
            if isinstance(comp, dict):
                logger.debug(
                    f"组件{i + 1}: 类型={comp.get('type')}, 数据={comp.get('data')}"
                )
            else:
                logger.debug(f"组件{i + 1}: 非字典类型，实际类型={type(comp)}")

        # 直接返回适合QQ API的字典格式
        node_data = {
            "type": "node",
            "data": {
                "uin": sender_id_str,
                "name": sender_name,
                "content": message_components,
                "time": timestamp,
            },
        }
        # 添加节点构建完整日志，便于调试
        try:
            for comp in message_components:
                if comp.get("type") == "image":
                    logger.debug(
                        f"图片组件详情: {json.dumps(comp, ensure_ascii=False)}"
                    )
            logger.debug(
                f"完整转发节点结构: {json.dumps(node_data, ensure_ascii=False)}"
            )
        except Exception as e:
            logger.debug(f"序列化节点结构失败: {e}")

        return node_data

    async def _process_component(
        self, comp_type: str, comp: dict, timestamp: int
    ) -> dict:
        """处理单个消息组件

        Args:
            comp_type: 组件类型
            comp: 组件数据
            timestamp: 时间戳

        Returns:
            Dict: 处理后的组件数据
        """
        # 文本消息
        if comp_type == "plain":
            return {"type": "text", "data": {"text": comp.get("text", "")}}

        # 图片消息
        elif comp_type == "image":
            return await self._process_image_component(comp)

        # 特殊表情/商店表情
        elif comp_type == "mface":  # 添加对商店表情/特殊表情包的支持
            mface_url = comp.get("url", "")
            if not mface_url:
                mface_url = comp.get("data", {}).get("url", "")

            summary = comp.get("summary", "") or comp.get("data", {}).get(
                "summary", "[表情]"
            )

            if mface_url:
                # 如果有URL，尝试转换为图片组件
                image_data = {"type": "image", "data": {"file": mface_url}}
                # 添加特殊标记
                image_data["data"]["mface"] = True
                image_data["data"]["summary"] = summary
                logger.info(f"处理特殊表情: {summary} -> {mface_url}")
                return image_data
            else:  # 退化为文本处理
                return {"type": "text", "data": {"text": f"{summary}"}}  # @消息
        elif comp_type == "at":
            # 获取@的用户名和QQ号
            at_name = comp.get("name", "")
            at_qq = comp.get("qq", "")

            # 添加调试日志
            logger.info(f"处理@消息: name='{at_name}', qq='{at_qq}'")

            # 尝试获取用户昵称
            display_text = await self._get_user_nickname(at_name, at_qq)
            logger.info(f"获取到的昵称: '{display_text}'")

            # 确保display_text是字符串类型，避免startswith()方法的AttributeError
            display_text = (
                str(display_text)
                if display_text
                else str(at_qq)
                if at_qq
                else "未知用户"
            )

            # 检查是否已经以@开头，避免重复@
            if display_text.startswith("@"):
                formatted_text = f"{display_text} "  # 添加空格
            else:
                formatted_text = f"@{display_text} "  # 添加@和空格

            # 返回文本组件而非at组件
            return {"type": "text", "data": {"text": formatted_text}}

        # QQ表情
        elif comp_type == "face":
            return {"type": "face", "data": {"id": comp.get("id", "0")}}

        # 语音消息
        elif comp_type == "record":
            return await self._process_record_component(comp)

        # 视频消息
        elif comp_type == "video":
            return await self._process_video_component(comp)

        # 文件消息
        elif comp_type == "file":
            return await self._process_file_component(comp)

        # JSON卡片消息
        elif comp_type == "json":  # QQ卡片消息
            return await self._process_json_component(comp)

        # XML消息
        elif comp_type == "xml":  # XML格式消息（如分享链接等）
            return await self._process_xml_component(comp)

        # 回复消息
        elif comp_type == "reply":
            return {
                "type": "reply",
                "data": {
                    "id": comp.get("id", ""),
                    "text": comp.get("text", ""),
                    "qq": comp.get("sender_id", ""),
                    "time": comp.get("time", timestamp),
                    "sender": {"nickname": comp.get("sender_nickname", "未知用户")},
                },
            }

        # 转发消息（嵌套）
        elif comp_type == "forward":
            # 对于嵌套转发，简化处理
            return {
                "type": "text",
                "data": {"text": f"[转发消息: {comp.get('id', '未知ID')}]"},
            }

        # 其他未知类型
        else:
            logger.warning(f"未知的消息组件类型: {comp_type}")
            return {
                "type": "text",
                "data": {"text": f"[不支持的消息类型: {comp_type}]"},
            }

    async def _process_image_component(self, comp: dict) -> dict:
        """处理图片组件"""
        # 检查是否是特殊表情转换来的图片
        if comp.get("is_mface", False):
            # 是特殊表情，添加特殊标记
            logger.warning(
                f"处理特殊表情(转换自mface): {comp.get('summary', '[表情]')}"
            )

            # 提取URL和其他信息
            url = comp.get("url", "")
            summary = comp.get("summary", "[表情]")
            emoji_id = comp.get("emoji_id", "")
            package_id = comp.get("emoji_package_id", "")
            key = comp.get("key", "")

            # 添加特殊标记用于表情显示
            image_data = {"type": "image", "data": {"file": url}}
            image_data["data"]["mface"] = True
            image_data["data"]["summary"] = summary
            if emoji_id:
                image_data["data"]["emoji_id"] = emoji_id
            if package_id:
                image_data["data"]["package_id"] = package_id
            if key:
                image_data["data"]["key"] = key

            if url:
                logger.warning(f"特殊表情处理完成: {summary} -> {url}")
                return image_data
            else:
                logger.warning(f"特殊表情缺少URL，尝试处理为普通图片: {summary}")
                # 如果没有URL，继续尝试普通图片处理流程

        # 获取图片信息
        url = comp.get("url", "")
        file = comp.get("file", "")
        base64_data = comp.get("base64", "")
        filename = comp.get("filename", "")

        # 检查是否为GIF
        is_gif = (
            url.endswith(".gif")
            if url
            else False or file.endswith(".gif")
            if file
            else False or filename.endswith(".gif")
            if filename
            else False
        )

        # 增加日志，查看接收到的原始组件结构
        logger.debug(f"图片组件信息: url={url}, file={file}, filename={filename}")

        image_data = {"type": "image", "data": {}}

        # 处理QQ图片链接
        if (
            "multimedia.nt.qq.com.cn" in url
            or "gchat.qpic.cn" in url
            or "multimedia.nt.qq.com.cn" in file
            or "gchat.qpic.cn" in file
            or "gxh.vip.qq.com" in url
            or "gxh.vip.qq.com" in file
        ):  # 添加表情包域名
            original_url = url or file

            # 保存原始URL和文件名，便于多级策略发送
            image_data["data"]["file"] = original_url
            if filename:
                image_data["data"]["filename"] = filename
                # 将原始URL添加为备用
                image_data["data"]["original_url"] = original_url
                logger.debug(f"同时保存filename和URL: {filename}, {original_url}")
            else:
                logger.debug(f"仅使用URL: {original_url}")

            # 如果是GIF，添加标记
            if is_gif:
                image_data["data"]["is_gif"] = True

            return image_data

        # base64编码图片
        if base64_data:
            if "base64://" not in base64_data:
                image_data["data"]["file"] = f"base64://{base64_data}"
            else:
                image_data["data"]["file"] = base64_data
            logger.debug("使用base64图片")

        # 普通URL图片 - 也直接使用URL而非文件名
        elif url:
            image_data["data"]["file"] = url
            logger.debug(f"使用图片URL: {url}")

        # 文件路径处理
        if file:
            if file.startswith("file:///"):
                # 本地文件路径
                clean_path = file.replace("file:///", "")
                try:
                    if os.path.exists(clean_path):
                        # 对于小文件，转为base64编码
                        with open(clean_path, "rb") as f:
                            img_content = f.read()
                        if len(img_content) < 1048576:  # 小于1MB的图片转base64
                            b64_data = base64.b64encode(img_content).decode("utf-8")
                            image_data["data"]["file"] = f"base64://{b64_data}"
                        else:
                            image_data["data"]["file"] = clean_path
                except Exception as e:
                    logger.warning(f"转换本地文件为base64失败: {e}")
                    # 如果base64转换失败，使用本地路径，但合并转发可能失败
                    image_data["data"]["file"] = clean_path
                    logger.debug(f"使用本地图片路径(合并转发可能失败): {clean_path}")
                return image_data

        # 兜底处理
        if not image_data["data"]:
            image_data["data"]["file"] = filename or url or file or ""

        return image_data

    async def _process_record_component(self, comp: dict) -> dict:
        """处理语音组件"""
        record_data = {"type": "record", "data": {}}

        # 下载语音到本地
        try:
            local_file_path = None
            if comp.get("url"):
                local_file_path = await self.download_helper.download_audio(
                    comp.get("url")
                )
            elif comp.get("file") and comp.get("file").startswith("http"):
                local_file_path = await self.download_helper.download_audio(
                    comp.get("file")
                )
            elif comp.get("file") and os.path.exists(comp.get("file")):
                local_file_path = comp.get("file")

            if local_file_path and os.path.exists(local_file_path):
                record_data["data"]["file"] = f"file:///{local_file_path}"
            else:
                # 下载失败时的回退方案
                if comp.get("url"):
                    record_data["data"]["file"] = comp.get("url")
                elif comp.get("file"):
                    record_data["data"]["file"] = comp.get("file")
                else:
                    return {"type": "text", "data": {"text": "[语音消息]"}}

        except Exception as e:
            logger.error(f"处理语音消息失败: {str(e)}")
            return {"type": "text", "data": {"text": "[语音消息]"}}

        return record_data

    async def _process_video_component(self, comp: dict) -> dict:
        """处理视频组件"""
        return {"type": "text", "data": {"text": "[视频消息]"}}

    async def _process_file_component(self, comp: dict) -> dict:
        """处理文件组件"""
        return {"type": "text", "data": {"text": "[文件消息]"}}

    async def _process_json_component(self, comp: dict) -> dict:
        """处理JSON卡片组件"""
        return {"type": "text", "data": {"text": "[卡片消息]"}}

    async def _process_xml_component(self, comp: dict) -> dict:
        """处理XML组件"""
        return {"type": "text", "data": {"text": "[XML消息]"}}

    def build_footer_node(
        self, source_name: str, message_count: int, is_retry: bool = False
    ) -> dict:
        """构建底部信息节点

        Args:
            source_name: 消息来源名称
            message_count: 消息数量
            is_retry: 是否为重试消息

        Returns:
            Dict: 底部信息节点
        """
        suffix = "重试缓存" if is_retry else source_name
        footer_text = f"[此消息包含 {message_count} 条消息，来自{suffix}]"

        return {
            "type": "node",
            "data": {
                "uin": "0",
                "name": "消息转发系统",
                "content": [{"type": "text", "data": {"text": footer_text}}],
                "time": int(time.time()),
            },
        }

    async def _get_user_nickname(self, at_name: str, at_qq: str) -> str:
        """获取用户昵称

        Args:
            at_name: @消息中的name字段
            at_qq: @消息中的qq字段

        Returns:
            str: 用户昵称，如果获取失败则返回QQ号
        """
        # 如果已经有昵称，直接使用
        if at_name and at_name.strip():
            logger.info(f"直接使用现有昵称: '{at_name.strip()}'")
            return at_name.strip()

        logger.info(f"昵称为空，尝试通过API获取用户 {at_qq} 的昵称")

        # 如果没有昵称但有QQ号，尝试通过API获取
        if at_qq and self.plugin:
            try:
                # 获取aiocqhttp客户端
                client = self.plugin.context.get_platform("aiocqhttp")
                if client:
                    logger.debug("找到aiocqhttp平台客户端")
                    bot_client = client.get_client()
                    if bot_client:
                        logger.debug(f"开始调用get_stranger_info API，用户ID: {at_qq}")
                        # 尝试获取用户信息
                        user_info = await bot_client.call_action(
                            action="get_stranger_info", user_id=int(at_qq)
                        )

                        logger.debug(f"API返回结果: {user_info}")
                        # 尝试多个可能的昵称字段，优先检查nickname字段
                        nickname = None
                        if user_info:
                            # 尝试不同的昵称字段名，nickname优先
                            for nick_field in ["nickname", "nick", "name"]:
                                if nick_field in user_info:
                                    nickname = user_info[nick_field]
                                    if nickname and nickname.strip():
                                        logger.info(
                                            f"成功获取用户 {at_qq} 的昵称 (字段: {nick_field}): {nickname}"
                                        )
                                        return nickname.strip()

                        if not nickname:
                            logger.warning(
                                f"API返回的用户信息中没有可用的昵称字段，可用字段: {list(user_info.keys()) if user_info else 'None'}"
                            )
                    else:
                        logger.warning("无法获取bot_client")
                else:
                    logger.warning("无法找到aiocqhttp平台客户端")
            except Exception as e:
                logger.error(f"获取用户 {at_qq} 昵称失败: {e}")
                import traceback

                logger.debug(traceback.format_exc())
        else:
            logger.warning(
                f"缺少必要条件: at_qq={at_qq}, plugin={self.plugin is not None}"
            )

        # 如果都获取不到，返回一个通用的用户显示名称而不是QQ号
        logger.info(f"无法获取昵称，使用通用显示名称代替QQ号: {at_qq}")
        return str(at_qq) if at_qq else "未知用户"
