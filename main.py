from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.all import Image

import io
from datetime import datetime, timedelta
from .数据库 import *
from PIL import Image as PIL_Image, ImageDraw, ImageFont

@register("astrbot_plugin_masturbation_sign", "周佳豪", "鹿插件,输出日历图片", "1.0", "")
class SignPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.素材文件路径 = os.path.join(os.getcwd(), r"data\plugins\astrbot_plugin_masturbation_sign")

    # @filter.command("鹿", alias={'撸', '🦌'})
    @filter.regex('[\s\S]*(手淫|打飞机|撸|鹿|🦌)[\s\S]*')
    async def 签到(self, event: AstrMessageEvent):
        qq号 = event.get_sender_id()
        用户昵称 = event.get_sender_name()
        当前时间 = datetime.now().strftime(("%Y-%m-%d"))

        # 存入数据库
        是否成功, 结果 = await 签到存储方法(qq号, 当前时间)

        if not 是否成功:
            if 结果 == "已签到":
                # 不提示, 防止因正则多次重复触发, 回复的提示信息造成骚扰
                # yield event.plain_result("今日已🦌, 请勿重复喵")
                return
            else:
                yield event.plain_result("未知错误:" + 结果)

            return

        # 取出历史数据
        当前日期 = datetime.strptime(当前时间.split()[0], '%Y-%m-%d').date()
        当前月份 = 当前日期.strftime('%Y-%m')

        # 转为无前缀0的纯天数
        月份最后一天: str = str(
            (
                当前日期.replace(day=28) +
                timedelta(days=4)
            ).replace(day=1) - timedelta(days=1)
        ).split('-')[-1]

        是否成功, 结果 = await 获取签到日历数据(qq号, 当前月份, 月份最后一天)

        if not 是否成功:
            yield event.plain_result("🦌失败了," + 结果)
            return

        try:
            # 生成图片
            图片bytes = self.生成日历图片(用户昵称, 结果)

            if not 图片bytes:
                return

            # 发送图片
            yield event.chain_result(
                [
                   Image.fromBytes(图片bytes)
                ]
            )

        except Exception as e:
            yield event.plain_result("🦌图片生成失败了: " + str(e))

        return

    def 生成日历图片(self, 用户昵称: str, 数据: dict) -> bytes | None:
        try:
            背景图片 = PIL_Image.open(self.素材文件路径 + r"\背景.png").convert("RGBA")
            章图片 = PIL_Image.open(self.素材文件路径 + r"\章.png").convert("RGBA")
        except FileNotFoundError as e:
            logger.error(f"无法找到素材文件：{e.filename}。请检查路径：'{self.素材文件路径}'是否正确且文件存在。")
            return

        # 绘制器 = PIL_Image.Draw.Draw(背景图片)
        绘制器 = ImageDraw.Draw(背景图片)

        # 从数据字典中提取所需信息
        本月签到天数_文本 = 数据['本月签到天数']
        本月签到日期列表 = 数据['本月签到日期列表']
        连续签到状态_文本 = 数据['连续签到状态']
        月份最后一天 = 数据['月份最后一天']

        字体路径 = "msyh.ttc"
        try:
            头部字体 = ImageFont.truetype("msyh.ttc", 26)
        except IOError:
            头部字体 = ImageFont.load_default() # 备用字体

        # 绘制顶部标题区域
        标题区域_左 = 160
        标题区域_上 = 126
        标题区域_下 = 162

        昵称_文本框 = 绘制器.textbbox((0, 0), 用户昵称, font=头部字体)
        昵称_文本高度 = 昵称_文本框[3] - 昵称_文本框[1]
        文本_Y = 标题区域_上 + (标题区域_下 - 标题区域_上 - 昵称_文本高度) / 2

        # 右下月份信息
        绘制器.text((标题区域_左+3, 文本_Y-8), 数据["当前月份"]+" 已签到", fill="#5C4033", font=头部字体)
        # 绘制器.text((630, 372), , fill="black", font=头部字体)

        # 绘制日历顶部用户昵称
        绘制器.text((标题区域_左+3, 文本_Y+22), 用户昵称, fill="#5C4033", font=头部字体)

        # 绘制底部签到信息
        绘制器.text((160, 497), 本月签到天数_文本, fill="#5C4033", font=头部字体)

        签到_X = 185 + 绘制器.textlength(本月签到天数_文本, font=头部字体)
        绘制器.text((签到_X, 497), 连续签到状态_文本, fill="#5C4033", font=头部字体)

        # 3. 绘制日历数值区域
        日历区域_左 = 183
        日历区域_上 = 162
        日历区域_右 = 593
        日历区域_下 = 553

        日历区域_宽 = 日历区域_右 - 日历区域_左
        日历区域_高 = 日历区域_下 - 日历区域_上

        列数 = 7
        行数 = 6

        单元格_宽 = 日历区域_宽 / 列数
        单元格_高 = 日历区域_高 / 行数

        # 根据单元格高度计算日期数字的字体大小
        数字字体大小 = int(单元格_高 * 0.6)

        try:
            数字字体 = ImageFont.truetype(字体路径, 数字字体大小)
        except IOError:
            数字字体 = ImageFont.load_default() # 备用字体

        当前日期 = 1
        # 遍历日历的每一行和每一列，绘制日期数字

        for 行索引 in range(行数):
            for 列索引 in range(列数):
                # 根据要求，“第一行第一个空缺”
                if 行索引 == 0 and 列索引 == 0:
                    continue

                # 如果当前日期超过了月份的最后一天，则停止绘制
                if 当前日期 > int(月份最后一天):
                    break

                # 计算当前日期所在单元格的左上角坐标
                单元格_X = 日历区域_左 + 列索引 * 单元格_宽
                单元格_Y = 日历区域_上 + 行索引 * 单元格_高

                # 绘制日期数字
                日期字符串 = str(当前日期)
                # 获取日期数字文本的边界框，用于计算居中位置
                日期文本框 = 绘制器.textbbox((0, 0), 日期字符串, font=数字字体)

                日期文本宽 = 日期文本框[2] - 日期文本框[0]
                日期文本高 = 日期文本框[3] - 日期文本框[1]

                # 计算日期文本在单元格内居中的位置
                日期文本_X = 单元格_X + (单元格_宽 - 日期文本宽) / 2
                日期文本_Y = 单元格_Y + (单元格_高 - 日期文本高) / 2

                绘制器.text((日期文本_X, 日期文本_Y), 日期字符串, fill="#4B3B2B", font=数字字体)

                # 如果当前日期存在于“本月签到日期列表”中，则叠加章图片
                if 当前日期 in 本月签到日期列表:
                    章_宽, 章_高 = 章图片.size
                    # 计算章图片在单元格内居中的位置
                    章_X = int(单元格_X + (单元格_宽 - 章_宽) / 2)
                    章_Y = int(单元格_Y + (单元格_高 - 章_高) / 2) + 8

                    # 叠加章图片
                    背景图片.paste(章图片, (章_X, 章_Y), 章图片)

                当前日期 += 1
            # 如果内层循环因为日期已画完而提前跳出，外层循环也应跳出
            if 当前日期 > int(月份最后一天):
                break

        结果bytes = io.BytesIO()
        背景图片.save(结果bytes, format='PNG')

        return 结果bytes.getvalue()






