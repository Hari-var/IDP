from openai import AzureOpenAI
import google.generativeai as genai 
import pandas as pd
from dotenv import load_dotenv
import os
import time
from prometheus_client import Counter, Histogram

# API rotation state
CURRENT_API_INDEX = 0
API_KEYS = []

# Load API keys on module import
def load_api_keys():
    global API_KEYS
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(env_path)
    
    keys = []
    for i in range(1, 10):  # Check for up to 10 API keys
        key_name = f"Gemini_api_key_{i}" if i > 1 else "Gemini_api_key"
        key = os.environ.get(key_name)
        if key:
            keys.append(key)
    
    API_KEYS = keys
    return keys

def get_next_api_key():
    global CURRENT_API_INDEX
    if not API_KEYS:
        load_api_keys()
    
    if not API_KEYS:
        return None
    
    key = API_KEYS[CURRENT_API_INDEX]
    CURRENT_API_INDEX = (CURRENT_API_INDEX + 1) % len(API_KEYS)
    return key

# Initialize API keys
load_api_keys()

# AI metrics - use try/except to avoid duplicate registration
try:
    AI_REQUEST_COUNT = Counter('ai_requests_total', 'Total AI requests', ['model', 'operation'])
    AI_LATENCY = Histogram('ai_request_duration_seconds', 'AI request latency', ['model', 'operation'])
    AI_TOKEN_COUNT = Counter('ai_tokens_total', 'Total AI tokens used', ['model', 'type'])
    AI_ERROR_COUNT = Counter('ai_errors_total', 'Total AI errors', ['model', 'error_type'])
    AI_CONFIDENCE_SCORE = Histogram('ai_confidence_score', 'AI model confidence scores', ['model', 'operation'])
except ValueError:
    # Metrics already registered, get existing ones
    from prometheus_client import REGISTRY
    AI_REQUEST_COUNT = REGISTRY._names_to_collectors['ai_requests_total']
    AI_LATENCY = REGISTRY._names_to_collectors['ai_request_duration_seconds']
    AI_TOKEN_COUNT = REGISTRY._names_to_collectors['ai_tokens_total']
    AI_ERROR_COUNT = REGISTRY._names_to_collectors['ai_errors_total']
    AI_CONFIDENCE_SCORE = REGISTRY._names_to_collectors['ai_confidence_score']
# doc_types=pd.read_excel("Doc_type field configuration.xlsx",sheet_name="doc_types")["doc_types"].tolist()  
def get_gemini_response(user_message):
    start_time = time.time()
    AI_REQUEST_COUNT.labels(model='gemini', operation='general').inc()
    
    try:
        print("DEBUG: Loading .env file...")
        # Load .env from parent directory since we're in app/ folder
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        print(f"DEBUG: Looking for .env at: {env_path}")
        load_dotenv(env_path)
        print(f"DEBUG: Current working directory: {os.getcwd()}")
        api=os.environ.get("Gemini_api_key")
        print(f"DEBUG: API key loaded: {'Yes' if api else 'No'}")
        print(f"DEBUG: API key length: {len(api) if api else 0}")
        if not api:
            print("DEBUG: Available environment variables:")
            for key in os.environ.keys():
                if 'gemini' in key.lower() or 'api' in key.lower():
                    print(f"  {key}")
        genai.configure(api_key=api)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(f"You are a helpful assistant. User: {user_message}")
        
        # Track metrics
        latency = time.time() - start_time
        print(latency)
        AI_LATENCY.labels(model='gemini', operation='general').observe(latency)
        
        if response and hasattr(response, 'candidates') and len(response.candidates) > 0:
            answer = response.candidates[0].content.parts[0].text
            
            # Track token usage
            if hasattr(response, 'usage_metadata'):
                AI_TOKEN_COUNT.labels(model='gemini', type='input').inc(response.usage_metadata.prompt_token_count)
                AI_TOKEN_COUNT.labels(model='gemini', type='output').inc(response.usage_metadata.candidates_token_count)
            
            return answer
        else:
            return "Sorry, I couldn't get a response from Gemini. Please try again."
    except Exception as e:
        AI_ERROR_COUNT.labels(model='gemini', error_type=type(e).__name__).inc()
        return f"Error: {str(e)}"

def extract_sql_query(text):
    if "`" in text:
        clean_query = text.replace("`", "").replace("json", "")
        return clean_query
    else:
        return text

def get_azure_response(text):
    try:
        endpoint = "https://defaultresourcegroup-ccan-resource-0475.cognitiveservices.azure.com/"
        deployment = "gpt-4.1-mini-312634"
        subscription_key = os.getenv("AZURE_AI_API_KEY")
        api_version = "2024-12-01-preview"

        if not subscription_key:
            return "Error: AZURE_OPENAI_KEY not found in environment variables"

        client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=endpoint,
            api_key=subscription_key,
        )

        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant.",
                },
                {
                    "role": "user",
                    "content": text,
                }
            ],
            max_tokens=1000,
            temperature=0.7,
            model=deployment
        )

        # Track Azure token usage
        if hasattr(response, 'usage') and response.usage:
            AI_TOKEN_COUNT.labels(model='azure', type='input').inc(response.usage.prompt_tokens)
            AI_TOKEN_COUNT.labels(model='azure', type='output').inc(response.usage.completion_tokens)
            AI_TOKEN_COUNT.labels(model='azure', type='total_input').inc(response.usage.prompt_tokens)
            AI_TOKEN_COUNT.labels(model='azure', type='total_output').inc(response.usage.completion_tokens)

        return response.choices[0].message.content
    except Exception as e:
        AI_ERROR_COUNT.labels(model='azure', error_type=type(e).__name__).inc()
        return f"Azure Error: {str(e)}" 
   
def get_gemini_response_with_context(text):
    start_time = time.time()
    AI_REQUEST_COUNT.labels(model='gemini', operation='classification').inc()
    
    question_prompt_1=f"""You are an expert document classifier for insurance claims processing. Your task is to classify documents based solely on their textual content and meaning.

## DOCUMENT CLASSIFICATION CATEGORIES:

### POLICY DOCUMENTS
**Policy and Coverage Documents:**
- Policy Declarations/Coverage terms, conditions, exclusions, and endorsements
- Insurance Certificates: Proof that coverage was in place for claimed event
- Customer Communications: Written correspondence between customers and insurance companies

### LOSS AND DAMAGE DOCUMENTATION  
**Proof of Loss Documents:**
- First Notice of Loss (FNOL): Initial claim reports detailing incident or loss
- Signed declarations from claimant certifying extent and nature of loss/damage

### INVESTIGATION AND ASSESSMENT
**Investigation Reports:**
- Reports documenting investigation findings related to liability, fraud detection, or root cause analysis
- Vehicle Reports: Reports related to estimates/lease/potential invoices/bills/vehicle registration/dealership
- ISO/Match Reports: ISO match reports provide detailed insights into similarities between submitted documents
- Property Reports: Reports documenting evaluation and assessment of damages, interviews, and liability
- Fraud Investigation Reports: Reports documenting suspicious activities, inconsistencies, or evidence of potential fraud
- Adjuster Reports: Reports created by insurance adjusters during the assessment of damages, interviews, and liability
- Police Reports: Incident reports from law enforcement agencies documenting details of accidents, thefts, or other incidents
- Arbitration: Documents outlining the procedures, agreements, and decisions involved in resolving disputes through arbitration

**Summons:** Legal documents served to notify parties of legal proceedings

### LEGAL AND REGULATORY
**Legal and Demand Letters:**
- Litigation-related documentation such as demand letters, court orders, subpoenas related to claims
- Power of Attorney: Legal document granting one person authority to act on behalf of another
- Demand Packets: Formal documents sent to request payment or action, typically outlining obligations, deadlines, and potential consequences

### SETTLEMENT AGREEMENTS
- Settlement/plea agreements, sanctions, and terms negotiated between parties involved in disputes

### MEDICAL RECORDS AND BILLS
**Medical Bills:** Medical records, diagnostic test, diagnostic test results, medical equipment highlighting key points and reasoning
**Explanation of Benefits (EOB):** Documents explaining coverage details for medical treatments or services
**Authorizations:** Documents outlining the process of granting or denying access to resources or actions under specific permissions and roles

### FINANCIAL AND PAYMENT DOCUMENTS
**Repair Estimates and Invoices:**
- Maintenance and invoices for repairing vehicles, property, or equipment, often uploaded by service providers
- Claims Reserves and Payment: Records of claims-reserves/funds set aside for claims and payments made throughout the claims
- Subrogation and Recovery Documents: Documentation related to recovery where the insurer seeks recovery from a third party responsible for the loss

### SUPPORTING EVIDENCE
**Photographs and Videos:** Visual evidence supporting claims, such as pictures or videos of damages, accident scenes, or property
**Appraisal Reports:** Appraisal documents detailing the value of property, vehicles, or other insured items
**Other Reports:** Any other relevant supporting documentation

## CLASSIFICATION INSTRUCTIONS:

1. **Read the document text carefully and analyze its primary purpose and content**
2. **Focus on what the document IS, not what it mentions** (e.g., a police report mentioning medical bills is still a Police Report)
3. **Look for key identifying phrases and document structure**
4. **If uncertain between categories, choose the most specific match**
5. **If the document doesn't clearly fit any category, classify as "Other Reports"**

## KEY IDENTIFYING PHRASES:

**Policy Documents:** "policy number", "coverage limits", "deductible", "premium", "policyholder", "effective date", "terms and conditions"

**Proof of Loss:** "notice of loss", "claim number", "date of loss", "extent of damage", "sworn statement", "claimant signature"

**Police Reports:** "incident report", "case number", "officer badge", "citation", "violation", "arrested", "police department"

**Medical Records:** "patient", "diagnosis", "treatment", "physician", "hospital", "medical history", "prescription"

**Repair Estimates:** "estimate", "labor costs", "parts", "repair", "invoice", "service provider", "total cost"

**Investigation Reports:** "investigation findings", "analysis", "assessment", "liability determination", "evidence review"

**Legal Documents:** "subpoena", "court order", "attorney", "legal proceeding", "settlement", "power of attorney"

## EXAMPLES:

**Input:** "POLICE INCIDENT REPORT - Case #12345. On March 15, 2024, at approximately 2:30 PM, officers responded to a motor vehicle accident at the intersection of Main St and Oak Ave..."
**Output:** Police Reports

**Input:** "ESTIMATE FOR VEHICLE REPAIR. Vehicle: 2020 Honda Civic. Labor: $850. Parts: $1,200. Total: $2,050. Estimated completion: 5 business days..."
**Output:** Repair Estimates and Invoices

**Input:** "FIRST NOTICE OF LOSS. Policy Number: ABC123456. Date of Loss: 03/15/2024. I, John Smith, hereby provide notice that damage occurred to my insured property..."
**Output:** First Notice of Loss (FNOL)

**Input:** "SETTLEMENT AGREEMENT. This agreement is entered into between XYZ Insurance Company and John Doe regarding claim number 789456..."
**Output:** Settlement/Plea Agreements

---

## DOCUMENT TO CLASSIFY:

Document Text:
{text}

## RESPONSE FORMAT:
Based on the content analysis, classify this document as one of the specific document types listed above. Return only the exact document type name (e.g., "Police Reports", "First Notice of Loss (FNOL)", "Repair Estimates and Invoices", etc.).

**Classification Result:**"""
    
    summary_prompt = f"""Provide a concise 2-3 sentence summary of this document focusing on the key information and purpose:

{text}

Summary:"""
    
    # Try each API key until one works
    for attempt in range(len(API_KEYS) if API_KEYS else 1):
        try:
            api = get_next_api_key()
            if not api:
                return "Error", "No API keys available"
                
            genai.configure(api_key=api)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Get classification
            classification_response = get_azure_response(question_prompt_1)
            print(classification_response)
            # Get summary
            summary_response = model.generate_content(summary_prompt)
            
            # Track metrics
            latency = time.time() - start_time
            AI_LATENCY.labels(model='gemini', operation='classification').observe(latency)
            
            doc_type = "Other"
            summary = "Unable to generate summary"
            
            if classification_response and hasattr(classification_response, 'candidates') and len(classification_response.candidates) > 0:
                doc_type = classification_response.candidates[0].content.parts[0].text.strip()
                
                # Track classification tokens
                if hasattr(classification_response, 'usage_metadata'):
                    AI_TOKEN_COUNT.labels(model='gemini', type='prediction_input').inc(classification_response.usage_metadata.prompt_token_count)
                    AI_TOKEN_COUNT.labels(model='gemini', type='prediction_output').inc(classification_response.usage_metadata.candidates_token_count)
                    AI_TOKEN_COUNT.labels(model='gemini', type='total_input').inc(classification_response.usage_metadata.prompt_token_count)
                    AI_TOKEN_COUNT.labels(model='gemini', type='total_output').inc(classification_response.usage_metadata.candidates_token_count)
            
            if summary_response and hasattr(summary_response, 'candidates') and len(summary_response.candidates) > 0:
                summary = summary_response.candidates[0].content.parts[0].text.strip()
                
                # Track summary tokens
                if hasattr(summary_response, 'usage_metadata'):
                    AI_TOKEN_COUNT.labels(model='gemini', type='summary_input').inc(summary_response.usage_metadata.prompt_token_count)
                    AI_TOKEN_COUNT.labels(model='gemini', type='summary_output').inc(summary_response.usage_metadata.candidates_token_count)
                    AI_TOKEN_COUNT.labels(model='gemini', type='total_input').inc(summary_response.usage_metadata.prompt_token_count)
                    AI_TOKEN_COUNT.labels(model='gemini', type='total_output').inc(summary_response.usage_metadata.candidates_token_count)
            
            return doc_type, summary
            
        except Exception as e:
            error_msg = str(e).lower()
            # Check if it's a rate limit error
            if 'quota' in error_msg or 'rate limit' in error_msg or 'exceeded' in error_msg:
                print(f"API key {attempt + 1} hit rate limit, trying next key...")
                AI_ERROR_COUNT.labels(model='gemini', error_type='RateLimit').inc()
                continue
            else:
                # Other error, return immediately
                AI_ERROR_COUNT.labels(model='gemini', error_type=type(e).__name__).inc()
                return "Error", f"Classification failed: {str(e)}"
    
    # All API keys exhausted
    return "Error", "All API keys have exceeded their limits"
   
if __name__ == "__main__":
    get_gemini_response_with_context("FIRST NOTICE OF LOSS. Policy Number: ABC123456. Date of loss: 03/15/2024. Claim number: CL789. I hereby provide notice that damage occurred to my insured property. Claimant signature required.")