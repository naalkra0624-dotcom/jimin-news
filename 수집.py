# -*- coding: utf-8 -*-
"""3일마다 깃허브가 이 파일을 돌립니다.

하는 일은 하나뿐입니다 —— 기사를 모아 후보.json 에 쌓습니다.
사이트에 올리지 않습니다. 발행은 준이야 님이 검수한 뒤에만 일어납니다.

직접 돌려보고 싶으면:  python 수집.py
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import jimin

HERE   = os.path.dirname(os.path.abspath(__file__))
후보파일 = os.path.join(HERE, "후보.json")

# 이 기간이 지난 후보는 검수 목록에서 저절로 사라집니다.
# (안 고른 채 쌓이기만 하면 검수 화면이 못 쓰게 되므로)
보관_일수 = 21


def 아이디(a):
    """기사마다 짧고 변하지 않는 이름표. 승인 목록에 적을 값입니다."""
    씨앗 = (a.get("링크") or "") + "|" + (a.get("제목") or "")
    return hashlib.sha1(씨앗.encode("utf-8")).hexdigest()[:8]


def 후보읽기():
    if not os.path.isfile(후보파일):
        return {"갱신": None, "기사": []}
    try:
        with open(후보파일, encoding="utf-8") as f:
            자료 = json.load(f)
        자료.setdefault("기사", [])
        return 자료
    except Exception as 오류:
        print(f"  후보.json 을 읽지 못했습니다 ({오류}). 새로 시작합니다.")
        return {"갱신": None, "기사": []}


def 오래된것_버리기(기사들):
    한계 = (datetime.now(timezone.utc) - timedelta(days=보관_일수)).strftime("%Y-%m-%d")
    남김 = [a for a in 기사들 if (a.get("수집일") or "9999") >= 한계]
    if len(남김) != len(기사들):
        print(f"  {len(기사들) - len(남김)}건은 {보관_일수}일이 지나 목록에서 뺐습니다.")
    return 남김


def main():
    print("\n" + "=" * 62)
    print("  지민 뉴스 — 3일치 수집")
    print(f"  버전 {jimin.버전}")
    print("=" * 62 + "\n")

    키 = jimin.키준비()
    기사들, 실패수, 통계, 수집수 = jimin.기사모으기()

    if not 기사들:
        print("  조건에 맞는 기사가 없습니다. 후보.json 은 그대로 둡니다.\n")
        return 0

    통과, 제외, 실패 = jimin.판정하기(키, 기사들)

    기존 = 후보읽기()
    이미있음 = {a.get("id") for a in 기존["기사"]}
    오늘 = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    새것 = 0
    for a in 통과:
        i = 아이디(a)
        if i in 이미있음:
            continue
        이미있음.add(i)
        기존["기사"].append({
            "id": i,
            "제목": a.get("제목", ""),
            "한글제목": a.get("한글제목", ""),
            "요약": a.get("요약", ""),
            "성격": a.get("성격", "?"),
            "주목도": a.get("주목도", 3),
            "매체": a.get("매체", ""),
            "나라": a.get("나라", ""),
            "날짜": a.get("날짜", ""),
            "링크": a.get("링크", ""),
            "국내수": a.get("국내수", 0),
            "국내기사": a.get("국내기사", []),
            "수집일": 오늘,
        })
        새것 += 1

    기존["기사"] = 오래된것_버리기(기존["기사"])
    기존["기사"].sort(key=lambda x: (x.get("수집일", ""), x.get("날짜", "")), reverse=True)
    기존["갱신"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    기존["마지막수집"] = {
        "날짜": 오늘, "훑은기사": 수집수, "대상": len(기사들),
        "확인": len(통과) + len(제외), "새후보": 새것,
        "검색실패": 실패수, "문제": 실패 or "",
    }

    with open(후보파일, "w", encoding="utf-8") as f:
        json.dump(기존, f, ensure_ascii=False, indent=1)

    print("=" * 62)
    print(f"  새 후보 {새것}건  ·  검수 대기 전체 {len(기존['기사'])}건")
    if 실패:
        print(f"  ⚠ {실패}")
    print("=" * 62 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
