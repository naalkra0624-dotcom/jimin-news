# -*- coding: utf-8 -*-
"""후보.json + 승인.txt 로 사이트를 만듭니다.

  docs/index.html   ← 공개되는 사이트. 승인.txt 에 적힌 기사만 들어갑니다.
  docs/검수.html     ← 준이야 님만 보는 화면. 여기서 고르고 승인.txt 에 붙여넣습니다.

기사를 새로 모으지 않습니다. 그래서 돈이 들지 않고 몇 초면 끝납니다.
직접 돌려보고 싶으면:  python 만들기.py
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from html import escape as e
from urllib.parse import quote

HERE   = os.path.dirname(os.path.abspath(__file__))
후보파일 = os.path.join(HERE, "후보.json")
승인파일 = os.path.join(HERE, "승인.txt")
문서함   = os.path.join(HERE, "docs")

# ── 사이트 정보 — 여기만 고치면 됩니다 ────────────────────────
사이트이름 = "밖에서 온 지민"
한줄설명   = "해외는 다뤘지만 국내에는 없는 기사"
꼬리말     = ("모든 기사의 저작권은 원 매체에 있습니다. 이 페이지는 기사의 소재를 "
           "소개하고 원문으로 연결할 뿐이며, 본문을 번역하거나 전재하지 않습니다.")

저장소 = os.environ.get("GITHUB_REPOSITORY", "")   # 깃허브가 알아서 넣어 줍니다


CSS = """
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:#faf9f7;color:#191917;
 font-family:-apple-system,'Malgun Gothic','맑은 고딕',Segoe UI,sans-serif;
 line-height:1.65;-webkit-text-size-adjust:100%}
.wrap{max-width:720px;margin:0 auto;padding:40px 20px 72px}
h1{font-size:27px;margin:0 0 4px;letter-spacing:-.5px}
.sub{color:#77746d;margin:0 0 26px;font-size:14.5px}
h2{font-size:16px;margin:38px 0 14px;padding-bottom:9px;
 border-bottom:1px solid #e7e5e0;color:#3d3b37}
.bar{display:flex;gap:9px;margin:0 0 26px;flex-wrap:wrap}
.stat{background:#fff;border:1px solid #e7e5e0;border-radius:10px;
 padding:11px 15px;flex:1;min-width:88px;text-align:center}
.stat b{display:block;font-size:20px}
.stat span{font-size:11.5px;color:#77746d}
article{background:#fff;border:1px solid #e7e5e0;border-radius:12px;
 padding:19px 21px;margin-bottom:13px}
article.zero{border-left:3px solid #d1493f}
article.low{border-left:3px solid #d99e2b}
.tags{display:flex;gap:7px;align-items:center;margin-bottom:9px;flex-wrap:wrap}
.tag{font-size:11.5px;padding:2px 9px;border-radius:20px;font-weight:600}
.t0{background:#fdeceb;color:#a8342c}
.t1{background:#fdf3e1;color:#8a6410}
.geo,.kind{font-size:11.5px;color:#77746d;background:#f4f3f0;
 padding:2px 9px;border-radius:20px}
.imp{margin-left:auto;color:#c9c5bd;font-size:11px;letter-spacing:1px}
h3{font-size:17px;margin:0 0 8px;line-height:1.45;letter-spacing:-.3px}
.orig{color:#a09c93;font-size:12.5px;margin:0 0 10px;line-height:1.5}
p.sum{margin:0 0 13px;color:#3d3b37;font-size:14.5px}
.kr{background:#fbfaf8;border:1px solid #eeece7;border-radius:8px;
 padding:11px 14px;margin:0 0 13px}
.kr b{font-size:12px;color:#77746d;display:block;margin-bottom:5px}
.kr ul{margin:0;padding-left:17px;font-size:13px;color:#55524d}
.src{display:flex;gap:10px;align-items:center;font-size:12.5px;color:#77746d;
 border-top:1px solid #eee;padding-top:12px;flex-wrap:wrap}
.src a{color:#191917;font-weight:600;text-decoration:none}
.src a.alt{margin-left:auto;color:#a09c93;font-weight:400;font-size:12px}
.none{text-align:center;color:#77746d;padding:44px 20px;background:#fff;
 border:1px solid #e7e5e0;border-radius:12px}
.tm{background:#eeeafa;color:#5b3fa8}
.also{margin:0 0 13px}
.also summary{padding:9px 13px;font-size:12.5px;font-weight:400;color:#77746d;
 background:#fbfaf8;border-radius:8px;border:1px solid #eeece7;cursor:pointer;
 list-style:none}
.also summary::-webkit-details-marker{display:none}
.also summary::before{content:"▸ "}
.also[open] summary{margin-bottom:8px}
.also[open] summary::before{content:"▾ "}
.also ul{margin:0;padding-left:18px;font-size:12.5px;line-height:1.9;color:#77746d}
.also li b{color:#3d3b37;font-weight:600}
.also li span{color:#a09c93;font-size:11.5px}
.also li a{color:#55524d}
footer{color:#a09c93;font-size:12.5px;line-height:1.8;
 border-top:1px solid #e7e5e0;margin-top:46px;padding-top:20px}
"""

검수CSS = """
.pick{display:flex;gap:13px;align-items:flex-start}
.pick input{margin-top:4px;width:19px;height:19px;flex:none;cursor:pointer}
.pick>div{flex:1;min-width:0}
article.on{border-color:#191917;box-shadow:0 0 0 1px #191917}
.act{position:sticky;bottom:0;background:#faf9f7;border-top:1px solid #e7e5e0;
 padding:15px 0 20px;margin-top:30px;display:flex;gap:10px;
 align-items:center;flex-wrap:wrap}
button{font:inherit;font-weight:600;font-size:14px;padding:11px 20px;
 border-radius:9px;border:1px solid #191917;background:#191917;color:#fff;
 cursor:pointer}
button.ghost{background:#fff;color:#191917}
button:disabled{opacity:.4;cursor:default}
.count{color:#77746d;font-size:13.5px}
#out{width:100%;height:150px;font-family:ui-monospace,Consolas,monospace;
 font-size:12.5px;padding:12px;border:1px solid #e7e5e0;border-radius:9px;
 background:#fff;margin-top:12px;display:none}
.step{background:#fff;border:1px solid #e7e5e0;border-radius:12px;
 padding:17px 21px;margin-bottom:22px;font-size:14px}
.step ol{margin:9px 0 0;padding-left:20px}
.step li{margin-bottom:5px}
.ok{color:#2a7a4b;font-weight:600}
.tn{background:#e8f1fb;color:#1d5fa8}
h2 .when{font-weight:400;color:#a09c93;font-size:13px}
details{margin:0 0 14px}
summary{cursor:pointer;padding:13px 17px;background:#fff;font-size:14px;
 border:1px solid #e7e5e0;border-radius:11px;color:#55524d;font-weight:600;
 list-style:none;user-select:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"▸ ";color:#a09c93}
details[open] summary{border-radius:11px 11px 0 0;margin-bottom:13px}
details[open] summary::before{content:"▾ "}
"""


def 머리(제목, 부제, 여분=""):
    return (f'<!doctype html><html lang="ko"><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(제목)}</title><style>{CSS}{여분}</style>'
            f'<div class="wrap"><h1>{e(제목)}</h1>'
            f'<p class="sub">{e(부제)}</p>')


# ══════════════════════════════════════════════════════════════
#  같은 사건 묶기
# ══════════════════════════════════════════════════════════════
# 한 사건을 여러 나라 매체가 받아쓰면, 국내 미보도 기사가 열 몇 건씩
# 쏟아진 것처럼 보입니다. 실제로는 사건 하나입니다.
# 묶어서 "해외 N개 매체 보도 / 국내 0건" 으로 보여주는 편이 정직하고,
# 숫자 자체가 근거가 되어 오히려 설득력이 큽니다.

불용어 = {"bts", "지민", "방탄", "방탄소년단", "해외", "기사", "보도", "매체", "화제",
       "공개", "소개", "선보여", "전해", "중인", "위해", "관련", "대한", "것으로",
       "있다", "기록", "논란", "반응", "팬들", "한다", "됐다", "이어", "통해",
       "가운데", "대해", "모습", "선정", "차지", "나선", "가진", "특별", "새로운"}

# 같은 사건인데 말만 다른 경우를 잡습니다.
# (소아암 / 암 투병 / 암환자 · 기부금 / 모금 / 선물 …)
주제군 = {
    "투병":   ["암", "소아암", "암환자", "투병", "환우", "난치병", "환자"],
    "나눔":   ["기부", "모금", "기금", "자선", "후원", "나눔", "선행"],
    "만남":   ["포옹", "키스", "볼키스", "허그", "만나", "만남", "위로", "선물"],
    "차트":   ["차트", "스트리밍", "플래티넘", "인증", "빌보드", "1위", "랭킹",
             "애정도", "호감도", "순위"],
    "계정":   ["틱톡", "인스타그램", "계정", "팔로워", "개설"],
    "브랜드": ["브랜드", "앰배서더", "광고", "협업", "사칭", "가짜", "사과"],
    "공연":   ["콘서트", "공연", "무대", "투어", "월드투어"],
    "수상":   ["수상", "후보", "시상식", "영화제", "노미네이트"],
    "AI":     ["제미나이", "인공지능", "gemini"],
}


def _낱말(글):
    글 = re.sub(r"[^0-9A-Za-z가-힣]+", " ", (글 or "")).lower()
    낱 = set()
    for w in 글.split():
        if len(w) < 2 or w in 불용어:
            continue
        낱.add(w)
        if re.match(r"^[가-힣]+$", w) and len(w) >= 3:
            낱.add(w[:2])      # 조사 때문에 어미가 달라지는 것을 흡수
            낱.add(w[:3])
    return 낱 - 불용어


def _주제(글):
    낮 = (글 or "").lower()
    return {k for k, ws in 주제군.items() if any(w in 낮 for w in ws)}


def _닮음(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def _같은사건(x, y):
    겹 = x["_주제"] & y["_주제"]
    닮 = _닮음(x["_낱말"], y["_낱말"])
    if len(겹) >= 2:
        return True                     # 주제군 둘이 겹치면 같은 사건
    if len(겹) == 1 and 닮 >= 0.10:
        return True                     # 하나만 겹치면 말도 어느 정도 비슷해야
    return 닮 >= 0.22                   # 주제군이 안 잡혀도 말이 아주 비슷하면


def _날(a):
    try:
        return datetime.fromisoformat((a.get("날짜") or "")[:19].replace("Z", ""))
    except ValueError:
        return datetime(1970, 1, 1)


def 사건묶기(기사들, 날짜폭=14):
    """받아쓴 기사들을 사건 단위로 묶는다. 각 무리의 첫 기사가 대표."""
    준비 = []
    for a in 기사들:
        b = dict(a)
        글 = f'{a.get("한글제목","")} {a.get("요약","")}'
        b["_낱말"], b["_주제"] = _낱말(글), _주제(글)
        준비.append(b)
    # 대표는 '가장 잘 설명한 기사'로 세웁니다.
    # 국내 보도가 적은 것을 대표로 세우면 숫자가 실제보다 적어 보입니다.
    준비.sort(key=lambda a: (-int(a.get("주목도", 3)),
                            -len(a.get("한글제목") or ""),
                            a.get("날짜") or ""))

    남, 묶음 = 준비, []
    while 남:
        무리, 남은것 = [남.pop(0)], []
        바뀜 = True
        while 바뀜:            # 무리에 붙은 기사를 기준으로 한 번 더 훑는다
            바뀜 = False
            for a in 남:
                if any(abs((_날(a) - _날(b)).days) <= 날짜폭 and _같은사건(b, a)
                       for b in 무리):
                    무리.append(a)
                    바뀜 = True
                else:
                    남은것.append(a)
            남, 남은것 = 남은것, []
        무리[1:] = sorted(무리[1:], key=lambda a: a.get("날짜") or "")
        묶음.append(무리)
    return 묶음


def 후보읽기():
    if not os.path.isfile(후보파일):
        return {"기사": [], "갱신": None, "마지막수집": {}}
    with open(후보파일, encoding="utf-8") as f:
        자료 = json.load(f)
    자료.setdefault("기사", [])
    return 자료


def 승인읽기():
    """승인.txt 에서 아이디만 뽑는다. '#' 로 시작하는 줄은 설명이라 건너뛴다."""
    고른것 = []
    if not os.path.isfile(승인파일):
        return 고른것
    for 줄 in open(승인파일, encoding="utf-8"):
        줄 = 줄.strip()
        if not 줄 or 줄.startswith("#"):
            continue
        고른것.append(줄.split()[0])
    return 고른것


def 검색링크(제목, 매체):
    return "https://www.google.com/search?q=" + quote(f'"{제목}" {매체}')


def 카드(무리, 고르기=False, 체크=False, 새것=False):
    """무리는 같은 사건을 다룬 기사 목록. 첫 기사가 대표입니다."""
    if isinstance(무리, dict):
        무리 = [무리]
    a, 나머지 = 무리[0], 무리[1:]

    # 국내 보도 건수는 무리에서 '가장 많이 찾은' 값을 씁니다.
    # 대표 기사 하나만 보면 실제보다 적어 보여, 미보도를 부풀리게 됩니다.
    국내수 = max(int(b.get("국내수", 0)) for b in 무리)
    배지 = ('<span class="tag t0">국내 0건</span>' if 국내수 == 0
          else f'<span class="tag t1">국내 {국내수}건</span>')
    if 나머지:
        나라들 = {b.get("나라") for b in 무리 if b.get("나라")}
        배지 = (f'<span class="tag tm">해외 {len(무리)}곳'
                + (f' · {len(나라들)}개국' if len(나라들) > 1 else '')
                + '</span>') + 배지
    if 새것:
        배지 = '<span class="tag tn">새로 들어옴</span>' + 배지

    # 같은 사건을 받아쓴 다른 매체들 —— 접어서 보여줍니다.
    # 국내 0건인데 해외 여러 곳이 다뤘다는 사실 자체가 근거가 됩니다.
    함께 = ""
    if 나머지:
        줄들 = "".join(
            f'<li><b>{e(b.get("매체",""))}</b> <span>{e(b.get("나라",""))}</span> '
            f'<a href="{e(b.get("링크",""))}" target="_blank" '
            f'rel="noopener nofollow">{e(b.get("한글제목") or b.get("제목",""))[:50]}</a></li>'
            for b in 나머지)
        함께 = (f'<details class="also"><summary>같은 사건을 다룬 다른 매체 '
                f'{len(나머지)}곳</summary><ul>{줄들}</ul></details>')
    별 = "●" * int(a.get("주목도", 3)) + "○" * (5 - int(a.get("주목도", 3)))
    본것, 국내제목 = set(), []
    for b in 무리:
        for t in b.get("국내기사", []):
            if t not in 본것:
                본것.add(t); 국내제목.append(t)
    찾음 = "".join(f"<li>{e(t)}</li>" for t in 국내제목[:5])
    국내블록 = (f'<div class="kr"><b>국내는 이렇게 썼습니다</b><ul>{찾음}</ul></div>'
             if 국내수 > 0 and 찾음 else "")
    속 = f"""<div class="tags">{배지}<span class="geo">{e(a.get("나라",""))}</span>
    <span class="kind">{e(a.get("성격","?"))}</span><span class="imp">{별}</span></div>
  <h3>{e(a.get("한글제목") or a.get("제목",""))}</h3>
  <p class="orig">{e(a.get("제목",""))}</p>
  <p class="sum">{e(a.get("요약",""))}</p>
  {국내블록}
  {함께}
  <div class="src"><span>{e(a.get("매체",""))} · {e((a.get("날짜") or "")[:10])}
    {'· ' + e(a["수집일"]) + ' 수집' if 고르기 and a.get("수집일") else ''}</span>
    <a class="alt" href="{e(검색링크(a.get("제목",""), a.get("매체","")))}"
       target="_blank" rel="noopener nofollow">제목으로 찾기</a>
    <a href="{e(a.get("링크",""))}" target="_blank" rel="noopener nofollow">원문 읽기 →</a></div>"""
    강조 = "zero" if 국내수 == 0 else "low"
    if not 고르기:
        return f'<article class="{강조}">{속}</article>'
    체크됨 = " checked" if 체크 else ""
    켜짐 = " on" if 체크 else ""
    return (f'<article class="{강조}{켜짐}" data-id="{e(a["id"])}"><div class="pick">'
            f'<input type="checkbox" data-id="{e(a["id"])}"{체크됨}>'
            f'<div>{속}</div></div></article>')


# ══════════════════════════════════════════════════════════════
#  공개 사이트
# ══════════════════════════════════════════════════════════════

def 사이트만들기(무리들, 승인목록):
    골라진 = {i: n for n, i in enumerate(승인목록)}

    # 무리 안의 어느 기사든 승인돼 있으면 실립니다.
    # 수집이 쌓이면서 대표가 바뀌어도 사이트에서 사라지지 않게 하려는 것입니다.
    실린것 = []
    for 무리 in 무리들:
        고른 = [a for a in 무리 if a["id"] in 골라진]
        if not 고른:
            continue
        머리기사 = min(고른, key=lambda a: 골라진[a["id"]])
        나머지 = [a for a in 무리 if a["id"] != 머리기사["id"]]
        실린것.append(([머리기사] + 나머지, 골라진[머리기사["id"]]))
    실린것.sort(key=lambda x: x[1])
    실린것 = [무리 for 무리, _ in 실린것]

    시각 = datetime.now(timezone.utc).astimezone().strftime("%Y년 %m월 %d일")
    영건 = sum(1 for 무리 in 실린것
                if max(int(a.get("국내수", 0)) for a in 무리) == 0)
    나라수 = len({a.get("나라") for 무리 in 실린것 for a in 무리 if a.get("나라")})
    기사수 = sum(len(무리) for 무리 in 실린것)

    글 = [머리(사이트이름, 한줄설명)]
    글.append(f"""<div class="bar">
      <div class="stat"><b>{len(실린것)}</b><span>실린 사건</span></div>
      <div class="stat"><b>{영건}</b><span>국내 0건</span></div>
      <div class="stat"><b>{기사수}</b><span>해외 기사</span></div>
      <div class="stat"><b>{나라수}</b><span>나라</span></div>
    </div>""")

    if not 실린것:
        글.append('<div class="none">아직 실린 기사가 없습니다.</div>')
    for 무리 in 실린것:
        글.append(카드(무리))

    글.append(f'<footer>{e(꼬리말)}<br><br>{e(시각)} 갱신 · 3일마다 새로 모읍니다'
              f'</footer></div></html>')

    os.makedirs(문서함, exist_ok=True)
    with open(os.path.join(문서함, "index.html"), "w", encoding="utf-8") as f:
        f.write("\n".join(글))
    return len(실린것)


# ══════════════════════════════════════════════════════════════
#  검수 화면
# ══════════════════════════════════════════════════════════════

def 검수만들기(무리들, 승인목록, 자료):
    승인집합 = set(승인목록)
    기사들 = 자료["기사"]
    수집 = 자료.get("마지막수집", {})

    # 가장 최근 수집일 —— 이 날짜에 들어온 것이 '이번에 새로 들어온 것'
    최신일 = 수집.get("날짜") or max((a.get("수집일") or "" for a in 기사들),
                                default="")

    def 골랐나(무리):
        return any(a["id"] in 승인집합 for a in 무리)

    def 새무리(무리):
        return any((a.get("수집일") or "") == 최신일 for a in 무리)

    def 순서(무리):
        return (-int(무리[0].get("주목도", 3)), 무리[0].get("국내수", 0))

    새로 = sorted([m for m in 무리들 if not 골랐나(m) and 새무리(m)], key=순서)
    지난 = sorted([m for m in 무리들 if not 골랐나(m) and not 새무리(m)],
                key=lambda m: max((a.get("수집일") or "") for a in m), reverse=True)
    실린 = [m for m in 무리들 if 골랐나(m)]
    새것 = 새로 + 지난

    편집주소 = f"https://github.com/{저장소}/edit/main/승인.txt" if 저장소 else ""

    글 = [머리("검수 — " + 사이트이름,
              "체크한 기사만 사이트에 올라갑니다", 검수CSS)]

    안내 = [
        "올릴 기사를 체크합니다. (체크를 풀면 사이트에서 내려갑니다)",
        "아래 <b>승인 목록 복사</b> 를 누릅니다.",
    ]
    안내 += ([f'<a href="{e(편집주소)}" target="_blank" rel="noopener">'
              f'<b>승인.txt 열기</b></a> → 안에 있던 내용을 <b>전부 지우고</b> 붙여넣기 '
              f'→ 맨 아래 <b>Commit changes</b>']
             if 편집주소 else
             ["저장소의 <b>승인.txt</b> 를 열어 내용을 전부 지우고 붙여넣은 뒤 저장합니다."])
    안내.append("1~2분 뒤 사이트가 바뀝니다.")

    글.append('<div class="step"><b>검수하는 법</b><ol>'
              + "".join(f"<li>{s}</li>" for s in 안내) + "</ol></div>")

    if 수집:
        글.append(f"""<div class="bar">
          <div class="stat"><b>{len(새로)}</b><span>새로 들어옴</span></div>
          <div class="stat"><b>{len(지난)}</b><span>지난 후보</span></div>
          <div class="stat"><b>{len(실린)}</b><span>사이트에 실림</span></div>
          <div class="stat"><b>{e(str(수집.get("날짜","—"))[5:])}</b><span>마지막 수집</span></div>
        </div>""")
    if 수집.get("문제"):
        글.append(f'<div class="step">⚠ 지난 수집에서 문제가 있었습니다 — '
                  f'{e(수집["문제"])}</div>')

    if not 기사들:
        글.append('<div class="none">후보가 없습니다. 아직 수집이 안 돌았거나 '
                  '조건에 맞는 기사가 없었습니다.</div>')

    # ── ① 이번에 새로 들어온 것 —— 여기만 보시면 됩니다 ──────────
    if 기사들:
        글.append(f'<h2>🆕 이번에 새로 들어온 것 {len(새로)}건'
                  f'<span class="when"> · {e(최신일)} 수집</span></h2>')
    if 기사들 and not 새로:
        훑음 = 수집.get("훑은기사", "?")
        글.append(f"""<div class="none" style="text-align:left">
        <b>이번 수집에서는 새로 들어온 기사가 없습니다.</b><br><br>
        해외 기사 {e(str(훑음))}건을 훑었지만, 전부 이미 목록에 있거나
        국내에 충분히 보도된 것이었습니다.<br><br>
        3일 간격으로 최근 14일치를 보기 때문에 겹치는 것이 많습니다.
        계속 0건이면 <b>jimin.py</b> 의 <b>국내보도_허용</b> 을 3에서 5로 올리거나,
        <b>정밀검사_최대</b> 를 60에서 100으로 올려 보세요.</div>""")
    for 무리 in 새로:
        글.append(카드(무리, 고르기=True, 체크=False, 새것=True))

    # ── ② 지난 후보 —— 접어 둡니다. 매번 다시 볼 필요 없습니다 ───
    if 지난:
        글.append(f'<details><summary>지난 후보 {len(지난)}건 — '
                  f'아직 안 고른 것들 (눌러서 펼치기)</summary>')
        for 무리 in 지난:
            글.append(카드(무리, 고르기=True, 체크=False))
        글.append('</details>')

    # ── ③ 이미 사이트에 실린 것 —— 뺄 때만 펼치면 됩니다 ─────────
    if 실린:
        글.append(f'<details><summary>사이트에 실린 {len(실린)}건 — '
                  f'내리려면 체크를 푸세요 (눌러서 펼치기)</summary>')
        for 무리 in 실린:
            글.append(카드(무리, 고르기=True, 체크=True))
        글.append('</details>')

    # 체크박스는 무리의 대표에만 답니다 —— 승인 목록에는 대표 아이디만 들어갑니다
    제목표 = {m[0]["id"]: (m[0].get("한글제목") or m[0].get("제목", ""))[:60]
            for m in 무리들}
    자료JSON = json.dumps(제목표, ensure_ascii=False).replace("</", "<\\/")

    글.append(f"""
<div class="act">
  <button id="copy">승인 목록 복사</button>
  {'<a href="' + e(편집주소) + '" target="_blank" rel="noopener">'
   '<button class="ghost" type="button">승인.txt 열기</button></a>' if 편집주소 else ''}
  <span class="count" id="cnt"></span>
</div>
<textarea id="out" readonly spellcheck="false"></textarea>
<script id="titles" type="application/json">{자료JSON}</script>
<script>
const 제목 = JSON.parse(document.getElementById('titles').textContent);
const 상자 = [...document.querySelectorAll('input[type=checkbox]')];
const 세기 = document.getElementById('cnt');
function 만들기() {{
  const 고른 = 상자.filter(c => c.checked).map(c => c.dataset.id);
  세기.textContent = 고른.length + '건 선택';
  return ['# 사이트에 올릴 기사 목록입니다. 이 파일을 지우면 사이트가 비워집니다.',
          '# 검수 화면에서 만들어진 내용을 그대로 붙여넣으세요.',
          ''].concat(
          고른.map(i => i + '  ' + (제목[i] || ''))).join('\\n') + '\\n';
}}
상자.forEach(c => c.addEventListener('change', () => {{
  c.closest('article').classList.toggle('on', c.checked);
  만들기();
}}));
document.getElementById('copy').addEventListener('click', async () => {{
  const 글 = 만들기();
  const 칸 = document.getElementById('out');
  칸.value = 글; 칸.style.display = 'block';
  try {{
    await navigator.clipboard.writeText(글);
    document.getElementById('copy').textContent = '복사했습니다 ✓';
  }} catch (err) {{
    칸.select();
    document.getElementById('copy').textContent = '아래 칸을 직접 복사하세요';
  }}
  setTimeout(() => document.getElementById('copy').textContent = '승인 목록 복사', 2500);
}});
만들기();
</script>
<footer>이 화면은 준이야 님이 보기 위한 것입니다. 주소를 아는 사람은 볼 수 있으니
비밀 정보는 넣지 마세요.</footer></div></html>""")

    os.makedirs(문서함, exist_ok=True)
    with open(os.path.join(문서함, "검수.html"), "w", encoding="utf-8") as f:
        f.write("\n".join(글))
    return len(새것)


def main():
    자료 = 후보읽기()
    승인목록 = 승인읽기()
    있는것 = {a["id"] for a in 자료["기사"]}
    사라진 = [i for i in 승인목록 if i not in 있는것]
    승인목록 = [i for i in 승인목록 if i in 있는것]

    무리들 = 사건묶기(자료["기사"])
    실림 = 사이트만들기(무리들, 승인목록)
    안고름 = 검수만들기(무리들, 승인목록, 자료)

    받아쓴것 = len(자료["기사"]) - len(무리들)
    print(f"  기사 {len(자료['기사'])}건 → 사건 {len(무리들)}개"
          + (f" (같은 사건을 받아쓴 {받아쓴것}건을 묶음)" if 받아쓴것 else ""))
    print(f"  사이트에 {실림}개 사건 · 아직 안 고른 것 {안고름}개")
    if 사라진:
        print(f"  승인 목록의 {len(사라진)}건은 후보에 없어 건너뛰었습니다 "
              f"(21일이 지나 정리된 기사입니다)")
    print(f"  docs/index.html · docs/검수.html 을 새로 썼습니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
