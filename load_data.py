import os
import pandas as pd
from database import engine, Base, SessionLocal
import models

# Create all tables in the engine
Base.metadata.create_all(bind=engine)

DATA_DIR = "../data"

def load_csv_to_db():
    db = SessionLocal()
    try:
        # Clear existing data to prevent unique constraint errors
        print("Clearing existing data...")
        db.query(models.FairnessBuckets).delete()
        db.query(models.MacroContext).delete()
        db.query(models.OfferOutcomes).delete()
        db.query(models.SettlementOffers).delete()
        db.query(models.BehavioralSignals).delete()
        db.query(models.AccountDebt).delete()
        db.query(models.CustomerProfile).delete()
        db.commit()

        # Load Customer Profile
        print("Loading Customer Profile...")
        df_customers = pd.read_csv(os.path.join(DATA_DIR, "customer_profile.csv"))
        df_customers.to_sql("customer_profile", con=engine, if_exists="append", index=False)

        # Load Account Debt
        print("Loading Account Debt...")
        df_accounts = pd.read_csv(os.path.join(DATA_DIR, "account_debt.csv"))
        df_accounts.to_sql("account_debt", con=engine, if_exists="append", index=False)

        # Load Behavioral Signals
        print("Loading Behavioral Signals...")
        df_behavior = pd.read_csv(os.path.join(DATA_DIR, "behavioral_signals.csv"))
        df_behavior.to_sql("behavioral_signals", con=engine, if_exists="append", index=False)

        # Load Settlement Offers
        print("Loading Settlement Offers...")
        df_offers = pd.read_csv(os.path.join(DATA_DIR, "settlement_offers.csv"))
        df_offers.to_sql("settlement_offers", con=engine, if_exists="append", index=False)

        # Load Offer Outcomes
        print("Loading Offer Outcomes...")
        df_outcomes = pd.read_csv(os.path.join(DATA_DIR, "offer_outcomes.csv"))
        df_outcomes.to_sql("offer_outcomes", con=engine, if_exists="append", index=False)

        # Load Macro Context
        print("Loading Macro Context...")
        df_macro = pd.read_csv(os.path.join(DATA_DIR, "macro_context.csv"))
        df_macro.to_sql("macro_context", con=engine, if_exists="append", index=False)

        # Load Fairness Buckets
        print("Loading Fairness Buckets...")
        df_fairness = pd.read_csv(os.path.join(DATA_DIR, "fairness_buckets.csv"))
        df_fairness.to_sql("fairness_buckets", con=engine, if_exists="append", index=False)
        
        print("Data loading complete.")
    except Exception as e:
        print(f"Error loading data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    load_csv_to_db()
