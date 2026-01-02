# # import smtplib # For sending emails
# # from email.mime.text import MIMEText





# # def send_email_notification(file_name, source, doc_type):
# #     print("Sending email notification...")
# #     subject = "Document Review Required"
# #     body = f"""
# #     Dear Team,

# #     A document requires your review.
    
# #     **File Name:** {file_name}
# #     **Predicted Type:** {doc_type} (requires manual classification/handling)
# #     **Upload Source:** {source}

# #     Please investigate and classify this document.

# #     Thank you,
# #     Automated Document Processor
# #     """

# #     msg = MIMEText(body)
# #     msg["Subject"] = subject
# #     msg["From"] = EMAIL_SENDER
# #     msg["To"] = EMAIL_RECEIVER

# #     try:
# #         with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server: # Use SMTP_SSL for direct SSL, or SMTP + starttls
# #             # If using SMTP (not SMTP_SSL) and TLS, you'd do:
# #             # server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
# #             # server.starttls()
# #             server.login(EMAIL_SENDER, EMAIL_PASSWORD)
# #             server.send_message(msg)
# #         print(f"Notification email sent successfully to {EMAIL_RECEIVER} for file '{file_name}'.")
# #     except Exception as e:
# #         print(f"Failed to send notification email for '{file_name}': {e}")
# #         print("Please check your email configuration (sender, password, SMTP server, port) and network connectivity.")



# from azure.communication.email import EmailClient
# from azure.core.credentials import AzureKeyCredential

# credential = AzureKeyCredential("BUWBUP5PpFKZywNMg94DJg7HGROomxyNbCdbYoBFL7ovl6Cvds1gJQQJ99BFACULyCpydQxwAAAAAZCSbulm")
# endpoint = "https://shashank-communication-service.india.communication.azure.com"
# client = EmailClient(endpoint, credential)
# def send_email_notification(file_name, source, doc_type):
#     message = {
#         "content": {
#             "subject": "Document Review Required",
            
#             "html": f"""
#                 <p>Dear Team,</p>
#                 <p>A document requires your review.</p>
#                 <p><strong>File Name:</strong> {file_name}</p>
#                 <p><strong>Predicted Type:</strong> {doc_type} (requires manual classification/handling)</p>
#                 <p><strong>Upload Source:</strong> {source}</p>
#                 <p>Please investigate and classify this document.</p>
#                 <p>Thank you,<br>Automated Document Processor</p>
#                 """
            
#         },
#         "recipients": {
#             "to": [
#                 {
#                     "address": "shashank.tudum@valuemomentum.com",
#                     "displayName": "Cloud Quick Labs"
#                 }
#             ]
#         },
#         "senderAddress": "DoNotReply@88295e93-5cda-4535-921f-7241cc7d1612.azurecomm.net"
#     }

#     poller = EmailClient.begin_send(client, message)
#     result = poller.result()
#     print(result)
    