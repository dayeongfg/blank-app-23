#######################
# Import libraries
import streamlit as st#######################
# Import libraries
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

#######################
# Page configuration
st.set_page_config(
    page_title="US Population Dashboard",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded")

alt.themes.enable("default")

#######################
# CSS styling
st.markdown("""
<style>

[data-testid="block-container"] {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 1rem;
    padding-bottom: 0rem;
    margin-bottom: -7rem;
}

[data-testid="stVerticalBlock"] {
    padding-left: 0rem;
    padding-right: 0rem;
}

[data-testid="stMetric"] {
    background-color: #393939;
    text-align: center;
    padding: 15px 0;
}

[data-testid="stMetricLabel"] {
  display: flex;
  justify-content: center;
  align-items: center;
}

[data-testid="stMetricDeltaIcon-Up"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

[data-testid="stMetricDeltaIcon-Down"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

</style>
""", unsafe_allow_html=True)


#######################
# Load data
df_reshaped = pd.read_csv('titanic.csv') ## 분석 데이터 넣기


#######################
#######################
# Sidebar
with st.sidebar:
    st.header("Titanic 분석 필터")
    st.caption("좌측 필터를 바꾸면 모든 지표/차트가 동기화됩니다.")

    # -----------------------------
    # 유틸 & 안전장치
    def has(col: str) -> bool:
        return col in df_reshaped.columns

    df = df_reshaped.copy()

    # -----------------------------
    # 시각화 테마
    theme = st.selectbox(
        "색상 테마",
        ["블루", "그린", "퍼플", "오렌지", "그레이"],
        index=0
    )

    # -----------------------------
    # 범주형 필터
    pclass_options = sorted(df["Pclass"].dropna().unique().tolist()) if has("Pclass") else []
    pclass_sel = st.multiselect(
        "객실 등급 (Pclass)",
        options=pclass_options,
        default=pclass_options
    )

    if has("Sex"):
        sex_vals = set(df["Sex"].dropna().astype(str).str.lower().unique().tolist())
        sex_options = ["전체"]
        if "male" in sex_vals:
            sex_options.append("male")
        if "female" in sex_vals:
            sex_options.append("female")
    else:
        sex_options = ["전체"]
    sex_sel = st.radio("성별 (Sex)", options=sex_options, index=0, horizontal=True)

    embarked_options = sorted(df["Embarked"].dropna().unique().tolist()) if has("Embarked") else []
    embarked_sel = st.multiselect(
        "승선 항구 (Embarked)",
        options=embarked_options,
        default=embarked_options
    )

    # -----------------------------
    # 연속형 필터
    # 나이 결측 처리 옵션
    age_strategy_options = ["제외", "전체 중앙값 대치"]
    if has("Pclass"):
        age_strategy_options.append("등급별(Pclass) 중앙값 대치")
    age_strategy = st.selectbox(
        "나이 결측 처리",
        options=age_strategy_options,
        index=1 if has("Age") else 0
    )

    if has("Age"):
        age_series = df["Age"].dropna()
        age_max = float(age_series.max()) if not age_series.empty else 80.0
        age_upper = float(max(80.0, age_max))
        age_range = st.slider(
            "나이 구간 (Age)",
            min_value=0.0,
            max_value=age_upper,
            value=(0.0, age_upper)
        )
    else:
        age_range = (0.0, 999.0)

    # 운임 필터 + 극단값 처리
    winsor = st.checkbox("운임(Fare) 상하위 1% 윈저라이즈", value=True)
    if has("Fare"):
        fare_series = df["Fare"].dropna()
        fare_min = float(fare_series.min()) if not fare_series.empty else 0.0
        fare_max = float(fare_series.max()) if not fare_series.empty else 100.0
        fare_min = float(max(0.0, fare_min))
        fare_range = st.slider(
            "운임 구간 (Fare)",
            min_value=fare_min,
            max_value=fare_max,
            value=(fare_min, fare_max)
        )
    else:
        fare_range = (0.0, 1e9)

    # 가족/동반
    family_size_enable = has("SibSp") and has("Parch")
    if family_size_enable:
        family_size_series = df["SibSp"].fillna(0) + df["Parch"].fillna(0) + 1
        fs_min = int(family_size_series.min())
        fs_max = int(family_size_series.max())
        fs_range = st.slider(
            "가족 규모 (FamilySize = SibSp + Parch + 1)",
            min_value=fs_min,
            max_value=fs_max,
            value=(fs_min, fs_max)
        )
    else:
        fs_range = (0, 999)

    # Cabin 유무 필터
    if has("Cabin"):
        cabin_opt = st.radio("Cabin 정보", options=["전체", "있음", "없음"], index=0, horizontal=True)
    else:
        cabin_opt = "전체"

    st.markdown("---")

    # -----------------------------
    # 필터 초기화
    if st.button("필터 초기화"):
        for k in ["filters", "df_filtered"]:
            if k in st.session_state:
                del st.session_state[k]
        st.experimental_rerun()

    # -----------------------------
    # 전처리 & 필터링 파이프라인
    # 1) 결측 처리: Age
    if has("Age"):
        if age_strategy == "제외":
            df = df[df["Age"].notna()]
        elif age_strategy == "전체 중앙값 대치":
            df.loc[:, "Age"] = df["Age"].fillna(df["Age"].median())
        elif age_strategy == "등급별(Pclass) 중앙값 대치" and has("Pclass"):
            df.loc[:, "Age"] = df.groupby("Pclass")["Age"].transform(lambda s: s.fillna(s.median()))

    # 2) 파생: FamilySize
    if family_size_enable:
        df.loc[:, "FamilySize"] = df["SibSp"].fillna(0) + df["Parch"].fillna(0) + 1

    # 3) Winsorize Fare
    if has("Fare") and winsor and df["Fare"].notna().any():
        lo = float(df["Fare"].quantile(0.01))
        hi = float(df["Fare"].quantile(0.99))
        df.loc[:, "Fare"] = df["Fare"].clip(lower=lo, upper=hi)

    # 4) 실제 필터 적용
    if has("Pclass") and pclass_sel:
        df = df[df["Pclass"].isin(pclass_sel)]
    if has("Sex") and sex_sel != "전체":
        df = df[df["Sex"].astype(str).str.lower() == sex_sel]
    if has("Embarked") and embarked_sel:
        df = df[df["Embarked"].isin(embarked_sel)]
    if has("Age"):
        df = df[(df["Age"] >= age_range[0]) & (df["Age"] <= age_range[1])]
    if has("Fare"):
        df = df[(df["Fare"] >= fare_range[0]) & (df["Fare"] <= fare_range[1])]
    if family_size_enable:
        df = df[(df["FamilySize"] >= fs_range[0]) & (df["FamilySize"] <= fs_range[1])]
    if has("Cabin") and cabin_opt != "전체":
        if cabin_opt == "있음":
            df = df[df["Cabin"].notna()]
        else:
            df = df[df["Cabin"].isna()]

    # -----------------------------
    # 세션 상태 저장 및 요약
    st.session_state["filters"] = {
        "theme": theme,
        "pclass": pclass_sel,
        "sex": sex_sel,
        "embarked": embarked_sel,
        "age_strategy": age_strategy,
        "age_range": age_range,
        "winsor": winsor,
        "fare_range": fare_range,
        "family_size_range": fs_range,
        "cabin_opt": cabin_opt,
    }
    st.session_state["df_filtered"] = df

    st.subheader("요약")
    st.metric("선택된 레코드 수", f"{len(df):,}")

#######################
# Plots




# #######################
# # Dashboard Main Panel
col = st.columns((1.5, 4.5, 2), gap='medium')



#######################
# Dashboard Main Panel - Column 1


with col[0]:
    st.subheader("요약 지표")

    df_filtered = st.session_state.get("df_filtered", df_reshaped)

    if len(df_filtered) == 0:
        st.warning("선택된 조건에 맞는 데이터가 없습니다.")
    else:
        total_passengers = len(df_filtered)
        survival_rate = df_filtered["Survived"].mean() * 100 if "Survived" in df_filtered else None
        avg_age = df_filtered["Age"].mean() if "Age" in df_filtered else None
        avg_fare = df_filtered["Fare"].mean() if "Fare" in df_filtered else None
        avg_family = df_filtered["FamilySize"].mean() if "FamilySize" in df_filtered else None

        # KPI metrics
        st.metric("총 탑승객 수", f"{total_passengers:,}")

        if survival_rate is not None:
            st.metric("생존율", f"{survival_rate:.1f}%")

        if avg_age is not None:
            st.metric("평균 나이", f"{avg_age:.1f}")

        if avg_fare is not None:
            st.metric("평균 운임", f"{avg_fare:.2f}")

        if avg_family is not None:
            st.metric("평균 가족 규모", f"{avg_family:.1f}")

        st.markdown("---")

        # 성별/등급 분포 요약
        if "Sex" in df_filtered:
            sex_counts = df_filtered["Sex"].value_counts(normalize=True) * 100
            st.caption("성별 분포 (%)")
            for sex, val in sex_counts.items():
                st.progress(val/100, text=f"{sex}: {val:.1f}%")

        if "Pclass" in df_filtered:
            pclass_counts = df_filtered["Pclass"].value_counts(normalize=True) * 100
            st.caption("객실 등급 분포 (%)")
            for cls, val in pclass_counts.items():
                st.progress(val/100, text=f"Pclass {cls}: {val:.1f}%")



# with col[1]:
#######################
# Dashboard Main Panel - Column 2

with col[1]:
    st.subheader("탑승객 특성별 생존 패턴")

    df_filtered = st.session_state.get("df_filtered", df_reshaped)

    if len(df_filtered) == 0:
        st.warning("선택된 조건에 맞는 데이터가 없습니다.")
    else:
        # -----------------------------
        # Age 분포 + 생존 여부
        if "Age" in df_filtered and "Survived" in df_filtered:
            st.markdown("**나이 분포와 생존 여부**")

            age_chart = alt.Chart(df_filtered).mark_bar().encode(
                alt.X("Age:Q", bin=alt.Bin(maxbins=20), title="나이(Age)"),
                alt.Y("count():Q", title="탑승객 수"),
                alt.Color("Survived:N",
                          scale=alt.Scale(domain=[0, 1],
                                          range=["#d62728", "#1f77b4"]),
                          title="생존 여부"),
                tooltip=["count()"]
            ).properties(
                width="container",
                height=300
            )
            st.altair_chart(age_chart, use_container_width=True)

        st.markdown("---")

        # -----------------------------
        # Age × Fare 히트맵 (생존율)
        if "Age" in df_filtered and "Fare" in df_filtered and "Survived" in df_filtered:
            st.markdown("**나이 × 운임 구간별 평균 생존율**")

            # Age, Fare를 구간화
            df_bins = df_filtered.copy()
            df_bins["AgeBin"] = pd.cut(df_bins["Age"], bins=10)
            df_bins["FareBin"] = pd.cut(df_bins["Fare"], bins=10)

            survival_pivot = (
                df_bins.groupby(["AgeBin", "FareBin"])["Survived"]
                .mean()
                .reset_index()
                .dropna()
            )

            heatmap = alt.Chart(survival_pivot).mark_rect().encode(
                alt.X("AgeBin:N", title="나이 구간"),
                alt.Y("FareBin:N", title="운임 구간"),
                alt.Color("Survived:Q",
                          scale=alt.Scale(scheme="blues"),
                          title="평균 생존율"),
                tooltip=["Survived:Q"]
            ).properties(
                width="container",
                height=400
            )
            st.altair_chart(heatmap, use_container_width=True)



# with col[2]:

#######################
# Dashboard Main Panel - Column 3
with col[2]:
    st.subheader("상세 분석 · 순위 · About")

    df_filtered = st.session_state.get("df_filtered", df_reshaped)

    if len(df_filtered) == 0:
        st.warning("선택된 조건에 맞는 데이터가 없습니다.")
    else:
        # -----------------------------
        # Top 그룹 순위 (생존율 기준)
        st.markdown("### Top 그룹 순위 (생존율)")

        grp_options = []
        if {"Pclass", "Sex"}.issubset(df_filtered.columns):
            grp_options.append("Pclass × Sex")
        if "Embarked" in df_filtered.columns:
            grp_options.append("Embarked")
        if "Pclass" in df_filtered.columns:
            grp_options.append("Pclass")
        if "Sex" in df_filtered.columns:
            grp_options.append("Sex")

        if "Survived" not in df_filtered.columns or len(grp_options) == 0:
            st.info("랭킹을 만들기 위한 컬럼(Survived, Pclass/Sex/Embarked)이 부족합니다.")
        else:
            sel_group = st.selectbox("그룹 선택", options=grp_options, index=0)
            top_n = st.slider("Top N", min_value=3, max_value=15, value=5, step=1)

            # 그룹 키 구성
            if sel_group == "Pclass × Sex":
                group_keys = ["Pclass", "Sex"]
            else:
                group_keys = [sel_group]

            agg = (
                df_filtered.groupby(group_keys)
                .agg(생존율=("Survived", "mean"), 표본수=("Survived", "size"))
                .reset_index()
            )
            # 퍼센트 컬럼 별도로 생성 (Altair 인코딩 안전)
            agg["생존율_pct"] = (agg["생존율"] * 100).round(1)

            # 그룹 라벨 문자열 컬럼 생성 (repeat 대신 y축에 바로 사용)
            agg["그룹"] = agg[group_keys].astype(str).agg(" - ".join, axis=1)

            agg = agg.sort_values(["생존율_pct", "표본수"], ascending=[False, False]).head(top_n)

            # 막대 + 텍스트 라벨 (repeat 없이 layer 가능)
            bars = alt.Chart(agg).mark_bar().encode(
                x=alt.X("생존율_pct:Q", title="생존율(%)"),
                y=alt.Y("그룹:N", sort="-x", title="그룹"),
                tooltip=["그룹", "생존율_pct", "표본수"]
            ).properties(
                width="container",
                height=220 + 18 * len(agg)
            )

            labels = alt.Chart(agg).mark_text(align="left", baseline="middle", dx=3).encode(
                x="생존율_pct:Q",
                y=alt.Y("그룹:N", sort="-x"),
                text="생존율_pct:Q"
            )

            st.altair_chart(bars + labels, use_container_width=True)
            st.dataframe(agg[["그룹", "생존율_pct", "표본수"]], use_container_width=True)

        st.markdown("---")

        # -----------------------------
        # 피벗 요약 테이블 (생존율, 표본수)
        st.markdown("### 피벗 요약 테이블")
        pivot_row_candidates = [c for c in ["Pclass", "Sex", "Embarked"] if c in df_filtered.columns]
        if "Survived" not in df_filtered.columns or len(pivot_row_candidates) == 0:
            st.info("피벗을 만들기 위한 컬럼(Survived, Pclass/Sex/Embarked)이 부족합니다.")
        else:
            row_key = st.selectbox("행 (Row)", options=pivot_row_candidates, index=0)
            col_candidates = [c for c in pivot_row_candidates if c != row_key]
            col_key = st.selectbox("열 (Column)", options=["(없음)"] + col_candidates, index=0)

            df_piv = df_filtered.copy()
            if col_key == "(없음)":
                surv_tbl = df_piv.groupby(row_key)["Survived"].agg(["mean", "size"]).reset_index()
                surv_tbl.rename(columns={"mean": "생존율", "size": "표본수"}, inplace=True)
                surv_tbl["생존율(%)"] = (surv_tbl["생존율"] * 100).round(1)
                surv_tbl = surv_tbl[[row_key, "생존율(%)", "표본수"]]
                st.caption("생존율(%) · 표본수")
                st.dataframe(surv_tbl, use_container_width=True)
            else:
                surv_pivot = pd.pivot_table(
                    df_piv, values="Survived", index=row_key, columns=col_key, aggfunc="mean"
                ) * 100
                surv_pivot = surv_pivot.round(1)
                count_pivot = pd.pivot_table(
                    df_piv, values="Survived", index=row_key, columns=col_key, aggfunc="size"
                ).astype(int)
                st.caption("생존율(%)")
                st.dataframe(surv_pivot, use_container_width=True)
                st.caption("표본수")
                st.dataframe(count_pivot, use_container_width=True)

        st.markdown("---")

        # -----------------------------
        # 상세 테이블 & 다운로드
        st.markdown("### 상세 데이터 & 다운로드")
        show_cols = [c for c in ["Name", "Ticket", "Pclass", "Sex", "Age", "Fare", "Survived", "Embarked", "FamilySize", "Cabin"] if c in df_filtered.columns]
        st.dataframe(df_filtered[show_cols].head(500), use_container_width=True)

        csv_bytes = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="현재 필터 적용 데이터 다운로드 (CSV)",
            data=csv_bytes,
            file_name="titanic_filtered.csv",
            mime="text/csv",
            use_container_width=True
        )

        st.markdown("---")

        # -----------------------------
        # About 섹션
        st.markdown("### About")
        st.write(
            "- **Dataset**: Titanic survival dataset\n"
            "- **주요 파생/처리**: FamilySize = SibSp + Parch + 1, Fare 윈저라이즈(옵션), Age 결측치 대치 옵션\n"
            "- **해석 유의**: 표본 수가 적은 그룹의 생존율은 변동성이 큽니다. 결측/극단값 처리 옵션에 따라 결과가 달라질 수 있습니다."
        )
