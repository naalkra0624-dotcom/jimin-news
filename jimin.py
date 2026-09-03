# -*- coding: utf-8 -*-
"""
BTS 지민 — 국내에 안 나온 해외 기사

전 세계 뉴스에서 지민 관련 기사를 모아, 국내 언론이 다루지 않은 것만
골라 읽을 수 있게 정리합니다.

쓰는 법:  시작하기.bat 더블클릭
"""

import os, re, sys, csv, json, time, base64, webbrowser
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

try:
    import requests
except ImportError:
    print("\n  requests 패키지가 필요합니다:  pip install --user requests\n")
    input("  엔터를 누르면 닫힙니다...")
    sys.exit(1)

# 이 숫자는 실행 화면과 결과.html 맨 아래에 찍힙니다.
# 파일을 제대로 바꿨는지 확인할 때 쓰세요.
버전 = "2026-08-17 (동명이인 앞뒤 어순)"

HERE = os.path.dirname(os.path.abspath(__file__))
ENV  = os.path.join(HERE, "키.txt")
LOG  = os.path.join(HERE, "기록.csv")
OUT  = os.path.join(HERE, "결과.html")

# ══════════════════════════════════════════════════════════════
#  설정  ← 여기만 고치면 됩니다
# ══════════════════════════════════════════════════════════════
최근_며칠     = 14     # 최근 며칠치를 볼지
국내보도_허용 = 3      # 국내 보도가 이 건수 이하면 통과
                       #   0 = 완전 미보도만  /  3 = 거의 안 다뤄진 것까지
                       #   결과는 '0건'과 '1~3건'으로 나눠서 보여줍니다
정밀검사_최대 = 60     # 국내 확인을 몇 건까지 할지 ★ 비용·시간에 직결
매체당_최대   = 4      # 한 매체가 목록을 독차지하지 않게

# 이름 조건
필수이름   = ["jimin", "지민", "박지민", "ジミン"]
그룹이름   = ["bts", "bangtan", "방탄", "防弾"]
그룹도_반드시 = False   # True 로 바꾸면 BTS 가 함께 나온 기사만

# ── 검색 각도 ──────────────────────────────────────────────
# 지민 기사는 각도가 다양합니다. 하나만 쓰면 절반을 놓칩니다.
검색어들 = [
    'Jimin BTS',
    'Jimin',
    '"Jimin" solo',
    '"Jimin" album OR single OR song',
    '"Jimin" concert OR tour OR stage',
    '"Jimin" chart OR Billboard OR Spotify',
    '"Jimin" interview',
    '"Jimin" brand OR ambassador OR campaign',
    '"Jimin" award OR nomination',
    '"Jimin" fans OR fandom',
]

# ── 어느 나라 뉴스를 볼지 ──────────────────────────────────
# K팝 보도는 영미권보다 남미·동남아·인도가 훨씬 많고,
# 그게 국내에 거의 안 들어오는 기사들입니다.
지역들 = [
    ("미국",       "en-US", "US", "US:en"),
    ("영국",       "en-GB", "GB", "GB:en"),
    ("인도",       "en-IN", "IN", "IN:en"),
    ("필리핀",     "en-PH", "PH", "PH:en"),
    ("싱가포르",   "en-SG", "SG", "SG:en"),
    ("멕시코",     "es-419", "MX", "MX:es-419"),
    ("스페인",     "es",    "ES", "ES:es"),
    ("브라질",     "pt-BR", "BR", "BR:pt-419"),
    ("인도네시아", "id-ID", "ID", "ID:id"),
    ("일본",       "ja",    "JP", "JP:ja"),
    ("프랑스",     "fr",    "FR", "FR:fr"),
]
# 지역을 줄이면 빨라집니다. 늘리면 더 많이 잡힙니다.

# 한국 매체(영문판 포함)는 '해외의 시선'이 아니므로 제외
한국매체 = ["yna.co.kr", "koreaherald", "koreatimes", "koreajoongang", "chosun",
        "donga", "hani.co.kr", "mk.co.kr", "kbs.co.kr", "korea.net", "sedaily",
        "hankyung", "ytn.co.kr", "newsis", "edaily", "sportskeeda", "allkpop",
        "soompi", "kpopstarz", "koreaboo", "mydaily", "osen", "xportsnews",
        "sportsseoul", "spotvnews", "tvreport", "wowtv", "mbn.co.kr", "sbs.co.kr",
        "imbc", "joynews24", "starnewskorea", "topstarnews", "newsen",
        # ★ 한국 연예뉴스를 그 나라 말로 옮기기만 하는 매체들.
        #   국적은 해외지만 내용은 국내 기사의 번역본이라 '해외의 시선'이 아닙니다.
        "wowkorea", "thefirsttimes", "kstyle.com", "kpopmonster", "sportsdonga",
        "kbanhada", "danmee", "hanryutimes", "kpopn", "koreastardaily",
        "kpopstarz", "kpopherald", "kdramastars", "hellokpop", "kprofiles"]

# 매체가 아닌 것 —— 링크 단축 서비스, SNS, 집계 사이트
비매체 = ["t.co", "bit.ly", "goo.gl", "ift.tt", "dlvr.it", "buff.ly", "tinyurl",
       "twitter.com", "x.com", "facebook.com", "instagram.com", "youtube.com",
       "reddit.com", "pinterest", "tumblr.com", "medium.com", "blogspot",
       "wordpress.com", "news.google.com"]

건너뛸말 = ["photos of", "in pictures", "quiz", "horoscope", "merch sale",
        "how to watch", "where to buy", "giveaway"]

# ── 매체 주소로 진짜 국적을 알아냅니다 ─────────────────────
# 지금까지 표시하던 '나라'는 매체의 국적이 아니라 '검색한 지역'이었습니다.
# 그래서 베트남 매체가 멕시코로, 필리핀 매체가 미국으로 나왔습니다.
나라코드 = {
    "ph": "필리핀", "in": "인도", "id": "인도네시아", "jp": "일본", "vn": "베트남",
    "mx": "멕시코", "es": "스페인", "br": "브라질", "fr": "프랑스", "de": "독일",
    "it": "이탈리아", "uk": "영국", "au": "호주", "ca": "캐나다", "sg": "싱가포르",
    "my": "말레이시아", "th": "태국", "tw": "대만", "hk": "홍콩", "cn": "중국",
    "ar": "아르헨티나", "cl": "칠레", "co": "콜롬비아", "pe": "페루", "tr": "튀르키예",
    "ru": "러시아", "pl": "폴란드", "nl": "네덜란드", "se": "스웨덴", "pt": "포르투갈",
    "ng": "나이지리아", "za": "남아공", "eg": "이집트", "sa": "사우디", "ae": "UAE",
    "pk": "파키스탄", "bd": "방글라데시", "np": "네팔", "lk": "스리랑카",
}
매체국적 = {   # 주소만으로는 알 수 없는 곳들
    "inquirer.net": "필리핀", "philstar.com": "필리핀", "rappler.com": "필리핀",
    "gmanetwork.com": "필리핀", "manilatimes.net": "필리핀",
    "timesofindia": "인도", "hindustantimes": "인도", "indiatoday": "인도",
    "ndtv.com": "인도", "thehindu.com": "인도", "firstpost.com": "인도",
    "economictimes": "인도", "news18.com": "인도", "indianexpress": "인도",
    "folha.uol": "브라질", "globo.com": "브라질", "uol.com.br": "브라질",
    "elpais.com": "스페인", "elmundo.es": "스페인", "marca.com": "스페인",
    "milenio.com": "멕시코", "eluniversal.com.mx": "멕시코", "excelsior.com.mx": "멕시코",
    "infobae.com": "아르헨티나", "clarin.com": "아르헨티나",
    "straitstimes": "싱가포르", "channelnewsasia": "싱가포르",
    "bbc.co.uk": "영국", "bbc.com": "영국", "theguardian": "영국",
    "independent.co.uk": "영국", "dailymail": "영국", "nme.com": "영국",
    "billboard.com": "미국", "rollingstone.com": "미국", "variety.com": "미국",
    "forbes.com": "미국", "people.com": "미국", "usatoday": "미국",
    "hollywoodreporter": "미국", "nytimes.com": "미국", "cnn.com": "미국",
    "teenvogue.com": "미국", "buzzfeed.com": "미국", "vogue.com": "미국",
    "lemonde.fr": "프랑스", "lefigaro.fr": "프랑스",
    "asahi.com": "일본", "yomiuri.co.jp": "일본", "nikkei.com": "일본",
    "oricon.co.jp": "일본", "natalie.mu": "일본", "modelpress.jp": "일본",
}


def 매체나라(주소, 검색지역):
    """기사 주소로 매체의 진짜 국적을 알아낸다. 모르면 검색 지역을 그대로 쓴다."""
    글 = (주소 or "").lower()
    for 조각, 나라 in 매체국적.items():
        if 조각 in 글:
            return 나라
    m = re.search(r"https?://[^/]*?\.([a-z]{2})(?:/|$|:)", 글)
    if m and m.group(1) in 나라코드:
        return 나라코드[m.group(1)]
    m = re.search(r"https?://[^/]*?\.(?:com|net|org|co)\.([a-z]{2})\b", 글)
    if m and m.group(1) in 나라코드:
        return 나라코드[m.group(1)]
    return 검색지역

# ══════════════════════════════════════════════════════════════
#  동명이인 걸러내기  ★ '지민'은 흔한 이름입니다
# ══════════════════════════════════════════════════════════════
# 개그우먼 김지민, 배우 한지민, 작가 지민, 가수 박지민(BTS 아님) 등이
# 국내 검색에 섞여 들어옵니다. 그대로 두면 엉뚱한 기사를 "국내에 보도됨"
# 으로 잘못 세어, 정작 미보도 기사가 탈락합니다.

# 이 말이 있으면 BTS 지민이 아닌 것으로 봅니다
다른사람_직업 = ["개그우먼", "개그맨", "코미디언", "아나운서", "치어리더",
           "기상캐스터", "국회의원", "의원", "변호사", "검사", "판사",
           "교수", "감독", "선수", "쇼트트랙", "피겨", "골프", "배구",
           "농구", "야구", "축구", "웹툰작가", "소설가", "시인"]

# BTS 지민이 아닌 동명이인 —— 성씨 한 글자 + 지민 이면 전부 걸러냅니다.
# 목록을 일일이 적으면 반드시 빠지는 게 생겨서, 성씨 자체로 잡습니다.
# (박지민은 BTS 지민의 본명이라 여기서 빼고 아래에서 따로 봅니다)
성씨_한글자 = ("김이최정강조윤장임한오서신권황안송류전홍고문양손배백허유"
          "남심노하곽성차주우구민진지엄채원천방공현함변염여추도소석"
          "선설마길위표명기반왕금옥육인맹제모탁국어은편용")

# 로마자로 쓴 동명이인도 막습니다 (Kim Jimin, Moon Jimin …)
성씨_로마자 = ["kim", "lee", "park", "choi", "jung", "jeong", "kang", "cho",
          "yoon", "jang", "lim", "han", "oh", "seo", "shin", "kwon",
          "hwang", "ahn", "song", "ryu", "jeon", "hong", "ko", "moon",
          "yang", "son", "bae", "baek", "heo", "yoo", "nam", "sim",
          "noh", "ha", "kwak", "sung", "cha", "joo", "woo", "koo", "min"]

# ★ 영어권 매체는 이름을 뒤집어 씁니다 —— "Jimin Moon" (브로드웨이 배우),
#   "Jimin Kang", "Jimin Lee" 처럼요. 그래서 뒤 순서도 함께 봅니다.
#   다만 뒤 순서는 평범한 영어 단어와 부딪히기 쉬워서 목록을 줄였습니다.
#     song  → "a new Jimin song"   (신곡 기사)
#     sung  → "Jimin sung live"    (공연 기사)
#     min   → "Jimin min"          (분 단위 표기)
#     ha/oh → 감탄사
#   이런 것들은 뺐습니다. 뺀 성씨는 앞 순서(Song Jimin)로는 여전히 잡힙니다.
_뒤순서_제외 = {"song", "sung", "min", "ha", "oh", "no", "noh", "so", "won"}
성씨_로마자_뒤 = [s for s in 성씨_로마자 if s not in _뒤순서_제외]

# ★★ 일본 매체는 이름을 가타카나로 씁니다 —— キム・ジミン(김지민),
#    ハン・ジミン(한지민) 이 그대로 통과하고 있었습니다.
#    일본어 기사가 수집의 큰 몫이라 구멍이 컸습니다. パク(박)는 뺍니다.
성씨_가타카나 = ["キム", "イ", "リ", "チェ", "チョン", "カン", "チョ", "ユン", "チャン",
           "イム", "ハン", "オ", "ソ", "シン", "クォン", "ファン", "アン", "ソン",
           "リュ", "ホン", "コ", "ムン", "ヤン", "ペ", "ペク", "ホ", "ユ", "ナム",
           "シム", "ノ", "ハ", "クァク", "チャ", "チュ", "ウ", "ク", "ミン", "チン",
           "チ", "オム", "ウォン", "パン", "コン", "ヒョン", "ハム", "ピョン", "ヨム",
           "ヨ", "ト", "ソク", "ソル", "マ", "キル", "ウィ", "ピョ", "ミョン", "キ",
           "ワン", "クム", "オク", "ユク", "イン", "メン", "モ", "タク", "ウン", "ヨン"]

# 일본 기사는 한자로도 씁니다 —— 文ジミン(문지민), 韓ジミン(한지민).
# 朴(박)은 BTS 지민의 성이라 뺍니다.
성씨_한자 = ("金李崔鄭姜趙尹張林韓呉徐申権黄安宋柳全洪高文楊孫裵白許劉"
         "南沈盧河郭成車朱禹具閔陳池厳蔡元千方孔玄咸卞廉呂秋都蘇石"
         "宣薛馬吉魏表明奇潘王琴玉陸印孟諸牟卓鞠魚殷片龍")

# 매체가 아니라 남의 글을 긁어 올리는 곳 —— 제목 끝에 정체불명의 코드가 붙습니다.
#   예) "...Giants Game Today (hPqJdxR6YH)"
잡음제목 = [
    re.compile(r"\([A-Za-z0-9]{8,14}\)\s*$"),      # 끝에 붙은 임의 코드
    re.compile(r"\bon instagram:", re.I),           # 인스타그램 게시물 전재
    re.compile(r"(?:#\w+[\s,]*){3,}"),              # 해시태그 나열
    re.compile(r"\|\|"),                            # || 로 꾸민 팬아트 제목
]

# BTS 지민임을 확실히 해주는 말
지민_문맥 = ["bts", "방탄", "방탄소년단", "아미", "army", "하이브", "hybe",
        "지민 솔로", "빅히트"]

# ⚠ '박지민' 은 BTS 지민의 본명이지만 동명이인 가수도 있습니다.
#   그래서 박지민은 위 '지민_문맥' 이 함께 있을 때만 인정합니다.


# ══════════════════════════════════════════════════════════════
#  키
# ══════════════════════════════════════════════════════════════

def 키준비():
    키 = {}
    # 깃허브에서 자동 실행될 때는 키를 물어볼 사람이 없습니다.
    # 그래서 환경변수(깃허브 Secrets)를 가장 먼저 봅니다.
    for k in ("NAVER_ID", "NAVER_SECRET", "CLAUDE_KEY"):
        if os.environ.get(k):
            키[k] = os.environ[k].strip()
    if len(키) == 3:
        return 키
    if os.path.isfile(ENV):
        for 줄 in open(ENV, encoding="utf-8"):
            줄 = 줄.strip()
            if 줄 and not 줄.startswith("#") and "=" in 줄:
                k, _, v = 줄.partition("=")
                키[k.strip()] = v.strip().strip('"').strip("'")
    필요 = [("NAVER_ID", "네이버 Client ID",
             "https://developers.naver.com 에서 애플리케이션 등록 (사용 API: 검색)"),
           ("NAVER_SECRET", "네이버 Client Secret", None),
           ("CLAUDE_KEY", "Claude API 키", "https://console.anthropic.com")]
    if all(키.get(k) for k, _, _ in 필요):
        return 키
    if not sys.stdin or not sys.stdin.isatty():
        빠진 = [이름 for k, 이름, _ in 필요 if not 키.get(k)]
        raise SystemExit(
            "\n  키가 없습니다: " + ", ".join(빠진) +
            "\n  자동 실행 환경에서는 물어볼 수 없습니다."
            "\n  깃허브 저장소 → Settings → Secrets and variables → Actions 에"
            "\n  NAVER_ID / NAVER_SECRET / CLAUDE_KEY 를 등록하세요.\n")
    print("\n  키를 한 번만 입력하면 다음부터는 안 물어봅니다.\n")
    for k, 이름, 안내 in 필요:
        if 키.get(k):
            continue
        if 안내:
            print(f"  ── {안내}")
        while True:
            값 = input(f"  {이름}: ").strip()
            if 값:
                키[k] = 값
                break
        print()
    with open(ENV, "w", encoding="utf-8") as f:
        f.write("# 이 파일은 남에게 보내지 마세요.\n")
        for k in ("NAVER_ID", "NAVER_SECRET", "CLAUDE_KEY"):
            f.write(f"{k}={키.get(k,'')}\n")
    print(f"  저장했습니다 → {ENV}\n")
    return 키


# ══════════════════════════════════════════════════════════════
#  공통
# ══════════════════════════════════════════════════════════════

def 태그제거(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    for a, b in [("&quot;",'"'),("&amp;","&"),("&#39;","'"),("&nbsp;"," "),("&apos;","'")]:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def 날짜(s):
    if not s:
        return None
    try:
        return parsedate_to_datetime(s)
    except Exception:
        pass
    for f in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            d = datetime.strptime(s, f)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def 단어있나(글, 목록):
    낮 = (글 or "").lower()
    for w in 목록:
        if re.search(r"[가-힣ぁ-んァ-ン一-龥]", w):   # 한글·일본어는 그냥 포함 검사
            if w in 낮:
                return True
        elif re.search(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", 낮):
            return True
    return False


def 한국매체인가(글):
    return any(d in (글 or "").lower() for d in 한국매체)


def 비매체인가(글):
    """t.co 같은 링크 단축 주소나 SNS 는 '매체'가 아닙니다."""
    낮 = (글 or "").lower()
    # 구글 뉴스 주소 자체는 링크 형태라 걸리므로, 매체명 쪽만 봅니다
    return any(d in 낮 for d in 비매체 if d != "news.google.com")


_동명이인_한글 = None
_동명이인_로마자 = None
_동명이인_가타카나 = None


def 동명이인_이름(글):
    """'문지민', 'Kim Jimin', 'Jimin Moon' 처럼 성이 붙은 다른 사람인지 본다.

    목록을 일일이 적는 대신 성씨로 잡습니다. 그래야 빠지는 이름이 없습니다.
    한국어는 성이 앞, 영어권 기사는 성이 뒤로 가므로 양쪽 다 봅니다.
    박지민은 BTS 지민의 본명이라 여기서 제외하고, 따로 판단합니다.
    """
    global _동명이인_한글, _동명이인_로마자, _동명이인_가타카나
    if _동명이인_한글 is None:
        _동명이인_한글 = re.compile(f"[{성씨_한글자}]지민")
        앞 = r"(?:" + "|".join(성씨_로마자) + r")[ \-]?jimin"
        뒤 = r"jimin[ \-](?:" + "|".join(성씨_로마자_뒤) + r")"
        _동명이인_로마자 = re.compile(
            r"(?<![\w-])(?:" + 앞 + r"|" + 뒤 + r")(?![\w-])")
        # 긴 성씨부터 맞춰야 'チョン' 이 'チ' 로 잘리지 않습니다.
        # 앞에 다른 가타카나가 있으면 성씨가 아닙니다 —— パク・ジミン(BTS 본명)의
        # 'ク' 만 떼어 잡는 것을 막습니다.
        긴것부터 = sorted(성씨_가타카나, key=len, reverse=True)
        _동명이인_가타카나 = re.compile(
            r"(?<![ァ-ヴー])(?:(?:" + "|".join(긴것부터) + r")"
            r"|[" + 성씨_한자 + r"])[・･\s]?ジミン")
    return bool(_동명이인_한글.search(글)
                or _동명이인_로마자.search(글)
                or _동명이인_가타카나.search(글))


def 국내기사_지민인가(제목, 설명=""):
    """국내 기사가 정말 BTS 지민에 관한 것인지 본다.

    · 개그우먼 김지민, 배우 한지민 같은 동명이인은 걸러낸다.
    · BTS·방탄 같은 문맥어가 있으면 확실히 인정.
    · 문맥어가 없고 '지민'만 있으면, 동명이인 신호가 없을 때만 인정.
    """
    글 = f"{제목} {설명}".lower()

    # 성이 붙은 동명이인 → 바로 제외 (박지민은 아래에서 따로 본다)
    #
    # 일부러 문맥보다 앞에 둡니다. "개그우먼 김지민이 BTS 지민 팬" 같은 기사는
    # BTS 지민에 대한 '보도'가 아니라 다른 사람 기사에 이름만 스친 것이라,
    # 국내 보도로 세면 진짜 미보도 기사가 억울하게 탈락합니다.
    # 드물게 "BTS 지민, 배우 한지민과 광고 촬영" 같은 진짜 기사도 빠지지만,
    # 오염을 막는 쪽이 이 도구의 목적에 맞습니다.
    if 동명이인_이름(글):
        return False

    문맥있음 = any(w in 글 for w in 지민_문맥)

    # 다른 직업이 붙어 있으면, BTS 문맥이 없는 한 제외
    if any(직업 in 글 for 직업 in 다른사람_직업) and not 문맥있음:
        return False

    if 문맥있음:
        return True

    # 본명 '박지민' 은 동명이인 가수가 있어 문맥 없이는 인정하지 않는다
    if "박지민" in 글:
        return False

    return "지민" in 글


def 실제주소(구글링크):
    """구글뉴스 링크 안에 감춰진 진짜 기사 주소를 꺼낸다.
    못 꺼내면 원래 링크를 그대로 쓴다 (브라우저에서는 원문으로 넘어간다)."""
    m = re.search(r"/articles/([A-Za-z0-9_\-]+)", 구글링크 or "")
    if not m:
        return 구글링크
    for 꼬리 in ("", "=", "==", "==="):
        try:
            원시 = base64.urlsafe_b64decode(m.group(1) + 꼬리)
        except Exception:
            continue
        글 = 원시.decode("utf-8", "ignore")
        찾음 = re.search(r"https?://[\w\-./%?=&+#~:,;@!$'()*\[\]]+", 글)
        if 찾음:
            주소 = re.sub(r"[^\w\-./%?=&+#~:,;@!$'()*\[\]].*$", "", 찾음.group(0))
            if "news.google" not in 주소 and len(주소) > 15:
                return 주소
        break
    return 구글링크


def 검색링크(제목, 매체):
    return "https://www.google.com/search?q=" + quote(f'"{제목}" {매체}')


# ══════════════════════════════════════════════════════════════
#  1. 전 세계에서 기사 모으기
# ══════════════════════════════════════════════════════════════

def 한번검색(검색어, hl, gl, ceid):
    주소 = ("https://news.google.com/rss/search?q="
          + quote(f"{검색어} when:{최근_며칠}d")
          + f"&hl={hl}&gl={gl}&ceid={ceid}")
    try:
        r = requests.get(주소, timeout=25,
                         headers={"User-Agent": "Mozilla/5.0 (jimin-news)"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        return None, type(e).__name__

    결과 = []
    for it in root.findall(".//item"):
        제목 = 태그제거(it.findtext("title") or "")
        if not 제목:
            continue
        링크 = it.findtext("link") or ""
        매체, 매체홈 = "?", ""
        src = it.find("source")
        if src is not None:
            매체 = (src.text or "?").strip()
            매체홈 = src.get("url") or ""          # 홈페이지 — 판정용
            제목 = re.sub(r"\s+-\s+" + re.escape(매체) + r"\s*$", "", 제목)
        d = 날짜(it.findtext("pubDate"))
        결과.append({"매체": 매체, "매체홈": 매체홈, "제목": 제목,
                    "링크": 실제주소(링크),
                    "설명": 태그제거(it.findtext("description") or "")[:300],
                    "날짜": d.isoformat() if d else ""})
    return 결과, None


def 기사모으기():
    총검색 = len(검색어들) * len(지역들)
    print(f"  [1/3] 전 세계 뉴스를 훑는 중 — 검색어 {len(검색어들)}개 × "
          f"지역 {len(지역들)}곳 = {총검색}회, 최근 {최근_며칠}일\n")

    모음, 실패 = [], 0
    for 나라, hl, gl, ceid in 지역들:
        받음 = 0
        for q in 검색어들:
            결과, 오류 = 한번검색(q, hl, gl, ceid)
            if 결과 is None:
                실패 += 1
                continue
            for a in 결과:
                a["나라"] = 나라
            모음 += 결과
            받음 += len(결과)
            time.sleep(0.25)
        print(f"        {나라:<8} {받음:>4}건")

    본것, 걸러진 = set(), []
    통계 = defaultdict(int)
    for a in 모음:
        키값 = re.sub(r"\W+", "", a["제목"].lower())[:70]
        if not 키값 or 키값 in 본것:
            통계["중복"] += 1
            continue
        본것.add(키값)

        if any(w in a["제목"].lower() for w in 건너뛸말):
            통계["잡음"] += 1
            continue
        # 남의 글을 긁어 올리는 곳 —— 제목 끝에 정체불명의 코드가 붙습니다
        if any(r.search(a["제목"]) for r in 잡음제목):
            통계["잡음"] += 1
            continue
        if 한국매체인가(f'{a["링크"]} {a["매체홈"]} {a["매체"]}'):
            통계["한국매체"] += 1
            continue
        # t.co 같은 링크 단축 주소는 매체가 아닙니다
        if 비매체인가(f'{a["매체홈"]} {a["매체"]}'):
            통계["비매체"] += 1
            continue
        # ★ 지금까지 '나라'에 검색한 지역을 넣고 있었습니다.
        #   베트남 매체가 멕시코로 나오던 원인입니다. 매체 주소로 바로잡습니다.
        a["검색지역"] = a["나라"]
        a["나라"] = 매체나라(f'{a["매체홈"]} {a["링크"]}', a["나라"])

        본문 = f'{a["제목"]} {a["설명"]}'
        if not 단어있나(본문, 필수이름):
            통계["지민없음"] += 1
            continue
        # Kim Jimin, Moon Jimin … 같은 동명이인은 해외 기사에서도 걸러낸다
        if 동명이인_이름(본문.lower()) and not 단어있나(본문, 그룹이름):
            통계["동명이인"] += 1
            continue
        a["그룹언급"] = 단어있나(본문, 그룹이름)
        if 그룹도_반드시 and not a["그룹언급"]:
            통계["BTS없음"] += 1
            continue
        걸러진.append(a)

    걸러진.sort(key=lambda x: x["날짜"] or "", reverse=True)

    # 한 매체가 독차지하지 않게 고르게 뽑는다
    셈, 고름 = defaultdict(int), []
    for a in 걸러진:
        if 셈[a["매체"]] >= 매체당_최대:
            통계["매체편중"] += 1
            continue
        셈[a["매체"]] += 1
        고름.append(a)

    print(f"\n        수집 {len(모음)}건 → 중복 {통계['중복']} · 한국매체 {통계['한국매체']} · "
          f"비매체 {통계['비매체']} · "
          f"지민 없음 {통계['지민없음']} · 동명이인 {통계['동명이인']} · 잡음 {통계['잡음']}"
          + (f" · BTS 없음 {통계['BTS없음']}" if 그룹도_반드시 else "")
          + (f" · 매체 편중 {통계['매체편중']}" if 통계['매체편중'] else ""))
    print(f"        → 대상 {len(고름)}건  (매체 {len(셈)}곳, {len({a['나라'] for a in 고름})}개국)")
    if 실패:
        print(f"        검색 {실패}회 실패 (일부 지역이 막혔을 수 있습니다)")
    print()
    return 고름, 실패, dict(통계), len(모음)


# ══════════════════════════════════════════════════════════════
#  2. 국내에 나왔는지 확인
# ══════════════════════════════════════════════════════════════

지시문 = """BTS 지민이 등장하는 해외 기사다. (영어가 아닐 수도 있다)
한국 뉴스에서 같은 사안을 찾을 검색어를 만들어라.

제목: {제목}
설명: {설명}
매체: {매체} ({나라})

규칙
- **모든 검색어에 "BTS" 를 반드시 넣어라.** 한국에는 개그우먼 김지민,
  배우 한지민 등 동명이인이 많아 "지민"만 쓰면 엉뚱한 기사가 잡힌다.
  예) "BTS 지민 빌보드", "BTS 지민 투어", "방탄 지민 인터뷰"
- 고유명사는 한국 언론이 쓰는 한글 표기로. (Jimin→지민, Billboard→빌보드,
  Rolling Stone→롤링스톤, Dior→디올)
- "BTS 지민 + 사건 핵심어" 2~3어절. 길면 검색이 안 된다. 3개.

그리고 아래도 만들어라.
- 제목: 한국어 40자 이내. 원문 번역이 아니라 무엇에 관한 기사인지 설명.
- 요약: 2문장 150자 이내. **원문을 번역하지 마라.** 이 기사가 무엇을 다루는지
  네 문장으로 설명해라. 사실을 지어내지 마라.
- 성격: 성과보도 / 비평분석 / 산업동향 / 인터뷰 / 현지반응 / 광고브랜드 / 가십 중 하나
- 주목도: 1~5. 국내 팬이 이걸 알면 좋을 이유가 얼마나 강한가.
- 맞는사람: 이 기사가 **BTS 의 지민(박지민)** 에 관한 것이면 true.
  동명이인(다른 가수·배우·작가 등)이거나 지민과 무관하면 false.

JSON만:
{{"검색어":["..."],"제목":"...","요약":"...","성격":"...","주목도":3,"맞는사람":true}}"""


def 클로드(키, 프롬프트):
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=60,
                      headers={"x-api-key": 키, "anthropic-version": "2023-06-01",
                               "content-type": "application/json"},
                      json={"model": "claude-haiku-4-5-20251001", "max_tokens": 700,
                            "messages": [{"role": "user", "content": 프롬프트}]})
    r.raise_for_status()
    m = re.search(r"\{.*\}", r.json()["content"][0]["text"], re.S)
    if not m:
        raise ValueError("응답 형식 오류")
    return json.loads(m.group())


def 네이버(키, 검색어):
    try:
        r = requests.get("https://openapi.naver.com/v1/search/news.json", timeout=20,
                         headers={"X-Naver-Client-Id": 키["NAVER_ID"],
                                  "X-Naver-Client-Secret": 키["NAVER_SECRET"]},
                         params={"query": 검색어, "display": 20, "sort": "date"})
        if r.status_code != 200:
            return None
        return r.json().get("items", [])
    except Exception:
        return None


def 판정하기(키, 기사들):
    대상 = 기사들[:정밀검사_최대]
    돈 = len(대상) * 8
    print(f"  [2/3] 국내에 나왔는지 확인하는 중... {len(대상)}건 (약 {돈}원)\n")
    통과, 제외, 실패 = [], [], None
    딴사람, 동명이인_제외 = 0, 0

    for i, a in enumerate(대상, 1):
        try:
            정보 = 클로드(키["CLAUDE_KEY"], 지시문.format(
                제목=a["제목"], 설명=a["설명"], 매체=a["매체"], 나라=a["나라"]))
        except Exception as e:
            if 실패 is None:
                실패 = f"Claude API 오류: {e}"
            print(f"     {i:>3}.  ?  {a['제목'][:50]}")
            continue

        # 해외 기사 자체가 다른 지민이면 여기서 버린다
        if 정보.get("맞는사람") is False:
            딴사람 += 1
            print(f"     {i:>3}.  ⛔ [동명이인] {a['제목'][:44]}")
            continue

        기준 = 날짜(a["날짜"]) or datetime.now(timezone.utc)
        시작, 끝 = 기준 - timedelta(days=7), 기준 + timedelta(days=7)
        국내, 걸러냄 = {}, 0
        for q in (정보.get("검색어") or [])[:3]:
            항목 = 네이버(키, q)
            if 항목 is None:
                if 실패 is None:
                    실패 = "네이버 검색 실패 — 키를 확인하세요 (키.txt 지우고 다시 실행)"
                break
            for it in 항목:
                d = 날짜(it.get("pubDate", ""))
                if not (d and 시작 <= d <= 끝):
                    continue
                제목ko = 태그제거(it.get("title", ""))
                설명ko = 태그제거(it.get("description", ""))
                # ★ 동명이인 기사는 국내 보도로 세지 않는다
                if not 국내기사_지민인가(제목ko, 설명ko):
                    걸러냄 += 1
                    continue
                국내[it.get("originallink") or it.get("link")] = 제목ko
            time.sleep(0.1)
        동명이인_제외 += 걸러냄

        주목 = 정보.get("주목도", 3)
        try:
            주목 = max(1, min(5, int(주목)))
        except (TypeError, ValueError):
            주목 = 3

        항목 = {**a,
              "한글제목": (정보.get("제목") or a["제목"])[:80],
              "요약": (정보.get("요약") or "")[:180],
              "성격": 정보.get("성격") or "?",
              "주목도": 주목,
              "검색어": 정보.get("검색어") or [],
              "국내수": len(국내),
              "국내기사": list(국내.values())[:3]}

        if len(국내) == 0:
            통과.append(항목); 표시 = "🔴"
        elif len(국내) <= 국내보도_허용:
            통과.append(항목); 표시 = "🟡"
        else:
            제외.append(항목); 표시 = "⚪"
        print(f"     {i:>3}. {표시} [{a['나라'][:4]}·국내{len(국내):>2}] {a['제목'][:44]}")

    통과.sort(key=lambda x: (-x["주목도"], x["국내수"]))
    영건 = sum(1 for a in 통과 if a["국내수"] == 0)
    print(f"\n        → 🔴 국내 0건 {영건}  ·  🟡 국내 1~{국내보도_허용}건 "
          f"{len(통과)-영건}  ·  ⚪ 제외 {len(제외)}")
    if 딴사람 or 동명이인_제외:
        print(f"        동명이인 정리 — 해외 기사 {딴사람}건 제외, "
              f"국내 검색결과 {동명이인_제외}건 무시")
    print()
    return 통과, 제외, 실패


# ══════════════════════════════════════════════════════════════
#  3. 기록
# ══════════════════════════════════════════════════════════════

def 기록추가(행):
    처음 = not os.path.isfile(LOG)
    with open(LOG, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if 처음:
            w.writerow(["날짜","수집","대상","정밀검사","국내0건","국내1_3건","국내미보도","국내있음","미보도율"])
        w.writerow(행)


def 기록읽기():
    if not os.path.isfile(LOG):
        return []
    with open(LOG, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ══════════════════════════════════════════════════════════════
#  4. 결과 화면
# ══════════════════════════════════════════════════════════════

머리 = """<!doctype html><html lang="ko"><meta charset="utf-8">
<title>BTS 지민 · 국내에 안 나온 해외 기사</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{margin:0;background:#faf9f7;color:#191917;
 font:16px/1.75 -apple-system,"Malgun Gothic","Apple SD Gothic Neo",sans-serif}
.wrap{max-width:720px;margin:0 auto;padding:0 22px 60px}
h1{font-size:28px;margin:42px 0 6px;font-weight:800;letter-spacing:-.02em}
.sub{color:#77746d;font-size:15px;margin:0 0 4px}
.when{color:#a09c93;font-size:13px;margin:0 0 22px}
.bar{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 26px}
.stat{background:#fff;border:1px solid #e7e5e0;border-radius:10px;padding:12px 16px;min-width:84px}
.stat b{display:block;font-size:22px;font-weight:700;line-height:1.3}
.stat span{font-size:12px;color:#77746d}
.warn{background:#fbeae7;border:1px solid #f0c8c0;color:#8a3323;padding:12px 16px;
 border-radius:8px;font-size:14px;margin:0 0 18px}
h2{font-size:17px;margin:34px 0 14px;padding-bottom:8px;border-bottom:2px solid #191917}
article{background:#fff;border:1px solid #e7e5e0;border-radius:12px;
 padding:20px 22px;margin-bottom:15px}
article.zero{border-left:3px solid #b8402f}
article.low{border-left:3px solid #d9a520}
.kr{background:#faf8f2;border:1px solid #eee5cf;border-radius:8px;
 padding:11px 14px;margin:0 0 13px;font-size:13px;color:#6b6355}
.kr b{display:block;font-size:11.5px;color:#a37613;margin-bottom:5px;font-weight:700}
.kr ul{margin:0;padding-left:18px;line-height:1.65}
.hint{color:#a09c93;font-size:13px;margin:-6px 0 14px}
.tags{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin-bottom:11px}
.tag{font-size:11px;font-weight:700;padding:3px 9px;border-radius:20px}
.t0{background:#fbeae7;color:#b8402f}.t1{background:#fbf3e0;color:#a37613}
.kind,.geo{font-size:11px;color:#77746d;border:1px solid #e7e5e0;padding:3px 9px;border-radius:20px}
.geo{background:#f3f1ec}
.imp{font-size:11px;color:#a09c93;letter-spacing:1px}
h3{font-size:19px;margin:0 0 10px;line-height:1.45;font-weight:700}
p.sum{margin:0 0 14px;color:#2f2e2b}
details{margin:0 0 12px}summary{cursor:pointer;color:#a09c93;font-size:12px}
details ul{font-size:12px;color:#77746d;margin:8px 0 0;line-height:1.7}
.src{display:flex;gap:8px;align-items:center;font-size:12.5px;color:#77746d;
 border-top:1px solid #eee;padding-top:12px;flex-wrap:wrap}
.src a{color:#191917;font-weight:600;text-decoration:none}
.src a.alt{margin-left:auto;color:#a09c93;font-weight:400;font-size:12px}
.src a.alt+a{margin-left:12px}
.mini{background:#fff;border:1px solid #e7e5e0;border-radius:10px;
 padding:12px 16px;margin-bottom:9px;font-size:14px}
.mini .m{color:#77746d;font-size:12px}
.none{text-align:center;color:#77746d;padding:44px 20px;background:#fff;
 border:1px solid #e7e5e0;border-radius:12px}
footer{color:#a09c93;font-size:12.5px;line-height:1.8;border-top:1px solid #e7e5e0;
 margin-top:44px;padding-top:20px}
</style><div class="wrap">
<h1>BTS 지민</h1>
<p class="sub">해외는 다뤘지만 국내에는 없는 기사</p>
"""


def 화면만들기(통과, 제외, 누적, 실패, 실패수, 수집수, 대상수):
    from html import escape as e
    시각 = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
    검사수 = len(통과) + len(제외)
    율 = f"{len(통과)/검사수*100:.0f}%" if 검사수 else "—"
    나라수 = len({a["나라"] for a in 통과}) if 통과 else 0
    날짜수 = len({r["날짜"] for r in 누적}) if 누적 else 1

    글 = [머리, f'<p class="when">{시각} · 최근 {최근_며칠}일 · {날짜수}일째</p>']
    영건수 = sum(1 for a in 통과 if a["국내수"] == 0)
    글.append(f"""<div class="bar">
      <div class="stat"><b>{영건수}</b><span>국내 0건</span></div>
      <div class="stat"><b>{len(통과)-영건수}</b><span>국내 1~{국내보도_허용}건</span></div>
      <div class="stat"><b>{검사수}</b><span>확인</span></div>
      <div class="stat"><b>{율}</b><span>미보도율</span></div>
      <div class="stat"><b>{나라수}</b><span>나라</span></div>
    </div>""")

    if 실패:
        글.append(f'<div class="warn">⚠ {e(실패)}</div>')
    if 대상수 > 정밀검사_최대:
        글.append(f'<div class="warn">대상 {대상수}건 중 {정밀검사_최대}건만 확인했습니다. '
                 f'jimin.py 의 <b>정밀검사_최대</b>를 올리면 더 봅니다.</div>')
    if 실패수:
        글.append(f'<div class="warn">검색 {실패수}회 실패 — 결과가 적을 수 있습니다</div>')

    영건 = [a for a in 통과 if a["국내수"] == 0]
    저건 = [a for a in 통과 if a["국내수"] > 0]

    def 카드(a, 강조):
        배지 = ('<span class="tag t0">국내 0건</span>' if a["국내수"] == 0
              else f'<span class="tag t1">국내 {a["국내수"]}건</span>')
        별 = "●" * a["주목도"] + "○" * (5 - a["주목도"])
        찾음 = "".join(f"<li>{e(t)}</li>" for t in a["국내기사"])
        # 국내에 조금이라도 나온 건 '국내는 뭐라고 썼나'가 핵심이라 접지 않고 보여준다
        국내블록 = ""
        if a["국내수"] > 0 and 찾음:
            국내블록 = (f'<div class="kr"><b>국내는 이렇게 썼습니다</b>'
                     f'<ul>{찾음}</ul></div>')
        근거항목 = (f"<li><b>찾은 국내 기사</b><ul>{찾음}</ul></li>" if 찾음
                else "<li>국내 기사를 찾지 못했습니다</li>")
        return f"""<article class="{강조}">
  <div class="tags">{배지}<span class="geo">{e(a["나라"])}</span>
    <span class="kind">{e(a["성격"])}</span><span class="imp">{별}</span></div>
  <h3>{e(a["한글제목"])}</h3>
  {f'<p class="sum">{e(a["요약"])}</p>' if a["요약"] else ""}
  {국내블록}
  <details><summary>어떻게 확인했나</summary><ul>
    <li><b>원문 제목</b> · {e(a["제목"])}</li>
    <li><b>검색한 말</b> · {e(", ".join(a["검색어"]))}</li>
    {근거항목}
  </ul></details>
  <div class="src"><span>{e(a["매체"])}</span><span>·</span><span>{e(a["날짜"][:10])}</span>
    <a class="alt" href="{e(검색링크(a["제목"], a["매체"]))}" target="_blank"
       rel="noopener nofollow">제목으로 찾기</a>
    <a href="{e(a["링크"])}" target="_blank" rel="noopener nofollow">원문 읽기 →</a></div>
</article>"""

    글.append(f"<h2>🔴 국내에 한 건도 없는 기사 {len(영건)}건</h2>")
    if not 영건:
        글.append('<div class="none">오늘은 없습니다.</div>')
    for a in 영건:
        글.append(카드(a, "zero"))

    if 국내보도_허용 > 0:
        글.append(f'<h2>🟡 국내에 1~{국내보도_허용}건뿐인 기사 {len(저건)}건</h2>')
        글.append('<p class="hint">국내가 <b>무엇을</b> 썼는지와 비교해 보세요. '
                 '같은 사안을 다르게 다뤘다면 그 차이가 곧 글감입니다.</p>')
        if not 저건:
            글.append('<div class="none">없습니다.</div>')
        for a in 저건:
            글.append(카드(a, "low"))

    if 제외:
        글.append(f'<h2>국내에도 나온 기사 {len(제외)}건</h2>')
        for a in sorted(제외, key=lambda x: -x["국내수"])[:15]:
            글.append(f'<div class="mini"><b>{e(a["한글제목"])}</b>'
                     f'<div class="m">{e(a["매체"])} · {e(a["나라"])} · '
                     f'국내 {a["국내수"]}건 · {e(a["성격"])}</div></div>')

    if 날짜수 > 1:
        글.append(f'<h2>누적 {날짜수}일</h2>')
        for r in 누적[-10:][::-1]:
            영 = r.get("국내0건", "?")
            저 = r.get("국내1_3건", "?")
            글.append(f'<div class="mini">{e(r["날짜"])} · 확인 {e(r["정밀검사"])}건 → '
                     f'0건 <b>{e(str(영))}</b> · 1~3건 <b>{e(str(저))}</b> '
                     f'({e(r.get("미보도율",""))})</div>')

    글.append(f"""<footer>
모든 기사의 저작권은 원 매체에 있습니다. 이 페이지는 기사의 소재를 소개하고
원문으로 연결할 뿐이며, 본문을 번역하거나 전재하지 않습니다.<br>
한국 매체의 기사는 '해외의 시선'이 아니므로 수집 단계에서 제외합니다.<br>
<br>프로그램 버전 <b>{e(버전)}</b> · {e(시각)} 생성
</footer></div></html>""")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(글))


# ══════════════════════════════════════════════════════════════

def 진단():
    """제목을 붙여넣으면 걸러지는지 아닌지, 그 이유를 알려준다.

    '왜 아직도 이 사람이 나오지?' 를 추측하지 않고 확인하기 위한 도구입니다.
    """
    print("\n" + "=" * 62)
    print("  동명이인 진단기")
    print(f"  버전 {버전}")
    print("=" * 62)
    print("\n  결과 화면에 나온 기사 제목을 그대로 붙여넣고 엔터를 누르세요.")
    print("  (그냥 엔터를 누르면 끝납니다)\n")

    # 파일이 제대로 바뀌었는지 스스로 점검
    확인 = [("문지민 작가 신작", True), ("Jimin Moon cast in musical", True),
          ("Moon Jimin publishes essay", True), ("BTS Jimin tops chart", False)]
    샘 = [t for t, 기대 in 확인 if 동명이인_이름(t.lower()) != 기대]
    if 샘:
        print("  ⚠ 이 파일은 최신본이 아닙니다. jimin.py 를 덮어쓰지 않으셨습니다.")
        print(f"    (자체 점검 실패: {샘[0]})\n")
    else:
        print("  ✅ 자체 점검 통과 — 최신 규칙이 들어 있는 파일입니다.\n")

    while True:
        try:
            제목 = input("  제목 > ").strip()
        except EOFError:
            break
        if not 제목:
            break
        글 = 제목.lower()
        print()
        print(f"    이름 있음        : {'예' if 단어있나(제목, 필수이름) else '아니오 → 애초에 수집 안 됨'}")
        print(f"    BTS·방탄 언급    : {'예' if 단어있나(제목, 그룹이름) else '아니오'}")
        한 = _동명이인_한글.search(글) if _동명이인_한글 else None
        동 = 동명이인_이름(글)
        print(f"    동명이인 규칙    : {'걸림' if 동 else '안 걸림'}"
              + (f"  ← '{한.group(0)}'" if 한 else ""))
        if 동 and not 단어있나(제목, 그룹이름):
            print("\n    → 이 제목은 제외됩니다. 결과에 나올 수 없습니다.")
            print("      그래도 나온다면 결과.html 이 예전 것입니다.")
        elif 동:
            print("\n    → 동명이인 신호가 있지만 BTS 가 함께 있어 살립니다.")
        else:
            print("\n    → 통과합니다. 이게 잘못이면 이 제목을 저에게 보내주세요.")
            print("      어떤 성씨가 빠졌는지 바로 넣겠습니다.")
        print()
    print("  끝났습니다.\n")


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("진단", "diag", "test"):
        진단()
        input("  엔터를 누르면 닫힙니다...")
        return

    print("\n" + "=" * 62)
    print("  BTS 지민 — 국내에 안 나온 해외 기사")
    print(f"  버전 {버전}")
    print("=" * 62 + "\n")

    키 = 키준비()
    기사들, 실패수, 통계, 수집수 = 기사모으기()

    if not 기사들:
        print("  조건에 맞는 기사가 없습니다.")
        print("  · 인터넷 연결을 확인하세요")
        print("  · jimin.py 의 최근_며칠 을 늘려 보세요\n")
        input("  엔터를 누르면 닫힙니다...")
        return

    통과, 제외, 실패 = 판정하기(키, 기사들)

    검사수 = len(통과) + len(제외)
    율 = f"{len(통과)/검사수*100:.0f}%" if 검사수 else "—"
    영건수 = sum(1 for a in 통과 if a["국내수"] == 0)
    기록추가([datetime.now().strftime("%Y-%m-%d"), 수집수, len(기사들), 검사수,
            영건수, len(통과) - 영건수, len(통과), len(제외), 율])

    print("  [3/3] 결과 화면을 만드는 중...\n")
    화면만들기(통과, 제외, 기록읽기(), 실패, 실패수, 수집수, len(기사들))

    print("=" * 62)
    print(f"  수집 {수집수} → 대상 {len(기사들)} → 확인 {검사수}")
    print(f"  🔴 국내 0건 {영건수}   🟡 국내 1~{국내보도_허용}건 {len(통과)-영건수}"
          f"   미보도율 {율}")
    if len(기사들) > 정밀검사_최대:
        print(f"  ※ 대상 {len(기사들)}건 중 {정밀검사_최대}건만 확인했습니다.")
        print(f"     jimin.py 의 정밀검사_최대 를 올리면 더 봅니다.")
    print(f"  결과: {OUT}")
    print("=" * 62 + "\n")

    try:
        webbrowser.open("file://" + OUT.replace("\\", "/"))
    except Exception:
        pass
    input("  엔터를 누르면 닫힙니다...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  중단했습니다.\n")
    except Exception as 오류:
        print(f"\n  오류: {type(오류).__name__}: {오류}\n")
        input("  엔터를 누르면 닫힙니다...")
