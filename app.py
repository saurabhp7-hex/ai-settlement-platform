import streamlit as st
import requests
import pandas as pd
import os
from dotenv import load_dotenv

# Load configuration
load_dotenv()
PORT = int(os.getenv("PORT", 8000))
API_BASE_URL = f"http://127.0.0.1:{PORT}"

st.set_page_config(page_title="AI Settlement Platform", layout="wide")

st.title("AI-Driven Intelligent Settlement Platform")
st.markdown("---")

# --- Sidebar: Account Selection ---
st.sidebar.header("Delinquent Accounts")

def select_account(account_id):
    st.session_state["selected_account"] = account_id

@st.cache_data(ttl=60)
def fetch_cases():
    try:
        res = requests.get(f"{API_BASE_URL}/api/cases")
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.sidebar.error("Failed to load accounts. Is the backend running?")
        return []

cases = fetch_cases()

if not cases:
    st.sidebar.write("No cases found or backend not reachable.")
else:
    # Show a static table with limited columns for quick overview
    cases_df = pd.DataFrame(cases)

    # Provide a list of selectable items with visual highlight
    if "selected_account" not in st.session_state:
        st.session_state["selected_account"] = None

    for idx, row in cases_df.iterrows():
        selectedRow = row["account_id"] == st.session_state.get("selected_account")
        label = f"{row['account_id']} - DPD: {row['days_past_due']} - Bal: ${row['current_balance']}"

        st.sidebar.button(label, 
                          key=f"select_{row['account_id']}", 
                          type="primary" if selectedRow else "secondary",
                          use_container_width=True,
                          on_click=select_account,
                          args=(row['account_id'],)
                          )
        # if st.sidebar.button(label, key=f"select_{row['account_id']}", type= "primary" if selectedRow else  "secondary"):
        #     st.session_state["selected_account"] = row["account_id"]

    account_id = st.session_state["selected_account"]
    if account_id is None:
        st.sidebar.write("Select a case from the list.")
        st.stop()
    
    try:
        # Fetch detailed info for the selected account
        res = requests.get(f"{API_BASE_URL}/api/cases/{account_id}")
        res.raise_for_status()
        case_details = res.json()
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Customer Profile")
            st.write(f"**Customer ID:** {case_details['customer']['customer_id']}")
            st.write(f"**Income Band:** {case_details['customer']['income_band']}")
            st.write(f"**Employment:** {case_details['customer']['employment_status']}")
            
            vuln = case_details['customer']['vulnerability_flag']
            if vuln == "Yes":
                st.error(f"**Vulnerable Customer:** {vuln}")
            else:
                st.success(f"**Vulnerable Customer:** {vuln}")
                
        with col2:
            st.subheader("Behavioral & Macro Context")
            st.write(f"**Broken Promises:** {case_details['behavior']['broken_promises_count']}")
            st.write(f"**Last Call Sentiment:** {case_details['behavior']['last_call_sentiment']}")
            st.write(f"**Economic Stress Flag:** {case_details['macro']['economic_stress_flag']}")
        
        st.markdown("---")
        
        # --- Previous Offers History ---
        st.subheader("Previous Offers")
        previous_offers = case_details.get("previous_offers", [])
        if previous_offers:
            po_df = pd.DataFrame(previous_offers)
            # Format columns for display
            po_df["Offer %"] = (po_df["ai_recommended_offer_percent"] * 100).astype(str) + "%"
            po_df["Agent %"] = po_df["actual_agent_offer_percent"].apply(lambda x: f"{x*100}%" if pd.notnull(x) else "N/A")
            po_df["Response"] = po_df["customer_response"].fillna("Pending")
            po_df["Installments"] = po_df["installment_months"].fillna(1).astype(int)
            po_df = po_df[["Offer %", "Agent %", "Response", "Installments", "human_override_flag"]]
            st.dataframe(po_df, use_container_width=True)
        else:
            st.info("No previous settlement offers found for this account.")
            
        st.markdown("---")
        
        # --- AI Recommendation Section ---
        st.subheader("AI Co-pilot")
        
        if st.button("Run AI Recommendation Engine", type="primary"):
            with st.spinner("Analyzing rules and generating recommendation..."):
                try:
                    rec_res = requests.post(f"{API_BASE_URL}/api/cases/{account_id}/recommend")
                    rec_res.raise_for_status()
                    rec_data = rec_res.json()
                    st.session_state[f'recommendation_{account_id}'] = rec_data
                except Exception as e:
                    st.error(f"Error generating recommendation: {e}")
        
        # Display recommendation if it exists in session state
        rec_data = st.session_state.get(f'recommendation_{account_id}')
        
        if rec_data:
            st.success("AI Recommendation Generated!")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Suggested Settlement", f"{rec_data['recommended_percentage'] * 100:.0f}%")
            m2.metric("Acceptance Probability", f"{rec_data['acceptance_probability'] * 100:.0f}%")
            m3.metric("Completion Risk", rec_data['completion_risk'])
            m4.metric("Recommended Plan", f"{rec_data.get('recommended_installment_months', 1)} Months")
            
            st.info(f"**Reasoning & Compliance:**\n\n{rec_data['explanation']}")
            st.info(f"**Payment Strategy Reasoning:**\n\n{rec_data.get('payment_strategy_explanation', 'N/A')}")
            
            st.markdown("---")
            
            # --- Final Decision Section ---
            st.subheader("Log Final Decision")
            
            agent_offer = st.number_input("Final Offer (%)", min_value=0.0, max_value=100.0, value=float(rec_data['recommended_percentage'] * 100), step=1.0)
            customer_resp = st.radio("Customer Response", ["Accepted", "Rejected"], horizontal=True)
            
            if st.button("Log Decision", type="primary", key=f"log_{account_id}"):
                is_override = (agent_offer / 100.0) != rec_data['recommended_percentage']
                # If accepted, we use the AI's recommended installment plan
                install_months = rec_data.get('recommended_installment_months', 1) if customer_resp == "Accepted" else None
                
                payload = {
                    "ai_recommended_offer_percent": rec_data['recommended_percentage'],
                    "actual_agent_offer_percent": agent_offer / 100.0,
                    "human_override_flag": "Yes" if is_override else "No",
                    "customer_response": customer_resp,
                    "installment_months": install_months
                }
                try:
                    log_res = requests.post(f"{API_BASE_URL}/api/cases/{account_id}/decide", json=payload)
                    log_res.raise_for_status()
                    st.success(f"Decision logged successfully! ({customer_resp})")
                    # Clear the recommendation state so the user can move to the next case safely
                    del st.session_state[f'recommendation_{account_id}']
                except Exception as e:
                    st.error(f"Failed to log decision: {e}")
                        
    except Exception as e:
        st.error(f"Failed to load case details: {e}")
