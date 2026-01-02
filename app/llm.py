import google.generativeai as genai 
import pandas as pd
# doc_types=pd.read_excel("Doc_type field configuration.xlsx",sheet_name="doc_types")["doc_types"].tolist()  
def get_gemini_response(user_message):
    
    try:
        genai.configure(api_key='AIzaSyDiB4eEW2OLHKyAIQaBHfsGPaEnCwCeLH4')
        model = genai.GenerativeModel('gemini-2.5-flash')  # Ensure the model name is correct
        response = model.generate_content(f"You are a helpful assistant. User: {user_message}")
        if response and hasattr(response, 'candidates') and len(response.candidates) > 0:
            answer = response.candidates[0].content.parts[0].text
            return answer
        else:
            return "Sorry, I couldn't get a response from Gemini. Please try again."
    except Exception as e:
        
        return f"Error: {str(e)}"

def extract_sql_query(text):
    if "`" in text:
        clean_query = text.replace("`", "").replace("json", "")
        return clean_query
    else:
        return text

   
def get_gemini_response_with_context(text):
    
    
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
#     question_prompt_1 = f"""
# Document Types for Claims Classification:
# - Policy Documents: Coverage terms, conditions, exclusions, and endorsements.
# - Proof of Loss Documents: Signed declarations certifying extent and nature of loss/damage.
# - Insurance Certificates: Proof that coverage was in place for the claimed event.
# - Other: Any other relevant documents that do not fit the above categories.

# Given a document's text, classify it as one of the above types *only based on its content and meaning. Do not classify based on the file name or any other metadata*. If the document does not fit any of the above types, classify it as "Other".

# Examples:
# Document text: "This is a police report regarding an auto accident on 5th Ave."
# Output: Police Reports

# Document text: "The following invoice is for repairs to the insured vehicle."
# Output: Repair Estimates and Invoices

# Document text:
# {text}

# What is the most appropriate document type for the above text? Return only the document type name from the list above.
# """
    # context = """
    # Document Types for Claims Classification:

    # - Policy Documents: Coverage terms, conditions, exclusions, and endorsements.
    # - Proof of Loss Documents: Signed declarations certifying extent and nature of loss/damage.
    # - Insurance Certificates: Proof that coverage was in place for the claimed event.
    # - First Notice of Loss (FNOL) Documents: Initial claim reports describing incident, damages, and parties.
    # - Customer Communications: Correspondence from claimants (emails, letters, forms) with claim info.
    # - Investigation Reports: Findings on liability, fraud, or root cause.
    # - Vehicle Reports: Estimates, photos, invoices, registrations, or dealership loss docs for vehicles.
    # - ISO Match Reports: Similarity analysis between submitted docs and ISO database records.
    # - Property Reports: Repair estimates, property forms, photos, or living expense forms.
    # - Fraud Investigation Reports: Reports on suspicious activities or potential fraud.
    # - Adjuster Reports: Assessments, interviews, and recommendations by adjusters.
    # - Police Reports: Law enforcement reports on accidents, thefts, or incidents.
    # - Arbitration: Documents on dispute resolution outside court by a neutral arbitrator.
    # - Summons: Official notifications for legal appearances or actions.
    # - Legal and Demand Letters: Demand letters, court orders, subpoenas related to claims.
    # - Power of Attorney: Authorization for one person to act on behalf of another.
    # - Demand Packets: Formal requests for payment/action, outlining obligations and deadlines.
    # - Settlement Agreements: Agreements on settlement amounts/terms between parties.
    # - Medical Bills: Records of treatments, diagnoses, and bills for bodily injury claims.
    # - Explanation of Review (EOR): Concise analysis or justification of feedback.
    # - Authorizations: Granting or denying access to resources/actions.
    # - Repair Estimates and Invoices: Estimates/invoices for repairs by service providers.
    # - Claims Reserves and Payment Records: Records of claim reserves and payments.
    # - Subrogation and Recovery Documents: Docs for insurer recovery from responsible third parties.
    # - Photographs and Videos: Visual evidence of damages, scenes, or property.
    # - Appraisal Reports: Value assessments for property, vehicles, or insured items.
    # - Vendor Reports: Service provider/vendor reports on repairs or completed work.
    # - Other: Any other relevant documents that do not fit the above categories.

    # Given a document's text, classify it as one of the above types *only based on its content and meaning. DO not classify based on the file name or any other metadata*. If the document does not fit any of the above types, classify it as "Other".
    # """

    # question_prompt_1 = f"""{context}

    # Document text:
    # {text}

    # What is the most appropriate document type for the above text? Return only the document type name from the documents attached.
    # """
    # question_prompt_1 = f"""\n
    # data:{text}."""
    question_prompt_2=f""" You are an summarizer agent please provide the overall summary of the below attached body without missing important and vital information such as names,dates, events and any kind of document IDs.Do not add preamble as i have to feed the data into another file\n
    data:{text}"""
    response_1 = get_gemini_response(question_prompt_1)
    response_2 = get_gemini_response(question_prompt_2)
    response_1 = extract_sql_query(response_1)
    response_2 = extract_sql_query(response_2)
    
    # Remove any leading or trailing single quotes
    print(response_1,response_2)
    predicted_doc_type,summary=response_1,response_2
    
    return predicted_doc_type, summary