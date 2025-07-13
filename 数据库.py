import os
import aiosqlite
import asyncio

数据库连接 = None

数据库文件路径 = os.path.join(os.getcwd(), r"data\plugins_db", "astrbot_plugin_masturbation_sign.db")


async def 建立数据库方法():
    async with aiosqlite.connect(数据库文件路径) as 数据库连接:
        await 数据库连接.execute("""
                            CREATE TABLE IF NOT EXISTS QQ用户表 (
                                qq INTEGER PRIMARY KEY,
                                最新签到日期 TEXT NOT NULL DEFAULT '1970-01-01',
                                连续签到天数 INTEGER NOT NULL DEFAULT 0,
                                上次月份更新 TEXT NOT NULL DEFAULT '1970-01'
                            );
                            """)

        await 数据库连接.execute("""
                            CREATE TABLE IF NOT EXISTS 签到记录表 (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                qq INTEGER NOT NULL,
                                签到日期 TEXT NOT NULL,
                                UNIQUE(qq, 签到日期)
                                FOREIGN KEY (qq) REFERENCES QQ用户表(qq_id) ON DELETE CASCADE
                            );
                            """)

        await 数据库连接.commit()


async def 获取数据库连接方法():
    global 数据库连接

    if not os.path.exists(数据库文件路径):
        await 建立数据库方法()

    if 数据库连接 is None:
        try:
            数据库连接 = await aiosqlite.connect(数据库文件路径)
        except:
            print("数据库连接失败!")
            return None
    return 数据库连接


async def 签到存储方法(qq号: str, 当前时间: str) -> tuple[bool, str]:
    连接 = await 获取数据库连接方法()

    try:
        游标 = await 连接.execute(
            "SELECT 1 FROM 签到记录表 WHERE qq = ? AND 签到日期 = ?;",
            (qq号, 当前时间)
        )

        if await 游标.fetchone():
            return False, "已签到"

        # 开始事务
        await 连接.execute("BEGIN TRANSACTION;")

        # 插入签到记录
        await 连接.execute(
            "INSERT INTO 签到记录表 (qq, 签到日期) VALUES (?, ?);",
            (qq号, 当前时间)
        )

        # 更新或初始化用户数据
        await 连接.execute("""
                INSERT OR IGNORE INTO QQ用户表 (qq, 最新签到日期, 连续签到天数, 上次月份更新)
                VALUES (?, '1970-01-01', 0, '1970-01');
            """, (qq号,))

        # 获取上次签到日期
        游标 = await 连接.execute(
            "SELECT 最新签到日期 FROM QQ用户表 WHERE qq = ?;",
            (qq号,)
        )
        上次签到日期 = await 游标.fetchone()

        # 计算连续签到
        if 上次签到日期 and 上次签到日期[0]:
            from datetime import datetime, timedelta
            上次日期 = datetime.strptime(上次签到日期[0], "%Y-%m-%d").date()
            当前日期 = datetime.strptime(当前时间, "%Y-%m-%d").date()

            if 当前日期 - 上次日期 == timedelta(days=1):
                # 连续签到
                await 连接.execute("""
                        UPDATE QQ用户表 
                        SET 最新签到日期 = ?, 连续签到天数 = 连续签到天数 + 1
                        WHERE qq = ?;
                    """, (当前时间, qq号))
            else:
                # 不连续，重置为1
                await 连接.execute("""
                        UPDATE QQ用户表 
                        SET 最新签到日期 = ?, 连续签到天数 = 1
                        WHERE qq = ?;
                    """, (当前时间, qq号))
        else:
            # 首次签到
            await 连接.execute("""
                    UPDATE QQ用户表 
                    SET 最新签到日期 = ?, 连续签到天数 = 1
                    WHERE qq = ?;
                """, (当前时间, qq号))

        # 提交事务
        await 连接.commit()
        return True, ""

    except Exception as e:
        # 回滚事务
        await 连接.execute("ROLLBACK;")
        return False, str(e)

async def 获取签到日历数据(qq号: str, 当前月份: str, 月份最后一天: str) -> tuple:
    """
    获取生成日历图片的必要数据
    :param qq号: 要查询的QQ号
    :param 当前时间: 可选，指定查询的时间（格式: 'YYYY-MM-DD'），默认为系统当前时间
    :return: (success: bool, data: dict or error_message: str)
    """

    try:
        # 获取数据库连接
        连接 = await 获取数据库连接方法()

        # 获取用户连续签到信息
        cursor = await 连接.execute(
            "SELECT 连续签到天数, 最新签到日期 FROM QQ用户表 WHERE qq = ?",
            (qq号,)
        )
        用户数据 = await cursor.fetchone()

        if not 用户数据:
            return False, "用户不存在"

        连续签到天数, 最新签到日期 = 用户数据

        # 获取本月所有签到日期
        cursor = await 连接.execute(
            "SELECT 签到日期 FROM 签到记录表 WHERE qq = ? AND 签到日期 BETWEEN ? AND ? ORDER BY 签到日期",
            (qq号, "1", 月份最后一天)
        )
        签到记录 = await cursor.fetchall()

        # 提取签到日期列表
        本月签到日期列表 = [int(记录[0].split('-')[-1]) for 记录 in 签到记录]

        # 计算签到统计
        本月签到天数 = f"本月已签到{len(本月签到日期列表)}天"
        连续签到状态 = f"连续签到{连续签到天数 if 连续签到天数 > 0 else '尚未连续签到'}天"

        return True, {
            'qq号': qq号,
            '当前月份': 当前月份,
            '本月签到天数': 本月签到天数,
            '本月签到日期列表': 本月签到日期列表,
            '连续签到状态': 连续签到状态,
            '最新签到日期': 最新签到日期 if 最新签到日期 else None,
            '月份最后一天': 月份最后一天
        }

    except Exception as e:
        return False, f"获取数据失败: {str(e)}"