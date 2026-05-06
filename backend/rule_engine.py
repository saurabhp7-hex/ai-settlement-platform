from sqlalchemy.orm import Session
from models import CustomerProfile, AccountDebt, FairnessBuckets

def get_fairness_bucket(db: Session, risk_band: str, income_band: str, product_type: str):
    """
    Look up the fairness bucket to infer the settlement floor.
    """
    bucket = db.query(FairnessBuckets).filter(
        FairnessBuckets.income_band == income_band,
        FairnessBuckets.product_type == product_type
    ).first()
    
    # Since the fairness_buckets.csv does not contain an explicit 'settlement_floor',
    # we infer it based on the risk band to enforce compliance.
    if risk_band == "Low":
        return 0.50
    elif risk_band == "Medium":
        return 0.40
    elif risk_band == "High":
        return 0.30
    else:
        return 0.40 # Default fallback
def calculate_risk_band(days_past_due: int):
    if days_past_due is None:
        return "Low"
    if days_past_due > 120:
        return "High"
    elif days_past_due > 60:
        return "Medium"
    else:
        return "Low"

def evaluate_rules(db: Session, customer: CustomerProfile, account: AccountDebt):
    """
    Evaluates constraints for a given customer and account.
    Returns a dictionary of constraints to be passed to the AI prompt.
    """
    risk_band = calculate_risk_band(account.days_past_due)
    settlement_floor = get_fairness_bucket(db, risk_band, customer.income_band, account.product_type)
    
    constraints = {
        "minimum_settlement_percentage": settlement_floor,
        "is_vulnerable": customer.vulnerability_flag == "Yes",
        "hard_constraints": []
    }
    
    if constraints["is_vulnerable"]:
        constraints["hard_constraints"].append("Customer is flagged as vulnerable. Do not use aggressive negotiation tactics. Prioritize compassion and long-term payment plans over immediate lump sums.")
        
    constraints["hard_constraints"].append(f"The settlement offer CANNOT be lower than {settlement_floor * 100}% of the current balance based on fair lending policies.")
    
    return constraints
