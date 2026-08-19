# -*- coding: utf-8 -*-
"""후보.json + 승인.txt 로 사이트를 만듭니다.

  docs/index.html   ← 공개되는 사이트. 승인.txt 에 적힌 기사만 들어갑니다.
  docs/검수.html     ← 준이야 님만 보는 화면. 여기서 고르고 승인.txt 에 붙여넣습니다.

기사를 새로 모으지 않습니다. 그래서 돈이 들지 않고 몇 초면 끝납니다.
직접 돌려보고 싶으면:  python 만들기.py
"""

import json
import os
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
"""


def 머리(제목, 부제, 여분=""):
    return (f'<!doctype html><html lang="ko"><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(제목)}</title><style>{CSS}{여분}</style>'
            f'<div class="wrap"><h1>{e(제목)}</h1>'
            f'<p class="sub">{e(부제)}</p>')


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


def 카드(a, 고르기=False, 체크=False):
    배지 = ('<span class="tag t0">국내 0건</span>' if a.get("국내수", 0) == 0
          else f'<span class="tag t1">국내 {a["국내수"]}건</span>')
    별 = "●" * int(a.get("주목도", 3)) + "○" * (5 - int(a.get("주목도", 3)))
    찾음 = "".join(f"<li>{e(t)}</li>" for t in a.get("국내기사", []))
    국내블록 = (f'<div class="kr"><b>국내는 이렇게 썼습니다</b><ul>{찾음}</ul></div>'
             if a.get("국내수", 0) > 0 and 찾음 else "")
    속 = f"""<div class="tags">{배지}<span class="geo">{e(a.get("나라",""))}</span>
    <span class="kind">{e(a.get("성격","?"))}</span><span class="imp">{별}</span></div>
  <h3>{e(a.get("한글제목") or a.get("제목",""))}</h3>
  <p class="orig">{e(a.get("제목",""))}</p>
  <p class="sum">{e(a.get("요약",""))}</p>
  {국내블록}
  <div class="src"><span>{e(a.get("매체",""))} · {e((a.get("날짜") or "")[:10])}</span>
    <a class="alt" href="{e(검색링크(a.get("제목",""), a.get("매체","")))}"
       target="_blank" rel="noopener nofollow">제목으로 찾기</a>
    <a href="{e(a.get("링크",""))}" target="_blank" rel="noopener nofollow">원문 읽기 →</a></div>"""
    강조 = "zero" if a.get("국내수", 0) == 0 else "low"
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

def 사이트만들기(자료, 승인목록):
    골라진 = {i: n for n, i in enumerate(승인목록)}
    실린것 = [a for a in 자료["기사"] if a["id"] in 골라진]
    실린것.sort(key=lambda x: 골라진[x["id"]])

    시각 = datetime.now(timezone.utc).astimezone().strftime("%Y년 %m월 %d일")
    영건 = sum(1 for a in 실린것 if a.get("국내수", 0) == 0)
    나라수 = len({a.get("나라") for a in 실린것})

    글 = [머리(사이트이름, 한줄설명)]
    글.append(f"""<div class="bar">
      <div class="stat"><b>{len(실린것)}</b><span>실린 기사</span></div>
      <div class="stat"><b>{영건}</b><span>국내 0건</span></div>
      <div class="stat"><b>{나라수}</b><span>나라</span></div>
    </div>""")

    if not 실린것:
        글.append('<div class="none">아직 실린 기사가 없습니다.</div>')
    for a in 실린것:
        글.append(카드(a))

    글.append(f'<footer>{e(꼬리말)}<br><br>{e(시각)} 갱신 · 3일마다 새로 모읍니다'
              f'</footer></div></html>')

    os.makedirs(문서함, exist_ok=True)
    with open(os.path.join(문서함, "index.html"), "w", encoding="utf-8") as f:
        f.write("\n".join(글))
    return len(실린것)


# ══════════════════════════════════════════════════════════════
#  검수 화면
# ══════════════════════════════════════════════════════════════

def 검수만들기(자료, 승인목록):
    승인집합 = set(승인목록)
    기사들 = 자료["기사"]
    # 이미 고른 것을 위로 — 빼고 싶을 때 찾기 쉽게
    기사들 = sorted(기사들, key=lambda a: (a["id"] not in 승인집합,
                                        -int(a.get("주목도", 3)),
                                        a.get("국내수", 0)))
    새것 = [a for a in 기사들 if a["id"] not in 승인집합]

    편집주소 = f"https://github.com/{저장소}/edit/main/승인.txt" if 저장소 else ""
    수집 = 자료.get("마지막수집", {})

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
          <div class="stat"><b>{len(새것)}</b><span>아직 안 고른 것</span></div>
          <div class="stat"><b>{len(승인집합)}</b><span>사이트에 실림</span></div>
          <div class="stat"><b>{e(str(수집.get("날짜","—")))}</b><span>마지막 수집</span></div>
        </div>""")
    if 수집.get("문제"):
        글.append(f'<div class="step">⚠ 지난 수집에서 문제가 있었습니다 — '
                  f'{e(수집["문제"])}</div>')

    글.append(f"<h2>후보 {len(기사들)}건</h2>")
    if not 기사들:
        글.append('<div class="none">후보가 없습니다. 아직 수집이 안 돌았거나 '
                  '조건에 맞는 기사가 없었습니다.</div>')
    for a in 기사들:
        글.append(카드(a, 고르기=True, 체크=a["id"] in 승인집합))

    제목표 = {a["id"]: (a.get("한글제목") or a.get("제목", ""))[:60] for a in 기사들}
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

    실림 = 사이트만들기(자료, 승인목록)
    안고름 = 검수만들기(자료, 승인목록)

    print(f"  후보 {len(자료['기사'])}건 · 사이트에 {실림}건 · 아직 안 고른 것 {안고름}건")
    if 사라진:
        print(f"  승인 목록의 {len(사라진)}건은 후보에 없어 건너뛰었습니다 "
              f"(21일이 지나 정리된 기사입니다)")
    print(f"  docs/index.html · docs/검수.html 을 새로 썼습니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
