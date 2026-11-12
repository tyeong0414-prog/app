"""합리적인 선택 도우기
실행: streamlit run app.py
배포: GitHub에 app.py와 requirements.txt를 올린 후 Streamlit Community Cloud 연결.
배포 주소를 QR로 공유하면 설치 없이 휴대폰 브라우저에서 사용할 수 있습니다.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
import html
from urllib.parse import urlparse

import qrcode
import streamlit as st


def compare_choices(choices: list[dict], won_per_point: int) -> list[dict]:
    """편익=C+S×환산액, 암묵적 비용=max(다른 대안의 편익-C).
    서로 배타적인 대안 중 하나를 고르는 상황, 공통 환산액을 가정합니다.
    명시적 비용 및 환산액은 음수가 아닌 원 단위 정수입니다.
    """
    if len(choices) < 2:
        raise ValueError("선택지는 최소 2개가 필요합니다.")
    if not isinstance(won_per_point, int) or won_per_point < 1:
        raise ValueError("만족도 1점의 금액은 1원 이상의 정수여야 합니다.")
    rows = []
    for index, choice in enumerate(choices):
        cost = choice["cost"]
        satisfaction = Decimal(str(choice["satisfaction"]))
        if not isinstance(cost, int) or cost < 0 or not 1 <= satisfaction <= 10:
            raise ValueError("비용은 0원 이상의 정수, 만족도는 1~10이어야 합니다.")
        net = int((satisfaction * won_per_point).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        rows.append({"index": index, "name": str(choice["name"]).strip() or f"선택 {index + 1}",
                     "cost": cost, "satisfaction": float(satisfaction),
                     "net_benefit": net, "benefit": cost + net})
    for row in rows:
        implicit = max(other["net_benefit"] for other in rows if other["index"] != row["index"])
        row["implicit_cost"] = implicit
        row["opportunity_cost"] = row["cost"] + implicit
        row["economic_profit"] = row["benefit"] - row["opportunity_cost"]
    return rows


def money(value: int) -> str:
    """휴대폰에서도 줄바꿈을 줄이는 정확한 원 단위 표시."""
    return f"{value:,}원"


def main() -> None:
    st.set_page_config(page_title="선택 한눈에", page_icon="⚖️", layout="centered", initial_sidebar_state="collapsed")
    st.markdown("""
<style>
.stApp {background:#F7F9FC; color:#18243B;}
.block-container {max-width:600px; padding:0.65rem 0.7rem 0.65rem !important;}
header[data-testid="stHeader"] {height:0; background:transparent;}
[data-testid="stToolbar"], #MainMenu, footer {display:none;}
/* 각 출력 영역에 실제 높이와 간격을 확보해 다음 입력/카드와 겹치지 않게 합니다. */
[data-testid="stVerticalBlock"] {gap:0.65rem;}
[data-testid="stMarkdownContainer"] {display:flow-root; height:auto; overflow:visible;}
[data-testid="stMarkdownContainer"] .hero,
[data-testid="stMarkdownContainer"] .sub,
[data-testid="stMarkdownContainer"] .colhead,
[data-testid="stMarkdownContainer"] .winner,
[data-testid="stMarkdownContainer"] .result,
[data-testid="stMarkdownContainer"] .note {box-sizing:border-box; position:relative; height:auto;}
[data-testid="stMarkdownContainer"] .colhead {padding:2px 0 4px; line-height:1.5; min-height:23px;}
[data-testid="stMarkdownContainer"] .winner,
[data-testid="stMarkdownContainer"] .result {margin:0;}
[data-testid="stMarkdownContainer"] .note {margin:0; padding:3px 0;}
[data-testid="stMarkdownContainer"] .metric {line-height:1.5;}
[data-testid="stMarkdownContainer"] .metric strong {line-height:1.5;}
[data-testid="stMarkdownContainer"] .sub {line-height:1.5;}
[data-testid="stMarkdownContainer"] .hero + .sub {padding-top:3px;}
[data-testid="stHorizontalBlock"] {flex-wrap:nowrap !important; gap:0.35rem !important;}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {min-width:0 !important; width:unset !important; flex-shrink:1 !important;}
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {font-size:14px; padding-left:7px; padding-right:3px; min-height:36px;}
[data-testid="stNumberInput"] button {display:none;}
[data-testid="stPopover"] button {min-height:36px; padding:0.2rem 0.6rem;}
[data-testid="stTextInput"], [data-testid="stNumberInput"] {min-width:0;}
.hero {font-size:22px; font-weight:850; letter-spacing:-0.8px; line-height:1.25; padding-top:3px;}
.sub {font-size:11px; color:#607087; line-height:1.35;}
.colhead {font-size:11px; color:#607087; white-space:nowrap;}
.winner {background:#E7F5EF; color:#145C42; border:1px solid #BFE4D4; border-radius:12px; padding:8px 10px; font-size:14px; line-height:1.35; margin-top:4px;}
.result {background:white; border:1px solid #E1E7EF; border-radius:10px; padding:6px 9px; margin-top:4px;}
.result-top {display:flex; justify-content:space-between; gap:6px; font-size:12px; line-height:1.3;}
.choice-name {overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:55%; font-weight:700;}
.metrics {display:grid; grid-template-columns:1fr 1fr 1fr; gap:3px; margin-top:4px;}
.metric {font-size:10px; color:#617088; white-space:nowrap;}
.metric strong {display:block; font-size:12px; color:#18243B; font-weight:650; letter-spacing:-0.3px;}
.note {font-size:10px; color:#68758A; line-height:1.35; margin-top:5px;}
@media(max-width:370px) {.metric strong{font-size:10px;} .hero{font-size:20px;}}
</style>
""", unsafe_allow_html=True)

    title, settings = st.columns([3.4, 1.1], vertical_alignment="center")
    with title:
        st.markdown('<div class="hero">⚖️ 선택 한눈에</div><div class="sub">비용과 만족을 입력하면, 비교는 바로 아래에.</div>', unsafe_allow_html=True)
    with settings:
        with st.popover("⚙ 설정", use_container_width=True):
            st.markdown("**비교 설정**")
            count = st.selectbox("선택지 수", [2, 3, 4], index=0, key="choice_count")
            rate = int(st.number_input("만족도 1점의 금액 (원)", min_value=1, max_value=1_000_000_000, value=10000, step=1000, key="point_rate"))
            st.caption("모든 선택지에 같은 환산액을 적용합니다. 원 단위 정수로 계산합니다.")
            st.markdown("**QR로 공유**")
            app_url = st.text_input("배포된 앱 주소", placeholder="https://your-app.streamlit.app", key="share_url").strip()
            if app_url:
                parsed = urlparse(app_url)
                if parsed.scheme in ("https", "http") and parsed.hostname and not parsed.username and not parsed.password:
                    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4)
                    qr.add_data(app_url)
                    qr.make(fit=True)
                    buf = BytesIO()
                    qr.make_image(fill_color="#18243B", back_color="white").save(buf, format="PNG")
                    image = buf.getvalue()
                    st.image(image, width=180)
                    st.download_button("QR 이미지 다운로드", image, file_name="choice-app-qr.png", mime="image/png")
                    st.caption("QR은 앱 접속용입니다. 입력한 선택지는 QR에 포함되지 않습니다.")
                else:
                    st.warning("http:// 또는 https://로 시작하는 올바른 배포 주소를 입력하세요.")
            else:
                st.caption("GitHub에 두 파일을 올리고 Streamlit Community Cloud에서 app.py를 배포한 뒤, 공개 주소를 입력하세요.")

    a, b, c = st.columns([1.15, 1.35, 1])
    a.markdown('<div class="colhead">선택지</div>', unsafe_allow_html=True)
    b.markdown('<div class="colhead">명시적 비용 · 원</div>', unsafe_allow_html=True)
    c.markdown('<div class="colhead">만족 · 1~10</div>', unsafe_allow_html=True)
    choices = []
    for i in range(count):
        a, b, c = st.columns([1.15, 1.35, 1])
        with a:
            name = st.text_input(f"선택지 {i + 1} 이름", value=f"선택 {chr(65 + i)}", key=f"name_{i}", max_chars=20, label_visibility="collapsed")
        with b:
            cost = int(st.number_input(f"선택지 {i + 1} 비용 (원)", min_value=0, max_value=1_000_000_000, value=10000 + 5000 * i, step=1000, key=f"cost_{i}", label_visibility="collapsed"))
        with c:
            satisfaction = int(st.number_input(f"선택지 {i + 1} 만족도", min_value=1, max_value=10, value=min(7 + i, 10), step=1, key=f"satisfaction_{i}", label_visibility="collapsed"))
        choices.append({"name": name, "cost": cost, "satisfaction": satisfaction})

    rows = compare_choices(choices, rate)
    best = max(row["economic_profit"] for row in rows)
    winners = [row for row in rows if row["economic_profit"] == best]
    names = ", ".join(html.escape(row["name"]) for row in winners)
    title_text = "공동 추천" if len(winners) > 1 else "추천"
    st.markdown(f'<div class="winner"><b>{title_text} · {names}</b><div class="sub">만족도 1점 = {money(rate)} · 경제적 이윤 기준</div></div>', unsafe_allow_html=True)
    for row in rows:
        name = html.escape(row["name"])
        profit = row["economic_profit"]
        prefix = "+" if profit > 0 else ""
        mark = " ✓" if row["economic_profit"] == best else ""
        st.markdown(f'''<div class="result">
<div class="result-top"><span class="choice-name">{name}{mark}</span><span>이윤 {prefix}{money(profit)}</span></div>
<div class="metrics"><div class="metric">편익<strong>{money(row['benefit'])}</strong></div><div class="metric">암묵적 비용<strong>{money(row['implicit_cost'])}</strong></div><div class="metric">기회비용<strong>{money(row['opportunity_cost'])}</strong></div></div></div>''', unsafe_allow_html=True)

    st.markdown('<div class="note">요청한 합산식에서는 비용이 순편익에서 상쇄되어, 추천 순위는 만족도로 결정됩니다.</div>', unsafe_allow_html=True)
    with st.popover("ⓘ 계산 기준", use_container_width=True):
        st.markdown("""**하나만 선택하는 상호 배타적인 대안**을 비교합니다.

- 환산 만족 = 만족도 × 1점의 금액
- **편익 = 명시적 비용 + 환산 만족** (요청한 정의)
- 순편익 = 편익 − 명시적 비용 = 환산 만족
- **암묵적 비용 = 포기하는 다른 선택지 중 가장 큰 순편익**
- **기회비용 = 명시적 비용 + 암묵적 비용**
- 경제적 이윤 = 편익 − 기회비용

암묵적 비용은 나머지 대안의 합이 아니라 **최선 대안 하나**의 순편익입니다. 동점은 공동 추천합니다. 시간·위험·예산 제약은 별도로 고려하지 않습니다.

일반적인 비용 대비 만족 비교를 원한다면, 편익을 ‘환산 만족’만으로 정의하고 비용을 차감하는 방식이 더 적합합니다. 이 앱은 요청하신 합산식을 그대로 사용합니다.

**모바일 안내:** 기본 2개, 최대 4개를 압축 배치했습니다. 아주 작은 화면·가로 모드·확대 글꼴·키보드 표시 중에는 스크롤이 생길 수 있습니다. 설정과 설명은 현재 화면 위에 열립니다.

**배포:** GitHub 저장소 루트에 `app.py`, `requirements.txt` → Streamlit Community Cloud에서 해당 저장소와 `app.py` 선택 → 배포 주소를 설정에 입력 → QR 다운로드. GitHub 자체는 Python 앱 실행 서버가 아니므로 Streamlit 배포가 필요합니다.

입력값은 서버의 현재 Streamlit 세션에서 처리되며, 앱에서 별도 파일이나 데이터베이스로 저장하지 않습니다. 새 접속 시 기본값으로 시작합니다.
""")


if __name__ == "__main__":
    main()
