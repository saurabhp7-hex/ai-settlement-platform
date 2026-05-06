from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import json
import uuid

from database import engine, Base, get_db
import models
from rule_engine import evaluate_rules
from ai_engine import generate_recommendation

app = FastAPI(title="AI Settlement Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/cases")
def list_cases(db: Session = Depends(get_db)):
    """Returns a list of accounts that are eligible for settlement."""
    accounts = db.query(models.AccountDebt).filter(models.AccountDebt.days_past_due > 0).limit(50).all()
    
    result = []
    for acc in accounts:
        result.append({
            "account_id": acc.account_id,
            "customer_id": acc.customer_id,
            "product_type": acc.product_type,
            "current_balance": acc.current_balance,
            "days_past_due": acc.days_past_due
        })
    return result

@app.get("/api/cases/{account_id}")
def get_case_details(account_id: str, db: Session = Depends(get_db)):
    """Get the full context for a specific case."""
    account = db.query(models.AccountDebt).filter(models.AccountDebt.account_id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    customer = account.customer
    behavior = db.query(models.BehavioralSignals).filter(models.BehavioralSignals.account_id == account_id).first()
    macro = db.query(models.MacroContext).filter(models.MacroContext.region_id == customer.region_type).first()
    
    return {
        "account": {
            "account_id": account.account_id,
            "product_type": account.product_type,
            "original_balance": account.original_balance,
            "current_balance": account.current_balance,
            "days_past_due": account.days_past_due,
            "legal_stage": account.legal_stage
        },
        "customer": {
            "customer_id": customer.customer_id,
            "age_band": customer.age_band,
            "income_band": customer.income_band,
            "employment_status": customer.employment_status,
            "vulnerability_flag": customer.vulnerability_flag
        },
        "behavior": {
            "broken_promises_count": behavior.broken_promises_count if behavior else 0,
            "last_call_sentiment": behavior.last_call_sentiment if behavior else "Unknown",
        },
        "macro": {
            "unemployment_rate": macro.unemployment_rate if macro else None,
            "economic_stress_flag": macro.economic_stress_flag if macro else "Unknown"
        }
    }

@app.post("/api/cases/{account_id}/recommend")
def recommend_settlement(account_id: str, db: Session = Depends(get_db)):
    account = db.query(models.AccountDebt).filter(models.AccountDebt.account_id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    customer = account.customer
    behavior = db.query(models.BehavioralSignals).filter(models.BehavioralSignals.account_id == account_id).first()
    macro = db.query(models.MacroContext).filter(models.MacroContext.region_id == customer.region_type).first()
    
    # Evaluate Rules
    constraints = evaluate_rules(db, customer, account)
    
    # Format contexts for LLM
    customer_context = f"Age: {customer.age_band}, Income: {customer.income_band}, Employment: {customer.employment_status}, Vulnerable: {customer.vulnerability_flag}"
    account_context = f"Product: {account.product_type}, Balance: ${account.current_balance}, DPD: {account.days_past_due}, Legal Stage: {account.legal_stage}"
    behavior_context = f"Broken Promises: {behavior.broken_promises_count if behavior else 0}, Last Call Sentiment: {behavior.last_call_sentiment if behavior else 'N/A'}"
    macro_context = f"Economic Stress: {macro.economic_stress_flag if macro else 'N/A'}"
    constraints_str = json.dumps(constraints["hard_constraints"])
    
    recommendation = generate_recommendation(
        customer_context, 
        account_context, 
        behavior_context, 
        macro_context, 
        constraints_str,
        constraints["minimum_settlement_percentage"]
    )
    
    return recommendation

@app.post("/api/cases/{account_id}/decide")
def log_decision(account_id: str, decision: dict, db: Session = Depends(get_db)):
    offer_id = f"O{str(uuid.uuid4())[:8].upper()}"
    
    new_offer = models.SettlementOffers(
        offer_id=offer_id,
        account_id=account_id,
        ai_recommended_offer_percent=decision.get("ai_recommended_offer_percent"),
        actual_agent_offer_percent=decision.get("actual_agent_offer_percent"),
        human_override_flag=decision.get("human_override_flag", "No")
    )
    db.add(new_offer)
    db.commit()
    
    return {"status": "success", "message": "Decision logged successfully."}

if __name__ == "__main__":
    import uvicorn
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
