"""
calculator.py — Financial logic for real estate investment analysis.

Handles:
  - Total acquisition cost (price + taxes + fees + renovation)
  - Mortgage amortization (French system)
  - Lombard / margin loan (interest-only, pignoración)
  - Annual cash-flow projection
  - Profitability metrics (Gross Yield, Net Yield, Cash-on-Cash, ROCE)
"""

from dataclasses import dataclass, field
from typing import Optional
import math


# ─── Default parameters ───────────────────────────────────────────────

DEFAULT_ITP_PCT = 0.07          # 7 % Impuesto de Transmisiones Patrimoniales
DEFAULT_NOTARY_EUR = 800.0
DEFAULT_REGISTRY_EUR = 400.0
DEFAULT_AGENCY_PCT = 0.0        # Buyer rarely pays agency in Spain
DEFAULT_RENOVATION_EUR = 0.0

DEFAULT_MORTGAGE_LTV = 0.80     # 80 % loan-to-value
DEFAULT_MORTGAGE_RATE = 0.027   # 2.7 % annual
DEFAULT_MORTGAGE_YEARS = 30

DEFAULT_LOMBARD_RATE = 0.015    # 1.5 % annual (Interactive Brokers margin)
DEFAULT_LOMBARD_LTV = 0.50      # 50 % of portfolio value

DEFAULT_VACANCY_WEEKS = 4       # 4 weeks / year vacant
DEFAULT_MAINTENANCE_PCT = 0.01  # 1 % of property value / year
DEFAULT_INSURANCE_EUR = 300.0
DEFAULT_IBI_EUR = 500.0
DEFAULT_COMUNIDAD_EUR = 500.0   # annual
DEFAULT_GESTORIA_EUR = 0.0      # annual management / tax filing

IRPF_REDUCCION_VIVIENDA = 0.60  # 60 % deduction on net rental income (habitual)
DEFAULT_IRPF_MARGINAL = 0.30    # assumed marginal tax rate


# ─── Data classes ─────────────────────────────────────────────────────

@dataclass
class AcquisitionCosts:
    """Breakdown of the total cost to acquire the property."""
    price: float
    taxes_and_fees: float
    agency: float
    renovation: float

    @property
    def total(self) -> float:
        return (self.price + self.taxes_and_fees + self.agency + self.renovation)


@dataclass
class FinancingDetails:
    """Describes how the purchase is financed."""
    method: str                     # "mortgage_cash" | "mortgage_personal"
    equity_required: float = 0.0    # Cash the investor must put up
    
    mortgage_loan_amount: float = 0.0
    mortgage_payment: float = 0.0
    mortgage_annual_rate: float = 0.0
    
    personal_loan_amount: float = 0.0
    personal_loan_payment: float = 0.0

    @property
    def total_monthly_payment(self) -> float:
        return self.mortgage_payment + self.personal_loan_payment

    @property
    def total_debt(self) -> float:
        return self.mortgage_loan_amount + self.personal_loan_amount


@dataclass
class AnnualExpenses:
    """Recurring annual costs of owning the property."""
    vacancy_loss: float
    maintenance: float
    insurance: float
    seguro_impago: float
    ibi: float
    comunidad: float
    gestoria: float
    management_fee: float = 0.0
    utilities_and_supplies: float = 0.0
    cleaning_costs: float = 0.0

    @property
    def total(self) -> float:
        return (self.vacancy_loss + self.maintenance + self.insurance + self.seguro_impago +
                self.ibi + self.comunidad + self.gestoria + self.management_fee + self.utilities_and_supplies + self.cleaning_costs)


@dataclass
class CashFlow:
    """Annual cash-flow summary."""
    gross_rental_income: float
    vacancy_loss: float
    effective_rental_income: float
    operating_expenses: float      # maintenance + insurance + IBI + comunidad + gestoría + management + utilities + cleaning
    noi: float                     # Net Operating Income
    debt_service: float            # annual mortgage / lombard payments
    pre_tax_cash_flow: float
    irpf_estimate: float
    post_tax_cash_flow: float
    deductible_interest: float = 0.0
    deductible_depreciation: float = 0.0


@dataclass
class Metrics:
    """Key profitability indicators."""
    gross_yield: float             # Gross rent / Purchase price
    net_yield: float               # NOI / Total acquisition cost
    cash_on_cash: float            # Pre-tax cash flow / Equity invested
    roce: float                    # NOI / Total acquisition cost
    per_ratio: float               # Price-to-Earnings Ratio (years to recoup)
    monthly_cash_flow: float
    dscr: float                    # Debt Service Coverage Ratio
    grm: float                     # Gross Rent Multiplier


# ─── Pure functions ───────────────────────────────────────────────────

def compute_acquisition_costs(
    price: float,
    taxes_and_fees_pct: float = 0.10,
    agency_pct: float = DEFAULT_AGENCY_PCT,
    renovation: float = DEFAULT_RENOVATION_EUR,
) -> AcquisitionCosts:
    """Calculate total acquisition costs."""
    return AcquisitionCosts(
        price=price,
        taxes_and_fees=price * taxes_and_fees_pct,
        agency=price * agency_pct,
        renovation=renovation,
    )


def compute_mortgage_payment(principal: float, annual_rate: float, years: int) -> float:
    """Monthly payment under French amortization (constant payment)."""
    if annual_rate == 0:
        return principal / (years * 12)
    r = annual_rate / 12
    n = years * 12
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def compute_financing(
    acquisition: AcquisitionCosts,
    method: str = "mortgage_cash",
    # Mortgage params
    mortgage_ltv: float = DEFAULT_MORTGAGE_LTV,
    mortgage_rate: float = DEFAULT_MORTGAGE_RATE,
    mortgage_years: int = DEFAULT_MORTGAGE_YEARS,
    # Personal/Margin loan params
    personal_rate: float = 0.035,
    personal_years: int = 10,
    include_renovation_in_ltv: bool = False,
) -> FinancingDetails:
    """Determine financing structure."""
    if include_renovation_in_ltv:
        base_for_mortgage = acquisition.price + acquisition.renovation
    else:
        base_for_mortgage = acquisition.price
        
    mortgage_loan = base_for_mortgage * mortgage_ltv
    mortgage_payment = compute_mortgage_payment(mortgage_loan, mortgage_rate, mortgage_years)
    
    if method == "mortgage_cash":
        equity = acquisition.total - mortgage_loan
        return FinancingDetails(
            method="mortgage_cash",
            equity_required=max(equity, 0),
            mortgage_loan_amount=mortgage_loan,
            mortgage_payment=mortgage_payment,
            mortgage_annual_rate=mortgage_rate,
        )

    elif method == "mortgage_personal":
        personal_loan = acquisition.total - mortgage_loan
        personal_payment = compute_mortgage_payment(personal_loan, personal_rate, personal_years)
        return FinancingDetails(
            method="mortgage_personal",
            equity_required=0.0,
            mortgage_loan_amount=mortgage_loan,
            mortgage_payment=mortgage_payment,
            mortgage_annual_rate=mortgage_rate,
            personal_loan_amount=personal_loan,
            personal_loan_payment=personal_payment,
        )


def compute_annual_expenses(
    monthly_rent: float,
    property_price: float,
    vacancy_weeks: int = DEFAULT_VACANCY_WEEKS,
    maintenance_pct: float = DEFAULT_MAINTENANCE_PCT,
    insurance: float = DEFAULT_INSURANCE_EUR,
    seguro_impago_pct: float = 0.045, # Default 4.5% of rent
    ibi: float = DEFAULT_IBI_EUR,
    comunidad_annual: float = DEFAULT_COMUNIDAD_EUR,
    gestoria: float = DEFAULT_GESTORIA_EUR,
    management_fee_pct: float = 0.0,
    utilities_annual: float = 0.0,
    cleaning_costs_annual: float = 0.0,
) -> AnnualExpenses:
    """Calculate recurring annual expenses."""
    weekly_rent = (monthly_rent * 12) / 52
    return AnnualExpenses(
        vacancy_loss=weekly_rent * vacancy_weeks,
        maintenance=property_price * maintenance_pct,
        insurance=insurance,
        seguro_impago=monthly_rent * 12 * seguro_impago_pct,
        ibi=ibi,
        comunidad=comunidad_annual,
        gestoria=gestoria,
        management_fee=monthly_rent * 12 * management_fee_pct,
        utilities_and_supplies=utilities_annual,
        cleaning_costs=cleaning_costs_annual,
    )


def compute_cash_flow(
    monthly_rent: float,
    expenses: AnnualExpenses,
    financing: FinancingDetails,
    acquisition: AcquisitionCosts,
    irpf_marginal: float = DEFAULT_IRPF_MARGINAL,
    land_value_pct: float = 0.30,
    rental_type: str = "traditional",
) -> CashFlow:
    """Build the annual cash-flow statement."""
    gross = monthly_rent * 12
    vacancy = expenses.vacancy_loss
    effective = gross - vacancy

    opex = (expenses.maintenance + expenses.insurance + expenses.seguro_impago +
            expenses.ibi + expenses.comunidad + expenses.gestoria + expenses.management_fee + expenses.utilities_and_supplies + expenses.cleaning_costs)
    noi = effective - opex

    debt_service = financing.total_monthly_payment * 12

    pre_tax = noi - debt_service

    # Calculate deductible mortgage interest (approx Year 1 interest)
    deductible_interest = financing.mortgage_loan_amount * financing.mortgage_annual_rate

    # Calculate deductible depreciation (3% of construction cost)
    construction_cost = acquisition.total * (1 - land_value_pct)
    deductible_depreciation = construction_cost * 0.03

    # IRPF: only on the net rental profit. 60% reduction applies only to habitual residence (traditional)
    tax_net_yield = max(noi - deductible_interest - deductible_depreciation, 0)
    reduccion = IRPF_REDUCCION_VIVIENDA if rental_type == "traditional" else 0.0
    taxable_base = tax_net_yield * (1 - reduccion)
    irpf = taxable_base * irpf_marginal

    post_tax = pre_tax - irpf

    return CashFlow(
        gross_rental_income=gross,
        vacancy_loss=vacancy,
        effective_rental_income=effective,
        operating_expenses=opex,
        noi=noi,
        debt_service=debt_service,
        pre_tax_cash_flow=pre_tax,
        irpf_estimate=irpf,
        post_tax_cash_flow=post_tax,
        deductible_interest=deductible_interest,
        deductible_depreciation=deductible_depreciation,
    )


def compute_metrics(
    monthly_rent: float,
    acquisition: AcquisitionCosts,
    cash_flow: CashFlow,
    financing: FinancingDetails,
) -> Metrics:
    """Compute key profitability metrics."""
    gross_yield = (cash_flow.gross_rental_income / acquisition.price) if acquisition.price else 0
    net_yield = (cash_flow.noi / acquisition.total) if acquisition.total else 0
    if financing.equity_required > 0:
        cash_on_cash = cash_flow.pre_tax_cash_flow / financing.equity_required
    else:
        cash_on_cash = float('inf') if cash_flow.pre_tax_cash_flow > 0 else float('-inf') if cash_flow.pre_tax_cash_flow < 0 else 0.0
        
    roce = net_yield  # For unleveraged; same as net yield on total capital
    per = (acquisition.total / cash_flow.noi) if cash_flow.noi > 0 else float("inf")
    
    dscr = (cash_flow.noi / cash_flow.debt_service) if cash_flow.debt_service > 0 else float('inf')
    grm = (acquisition.price / cash_flow.gross_rental_income) if cash_flow.gross_rental_income > 0 else float('inf')

    return Metrics(
        gross_yield=gross_yield,
        net_yield=net_yield,
        cash_on_cash=cash_on_cash,
        roce=roce,
        per_ratio=per,
        monthly_cash_flow=cash_flow.post_tax_cash_flow / 12,
        dscr=dscr,
        grm=grm,
    )


def generate_amortization_schedule(
    principal: float, annual_rate: float, years: int
) -> list[dict]:
    """
    Return a year-by-year amortization table (French system).
    Each row: {year, opening_balance, annual_payment, interest, principal_paid, closing_balance}
    """
    schedule = []
    balance = principal
    monthly = compute_mortgage_payment(principal, annual_rate, years)
    r = annual_rate / 12

    for year in range(1, years + 1):
        year_interest = 0.0
        year_principal = 0.0
        for _ in range(12):
            interest = balance * r
            princ = monthly - interest
            year_interest += interest
            year_principal += princ
            balance -= princ
        schedule.append({
            "year": year,
            "opening_balance": balance + year_principal,
            "annual_payment": monthly * 12,
            "interest": year_interest,
            "principal_paid": year_principal,
            "closing_balance": max(balance, 0),
        })
    return schedule
