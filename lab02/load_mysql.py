# -*- coding: utf-8 -*-
"""实验二第三阶段：读取 lab02/data/houseinfo.csv，写入 MySQL houseinfo 表。

在课程 JupyterLab 中运行（host=mysql）。重复运行时按 8 个字段比对
已有记录，只插入不存在的记录，不清空表。
"""
import csv
from pathlib import Path

import pymysql

CSV_PATH = Path(__file__).parent / "data" / "houseinfo.csv"
FIELDS = ["title", "house", "address", "struct",
          "area", "floor", "maketime", "price"]

conn = None
cur = None
try:
    # 1. 读取 CSV，检查表头，按 8 个字段的固定顺序整理记录
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == FIELDS, f"表头不符：{reader.fieldnames}"
        records = [tuple(row[k] for k in FIELDS) for row in reader]
    print(f"CSV 数据行数：{len(records)}")

    # 2. 连接数据库，查询一条数据确认连接正常
    conn = pymysql.connect(
        host="mysql", port=3306, database="smartpark_lab",
        user="student", password="123456",
        charset="utf8mb4", autocommit=False)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM houseinfo")
    before = cur.fetchone()[0]
    print(f"入库前条数：{before}")

    # 3. 查询库内已有的 8 字段记录，避免重复插入
    cur.execute(
        "SELECT title, house, address, struct, area, floor, maketime, price "
        "FROM houseinfo")
    existing = {tuple(r) for r in cur.fetchall()}
    new_records = [r for r in records if r not in existing]
    print(f"库内已有 {len(existing)} 条，本次待插入 {len(new_records)} 条")

    if new_records:
        # 4. 批量写入：%s 占位，不用字符串拼接
        sql = ("INSERT INTO houseinfo "
               "(title, house, address, struct, area, floor, maketime, price) "
               "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")
        affected = cur.executemany(sql, new_records)
        conn.commit()                       # 5. 提交事务
        print(f"executemany 影响 {affected} 行，已 commit")
    else:
        print("无新增记录，跳过插入")

    cur.execute("SELECT COUNT(*) FROM houseinfo")
    after = cur.fetchone()[0]
    print(f"入库后条数：{after}，本次新增：{after - before}")

except Exception as e:
    print(f"出错：{e}")
    if conn is not None:
        conn.rollback()                     # 6. 回滚未提交的修改
        print("已 rollback")
finally:
    # 7. 先关游标再关连接；连接可能未建立，先判断
    if cur is not None:
        cur.close()
    if conn is not None:
        conn.close()
    print("游标与连接已关闭")
