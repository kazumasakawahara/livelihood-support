"""
生活保護受給者尊厳支援データベース - ケース記録アーカイブ
Manifesto: Livelihood Protection Support & Dignity Graph 準拠

Version: 1.0
- マニフェスト「6本柱」に基づくデータモデル
- 二次被害防止を最優先とした設計
- ケース記録から本人像を構築するプロセス支援
"""

import streamlit as st
import json
from datetime import date

# --- ライブラリからインポート ---
from lib.db_connection import run_query
from lib.db_operations import register_to_database
from lib.db_queries import (
    get_recipients_list, get_recipient_stats,
    get_recipient_profile, get_handover_summary
)
from lib.ai_extractor import extract_from_text, detect_critical_expressions, validate_extracted_data
from lib.utils import (
    safe_date_parse, init_session_state, reset_session_state,
    get_input_example, get_risk_emoji, format_mental_health_warning
)
from lib.file_readers import read_uploaded_file, get_supported_extensions, check_dependencies
from lib.auth import (
    require_authentication,
    render_user_info,
    get_current_user,
    has_role,
    is_auth_disabled,
)

# --- 初期設定 ---
st.set_page_config(
    page_title="生活保護尊厳支援DB", 
    layout="wide",
    page_icon="📋",
    initial_sidebar_state="expanded"
)

init_session_state()

# =============================================================================
# 認証チェック
# 環境変数 SKIP_AUTH=true で認証をスキップ可能（開発環境用）
# =============================================================================

if not require_authentication():
    st.stop()

# 認証済みユーザー情報を取得
current_user = get_current_user()
if current_user:
    # 認証ユーザー名をcaseworker_nameとして設定
    st.session_state.caseworker_name = current_user.get('name') or current_user.get('username') or 'system'

# ロールベースアクセス制御: ケース記録入力には適切なロールが必要
ALLOWED_ROLES = ['caseworker', 'supervisor', 'admin']
user_roles = current_user.get('roles', []) if current_user else []
has_access = any(role in user_roles for role in ALLOWED_ROLES)

if not has_access:
    st.error("⚠️ アクセス権限がありません。")
    st.info("ケース記録の入力には **caseworker**、**supervisor**、または **admin** ロールが必要です。")
    st.write(f"現在のロール: {', '.join(user_roles) if user_roles else 'なし'}")
    st.stop()

# =============================================================================
# サイドバー
# =============================================================================

with st.sidebar:
    st.header("📋 生活保護尊厳支援DB")
    st.caption("ケース記録アーカイブ v1.0")

    st.divider()

    # 認証ユーザー情報表示
    if is_auth_disabled():
        # 開発モード: シンプル表示
        st.write(f"👤 ログイン中: **{current_user.get('name')}**")
        st.caption("（開発モード - SKIP_AUTH=true）")
    else:
        # 本番モード: Keycloak連携
        render_user_info()

    st.divider()
    
    # 現在のステップ表示
    steps = {
        'input': '1️⃣ データ入力',
        'edit': '2️⃣ 確認・修正',
        'confirm': '3️⃣ 最終確認',
        'done': '✅ 完了'
    }
    
    st.subheader("📍 現在のステップ")
    for key, label in steps.items():
        if key == st.session_state.step:
            st.markdown(
                f'<div style="background-color: #1E3A5F; padding: 8px 12px; border-radius: 8px; '
                f'border-left: 4px solid #4DA6FF; margin: 4px 0;">'
                f'<strong style="color: #4DA6FF;">→ {label}</strong></div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"<span style='color: #888;'>　{label}</span>", unsafe_allow_html=True)
    
    st.divider()
    
    # 統計表示
    st.subheader("📊 登録状況")
    try:
        stats = get_recipient_stats()
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="👤 受給者数", value=stats['recipient_count'])
        with col2:
            st.metric(label="🏥 精神疾患", value=stats['mental_health_count'])
        
        if stats['ng_by_recipient']:
            st.markdown("**⚠️ 避けるべき関わり方**")
            for row in stats['ng_by_recipient']:
                if row['ng_count'] > 0:
                    st.markdown(f"　・{row['name']}: **{row['ng_count']}件**")
    except:
        st.error("DB接続エラー")
    
    st.divider()
    
    # リセットボタン
    if st.button("🔄 最初からやり直す", use_container_width=True):
        reset_session_state()
        st.rerun()

# =============================================================================
# Step 1: データ入力
# =============================================================================

def render_input_step():
    st.title("📋 ケース記録を入力")
    
    # マニフェストに基づく説明
    st.markdown("""
    **ケース記録・家庭訪問記録・面談メモ**などを入力してください。  
    AIが自動的に以下の情報を抽出・構造化します：
    
    - 🚫 **避けるべき関わり方** - 本人を傷つける可能性のある対応
    - ✅ **効果的だった関わり方** - 良い反応があった対応
    - 💪 **発見された強み** - 課題より先に強みを抽出
    - 🏥 **精神疾患の状況** - 治療状況と注意点
    """)
    
    # 既存受給者選択
    existing_recipients = get_recipients_list()
    append_mode = st.checkbox("既存受給者に追記する")
    selected_recipient = None
    
    if append_mode and existing_recipients:
        selected_recipient = st.selectbox("受給者を選択", existing_recipients)
        
        # 選択した受給者の警告情報を表示
        if selected_recipient:
            profile = get_recipient_profile(selected_recipient)
            if profile.get('mental_health'):
                mh = profile['mental_health']
                st.warning(format_mental_health_warning(mh['diagnosis']))
            if profile.get('ng_approaches'):
                with st.expander("⚠️ この方の避けるべき関わり方を確認", expanded=False):
                    for ng in profile['ng_approaches']:
                        st.markdown(f"- {get_risk_emoji(ng['riskLevel'])} **{ng['description']}**")
                        if ng['reason']:
                            st.markdown(f"  - 理由: {ng['reason']}")
    
    # 入力方式の選択
    st.subheader("📝 入力方式を選択")
    input_method = st.radio(
        "入力方式",
        ["✍️ テキスト入力", "📁 ファイルアップロード"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    input_text = ""
    
    # --- テキスト入力 ---
    if input_method == "✍️ テキスト入力":
        with st.expander("💡 入力例を見る"):
            st.code(get_input_example(), language=None)
        
        input_text = st.text_area(
            "ここにケース記録を入力してください",
            height=400,
            value=st.session_state.narrative_text,
            placeholder="訪問記録、面談メモ、本人の発言などを自由に記述..."
        )
        st.session_state.narrative_text = input_text
        
        # 批判的表現の検出
        if input_text:
            critical_expressions = detect_critical_expressions(input_text)
            if critical_expressions:
                st.warning("⚠️ 以下の表現は変換が推奨されます：")
                for ce in critical_expressions:
                    st.markdown(f"- 「{ce['original']}」→「{ce['suggested']}」")
    
    # --- ファイルアップロード ---
    else:
        extensions = get_supported_extensions()
        ext_list = ', '.join([f"{v}({k})" for k, v in extensions.items()])
        st.info(f"📂 対応形式: {ext_list}")
        
        deps = check_dependencies()
        missing = [k for k, v in deps.items() if not v]
        if missing:
            st.warning(f"⚠️ 一部のライブラリがインストールされていません: {', '.join(missing)}")
        
        uploaded_file = st.file_uploader(
            "ファイルをアップロード",
            type=['docx', 'xlsx', 'pdf', 'txt'],
            help="Word、Excel、PDF、テキストファイルに対応"
        )
        
        if uploaded_file:
            with st.spinner(f"📄 {uploaded_file.name} を読み込み中..."):
                try:
                    input_text = read_uploaded_file(uploaded_file)
                    st.session_state.uploaded_file_text = input_text
                    st.success(f"✅ {uploaded_file.name} を読み込みました（{len(input_text):,}文字）")
                    
                    with st.expander("📄 抽出されたテキストを確認", expanded=False):
                        st.text_area("抽出内容", value=input_text, height=300, disabled=True)
                except Exception as e:
                    st.error(f"❌ 読み込みエラー: {e}")
        else:
            input_text = st.session_state.uploaded_file_text
    
    # AI構造化ボタン
    st.divider()
    
    if st.button("🧠 AIで構造化する", type="primary", use_container_width=True, disabled=not input_text):
        with st.spinner("テキストを分析中...（二次被害防止の観点で抽出しています）"):
            extracted = extract_from_text(input_text, selected_recipient)
            
            if extracted:
                # 検証
                is_valid, errors = validate_extracted_data(extracted)
                
                st.session_state.extracted_data = extracted
                st.session_state.edited_data = json.loads(json.dumps(extracted))
                
                if errors:
                    for e in errors:
                        if e.startswith("⚠️"):
                            st.warning(e)
                        else:
                            st.error(e)
                
                st.session_state.step = 'edit'
                st.rerun()
            else:
                st.error("データの抽出に失敗しました。もう一度お試しください。")

# =============================================================================
# Step 2: 確認・修正
# =============================================================================

def render_edit_step():
    st.title("✏️ 抽出データの確認・修正")
    
    # マニフェストに基づく警告
    st.markdown("""
    **AIが抽出した内容を確認してください。**  
    特に以下の項目は支援者交代時の引き継ぎに重要です：
    - ⚠️ **避けるべき関わり方** - 二次被害防止の要
    - ✅ **効果的だった関わり方** - 成功体験の継承
    - 💪 **強み** - 課題だけでなく良い面も
    """)
    
    if not st.session_state.edited_data:
        st.error("データがありません")
        return
    
    data = st.session_state.edited_data
    
    # 精神疾患がある場合の警告
    mental_health = data.get('mentalHealthStatus', {})
    if mental_health.get('diagnosis'):
        st.error(f"⚠️ 精神疾患（{mental_health['diagnosis']}）の登録があります。避けるべき関わり方を必ず確認してください。")
    
    # タブで6本柱を表示
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "⚠️ 関わり方", "📋 ケース記録", "💪 本人像", 
        "📝 申告歴", "🤝 ネットワーク", "📜 法的基盤"
    ])
    
    # --- 第3の柱: 関わり方の知恵（最重要タブ） ---
    with tab1:
        st.subheader("🚫 避けるべき関わり方（NgApproach）")
        st.error("⚠️ **最重要**: 本人を傷つける可能性のある対応です。必ず確認してください。")
        
        ng_approaches = data.get('ngApproaches', [])
        
        for i, ng in enumerate(ng_approaches):
            with st.expander(f"禁忌 {i+1}: {ng.get('description', '未入力')[:40]}...", expanded=True):
                ng['description'] = st.text_area(
                    "避けるべき関わり方 *", 
                    value=ng.get('description', ''), 
                    key=f"ng_desc_{i}",
                    help="この対応をすると本人が傷つく可能性があります"
                )
                ng['reason'] = st.text_area(
                    "理由（なぜ避けるべきか）*", 
                    value=ng.get('reason', ''), 
                    key=f"ng_reason_{i}"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    risk_options = ["High", "Medium", "Low"]
                    current_risk = ng.get('riskLevel', 'Medium')
                    if current_risk not in risk_options:
                        current_risk = 'Medium'
                    ng['riskLevel'] = st.selectbox(
                        "リスクレベル",
                        risk_options,
                        index=risk_options.index(current_risk),
                        key=f"ng_risk_{i}",
                        format_func=lambda x: {"High": "🔴 High（症状悪化リスク大）", 
                                               "Medium": "🟠 Medium（注意必要）", 
                                               "Low": "🟡 Low（配慮推奨）"}.get(x, x)
                    )
                with col2:
                    ng['consequence'] = st.text_input(
                        "実際に起きた結果（あれば）",
                        value=ng.get('consequence', ''),
                        key=f"ng_consequence_{i}"
                    )
        
        if st.button("➕ 避けるべき関わり方を追加", key="add_ng"):
            data.setdefault('ngApproaches', []).append({
                'description': '', 'reason': '', 'riskLevel': 'Medium', 'consequence': ''
            })
            st.rerun()
        
        st.divider()
        
        st.subheader("✅ 効果的だった関わり方（EffectiveApproach）")
        effective = data.get('effectiveApproaches', [])
        
        for i, ea in enumerate(effective):
            with st.expander(f"効果的 {i+1}: {ea.get('description', '未入力')[:40]}...", expanded=True):
                ea['description'] = st.text_area(
                    "効果があった関わり方 *",
                    value=ea.get('description', ''),
                    key=f"ea_desc_{i}"
                )
                ea['context'] = st.text_input(
                    "どんな状況で効果的だったか",
                    value=ea.get('context', ''),
                    key=f"ea_context_{i}"
                )
        
        if st.button("➕ 効果的だった関わり方を追加", key="add_ea"):
            data.setdefault('effectiveApproaches', []).append({
                'description': '', 'context': '', 'frequency': ''
            })
            st.rerun()
        
        st.divider()
        
        st.subheader("⚡ 注意が必要な状況（TriggerSituation）")
        triggers = data.get('triggerSituations', [])
        
        for i, ts in enumerate(triggers):
            with st.expander(f"トリガー {i+1}: {ts.get('description', '未入力')[:40]}...", expanded=True):
                ts['description'] = st.text_input(
                    "状況",
                    value=ts.get('description', ''),
                    key=f"ts_desc_{i}"
                )
                ts['recommendedResponse'] = st.text_area(
                    "推奨される対応",
                    value=ts.get('recommendedResponse', ''),
                    key=f"ts_response_{i}"
                )
        
        if st.button("➕ 注意状況を追加", key="add_ts"):
            data.setdefault('triggerSituations', []).append({
                'description': '', 'signs': [], 'recommendedResponse': ''
            })
            st.rerun()
    
    # --- 第1の柱: ケース記録 ---
    with tab2:
        st.subheader("📋 ケース記録")
        
        records = data.get('caseRecords', [])
        
        for i, cr in enumerate(records):
            with st.expander(f"記録 {i+1}: {cr.get('date', '日付不明')} - {cr.get('category', '')}", expanded=True):
                col1, col2 = st.columns([1, 2])
                with col1:
                    cr_date = safe_date_parse(cr.get('date')) or date.today()
                    cr['date'] = st.date_input(
                        "記録日",
                        value=cr_date,
                        key=f"cr_date_{i}"
                    ).isoformat()
                    
                    cat_options = ["訪問", "電話", "来所", "相談", "同行", "会議", "その他"]
                    current_cat = cr.get('category', 'その他')
                    if current_cat not in cat_options:
                        cat_options.append(current_cat)
                    cr['category'] = st.selectbox(
                        "カテゴリ",
                        cat_options,
                        index=cat_options.index(current_cat),
                        key=f"cr_cat_{i}"
                    )
                
                with col2:
                    cr['caseworker'] = st.text_input(
                        "記録者",
                        value=cr.get('caseworker', st.session_state.caseworker_name),
                        key=f"cr_cw_{i}"
                    )
                
                cr['content'] = st.text_area(
                    "記録内容",
                    value=cr.get('content', ''),
                    key=f"cr_content_{i}",
                    height=150
                )
                
                cr['recipientResponse'] = st.text_area(
                    "本人の反応・様子",
                    value=cr.get('recipientResponse', ''),
                    key=f"cr_response_{i}",
                    help="表情、態度、発言などを記録"
                )
        
        if st.button("➕ ケース記録を追加", key="add_cr"):
            data.setdefault('caseRecords', []).append({
                'date': date.today().isoformat(),
                'category': 'その他',
                'content': '',
                'caseworker': st.session_state.caseworker_name,
                'recipientResponse': '',
                'observations': []
            })
            st.rerun()
    
    # --- 第2の柱: 抽出された本人像 ---
    with tab3:
        st.subheader("💪 発見された強み")
        st.success("💡 課題だけでなく、本人の良い面も記録しましょう")
        
        strengths = data.get('strengths', [])
        
        for i, s in enumerate(strengths):
            with st.expander(f"強み {i+1}: {s.get('description', '未入力')[:40]}...", expanded=True):
                s['description'] = st.text_input(
                    "強み *",
                    value=s.get('description', ''),
                    key=f"s_desc_{i}"
                )
                s['context'] = st.text_input(
                    "どんな場面で発揮されたか",
                    value=s.get('context', ''),
                    key=f"s_context_{i}"
                )
        
        if st.button("➕ 強みを追加", key="add_strength"):
            data.setdefault('strengths', []).append({
                'description': '', 'context': '', 'discoveredDate': date.today().isoformat()
            })
            st.rerun()
        
        st.divider()
        
        st.subheader("🏥 精神疾患の状況")
        
        mh = data.get('mentalHealthStatus', {})
        
        mh['diagnosis'] = st.text_input(
            "診断名",
            value=mh.get('diagnosis', ''),
            key="mh_diagnosis",
            placeholder="例: うつ病、統合失調症、双極性障害"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            status_options = ["安定", "不安定", "改善傾向", "悪化傾向", "不明"]
            current_status = mh.get('currentStatus', '不明')
            if current_status not in status_options:
                status_options.append(current_status)
            mh['currentStatus'] = st.selectbox(
                "現在の状態",
                status_options,
                index=status_options.index(current_status),
                key="mh_status"
            )
        with col2:
            treatment_options = ["通院中", "入院中", "治療中断", "未受診", "不明"]
            current_treatment = mh.get('treatmentStatus', '不明')
            if current_treatment not in treatment_options:
                treatment_options.append(current_treatment)
            mh['treatmentStatus'] = st.selectbox(
                "治療状況",
                treatment_options,
                index=treatment_options.index(current_treatment),
                key="mh_treatment"
            )
        
        data['mentalHealthStatus'] = mh
        
        st.divider()
        
        st.subheader("📊 課題")
        challenges = data.get('challenges', [])
        
        for i, ch in enumerate(challenges):
            with st.expander(f"課題 {i+1}: {ch.get('description', '未入力')[:40]}...", expanded=True):
                ch['description'] = st.text_input(
                    "課題",
                    value=ch.get('description', ''),
                    key=f"ch_desc_{i}"
                )
                col1, col2 = st.columns(2)
                with col1:
                    sev_options = ["High", "Medium", "Low"]
                    current_sev = ch.get('severity', 'Medium')
                    ch['severity'] = st.selectbox(
                        "深刻度",
                        sev_options,
                        index=sev_options.index(current_sev) if current_sev in sev_options else 1,
                        key=f"ch_sev_{i}"
                    )
                with col2:
                    stat_options = ["Active", "Improving", "Resolved"]
                    current_stat = ch.get('currentStatus', 'Active')
                    ch['currentStatus'] = st.selectbox(
                        "状態",
                        stat_options,
                        index=stat_options.index(current_stat) if current_stat in stat_options else 0,
                        key=f"ch_stat_{i}"
                    )
        
        if st.button("➕ 課題を追加", key="add_challenge"):
            data.setdefault('challenges', []).append({
                'description': '', 'severity': 'Medium', 'currentStatus': 'Active'
            })
            st.rerun()
    
    # --- 第4の柱: 参考情報としての申告歴 ---
    with tab4:
        st.subheader("👤 受給者基本情報")
        
        recipient = data.get('recipient', {})
        
        col1, col2 = st.columns(2)
        with col1:
            recipient['name'] = st.text_input(
                "氏名 *",
                value=recipient.get('name', ''),
                key="r_name"
            )
            recipient['caseNumber'] = st.text_input(
                "ケース番号",
                value=recipient.get('caseNumber', ''),
                key="r_case"
            )
        with col2:
            dob_value = safe_date_parse(recipient.get('dob'))
            if dob_value:
                dob = st.date_input(
                    "生年月日",
                    value=dob_value,
                    min_value=date(1920, 1, 1),
                    max_value=date.today(),
                    key="r_dob"
                )
                recipient['dob'] = dob.isoformat()
            else:
                st.text_input("生年月日", value="", key="r_dob_text", placeholder="未設定")
            
            gender_options = ["男性", "女性", "その他", "不明"]
            current_gender = recipient.get('gender', '不明')
            if current_gender not in gender_options:
                gender_options.append(current_gender)
            recipient['gender'] = st.selectbox(
                "性別",
                gender_options,
                index=gender_options.index(current_gender),
                key="r_gender"
            )
        
        data['recipient'] = recipient
        
        st.divider()
        
        st.subheader("📝 本人が語った生活歴（参考情報）")
        st.info("💡 本人からの聴き取りは不正確な可能性があります。「参考情報」として扱います。")
        
        histories = data.get('declaredHistories', [])
        
        for i, dh in enumerate(histories):
            with st.expander(f"申告歴 {i+1}: {dh.get('era', '時期不明')}", expanded=True):
                col1, col2 = st.columns([1, 3])
                with col1:
                    era_options = ["幼少期", "学齢期", "20代", "30代", "40代", "50代", "60代以降", "その他"]
                    current_era = dh.get('era', 'その他')
                    if current_era not in era_options:
                        era_options.append(current_era)
                    dh['era'] = st.selectbox(
                        "時期",
                        era_options,
                        index=era_options.index(current_era),
                        key=f"dh_era_{i}"
                    )
                with col2:
                    dh['content'] = st.text_area(
                        "本人が語った内容",
                        value=dh.get('content', ''),
                        key=f"dh_content_{i}"
                    )
        
        if st.button("➕ 申告歴を追加", key="add_dh"):
            data.setdefault('declaredHistories', []).append({
                'era': '', 'content': '', 'reliability': 'Declared'
            })
            st.rerun()
        
        st.divider()
        
        st.subheader("💭 本人の願い")
        wishes = data.get('wishes', [])
        
        for i, w in enumerate(wishes):
            col1, col2 = st.columns([3, 1])
            with col1:
                w['content'] = st.text_input(
                    f"願い {i+1}",
                    value=w.get('content', ''),
                    key=f"w_content_{i}"
                )
            with col2:
                pri_options = ["High", "Medium", "Low"]
                current_pri = w.get('priority', 'Medium')
                w['priority'] = st.selectbox(
                    "優先度",
                    pri_options,
                    index=pri_options.index(current_pri) if current_pri in pri_options else 1,
                    key=f"w_pri_{i}"
                )
        
        if st.button("➕ 願いを追加", key="add_wish"):
            data.setdefault('wishes', []).append({
                'content': '', 'priority': 'Medium', 'status': 'Active'
            })
            st.rerun()
    
    # --- 第5の柱: 社会的ネットワーク ---
    with tab5:
        st.subheader("📞 キーパーソン")
        
        key_persons = data.get('keyPersons', [])
        
        for i, kp in enumerate(key_persons):
            with st.expander(f"連絡先 {i+1}: {kp.get('name', '未入力')}（{kp.get('relationship', '')}）", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    kp['name'] = st.text_input("氏名", value=kp.get('name', ''), key=f"kp_name_{i}")
                    kp['relationship'] = st.text_input("関係", value=kp.get('relationship', ''), key=f"kp_rel_{i}")
                with col2:
                    kp['contactInfo'] = st.text_input("連絡先", value=kp.get('contactInfo', ''), key=f"kp_contact_{i}")
                    kp['rank'] = st.number_input("優先順位", min_value=1, max_value=10, value=kp.get('rank', i+1), key=f"kp_rank_{i}")
        
        if st.button("➕ キーパーソンを追加", key="add_kp"):
            data.setdefault('keyPersons', []).append({
                'name': '', 'relationship': '', 'contactInfo': '', 'rank': len(key_persons)+1
            })
            st.rerun()
        
        st.divider()
        
        st.subheader("👨‍👩‍👧 家族")
        families = data.get('familyMembers', [])
        
        for i, fm in enumerate(families):
            with st.expander(f"家族 {i+1}: {fm.get('name', '未入力')}（{fm.get('relationship', '')}）", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    fm['name'] = st.text_input("氏名", value=fm.get('name', ''), key=f"fm_name_{i}")
                    fm['relationship'] = st.text_input("続柄", value=fm.get('relationship', ''), key=f"fm_rel_{i}")
                with col2:
                    contact_options = ["良好", "疎遠", "断絶", "不明"]
                    current_contact = fm.get('contactStatus', '不明')
                    fm['contactStatus'] = st.selectbox(
                        "関係性",
                        contact_options,
                        index=contact_options.index(current_contact) if current_contact in contact_options else 3,
                        key=f"fm_contact_{i}"
                    )
        
        if st.button("➕ 家族を追加", key="add_fm"):
            data.setdefault('familyMembers', []).append({
                'name': '', 'relationship': '', 'contactStatus': '不明'
            })
            st.rerun()
        
        st.divider()
        
        st.subheader("🏥 医療機関")
        medicals = data.get('medicalInstitutions', [])
        
        for i, mi in enumerate(medicals):
            with st.expander(f"医療機関 {i+1}: {mi.get('name', '未入力')}", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    mi['name'] = st.text_input("病院名", value=mi.get('name', ''), key=f"mi_name_{i}")
                    mi['department'] = st.text_input("診療科", value=mi.get('department', ''), key=f"mi_dept_{i}")
                with col2:
                    mi['doctor'] = st.text_input("担当医", value=mi.get('doctor', ''), key=f"mi_doc_{i}")
                    role_options = ["主治医", "専門医", "かかりつけ"]
                    current_role = mi.get('role', 'かかりつけ')
                    mi['role'] = st.selectbox(
                        "役割",
                        role_options,
                        index=role_options.index(current_role) if current_role in role_options else 2,
                        key=f"mi_role_{i}"
                    )
        
        if st.button("➕ 医療機関を追加", key="add_mi"):
            data.setdefault('medicalInstitutions', []).append({
                'name': '', 'department': '', 'doctor': '', 'role': 'かかりつけ'
            })
            st.rerun()
    
    # --- 第6の柱: 法的・制度的基盤 ---
    with tab6:
        st.subheader("📜 保護決定")
        
        pd = data.get('protectionDecision', {})
        
        col1, col2 = st.columns(2)
        with col1:
            pd_date = safe_date_parse(pd.get('decisionDate'))
            if pd_date:
                pd['decisionDate'] = st.date_input(
                    "決定日",
                    value=pd_date,
                    key="pd_date"
                ).isoformat()
            else:
                st.text_input("決定日", value="", key="pd_date_text", placeholder="未設定")
        with col2:
            type_options = ["開始", "変更", "廃止"]
            current_type = pd.get('type', '開始')
            pd['type'] = st.selectbox(
                "種別",
                type_options,
                index=type_options.index(current_type) if current_type in type_options else 0,
                key="pd_type"
            )
        
        data['protectionDecision'] = pd
        
        st.divider()
        
        st.subheader("🎫 手帳・証明書")
        certs = data.get('certificates', [])
        
        for i, c in enumerate(certs):
            with st.expander(f"証明書 {i+1}: {c.get('type', '種類不明')}", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    cert_options = ["障害者手帳", "介護保険証", "自立支援医療", "その他"]
                    current_cert = c.get('type', 'その他')
                    if current_cert not in cert_options:
                        cert_options.append(current_cert)
                    c['type'] = st.selectbox(
                        "種類",
                        cert_options,
                        index=cert_options.index(current_cert),
                        key=f"c_type_{i}"
                    )
                with col2:
                    c['grade'] = st.text_input("等級", value=c.get('grade', ''), key=f"c_grade_{i}")
        
        if st.button("➕ 証明書を追加", key="add_cert"):
            data.setdefault('certificates', []).append({'type': '', 'grade': ''})
            st.rerun()
        
        st.divider()
        
        st.subheader("🎯 支援目標")
        goals = data.get('supportGoals', [])
        
        for i, g in enumerate(goals):
            with st.expander(f"目標 {i+1}: {g.get('description', '未入力')[:40]}...", expanded=True):
                g['description'] = st.text_area(
                    "目標",
                    value=g.get('description', ''),
                    key=f"g_desc_{i}"
                )
                g['paceConsideration'] = st.text_input(
                    "本人のペースに関する配慮",
                    value=g.get('paceConsideration', ''),
                    key=f"g_pace_{i}",
                    help="本人のペースを尊重した目標設定を"
                )
        
        if st.button("➕ 支援目標を追加", key="add_goal"):
            data.setdefault('supportGoals', []).append({
                'description': '', 'status': 'Active', 'paceConsideration': ''
            })
            st.rerun()
    
    # 更新されたデータを保存
    st.session_state.edited_data = data
    
    # ナビゲーションボタン
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("← 入力に戻る", use_container_width=True):
            st.session_state.step = 'input'
            st.rerun()
    
    with col3:
        if st.button("最終確認へ →", type="primary", use_container_width=True):
            if not data.get('recipient', {}).get('name'):
                st.error("受給者名は必須です")
            else:
                st.session_state.step = 'confirm'
                st.rerun()

# =============================================================================
# Step 3: 最終確認
# =============================================================================

def render_confirm_step():
    st.title("✅ 最終確認")
    st.markdown("以下の内容でデータベースに登録します。**特に避けるべき関わり方を再確認してください。**")
    
    data = st.session_state.edited_data
    
    if not data:
        st.error("データがありません")
        return
    
    recipient_name = data.get('recipient', {}).get('name', '不明')
    
    st.header(f"👤 {recipient_name} さんの登録内容")
    
    # 警告セクション（最初に表示）
    ng_approaches = data.get('ngApproaches', [])
    if ng_approaches:
        st.subheader("⚠️ 避けるべき関わり方")
        for ng in ng_approaches:
            if ng.get('description'):
                st.markdown(
                    f'<div style="background-color: #ffebee; padding: 12px; border-left: 4px solid #f44336; '
                    f'border-radius: 4px; margin: 8px 0;">'
                    f'{get_risk_emoji(ng.get("riskLevel", ""))} <strong>{ng["description"]}</strong><br>'
                    f'<span style="color: #666;">理由: {ng.get("reason", "未設定")}</span></div>',
                    unsafe_allow_html=True
                )
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 精神疾患
        mh = data.get('mentalHealthStatus', {})
        if mh.get('diagnosis'):
            st.subheader("🏥 精神疾患の状況")
            st.write(f"- **診断**: {mh['diagnosis']}")
            st.write(f"- **状態**: {mh.get('currentStatus', '不明')}")
            st.write(f"- **治療**: {mh.get('treatmentStatus', '不明')}")
        
        # 効果的な関わり方
        effective = data.get('effectiveApproaches', [])
        if effective:
            st.subheader("✅ 効果的だった関わり方")
            for ea in effective:
                if ea.get('description'):
                    st.write(f"- {ea['description']}")
        
        # 強み
        strengths = data.get('strengths', [])
        if strengths:
            st.subheader("💪 発見された強み")
            for s in strengths:
                if s.get('description'):
                    st.write(f"- {s['description']}")
    
    with col2:
        # ケース記録
        records = data.get('caseRecords', [])
        if records:
            st.subheader("📋 ケース記録")
            st.write(f"**{len(records)}件の記録**")
        
        # キーパーソン
        key_persons = data.get('keyPersons', [])
        if key_persons:
            st.subheader("📞 キーパーソン")
            for kp in sorted(key_persons, key=lambda x: x.get('rank', 99)):
                if kp.get('name'):
                    st.write(f"{kp.get('rank', '-')}. **{kp['name']}**（{kp.get('relationship', '')}）")
        
        # 願い
        wishes = data.get('wishes', [])
        if wishes:
            st.subheader("💭 本人の願い")
            for w in wishes:
                if w.get('content'):
                    st.write(f"- {w['content']}")
    
    # ナビゲーションボタン
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("← 修正に戻る", use_container_width=True):
            st.session_state.step = 'edit'
            st.rerun()
    
    with col3:
        if st.button("✅ データベースに登録", type="primary", use_container_width=True):
            with st.spinner("登録中..."):
                try:
                    result = register_to_database(data, st.session_state.caseworker_name or "system")
                    
                    if result.get('warnings'):
                        for w in result['warnings']:
                            st.warning(w)
                    
                    st.session_state.step = 'done'
                    st.rerun()
                except Exception as e:
                    st.error(f"登録エラー: {e}")

# =============================================================================
# Step 4: 完了
# =============================================================================

def render_done_step():
    st.title("🎉 登録完了")
    
    st.success("データベースへの登録が完了しました！")
    st.balloons()
    
    recipient_name = st.session_state.edited_data.get('recipient', {}).get('name', '')
    
    # 引き継ぎサマリーを表示
    st.subheader("📋 引き継ぎサマリー")
    st.markdown("担当者交代時にこの情報を共有してください。")
    
    try:
        summary = get_handover_summary(recipient_name)
        st.markdown(summary)
    except:
        pass
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📝 続けて登録する", use_container_width=True, type="primary"):
            reset_session_state()
            st.rerun()
    
    with col2:
        if st.button("📊 登録データを確認", use_container_width=True):
            st.session_state.show_data = True
            st.rerun()
    
    # データ確認表示
    if st.session_state.get('show_data'):
        st.divider()
        st.subheader(f"📋 {recipient_name}さんの登録データ")
        
        tab1, tab2, tab3, tab4 = st.tabs(["⚠️避けるべき関わり方", "✅効果的な関わり方", "💪強み", "📋ケース記録"])
        
        with tab1:
            ng_data = run_query("""
                MATCH (r:Recipient {name: $name})-[:MUST_AVOID]->(ng:NgApproach)
                RETURN ng.description as 内容, ng.reason as 理由, ng.riskLevel as リスク
            """, {"name": recipient_name})
            if ng_data:
                st.dataframe(ng_data, use_container_width=True)
            else:
                st.info("登録なし")
        
        with tab2:
            ea_data = run_query("""
                MATCH (r:Recipient {name: $name})-[:RESPONDS_WELL_TO]->(ea:EffectiveApproach)
                RETURN ea.description as 内容, ea.context as 状況
            """, {"name": recipient_name})
            if ea_data:
                st.dataframe(ea_data, use_container_width=True)
            else:
                st.info("登録なし")
        
        with tab3:
            s_data = run_query("""
                MATCH (r:Recipient {name: $name})-[:HAS_STRENGTH]->(s:Strength)
                RETURN s.description as 強み, s.context as 状況
            """, {"name": recipient_name})
            if s_data:
                st.dataframe(s_data, use_container_width=True)
            else:
                st.info("登録なし")
        
        with tab4:
            cr_data = run_query("""
                MATCH (r:Recipient {name: $name})-[:HAS_RECORD]->(cr:CaseRecord)
                RETURN cr.date as 日付, cr.category as カテゴリ, 
                       cr.content as 内容, cr.recipientResponse as 本人の反応
                ORDER BY cr.date DESC
                LIMIT 10
            """, {"name": recipient_name})
            if cr_data:
                st.dataframe(cr_data, use_container_width=True)
            else:
                st.info("登録なし")

# =============================================================================
# メイン: ステップに応じた画面表示
# =============================================================================

if st.session_state.step == 'input':
    render_input_step()
elif st.session_state.step == 'edit':
    render_edit_step()
elif st.session_state.step == 'confirm':
    render_confirm_step()
elif st.session_state.step == 'done':
    render_done_step()
