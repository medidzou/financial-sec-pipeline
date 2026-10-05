import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import text
from security.auth import ROLE_AUDITOR, authenticate
from security.database import create_database_engine

# --- Configuration de la page Streamlit ---
st.set_page_config(
    page_title="Financial & Cyber Data Pipeline",
    page_icon="",
    layout="wide"
)

# --- Connexion BDD avec Cache Streamlit ---
@st.cache_resource
def get_database_engine():
    return create_database_engine()

@st.cache_data(ttl=60)
def load_assets():
    engine = get_database_engine()
    query = "SELECT id, symbol, name, asset_type FROM assets ORDER BY symbol;"
    return pd.read_sql(query, engine)

@st.cache_data(ttl=60)
def load_financial_data(asset_id: int):
    engine = get_database_engine()
    query = text("""
        SELECT 
            p.price_date,
            p.open_price,
            p.high_price,
            p.low_price,
            p.close_price,
            p.volume,
            i.daily_return,
            i.volatility,
            i.moving_avg
        FROM asset_prices p
        LEFT JOIN indicators i 
            ON p.asset_id = i.asset_id AND p.price_date = i.price_date
        WHERE p.asset_id = :asset_id
        ORDER BY p.price_date ASC;
    """)
    return pd.read_sql(query, engine, params={"asset_id": asset_id})

def load_audit_logs(user_role: str, limit: int = 50):
    if user_role != ROLE_AUDITOR:
        raise PermissionError("Le rôle Auditeur est requis pour consulter les journaux.")
    engine = get_database_engine()
    query = text("""
        SELECT id, timestamp, user_action, status, details 
        FROM audit_logs 
        ORDER BY timestamp DESC 
        LIMIT :limit;
    """)
    return pd.read_sql(query, engine, params={"limit": limit})


try:
    database_engine = get_database_engine()
except (RuntimeError, ValueError) as error:
    st.error(str(error))
    st.stop()

if "authenticated_user" not in st.session_state:
    st.title("Connexion au dashboard financier")
    with st.form("login_form"):
        username = st.text_input("Identifiant")
        password = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")

    if submitted:
        try:
            user = authenticate(database_engine, username, password)
        except Exception:
            st.error("Connexion impossible. Vérifiez la base de données et réessayez.")
            st.stop()
        if user:
            st.session_state["authenticated_user"] = user
            st.rerun()
        st.error("Identifiant ou mot de passe incorrect, ou compte temporairement verrouillé.")
    st.stop()

authenticated_user = st.session_state["authenticated_user"]
user_role = authenticated_user["role"]
if user_role not in {"analyst", ROLE_AUDITOR}:
    st.session_state.pop("authenticated_user", None)
    st.error("Rôle utilisateur invalide.")
    st.stop()

st.sidebar.caption(f"Connecté : {authenticated_user['username']} ({user_role})")
if st.sidebar.button("Se déconnecter"):
    st.session_state.pop("authenticated_user", None)
    st.rerun()


# --- Interface Utilisateur ---
st.title("Financial & Cyber Data Dashboard")

# Récupération de la liste des actifs
assets_df = load_assets()

if assets_df.empty:
    st.warning("Aucun actif trouvé dans la base de données. Veuillez exécuter le pipeline ETL d'abord.")
    st.stop()

# Barre latérale : Filtres
st.sidebar.header("Filtres & Sélection")

symbol_list = assets_df["symbol"].tolist()
selected_symbol = st.sidebar.selectbox("Sélectionner un actif", symbol_list)

selected_asset_info = assets_df[assets_df["symbol"] == selected_symbol].iloc[0]
asset_id = int(selected_asset_info["id"])

# Chargement des données pour l'actif sélectionné
data_df = load_financial_data(asset_id)

if not data_df.empty:
    data_df["price_date"] = pd.to_datetime(data_df["price_date"])
    min_date = data_df["price_date"].min().date()
    max_date = data_df["price_date"].max().date()

    date_range = st.sidebar.date_input(
        "Période",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = data_df[
            (data_df["price_date"].dt.date >= start_date) & 
            (data_df["price_date"].dt.date <= end_date)
        ]
    else:
        filtered_df = data_df
else:
    filtered_df = pd.DataFrame()

# Bouton de rafraîchissement
if st.sidebar.button("Actualiser les données"):
    st.cache_data.clear()
    st.rerun()

# --- Onglets Principaux ---
tab_labels = ["Analyse de Marché", "Indicateurs & Risque"]
if user_role == ROLE_AUDITOR:
    tab_labels.append("Qualité de Données & Audit")
dashboard_tabs = st.tabs(tab_labels)
tab_market, tab_indicators = dashboard_tabs[:2]
tab_audit = dashboard_tabs[2] if user_role == ROLE_AUDITOR else None

# ==========================================
# Onglet 1 : Marché (Chandelier + Moyenne Mobile + Volume)
# ==========================================
with tab_market:
    st.subheader(f"Cotations pour {selected_asset_info['name']} ({selected_symbol})")

    if filtered_df.empty:
        st.info("Aucune donnée disponible pour la période sélectionnée.")
    else:
        # Métriques clés
        latest = filtered_df.iloc[-1]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Dernier Cours", f"{latest['close_price']:.2f} $")
        
        daily_ret = latest['daily_return']
        ret_label = f"{daily_ret:+.2f} %" if pd.notnull(daily_ret) else "N/A"
        col2.metric("Rendement Journalier", ret_label, delta=ret_label if pd.notnull(daily_ret) else None)
        
        volat = latest['volatility']
        col3.metric("Volatilité (5j)", f"{volat:.4f}" if pd.notnull(volat) else "N/A")
        
        col4.metric("Volume", f"{int(latest['volume']):,}")

        # Graphique Chandelier + Moyenne Mobile + Volume
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.08, 
            row_heights=[0.75, 0.25],
            subplot_titles=("Chandeliers Japonais & MA(5)", "Volume d'échange")
        )

        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=filtered_df["price_date"],
                open=filtered_df["open_price"],
                high=filtered_df["high_price"],
                low=filtered_df["low_price"],
                close=filtered_df["close_price"],
                name="OHLC"
            ),
            row=1, col=1
        )

        # Moyenne Mobile
        if "moving_avg" in filtered_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=filtered_df["price_date"],
                    y=filtered_df["moving_avg"],
                    mode="lines",
                    name="Moving Avg (5j)",
                    line=dict(color="orange", width=1.5)
                ),
                row=1, col=1
            )

        # Volume
        fig.add_trace(
            go.Bar(
                x=filtered_df["price_date"],
                y=filtered_df["volume"],
                name="Volume",
                marker_color="rgba(100, 149, 237, 0.6)"
            ),
            row=2, col=1
        )

        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=600,
            template="plotly_dark",
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# Onglet 2 : Indicateurs (Rendement & Volatilité)
# ==========================================
with tab_indicators:
    st.subheader("Dynamique du Rendement & de la Volatilité")
    
    if not filtered_df.empty:
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            fig_ret = go.Figure()
            fig_ret.add_trace(
                go.Scatter(
                    x=filtered_df["price_date"], 
                    y=filtered_df["daily_return"],
                    mode="lines+markers",
                    name="Daily Return (%)",
                    line=dict(color="#00CC96")
                )
            )
            fig_ret.update_layout(
                title="Rendement Journalier (%)",
                template="plotly_dark",
                yaxis_title="%",
                height=380
            )
            st.plotly_chart(fig_ret, use_container_width=True)

        with col_g2:
            fig_vol = go.Figure()
            fig_vol.add_trace(
                go.Scatter(
                    x=filtered_df["price_date"], 
                    y=filtered_df["volatility"],
                    mode="lines",
                    name="Volatilité (5j)",
                    line=dict(color="#EF553B")
                )
            )
            fig_vol.update_layout(
                title="Volatilité glissante sur 5 jours",
                template="plotly_dark",
                yaxis_title="Écart-type",
                height=380
            )
            st.plotly_chart(fig_vol, use_container_width=True)

# ==========================================
# Onglet 3 : Qualité des données & Audit Logs
# ==========================================
if tab_audit is not None:
    with tab_audit:
        st.subheader("Traçabilité du Pipeline ETL (`audit_logs`)")

        logs_df = load_audit_logs(user_role)

        if logs_df.empty:
            st.info("Aucun log d'audit enregistré.")
        else:
            counts = logs_df["status"].value_counts().to_dict()
            col_a1, col_a2, col_a3 = st.columns(3)
            col_a1.metric("Succès", counts.get("SUCCESS", 0))
            col_a2.metric("Avertissements", counts.get("WARNING", 0))
            col_a3.metric("Échecs", counts.get("FAILURE", 0))

            def color_status(val):
                if val == "SUCCESS":
                    return "color: #00CC96; font-weight: bold;"
                if val == "WARNING":
                    return "color: #FFA15A; font-weight: bold;"
                if val == "FAILURE":
                    return "color: #EF553B; font-weight: bold;"
                return ""

            styled_logs = logs_df.style.map(color_status, subset=["status"])
            st.dataframe(styled_logs, use_container_width=True, hide_index=True)