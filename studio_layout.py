"""Presentation only: historical calculations and live quotes stay separate."""
def apply_studio_layout(st, production=False):
    st.markdown("""
    <style>
    .stApp {background:#0e191e;color:#dce5e7}
    [data-testid="stHeader"] {background:#0e191e}
    [data-testid="stSidebar"] {background:#152228;border-right:1px solid #2c3b40}
    [data-testid="stSidebar"]>div {padding-top:1.5rem}
    .block-container {max-width:1480px;padding-top:2rem}
    h1,h2,h3 {color:#e8edef!important;letter-spacing:.025em}
    h1 {font-size:2.1rem!important}
    [data-testid="stCaptionContainer"] {color:#9baeb3}
    [data-testid="stExpander"] {background:#152228;border:1px solid #2c3b40;border-radius:12px}
    [data-testid="stBaseButton-primary"] {background:#d6ad62;color:#111c21;border-color:#d6ad62;font-weight:700}
    [data-testid="stBaseButton-primary"]:hover {background:#e7c17a;color:#111c21;border-color:#e7c17a}
    [data-testid="stMetric"] {padding:1rem;background:#17262d;border:1px solid #2c3b40;border-radius:10px}
    /* Keep complete prices readable inside narrow metric cards. */
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
        white-space:normal!important;overflow:visible!important;
        text-overflow:clip!important;overflow-wrap:anywhere;
        font-size:clamp(1.25rem,2.4vw,2.25rem)!important;line-height:1.3
    }
    [data-testid="stMetricLabel"] {white-space:normal;overflow-wrap:anywhere}
    .studio-brand {color:#d6ad62;font-size:.85rem;letter-spacing:.15em;margin-bottom:.6rem}
    @media(max-width:640px) {.block-container{padding:1rem}h1{font-size:1.65rem!important}}
    </style>
    """, unsafe_allow_html=True)
    edition = "正式版 V1.0.5" if production else "候選測試版"
    st.markdown(f'<div class="studio-brand">亞當鏡像 · 台股走勢分析工作室｜{edition}</div>', unsafe_allow_html=True)
    st.sidebar.markdown("### 個股查詢與圖表")
    st.sidebar.caption("輸入股票 → 選擇週期 → 開始分析。手機請展開左上角側欄。")
