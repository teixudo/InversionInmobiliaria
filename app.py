"""
app.py — Streamlit UI for Real Estate Investment Analysis.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

import json
import os

from calculator import (
    compute_acquisition_costs, compute_financing, compute_annual_expenses,
    compute_cash_flow, compute_metrics, generate_amortization_schedule,
    DEFAULT_ITP_PCT, DEFAULT_NOTARY_EUR, DEFAULT_REGISTRY_EUR,
    DEFAULT_RENOVATION_EUR, DEFAULT_MORTGAGE_LTV, DEFAULT_MORTGAGE_RATE,
    DEFAULT_MORTGAGE_YEARS, DEFAULT_LOMBARD_RATE, DEFAULT_LOMBARD_LTV,
    DEFAULT_VACANCY_WEEKS, DEFAULT_MAINTENANCE_PCT, DEFAULT_INSURANCE_EUR,
    DEFAULT_IBI_EUR, DEFAULT_COMUNIDAD_EUR, DEFAULT_GESTORIA_EUR,
    DEFAULT_IRPF_MARGINAL,
)

DATA_FILE = "analisis_guardados.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ─── Page config ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="Análisis Inversión Inmobiliaria",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .metric-card {
        background: #ffffff;
        border: 1px solid rgba(0,0,0,0.05);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border-radius: 16px; padding: 1.5rem;
        text-align: center; transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }
    .metric-value {
        font-size: 2rem; font-weight: 700;
        background: linear-gradient(135deg, #3a7bd5, #00d2ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .metric-label { font-size: 0.85rem; color: #64748b; margin-top: 0.3rem; }
    .metric-good { background: linear-gradient(135deg, #059669, #10b981); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .metric-warn { background: linear-gradient(135deg, #d97706, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .metric-bad  { background: linear-gradient(135deg, #e11d48, #ef4444); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .section-header {
        font-size: 1.1rem; font-weight: 600; color: #334155;
        border-bottom: 2px solid rgba(58,123,213,0.3);
        padding-bottom: 0.5rem; margin-bottom: 1rem;
    }
    .cashflow-row {
        display: flex; justify-content: space-between;
        padding: 0.4rem 0; border-bottom: 1px solid rgba(0,0,0,0.05);
    }
    .cashflow-label { color: #475569; }
    .cashflow-value { font-weight: 600; color: #1e293b; }
    .positive { color: #10b981 !important; }
    .negative { color: #ef4444 !important; }
    div[data-testid="stSidebar"] { background: #f1f5f9; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background: rgba(0,0,0,0.03); border-radius: 8px;
        padding: 8px 16px; color: #475569;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3a7bd522, #00d2ff22);
        color: #3a7bd5 !important; border-bottom: 2px solid #3a7bd5;
    }
</style>
""", unsafe_allow_html=True)


# ─── Helper: render a metric card ────────────────────────────────────

def metric_card(label: str, value: str, quality: str = ""):
    cls = f"metric-value {quality}" if quality else "metric-value"
    st.markdown(f"""
    <div class="metric-card">
        <div class="{cls}">{value}</div>
        <div class="metric-label">{label}</div>
    </div>""", unsafe_allow_html=True)


def cashflow_line(label: str, amount: float, bold: bool = False):
    sign = "positive" if amount >= 0 else "negative"
    w = "700" if bold else "400"
    st.markdown(f"""
    <div class="cashflow-row">
        <span class="cashflow-label" style="font-weight:{w}">{label}</span>
        <span class="cashflow-value {sign}" style="font-weight:{w}">{amount:,.0f} €</span>
    </div>""", unsafe_allow_html=True)


def yield_quality(val: float) -> str:
    if val >= 0.06: return "metric-good"
    if val >= 0.04: return "metric-warn"
    return "metric-bad"


# ═══════════════════════════════════════════════════════════════════════
# SIDEBAR — Data Input
# ═══════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 💾 Mis Análisis")
    saved_analyses = load_data()
    saved_names = ["-- Nuevo --"] + list(saved_analyses.keys())
    
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        load_name = st.selectbox("Cargar", saved_names, label_visibility="collapsed")
    with col_btn:
        if st.button("Cargar") and load_name != "-- Nuevo --":
            data = saved_analyses[load_name]
            for k, v in data.items():
                st.session_state[k] = v
            
            # Retrocompatibilidad con análisis guardados antiguos
            if "rental_type" not in data:
                st.session_state["rental_type"] = "traditional"
            if "management_fee_pct" not in data:
                st.session_state["management_fee_pct"] = 0.0
            if "utilities_monthly" not in data:
                st.session_state["utilities_monthly"] = 0.0
            if "cleaning_costs" not in data:
                st.session_state["cleaning_costs"] = 0.0
            if "manager_commission_pct" not in data:
                st.session_state["manager_commission_pct"] = 20.0
            if "owner_rent_traditional" not in data:
                st.session_state["owner_rent_traditional"] = 800.0
            if "owner_utilities" not in data:
                st.session_state["owner_utilities"] = 150.0
            if "airdna_annual" not in data:
                st.session_state["airdna_annual"] = data.get("monthly_rent", 700.0) * 12

            st.rerun()

    st.markdown("---")
    st.markdown("## 🏠 Datos del Inmueble")
    
    rental_type = st.radio(
        "Modalidad de Alquiler", 
        ["traditional", "vacational", "management", "commercial_to_at"],
        format_func=lambda x: {"traditional": "Larga Estancia (Tradicional)", 
                               "vacational": "Vacacional (Inversión)", 
                               "management": "Gestión Vacacional (Property Manager)",
                               "commercial_to_at": "Cambio de Uso (Local a AT)"}[x],
        help="Determina los parámetros de ingresos, gastos y fiscalidad aplicable.",
        key="rental_type"
    )

    if rental_type == "traditional":
        price = st.number_input("Precio de compra (€)", value=150000.0, step=1000.0, format="%.0f", help="Precio al que vas a adquirir la propiedad.", key="price")
        monthly_rent = st.number_input("Alquiler mensual estimado (€)", value=700.0, step=25.0, format="%.0f", help="Ingreso mensual bruto estimado por alquilar el inmueble.", key="monthly_rent")
        airdna_annual = 0.0
        manager_commission_pct = 0.0
    elif rental_type == "vacational":
        price = st.number_input("Precio de compra (€)", value=150000.0, step=1000.0, format="%.0f", help="Precio al que vas a adquirir la propiedad.", key="price")
        airdna_annual = st.number_input("Ingresos anuales estimados AirDNA (€)", value=15000.0, step=500.0, format="%.0f", help="Estimación de ingresos anuales (Revenue) proporcionada por AirDNA.", key="airdna_annual")
        monthly_rent = airdna_annual / 12
        manager_commission_pct = 0.0
    elif rental_type == "management":
        airdna_annual = st.number_input("Facturación bruta anual estimada (AirDNA) (€)", value=25000.0, step=500.0, format="%.0f", help="Estimación de ingresos anuales (Revenue).", key="airdna_annual")
        manager_commission_pct = st.slider("Tu Comisión (%)", 5.0, 50.0, 20.0, 1.0, help="Porcentaje sobre la facturación bruta que te llevas como gestor.", key="manager_commission_pct") / 100
        monthly_rent = (airdna_annual * manager_commission_pct) / 12
        price = 0.0

        st.markdown("#### 👤 Datos para el Pitch al Propietario")
        owner_rent_traditional = st.number_input("Alternativa del propietario (Alquiler tradicional €/mes)", value=800.0, step=50.0, format="%.0f", help="Lo que ganaría el propietario alquilando a largo plazo.", key="owner_rent_traditional")
        owner_utilities = st.number_input("Suministros a cargo del propietario (€/mes)", value=150.0, step=25.0, help="Luz, agua, internet, etc.", key="owner_utilities")

    elif rental_type == "commercial_to_at":
        st.markdown("#### 🏗️ Inversión y Datos del Local")
        c1, c2 = st.columns(2)
        with c1:
            price = st.number_input("Precio de compra (€)", value=50000, step=1000, key="price")
            sqm = st.number_input("Metros cuadrados (m²)", value=70, step=5, key="sqm")
        with c2:
            num_apts = st.number_input("Nº de Apartamentos", min_value=1, value=2, step=1, key="num_apts")
            airdna_per_apt = st.number_input("Ingresos anuales/apto (€)", value=21000, step=500, key="airdna_per_apt")
        
        airdna_annual = float(airdna_per_apt * num_apts)
        monthly_rent = airdna_annual / 12
        manager_commission_pct = 0.0

        # Auto-calculated CAPEX & Taxes
        price_f = float(price)
        costes_reforma = float(sqm * 900)
        proyecto_arq = price_f * (4000.0 / 50000.0)
        jefe_obra = price_f * (1500.0 / 50000.0)
        mobiliario = float(num_apts * 5000)
        
        itp_eur = price_f * 0.10
        ajd_eur = price_f * 0.015
        notaria_eur = price_f * 0.01
        registro_eur = price_f * 0.005
        honorarios_legales = price_f * 0.005
        
        renovation = costes_reforma + mobiliario + proyecto_arq + jefe_obra
        taxes_and_fees_eur = itp_eur + ajd_eur + notaria_eur + registro_eur + honorarios_legales
        taxes_and_fees_pct = taxes_and_fees_eur / price_f if price_f > 0 else 0
        owner_rent_traditional, owner_utilities = 0.0, 0.0
        
        with st.expander("📊 Ver desglose automático de Inversión"):
            st.markdown(f"""
            **CAPEX (Reforma y Equipamiento)**
            *   Coste de reforma: {costes_reforma:,.0f} € *(900€/m²)*
            *   Proyecto arquitectónico: {proyecto_arq:,.0f} €
            *   Jefe de Obra: {jefe_obra:,.0f} €
            *   Mobiliario: {mobiliario:,.0f} € *(5.000€/apto)*
            
            **Impuestos y Gastos de Compra**
            *   ITP (10%): {itp_eur:,.0f} €
            *   AJD (1.5%): {ajd_eur:,.0f} €
            *   Notaría (1%): {notaria_eur:,.0f} €
            *   Registro (0.5%): {registro_eur:,.0f} €
            *   Gestoría (0.5%): {honorarios_legales:,.0f} €
            
            **TOTAL ADQUISICIÓN: {(price + renovation + taxes_and_fees_eur):,.0f} €**
            """)

    if rental_type != "management" and rental_type != "commercial_to_at":
        # ── Acquisition costs ──
        st.markdown("---")
        st.markdown("### 💰 Costes de Adquisición")
        taxes_and_fees_pct = st.slider("Impuestos y Gastos (%)", 0.0, 15.0, 10.0, 0.5, help="Porcentaje sobre el valor de compra que agrupa ITP, notaría y registro (típicamente ~10%).", key="taxes_and_fees_pct") / 100
        renovation = st.number_input("Reforma (€)", value=DEFAULT_RENOVATION_EUR, step=500.0, help="Presupuesto estimado para reformas o puesta a punto antes de alquilar.", key="renovation")

    if rental_type != "management":
        # ── Financing ──
        st.markdown("---")
        st.markdown("### 🏦 Financiación")
        fin_method = st.selectbox("Entrada y Gastos", ["mortgage_cash", "mortgage_personal"],
                                  format_func=lambda x: {"mortgage_cash": "💵 Al contado",
                                                         "mortgage_personal": "📈 Con Crédito Margen (IBKR)"}[x],
                                  help="Cómo vas a pagar la parte que no cubre la hipoteca y los gastos de adquisición.", key="fin_method")

        mortgage_ltv = st.slider("LTV Hipoteca (%)", 10, 100, int(DEFAULT_MORTGAGE_LTV * 100), help="Porcentaje del coste (compra+reforma) cubierto por el banco.", key="mortgage_ltv") / 100
        mortgage_rate = st.slider("Tipo interés hipoteca (%)", 0.5, 6.0, DEFAULT_MORTGAGE_RATE * 100, 0.1, help="TIN anual.", key="mortgage_rate") / 100
        mortgage_years = st.slider("Plazo hipoteca (años)", 5, 40, DEFAULT_MORTGAGE_YEARS, help="Plazo en años.", key="mortgage_years")

        personal_rate = 0.035
        personal_years = 10
        
        if fin_method == "mortgage_personal":
            st.markdown("---")
            st.markdown("### 💳 Crédito Margen")
            personal_rate = st.slider("Tipo interés margen (%)", 0.5, 9.0, 3.5, 0.1, help="Interés anual del crédito margen o personal.", key="personal_rate") / 100
            personal_years = st.slider("Plazo amortización (años)", 1, 30, 10, help="En cuántos años quieres devolver el crédito.", key="personal_years")
    else:
        taxes_and_fees_pct = 0.0
        renovation = 0.0
        fin_method = "mortgage_cash"
        mortgage_ltv = 0.0
        mortgage_rate = 0.0
        mortgage_years = 10
        personal_rate = 0.035
        personal_years = 10

    # ── Operating expenses ──
    st.markdown("---")
    st.markdown("### 📋 Gastos Recurrentes")
    
    if rental_type == "traditional":
        vacancy_weeks = st.slider("Semanas vacías / año", 0, 12, DEFAULT_VACANCY_WEEKS, key="vacancy_weeks")
        seguro_impago_pct = st.slider("Seguro de impago (% del alquiler)", 0.0, 10.0, 4.5, 0.1, key="seguro_impago_pct") / 100
        management_fee_pct = 0.0
        utilities_monthly = 0.0
        cleaning_costs = 0.0
        maintenance_pct = st.slider("Mantenimiento (% valor)", 0.0, 3.0, DEFAULT_MAINTENANCE_PCT * 100, 0.1, key="maintenance_pct") / 100
        insurance = st.number_input("Seguro hogar (€/año)", value=DEFAULT_INSURANCE_EUR, step=25.0, key="insurance")
        ibi = st.number_input("IBI (€/año)", value=DEFAULT_IBI_EUR, step=25.0, key="ibi")
        comunidad = st.number_input("Comunidad (€/año)", value=DEFAULT_COMUNIDAD_EUR, step=25.0, key="comunidad")
    elif rental_type == "vacational":
        vacancy_weeks = 0
        st.info("ℹ️ La ocupación ya suele estar contemplada en la estimación neta de AirDNA. Semanas vacías fijadas a 0.")
        seguro_impago_pct = 0.0
        management_fee_pct = st.slider("Comisión Plataforma / Gestión (%)", 0.0, 30.0, 15.0, 0.5, key="management_fee_pct") / 100
        utilities_monthly = st.number_input("Suministros y Bienvenida (€/mes)", value=150.0, step=25.0, help="Luz, agua, internet, amenities y packs de bienvenida. Al mes.", key="utilities_monthly")
        cleaning_costs = 0.0
        maintenance_pct = st.slider("Mantenimiento (% valor)", 0.0, 3.0, DEFAULT_MAINTENANCE_PCT * 100, 0.1, key="maintenance_pct") / 100
        insurance = st.number_input("Seguro hogar (€/año)", value=DEFAULT_INSURANCE_EUR, step=25.0, key="insurance")
        ibi = st.number_input("IBI (€/año)", value=DEFAULT_IBI_EUR, step=25.0, key="ibi")
        comunidad = st.number_input("Comunidad (€/año)", value=DEFAULT_COMUNIDAD_EUR, step=25.0, key="comunidad")
    elif rental_type == "commercial_to_at":
        vacancy_weeks = 0
        seguro_impago_pct = 0.0
        
        c1, c2 = st.columns(2)
        with c1:
            internet_monthly = st.number_input("Internet (€/mes TOTAL)", value=20.0, step=5.0, key="internet_monthly")
            electricidad_por_apto = st.number_input("Electricidad (€/mes por apto)", value=95.0, step=10.0, key="electricidad_por_apto")
            agua_por_apto = st.number_input("Agua (€/mes por apto)", value=18.0, step=5.0, key="agua_por_apto")
            software_monthly = st.number_input("Automatización (€/mes TOTAL)", value=100.0, step=10.0, key="software_monthly")
        with c2:
            cleaning_por_apto = st.number_input("Limpieza (€/mes por apto)", value=200.0, step=10.0, key="cleaning_por_apto")
            mantenimiento_por_apto = st.number_input("Mantenimiento (€/mes por apto)", value=30.0, step=5.0, key="mantenimiento_por_apto")
            management_fee_pct = st.slider("Comisión (Airbnb/Booking) (%)", 0.0, 30.0, 15.0, 0.5, key="management_fee_pct") / 100
            
        cleaning_costs = (cleaning_por_apto * num_apts) * 12
        utilities_monthly = internet_monthly + software_monthly + (electricidad_por_apto * num_apts) + (agua_por_apto * num_apts)
        maintenance_pct = ((mantenimiento_por_apto * num_apts) * 12) / price_f if price_f > 0 else 0
        
        insurance = st.number_input("Seguros (€/año)", value=500.0, step=25.0, key="insurance")
        ibi = st.number_input("Impuestos (IBI, basuras...) (€/año)", value=300.0, step=25.0, key="ibi")
        comunidad = st.number_input("Comunidad de propietarios (€/año)", value=400.0, step=10.0, key="comunidad")
    else: # management
        vacancy_weeks = 0
        seguro_impago_pct = 0.0
        management_fee_pct = 0.0
        utilities_monthly = 0.0
        maintenance_pct = 0.0
        
        st.markdown("#### 👔 Tus Gastos (Property Manager)")
        cleaning_costs = st.number_input("Limpieza y Lavandería (€/año)", value=2000.0, step=100.0, help="Gastos anuales de limpieza a cargo del Property Manager.", key="cleaning_costs")
        gestoria = st.number_input("Gestoría (€/año)", value=DEFAULT_GESTORIA_EUR, step=25.0, key="gestoria")
        
        st.markdown("#### 👤 Gastos Fijos del Propietario")
        st.caption("Gastos que sigue pagando el dueño del inmueble (seguro, IBI, comunidad).")
        insurance = st.number_input("Seguro hogar (€/año)", value=DEFAULT_INSURANCE_EUR, step=25.0, key="insurance")
        ibi = st.number_input("IBI (€/año)", value=DEFAULT_IBI_EUR, step=25.0, key="ibi")
        comunidad = st.number_input("Comunidad (€/año)", value=DEFAULT_COMUNIDAD_EUR, step=25.0, key="comunidad")
    
    if rental_type != "management":
        gestoria = st.number_input("Gestoría (€/año)", value=DEFAULT_GESTORIA_EUR, step=25.0, key="gestoria")
    
    st.markdown("---")
    st.markdown("### 🏛️ Fiscalidad")
    irpf_marginal = st.slider("Tipo marginal IRPF (%)", 10, 50, int(DEFAULT_IRPF_MARGINAL * 100), help="Tu tipo marginal máximo en la declaración de la renta.", key="irpf_marginal") / 100
    if rental_type == "traditional":
        st.caption("✅ **Alquiler Tradicional:** Se aplica automáticamente la **reducción del 60%** sobre el rendimiento neto (IRPF de vivienda habitual).")
    elif rental_type == "vacational":
        st.caption("⚠️ **Alquiler Vacacional:** Tributa al marginal completo. **No se aplica** la reducción del 60% por vivienda habitual.")
    elif rental_type == "commercial_to_at":
        st.caption("🏬 **Cambio de Uso (Local a AT):** Actividad económica completa. Tributa en Impuesto de Sociedades (aprox. 25%) o en tu marginal de IRPF.")
    else:
        st.caption("👔 **Gestión Vacacional:** Rendimientos de actividades económicas o trabajo. Tributa al marginal completo sin deducciones especiales de vivienda.")

    st.markdown("---")
    st.markdown("### 💾 Guardar Análisis")
    save_name = st.text_input("Nombre para guardar", value=(load_name if load_name != "-- Nuevo --" else ""))
    if st.button("Guardar", use_container_width=True):
        if save_name:
            keys_to_save = [
                "rental_type", "airdna_annual", "manager_commission_pct", "owner_rent_traditional", "owner_utilities", "price", "monthly_rent", "taxes_and_fees_pct", "renovation", "fin_method",
                "mortgage_ltv", "mortgage_rate", "mortgage_years", "personal_rate", "personal_years",
                "vacancy_weeks", "maintenance_pct", "seguro_impago_pct", "management_fee_pct", "cleaning_costs", "utilities_monthly", "insurance", "ibi", "comunidad", "gestoria", "irpf_marginal"
            ]
            save_dict = {}
            for k in keys_to_save:
                if k in st.session_state:
                    save_dict[k] = st.session_state[k]
            saved_analyses[save_name] = save_dict
            save_data(saved_analyses)
            st.success("Guardado correctamente!")


# ═══════════════════════════════════════════════════════════════════════
# COMPUTATIONS
# ═══════════════════════════════════════════════════════════════════════

acquisition = compute_acquisition_costs(price, taxes_and_fees_pct, 0.0, renovation)
financing = compute_financing(
    acquisition, fin_method,
    mortgage_ltv, mortgage_rate, mortgage_years,
    personal_rate, personal_years,
    include_renovation_in_ltv=(rental_type == "commercial_to_at"),
)
expenses = compute_annual_expenses(
    monthly_rent=monthly_rent, 
    property_price=price, 
    vacancy_weeks=vacancy_weeks, 
    maintenance_pct=maintenance_pct,
    insurance=insurance if rental_type != "management" else 0.0, 
    seguro_impago_pct=seguro_impago_pct, 
    ibi=ibi if rental_type != "management" else 0.0, 
    comunidad_annual=comunidad if rental_type != "management" else 0.0, 
    gestoria=gestoria, 
    management_fee_pct=management_fee_pct,
    utilities_annual=utilities_monthly * 12,
    cleaning_costs_annual=cleaning_costs,
)
cf = compute_cash_flow(
    monthly_rent=monthly_rent, 
    expenses=expenses, 
    financing=financing, 
    acquisition=acquisition, 
    irpf_marginal=irpf_marginal, 
    rental_type=rental_type
)
met = compute_metrics(monthly_rent, acquisition, cf, financing)

# ═══════════════════════════════════════════════════════════════════════
# MAIN VIEW
# ═══════════════════════════════════════════════════════════════════════

st.markdown("# 🏠 Análisis de Inversión Inmobiliaria")
if load_name and load_name != "-- Nuevo --":
    st.markdown(f"**Análisis Activo:** {load_name}")

# ── KPI row ──
if rental_type != "management":
    cols = st.columns(4)
    with cols[0]:
        metric_card("Rentabilidad Bruta", f"{met.gross_yield:.1%}", yield_quality(met.gross_yield))
    with cols[1]:
        metric_card("ROCE (Rent. Neta)", f"{met.roce:.1%}", yield_quality(met.roce))
    with cols[2]:
        coc_str = "∞" if met.cash_on_cash == float('inf') else f"{met.cash_on_cash:.1%}"
        q = "metric-good" if met.cash_on_cash >= 0.08 or met.cash_on_cash == float('inf') else ("metric-warn" if met.cash_on_cash >= 0.04 else "metric-bad")
        metric_card("Cash-on-Cash", coc_str, q)
    with cols[3]:
        q2 = "metric-good" if met.monthly_cash_flow > 0 else "metric-bad"
        metric_card("Cash Flow Mensual", f"{met.monthly_cash_flow:,.0f} €", q2)

    st.markdown("<br>", unsafe_allow_html=True)
    cols2 = st.columns(4)
    with cols2[0]:
        metric_card("PER", f"{met.per_ratio:.1f} años", "metric-good" if met.per_ratio <= 15 else "metric-warn" if met.per_ratio <= 20 else "metric-bad")
    with cols2[1]:
        grm_str = "∞" if met.grm == float('inf') else f"{met.grm:.1f}x"
        metric_card("Multiplicador (GRM)", grm_str, "metric-good" if met.grm <= 10 else "metric-warn" if met.grm <= 15 else "metric-bad")
    with cols2[2]:
        dscr_q = "metric-good" if met.dscr >= 1.25 else "metric-warn" if met.dscr >= 1.0 else "metric-bad"
        dscr_str = "∞" if met.dscr == float('inf') else f"{met.dscr:.2f}x"
        metric_card("Cobertura Deuda (DSCR)", dscr_str, dscr_q)
    with cols2[3]:
        metric_card("Capital Necesario", f"{financing.equity_required:,.0f} €", "metric-good" if financing.equity_required == 0 else "")
else:
    cols = st.columns(4)
    with cols[0]:
        metric_card("Facturación Total", f"{airdna_annual:,.0f} €", "")
    with cols[1]:
        comision_bruta = airdna_annual * manager_commission_pct
        metric_card("Tu Comisión Bruta", f"{comision_bruta:,.0f} €", "")
    with cols[2]:
        q2 = "metric-good" if met.monthly_cash_flow > 0 else "metric-bad"
        metric_card("Beneficio Mensual", f"{met.monthly_cash_flow:,.0f} €", q2)
    with cols[3]:
        margen = (cf.post_tax_cash_flow / comision_bruta) if comision_bruta > 0 else 0
        q3 = "metric-good" if margen > 0.5 else "metric-warn"
        metric_card("Margen Neto", f"{margen:.1%}", q3)

    st.markdown("---")
    st.markdown("### 🤝 Impacto para el Propietario (Pitch)")
    
    # Cálculos comparativos para el dueño
    owner_gross_trad = owner_rent_traditional * 12
    owner_opex_trad = insurance + ibi + comunidad
    owner_net_trad_pretax = owner_gross_trad - owner_opex_trad
    base_imponible_trad = owner_net_trad_pretax * 0.40 if owner_net_trad_pretax > 0 else owner_net_trad_pretax
    owner_tax_trad = base_imponible_trad * irpf_marginal if base_imponible_trad > 0 else 0
    owner_net_trad = owner_net_trad_pretax - owner_tax_trad

    owner_gross_vac = airdna_annual - comision_bruta
    owner_opex_vac = insurance + ibi + comunidad + (owner_utilities * 12)
    owner_net_vac_pretax = owner_gross_vac - owner_opex_vac
    owner_tax_vac = owner_net_vac_pretax * irpf_marginal if owner_net_vac_pretax > 0 else 0
    owner_net_vac = owner_net_vac_pretax - owner_tax_vac

    diff_net = owner_net_vac - owner_net_trad
    diff_pct = (diff_net / owner_net_trad) if owner_net_trad > 0 else 0

    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        metric_card("Neto Propietario (Tradicional)", f"{owner_net_trad:,.0f} €/año", "")
    with pc2:
        metric_card("Neto Propietario (Contigo)", f"{owner_net_vac:,.0f} €/año", "metric-good" if diff_net > 0 else "metric-bad")
    with pc3:
        q_diff = "metric-good" if diff_net > 0 else "metric-bad"
        metric_card("Mejora en su bolsillo", f"{diff_net:,.0f} € (+{diff_pct:.1%})", q_diff)

    with st.expander("Ver desglose comparativo"):
        df_pitch = pd.DataFrame({
            "Concepto": ["Ingreso Bruto Anual", "Tu Comisión (-)", "Gastos de Suministros (-)", "Otros Gastos Fijos (IBI, Seg, Com)", "IRPF Propietario (Estimado)", "Beneficio Neto Anual"],
            "Larga Estancia": [owner_gross_trad, 0, 0, owner_opex_trad, owner_tax_trad, owner_net_trad],
            "Contigo (Vacacional)": [airdna_annual, comision_bruta, owner_utilities*12, owner_opex_trad, owner_tax_vac, owner_net_vac]
        })
        for c in ["Larga Estancia", "Contigo (Vacacional)"]:
            df_pitch[c] = df_pitch[c].map(lambda x: f"{x:,.0f} €")
        st.table(df_pitch)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──
tab1, tab2, tab3, tab4 = st.tabs(["📊 Cash Flow", "💰 Costes de Adquisición", "📈 Proyección", "📋 Resumen"])

with tab1:
    st.markdown('<div class="section-header">Cascada de Cash Flow Anual</div>', unsafe_allow_html=True)
    fig_wf = go.Figure(go.Waterfall(
        name="Cash Flow", orientation="v",
        measure=["relative", "relative", "relative", "relative", "relative", "total"],
        x=["Ingresos Brutos", "Pérdida Vacío", "Gastos Operativos", "Servicio Deuda", "Impuestos", "Cash Flow Neto"],
        y=[cf.gross_rental_income, -cf.vacancy_loss, -cf.operating_expenses, -cf.debt_service, -cf.irpf_estimate, cf.post_tax_cash_flow],
        connector={"line":{"color":"rgba(255,255,255,0.1)"}},
        decreasing={"marker":{"color":"#fc5c7d"}},
        increasing={"marker":{"color":"#00c9a7"}},
        totals={"marker":{"color":"#3a7bd5"}}
    ))
    fig_wf.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1e293b"), height=350, margin=dict(t=20, b=20)
    )
    st.plotly_chart(fig_wf, use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown('<div class="section-header">Estado de Resultados Anual</div>', unsafe_allow_html=True)
        cashflow_line("Ingresos brutos por alquiler", cf.gross_rental_income)
        cashflow_line("Pérdida por vacío", -cf.vacancy_loss)
        cashflow_line("Ingresos efectivos", cf.effective_rental_income, bold=True)
        st.markdown("<br>", unsafe_allow_html=True)
        cashflow_line("Gastos operativos", -cf.operating_expenses)
        cashflow_line("NOI (Beneficio Operativo Neto)", cf.noi, bold=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if cf.debt_service > 0:
            cashflow_line(f"Servicio de deuda ({fin_method})", -cf.debt_service)
        cashflow_line("Cash flow antes de impuestos", cf.pre_tax_cash_flow, bold=True)
        cashflow_line("IRPF estimado (con reducción 60%)", -cf.irpf_estimate)
        st.markdown(f"<div style='font-size:0.8rem; color:#64748b; margin-top:-5px; margin-bottom:10px;'>* Se han deducido {cf.deductible_depreciation:,.0f} € de amortización del inmueble y {cf.deductible_interest:,.0f} € de intereses.</div>", unsafe_allow_html=True)
        st.markdown("<hr style='border-color:rgba(0,210,255,0.3)'>", unsafe_allow_html=True)
        cashflow_line("CASH FLOW NETO ANUAL", cf.post_tax_cash_flow, bold=True)

    with c2:
        st.markdown('<div class="section-header">Distribución de Gastos</div>', unsafe_allow_html=True)
        labels = ["Mantenimiento", "Seguro Hogar", "Seguro/Gestión", "Suministros", "IBI", "Comunidad", "Gestoría", "Vacío"]
        seguro_gestion = expenses.seguro_impago if rental_type == "traditional" else expenses.management_fee
        values = [expenses.maintenance, expenses.insurance, seguro_gestion, expenses.utilities_and_supplies, expenses.ibi,
                  expenses.comunidad, expenses.gestoria, expenses.vacancy_loss]
        fig = go.Figure(go.Pie(
            labels=labels, values=values, hole=0.55,
            marker=dict(colors=["#00d2ff", "#3a7bd5", "#16213e", "#ffb703", "#7c4dff", "#f7971e", "#00c9a7", "#fc5c7d"]),
            textinfo="label+percent", textfont=dict(size=11, color="#1e293b"),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    if rental_type == "management":
        st.info("ℹ️ Esta pestaña no aplica al modelo de Gestión Vacacional (Property Management).")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-header">Desglose de Costes</div>', unsafe_allow_html=True)
            data = {
                "Concepto": ["Precio de compra", f"Impuestos y Gastos ({taxes_and_fees_pct:.1%})", "Reforma"],
                "Importe (€)": [acquisition.price, acquisition.taxes_and_fees, acquisition.renovation],
            }
            df = pd.DataFrame(data)
            df["Importe (€)"] = df["Importe (€)"].map(lambda x: f"{x:,.0f}")
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.markdown(f"**Total adquisición: {acquisition.total:,.0f} €**")
    
        with c2:
            st.markdown('<div class="section-header">Financiación</div>', unsafe_allow_html=True)
            if fin_method == "mortgage_cash":
                st.metric("Préstamo hipotecario", f"{financing.mortgage_loan_amount:,.0f} €")
                st.metric("Cuota hipoteca", f"{financing.mortgage_payment:,.0f} €/mes")
                st.metric("Capital necesario (Contado)", f"{financing.equity_required:,.0f} €")
            else:
                st.metric("Préstamo hipotecario", f"{financing.mortgage_loan_amount:,.0f} €")
                st.metric("Crédito Margen", f"{financing.personal_loan_amount:,.0f} €")
                st.metric("Cuota Hipoteca", f"{financing.mortgage_payment:,.0f} €/mes")
                st.metric("Cuota Crédito", f"{financing.personal_loan_payment:,.0f} €/mes")
                st.metric("Cuota TOTAL combinada", f"{financing.total_monthly_payment:,.0f} €/mes")

with tab3:
    if rental_type == "management":
        st.info("ℹ️ Esta pestaña no aplica al modelo de Gestión Vacacional (Property Management).")
    else:
        years_proj = st.slider("Años de proyección", 5, 30, 10, key="proj_years")
        appreciation = st.slider("Revalorización anual (%)", 0.0, 5.0, 2.0, 0.5) / 100
        rent_growth = st.slider("Incremento alquiler anual (%)", 0.0, 5.0, 2.0, 0.5) / 100
    
        years_list, equity_list, cumcf_list, prop_val_list = [], [], [], []
        cum_cf = 0
        for y in range(1, years_proj + 1):
            r = monthly_rent * (1 + rent_growth) ** (y - 1)
            pv = price * (1 + appreciation) ** y
            annual_cf = cf.post_tax_cash_flow * (1 + rent_growth) ** (y - 1)
            cum_cf += annual_cf
            equity_built = pv - financing.total_debt + cum_cf
            years_list.append(y)
            equity_list.append(equity_built)
            cumcf_list.append(cum_cf)
            prop_val_list.append(pv)
    
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=years_list, y=prop_val_list, name="Valor propiedad",
                                  line=dict(color="#3a7bd5", width=2), fill="tozeroy",
                                  fillcolor="rgba(58,123,213,0.1)"))
        fig2.add_trace(go.Scatter(x=years_list, y=equity_list, name="Equity acumulado",
                                  line=dict(color="#00c9a7", width=2), fill="tozeroy",
                                  fillcolor="rgba(0,201,167,0.1)"))
        fig2.add_trace(go.Bar(x=years_list, y=cumcf_list, name="Cash flow acumulado",
                              marker_color="rgba(0,210,255,0.4)"))
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#1e293b"), height=400,
            xaxis=dict(title="Año", gridcolor="rgba(0,0,0,0.05)"),
            yaxis=dict(title="€", gridcolor="rgba(0,0,0,0.05)", tickformat=","),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=40, b=40),
        )
        st.plotly_chart(fig2, use_container_width=True)
    
        roi_total = ((equity_list[-1] - financing.equity_required) / financing.equity_required) if financing.equity_required > 0 else 0
        roi_annual = (1 + roi_total) ** (1 / years_proj) - 1 if roi_total > -1 else 0
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            metric_card("ROI Total", f"{roi_total:.1%}", "metric-good" if roi_total > 0.5 else "metric-warn")
        with rc2:
            metric_card("ROI Anualizado", f"{roi_annual:.1%}", "metric-good" if roi_annual > 0.06 else "metric-warn")
        with rc3:
            metric_card(f"Valor en año {years_proj}", f"{prop_val_list[-1]:,.0f} €", "")

with tab4:
    st.markdown('<div class="section-header">Resumen Ejecutivo</div>', unsafe_allow_html=True)
    if rental_type != "management":
        fin_str = {"mortgage_cash": "Hipoteca + Contado", "mortgage_personal": "Hipoteca + Margen (IBKR)"}[fin_method]
        coc_str_val = "∞" if met.cash_on_cash == float('inf') else f"{met.cash_on_cash:.2%}"
        dscr_str_val = "∞" if met.dscr == float('inf') else f"{met.dscr:.2f}x"
        grm_str_val = "∞" if met.grm == float('inf') else f"{met.grm:.1f}x"
        
        summary = f"""
| Concepto | Valor |
|---|---|
| **Modalidad** | {"Tradicional" if rental_type == "traditional" else "Vacacional (Inversión)"} |
| **Precio de compra** | {price:,.0f} € |
| **Coste total adquisición** | {acquisition.total:,.0f} € |
| **Ingreso estimado (Mensual)** | {monthly_rent:,.0f} € |
| **Rentabilidad bruta** | {met.gross_yield:.2%} |
| **Rentabilidad neta (ROCE)** | {met.roce:.2%} |
| **Cash-on-Cash** | {coc_str_val} |
| **Cobertura de Deuda (DSCR)** | {dscr_str_val} |
| **PER / Multiplicador GRM** | {met.per_ratio:.1f} años / {grm_str_val} |
| **Cash flow mensual neto** | {met.monthly_cash_flow:,.0f} € |
| **Financiación** | {fin_str} |
| **Capital necesario** | {financing.equity_required:,.0f} € |
"""
        st.markdown(summary)
    
        verdict = ""
        if met.net_yield >= 0.06 and met.monthly_cash_flow > 0:
            verdict = "✅ **OPERACIÓN RENTABLE** — La rentabilidad neta supera el 6% y el cash flow es positivo."
        elif met.net_yield >= 0.04 and met.monthly_cash_flow > 0:
            verdict = "⚠️ **OPERACIÓN ACEPTABLE** — Rentabilidad moderada. Valorar si la revalorización esperada compensa."
        elif met.monthly_cash_flow < 0:
            verdict = "❌ **CASH FLOW NEGATIVO** — La operación genera pérdidas mensuales. Revisar precio o alquiler."
        else:
            verdict = "⚠️ **RENTABILIDAD BAJA** — Por debajo del 4% neto. Considerar alternativas."
        st.markdown(f"### Veredicto\n{verdict}")
    
        if fin_method in ["mortgage", "mortgage_plus_lombard"]:
            with st.expander("📊 Tabla de amortización (solo Hipoteca)"):
                sched = generate_amortization_schedule(financing.mortgage_loan_amount, mortgage_rate, mortgage_years)
                df_sched = pd.DataFrame(sched)
                df_sched.columns = ["Año", "Saldo inicial", "Cuota anual", "Intereses", "Amortización", "Saldo final"]
                for c in ["Saldo inicial", "Cuota anual", "Intereses", "Amortización", "Saldo final"]:
                    df_sched[c] = df_sched[c].map(lambda x: f"{x:,.0f}")
                st.dataframe(df_sched, use_container_width=True, hide_index=True)
    else:
        comision_bruta = airdna_annual * manager_commission_pct
        margen = (cf.post_tax_cash_flow / comision_bruta) if comision_bruta > 0 else 0
        summary = f"""
| Concepto | Valor |
|---|---|
| **Modalidad** | Gestión Vacacional (Property Manager) |
| **Facturación bruta anual (AirDNA)** | {airdna_annual:,.0f} € |
| **Tu Comisión ({manager_commission_pct:.0%})** | {comision_bruta:,.0f} € |
| **Gastos anuales (Limpieza y Gestoría)** | {(expenses.cleaning_costs + expenses.gestoria):,.0f} € |
| **Cash flow mensual neto** | {met.monthly_cash_flow:,.0f} € |
| **Margen de beneficio neto** | {margen:.1%} |
"""
        st.markdown(summary)
        if met.monthly_cash_flow > 0:
            st.markdown("### Veredicto\n✅ **OPERACIÓN RENTABLE** — La gestión de este inmueble te dejará beneficio positivo todos los meses.")
        else:
            st.markdown("### Veredicto\n❌ **CASH FLOW NEGATIVO** — Los gastos superan a tu comisión. Pide más % de comisión o no gestiones esta propiedad.")
