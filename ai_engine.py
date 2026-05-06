import os
import json
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
import mlflow

load_dotenv()

class SettlementRecommendation(BaseModel):
    recommended_percentage: float = Field(description="The recommended settlement percentage (e.g. 0.45 for 45%)")
    acceptance_probability: float = Field(description="The predicted probability that the customer will accept this offer (0.0 to 1.0)")
    completion_risk: str = Field(description="The risk level of the customer failing to complete the payment plan (Low, Medium, High)")
    explanation: str = Field(description="A detailed human-readable explanation of why this offer was recommended, citing specific customer and account factors, and compliance rules.")

# Set up the Azure OpenAI model
llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
    openai_api_version=os.getenv("AZURE_API_VERSION", "2023-05-15"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "https://placeholder.openai.azure.com/"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY", "placeholder"),
    temperature=0.2,
)

parser = JsonOutputParser(pydantic_object=SettlementRecommendation)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an AI assistant for a collections department at a bank. Your goal is to recommend the optimal settlement offer for a delinquent account. "
               "You must balance maximizing recovery, customer affordability, and regulatory compliance. "
               "You MUST strictly adhere to any hard constraints provided. "
               "Return your response in valid JSON matching the following schema:\n{format_instructions}"),
    ("user", "Customer Profile:\n{customer_context}\n\n"
             "Account Debt Details:\n{account_context}\n\n"
             "Behavioral Signals:\n{behavior_context}\n\n"
             "Macro Economic Context:\n{macro_context}\n\n"
             "Compliance and Rule Engine Constraints:\n{constraints}\n\n"
             "Based on this data, provide the optimal settlement recommendation.")
])

chain = prompt | llm | parser

def generate_recommendation(
    customer_context: str, 
    account_context: str, 
    behavior_context: str, 
    macro_context: str, 
    constraints: str,
    settlement_floor: float
) -> dict:
    
    # MLflow Tracking
    try:
        mlflow.set_tracking_uri("sqlite:///mlruns.db")
        mlflow.set_experiment("Settlement_Recommendations")
        with mlflow.start_run():
            # Log inputs
            mlflow.log_param("customer_vulnerable", "Yes" if "Customer is flagged as vulnerable" in constraints else "No")
            mlflow.log_param("settlement_floor", settlement_floor)
            
            # Execute LangChain
            response = chain.invoke({
                "customer_context": customer_context,
                "account_context": account_context,
                "behavior_context": behavior_context,
                "macro_context": macro_context,
                "constraints": constraints,
                "format_instructions": parser.get_format_instructions()
            })
            
            # Log outputs
            mlflow.log_metric("recommended_percentage", response.get("recommended_percentage", 0))
            mlflow.log_metric("acceptance_probability", response.get("acceptance_probability", 0))
            
            return response
            
    except Exception as e:
        # Fallback if Azure OpenAI is not configured or fails
        print(f"Error calling LLM: {e}")
            
        return {
            "recommended_percentage": max(0.50, settlement_floor),
            "acceptance_probability": 0.65,
            "completion_risk": "Medium",
            "explanation": f"FALLBACK MODE: Unable to reach Azure OpenAI. Using standard heuristic recommendation. Please check API keys. Error: {str(e)}"
        }
