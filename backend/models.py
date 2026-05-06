from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base

class CustomerProfile(Base):
    __tablename__ = "customer_profile"
    customer_id = Column(String, primary_key=True, index=True)
    age_band = Column(String)
    income_band = Column(String)
    employment_status = Column(String)
    residential_type = Column(String)
    region_type = Column(String)
    vulnerability_flag = Column(String)
    dataset_split = Column(String)
    
    accounts = relationship("AccountDebt", back_populates="customer")

class AccountDebt(Base):
    __tablename__ = "account_debt"
    account_id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, ForeignKey("customer_profile.customer_id"))
    product_type = Column(String)
    original_balance = Column(Float)
    current_balance = Column(Float)
    interest_rate_band = Column(String)
    fees_accrued = Column(Float)
    days_past_due = Column(Integer)
    loan_tenure_months = Column(Integer)
    legal_stage = Column(String)
    region_id = Column(String)
    
    customer = relationship("CustomerProfile", back_populates="accounts")
    behavioral_signals = relationship("BehavioralSignals", back_populates="account")
    settlement_offers = relationship("SettlementOffers", back_populates="account")

class BehavioralSignals(Base):
    __tablename__ = "behavioral_signals"
    signal_id = Column(String, primary_key=True, index=True)
    account_id = Column(String, ForeignKey("account_debt.account_id"))
    customer_id = Column(String)
    past_payment_frequency = Column(String)
    avg_payment_percent = Column(Float)
    broken_promises_count = Column(Integer)
    last_contact_outcome = Column(String)
    last_call_sentiment = Column(String)
    digital_engagement_score = Column(Integer)
    response_latency_days = Column(Integer)
    
    account = relationship("AccountDebt", back_populates="behavioral_signals")

class SettlementOffers(Base):
    __tablename__ = "settlement_offers"
    offer_id = Column(String, primary_key=True, index=True)
    account_id = Column(String, ForeignKey("account_debt.account_id"))
    offer_sequence_number = Column(Integer)
    ai_recommended_offer_percent = Column(Float)
    actual_agent_offer_percent = Column(Float, nullable=True)
    offer_type = Column(String)
    offer_percent = Column(Float)
    installment_months = Column(Integer)
    emi_percent_of_income = Column(Float)
    offer_channel = Column(String)
    offer_timestamp = Column(String)
    response_timestamp = Column(String)
    days_between_offer_and_response = Column(Integer)
    ai_confidence_score = Column(Float)
    human_override_flag = Column(String, nullable=True)
    override_reason_code = Column(String)
    customer_response = Column(String)
    considered_offer_percents = Column(String)
    
    account = relationship("AccountDebt", back_populates="settlement_offers")

class OfferOutcomes(Base):
    __tablename__ = "offer_outcomes"
    offer_id = Column(String, primary_key=True)
    payment_started_flag = Column(String)
    payment_completed_flag = Column(String)
    default_stage = Column(String)
    time_to_default_days = Column(Integer)
    net_amount_collected = Column(Float)
    write_off_amount = Column(Float)
    completion_timestamp = Column(String)

class MacroContext(Base):
    __tablename__ = "macro_context"
    macro_context_id = Column(String, primary_key=True, index=True)
    region_id = Column(String)
    month = Column(String)
    unemployment_rate = Column(Float)
    cost_of_living_index = Column(Integer)
    economic_stress_flag = Column(String)

class FairnessBuckets(Base):
    __tablename__ = "fairness_buckets"
    fairness_bucket_id = Column(String, primary_key=True, index=True)
    risk_band = Column(String)
    income_band = Column(String)
    dpd_band = Column(String)
    product_type = Column(String)
