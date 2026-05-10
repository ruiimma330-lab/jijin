#!/usr/bin/env python3
"""基金数据获取工具 — 命令行快速查询基金信息。

用法:
    python scripts/data/fetch_fund.py              # 查看基金排行
    python scripts/data/fetch_fund.py --code 000001 # 查看某只基金净值
    python scripts/data/fetch_fund.py --list        # 列出基金列表(前50只)
    python scripts/data/fetch_fund.py --search 沪深300  # 搜索基金
"""

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.data.client import (
    DataSourceError,
    get_fund_list,
    get_fund_nav,
    get_fund_ranking,
)


def show_ranking(fund_type: str = "all"):
    """打印基金收益排名。"""
    print(f"\n{'='*70}")
    print(f"  基金收益排名 ({fund_type})")
    print(f"{'='*70}")
    try:
        df = get_fund_ranking(fund_type=fund_type, top_n=20)
        print(df.to_string(index=False))
    except DataSourceError as e:
        print(f"数据获取失败: {e}")


def show_fund_nav(fund_code: str):
    """查看单只基金净值走势摘要。"""
    print(f"\n{'='*70}")
    try:
        df = get_fund_nav(fund_code)
        if df.empty:
            print(f"未找到基金 {fund_code} 的数据")
            return

        latest = df.iloc[-1]
        first = df.iloc[0]
        total_return = (latest["nav"] - first["nav"]) / first["nav"] * 100

        print(f"  基金 {fund_code} 净值走势")
        print(f"{'='*70}")
        print(f"数据范围: {first['date'].date()} ~ {latest['date'].date()}")
        print(f"最新净值: {latest['nav']:.4f}")
        print(f"期初净值: {first['nav']:.4f}")
        print(f"期间收益: {total_return:.2f}%")
        print(f"最大回撤: {(df['nav'].cummax() - df['nav']).max() / df['nav'].cummax().max() * 100:.2f}%")

        print(f"\n近20个交易日:")
        recent = df.tail(20)[["date", "nav", "daily_return"]].copy()
        recent["date"] = recent["date"].dt.date
        recent["daily_return"] = (
            recent["daily_return"] * 100
        ).round(2).astype(str) + "%"
        recent["nav"] = recent["nav"].round(4)
        print(recent.to_string(index=False))

    except DataSourceError as e:
        print(f"数据获取失败: {e}")


def show_fund_list():
    """打印基金列表。"""
    print(f"\n{'='*70}")
    print("  公募基金列表 (前50只)")
    print(f"{'='*70}")
    try:
        df = get_fund_list().head(50)
        if "establish_date" in df.columns:
            df["establish_date"] = pd.to_datetime(
                df["establish_date"]
            ).dt.date
        print(df.to_string(index=False))
    except DataSourceError as e:
        print(f"数据获取失败: {e}")


def search_fund(keyword: str):
    """搜索基金。"""
    try:
        df = get_fund_list()
        mask = df["name"].str.contains(keyword, na=False)
        result = df[mask]
        if result.empty:
            print(f"未找到包含 '{keyword}' 的基金")
            return
        print(f"\n搜索 '{keyword}' 结果 ({len(result)} 只):")
        print(result.head(30).to_string(index=False))
    except DataSourceError as e:
        print(f"数据获取失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="基金数据查询工具")
    parser.add_argument("--code", type=str, help="基金代码")
    parser.add_argument("--list", action="store_true", help="列出基金列表")
    parser.add_argument("--search", type=str, help="搜索基金名称")
    parser.add_argument(
        "--type", type=str, default="all",
        choices=["all", "stock", "bond", "mix", "money", "index"],
        help="基金类型 (默认: all)",
    )
    args = parser.parse_args()

    if args.code:
        show_fund_nav(args.code)
    elif args.search:
        search_fund(args.search)
    else:
        show_fund_list() if args.list else show_ranking(args.type)


if __name__ == "__main__":
    main()
