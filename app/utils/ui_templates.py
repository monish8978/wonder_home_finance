def get_welcome_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "Welcome to Wonder Home Finance Limited.\n\nThis is Citra, your personal virtual assistant. Our Home Loan products are designed to meet your specific needs. To ensure you get the best experience, please select the below language to start."
            },
            {
                "type": "Button",
                "id": "serviceType",
                "style": "expanded",
                "choices": [
                    {"id": "English", "title": "English", "value": "English"},
                    {"id": "Hindi", "title": "Hindi", "value": "Hindi"}
                ]
            }
        ]
    }

def get_main_menu_card(message="I'll be glad to assist you, please select the option from below."):
    return {
        "type": "adaptiveCard",
        "body": [
            {"type": "TextBlock", "text": message},
            {
                "type": "Button",
                "id": "serviceType",
                "style": "expanded",
                "choices": [
                    {"id": "Apply For New Loan", "title": "Apply For New Loan", "value": "Apply For New Loan"},
                    {"id": "Existing Customer", "title": "Existing Customer", "value": "Existing Customer"},
                    {"id": "Branch Locator", "title": "Branch Locator", "value": "Branch Locator"},
                    {"id": "Calculators", "title": "Calculators", "value": "Calculators"},
                    {"id": "Customer Support", "title": "Customer Support", "value": "Customer Support"}
                ]
            }
        ]
    }

def get_ask_mobile_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "Please enter your valid 10-digit mobile number to continue with the verification process."
            }
        ]
    }

def get_otp_sent_card(resend=False):
    text = "Your One-Time Password (OTP) has been sent successfully..." if not resend else "Your One-Time Password (OTP) has been resent successfully..."
    return {
        "type": "adaptiveCard",
        "body": [
            {"type": "TextBlock", "text": text},
            {
                "type": "Button",
                "id": "serviceType",
                "style": "expanded",
                "choices": [
                    {"id": "Change Number", "title": "Change Number", "value": "Change Number"},
                    {"id": "RESEND OTP", "title": "RESEND OTP", "value": "RESEND OTP"}
                ]
            }
        ]
    }

def get_invalid_response_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {"type": "TextBlock", "text": "Invalid response. Please choose from the options shared below."}
        ]
    }

def get_new_loan_consent_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "By providing your information, you consent to Wonder Home Finance to be contacted via SMS or Whatsapp or Email or phone calls for marketing and information purposes."
            },
            {
                "type": "Button",
                "id": "serviceType",
                "style": "expanded",
                "choices": [
                    {"id": "Proceed", "title": "Proceed", "value": "Proceed"}
                ]
            }
        ]
    }

def get_ec_menu_card(customer_name):
    return {
        "type": "adaptiveCard",
        "body": [
            {"type": "TextBlock", "text": f"Hi {customer_name}, I'll be glad to assist you, please select the option from below."},
            {
                "type": "Button",
                "id": "serviceType",
                "style": "expanded",
                "choices": [
                    {"id": "Apply For Top Up Loan", "title": "Apply For Top Up Loan", "value": "Apply For Top Up Loan"},
                    {"id": "My Loans", "title": "My Loans", "value": "My Loans"},
                    {"id": "Branch Locator", "title": "Branch Locator", "value": "Branch Locator"},
                    {"id": "Documents", "title": "Documents", "value": "Documents"},
                    {"id": "Install WHFL App", "title": "Install WHFL App", "value": "Install WHFL App"},
                    {"id": "Pay EMI Now", "title": "Pay EMI Now", "value": "Pay EMI Now"},
                    {"id": "Contact Us", "title": "Contact Us", "value": "Contact Us"},
                    {"id": "Refer a Friend", "title": "Refer a Friend", "value": "Refer a Friend"},
                    {"id": "Back To Menu", "title": "Back To Menu", "value": "Back To Menu"}
                ]
            }
        ]
    }

def get_customer_support_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {"type": "TextBlock", "text": "Do you need any further assistance?\n\nPlease select an option below:"},
            {
                "type": "Button",
                "id": "faqCategory",
                "style": "expanded",
                "choices": [
                    {"id": "Yes", "title": "Yes", "value": "Yes"},
                    {"id": "No", "title": "No", "value": "No"},
                    {"id": "Back To Menu", "title": "Back To Menu", "value": "Back To Menu"}
                ]
            }
        ]
    }

def get_loan_options_card(customer_name):
    return {
        "type": "adaptiveCard",
        "body": [
            {"type": "TextBlock", "text": f"Thanks, {customer_name}! Which of these loan options would you like to explore today?"},
            {
                "type": "Button",
                "id": "loanType",
                "style": "expanded",
                "choices": [
                    {"id": "Home Purchase Loan", "title": "Home Purchase Loan", "value": "Home Purchase Loan"},
                    {"id": "Plot Pur. + Construction", "title": "Plot Pur. + Construction", "value": "Plot Pur. + Construction"},
                    {"id": "Home Renovation Loan", "title": "Home Renovation Loan", "value": "Home Renovation Loan"},
                    {"id": "Home Extension Loan", "title": "Home Extension Loan", "value": "Home Extension Loan"},
                    {"id": "Loan Against Property", "title": "Loan Against Property", "value": "Loan Against Property"},
                    {"id": "Balance Transfer", "title": "Balance Transfer", "value": "Balance Transfer"},
                    {"id": "Back To Menu", "title": "Back To Menu", "value": "Back To Menu"}
                ]
            }
        ]
    }

def get_doc_menu_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "Please choose the type of document you would like to download from the list below."
            },
            {
                "type": "Button",
                "id": "Documents",
                "style": "expanded",
                "choices": [
                    {"id": "Interest Certificate", "title": "Interest Certificate", "value": "Interest Certificate"},
                    {"id": "Repayment Schedule", "title": "Repayment Schedule", "value": "Repayment Schedule"},
                    {"id": "Welcome Letter", "title": "Welcome Letter", "value": "Welcome Letter"},
                    {"id": "Back To Menu", "title": "Back To Menu", "value": "Back To Menu"},
                    {"id": "Main Menu", "title": "Main Menu", "value": "Main Menu"}
                ]
            }
        ]
    }

def get_refer_friend_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "flow",
                "id": "referfriend",
                "style": "expanded",
                "flow": {
                    "name": "refer_friend",
                    "language": {"code": "en"},
                    "components": [{"type": "button", "sub_type": "flow", "index": "0", "parameters": [{"type": "action", "action": {"flow_token": "123"}}]}]
                }
            }
        ]
    }

def get_cta_sent_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "Thank you for connecting with Wonder Home Finance!\n\nIf you need any further assistance, feel free to reach out. Wishing you a wonderful day!"
            },
            {
                "type": "Button",
                "id": "serviceType",
                "style": "expanded",
                "choices": [
                    {"id": "Customer Support", "title": "Customer Support", "value": "Customer Support"},
                    {"id": "Back To Menu", "title": "Back To Menu", "value": "Back To Menu"},
                    {"id": "Main Menu", "title": "Main Menu", "value": "Main Menu"}
                ]
            }
        ]
    }

def get_otp_failed_menu_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "You have entered an incorrect OTP three times. You can request a new OTP to try again, or update your mobile number if you wish to use a different one."
            },
            {
                "type": "Button",
                "id": "serviceType",
                "style": "expanded",
                "choices": [
                    {"id": "Change Number", "title": "Change Number", "value": "Change Number"},
                    {"id": "RESEND OTP", "title": "RESEND OTP", "value": "RESEND OTP"}
                ]
            }
        ]
    }

def get_agent_transfer_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "Hi 👋\n\nWe are connecting you to a live agent.\n\nPlease wait for a moment while we transfer your chat.\n\nThank you for your patience 😊"
            }
        ]
    }

def get_visit_website_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {"type": "TextBlock", "text": "Tap the Visit Website button below to view the branch nearest to your location."},
            {
                "type": "Button",
                "id": "serviceType",
                "style": "expanded",
                "choices": [
                    {"id": "Visit website", "title": "Visit website", "value": "Visit website"},
                    {"id": "Back To Menu", "title": "Back To Menu", "value": "Back To Menu"},
                    {"id": "Main Menu", "title": "Main Menu", "value": "Main Menu"}
                ]
            }
        ]
    }

def get_customer_support_categories_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "Welcome to Wonder Home Finance Customer Support.\n\nPlease select the service request that best matches your concern."
            },
            {
                "type": "Button",
                "id": "serviceType",
                "style": "expanded",
                "choices": [
                    {"id": "FCL/SOA/LOD Request", "title": "FCL / SOA / LOD Request", "value": "FCL / SOA / LOD Request"},
                    {"id": "EMI/ Pre-EMI Related", "title": "EMI / Pre-EMI Related", "value": "EMI/ Pre-EMI Related"},
                    {"id": "Refund", "title": "Refund", "value": "Refund"},
                    {"id": "ROI/Tenure Miscomm", "title": "ROI/Tenure Miscomm", "value": "ROI/Tenure Miscomm"},
                    {"id": "Cibil related", "title": "CIBIL Related", "value": "Cibil related"},
                    {"id": "Others", "title": "Others", "value": "Others"},
                    {"id": "Back To Menu", "title": "Back To Menu", "value": "Back To Menu"},
                    {"id": "Main Menu", "title": "Main Menu", "value": "Main Menu"}
                ]
            }
        ]
    }

def get_loan_submission_success_card(applicant_name):
    return {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": f"Dear {applicant_name},\n\nThank you for applying for a loan with Wonder Homes Finance.\n\nYour application details have been successfully submitted to our verification team. Our experts will review your information and contact you shortly regarding the next steps in the loan process.\n\nYour CIBIL report and eligibility update will be shared with you on WhatsApp shortly."
            },
            {
                "type": "Button",
                "id": "postApplicationOptions",
                "style": "expanded",
                "choices": [
                    {"id": "Customer Support", "title": "Customer Support", "value": "Customer Support"},
                    {"id": "Back To Menu", "title": "Back To Menu", "value": "Back To Menu"},
                    {"id": "Main Menu", "title": "Main Menu", "value": "Main Menu"}
                ]
            }
        ]
    }

def get_critical_contact_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "Thank you for reaching out.\n\nFor assistance with this request, please contact our customer support team at 1800 102 1002 or email us at hello@wonderhfl.com.\n\nOur team will be happy to help you."
            },
            {
                "type": "Button",
                "id": "serviceType",
                "style": "expanded",
                "choices": [
                    {"id": "Back To Menu", "title": "Back To Menu", "value": "Back To Menu"},
                    {"id": "Main Menu", "title": "Main Menu", "value": "Main Menu"}
                ]
            }
        ]
    }

def get_no_loan_associated_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "Based on the information provided, there is currently no existing loan associated with your profile in our records. If you require any further assistance, please reach out."
            },
            {
                "type": "Button",
                "id": "serviceType",
                "style": "expanded",
                "choices": [
                    {"id": "Main Menu", "title": "Main Menu", "value": "Main Menu"},
                    {"id": "Back To Menu", "title": "Back To Menu", "value": "Back To Menu"}
                ]
            }
        ]
    }

def get_apply_loan_flow_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "flow",
                "id": "loanApplication",
                "style": "expanded",
                "flow": {
                    "name": "apply_loan_application",
                    "language": {"code": "en"},
                    "components": [
                        {
                            "type": "button",
                            "sub_type": "flow",
                            "index": "0",
                            "parameters": [
                                {
                                    "type": "action",
                                    "action": {
                                        "flow_token": "123"
                                    }
                                }
                            ]
                        }
                    ]
                }
            }
        ],
        "actions": []
    }

def get_no_loan_found_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "Based on the information provided, there is currently no existing loan associated with your profile in our records. If you require any further assistance or clarification, please feel free to reach out."
            },
            {
                "type": "Button",
                "id": "serviceType",
                "style": "expanded",
                "choices": [
                    {"id": "Back To Menu", "title": "Back To Menu", "value": "Back To Menu"},
                    {"id": "Main Menu", "title": "Main Menu", "value": "Main Menu"}
                ]
            }
        ]
    }

def get_loan_verification_failed_card():
    return {
        "type": "adaptiveCard",
        "body": [
            {
                "type": "TextBlock",
                "text": "We are unable to verify the loan number with the registered mobile number. Kindly update your mobile number at the nearest branch or raise a request through the WHFL Mobile App for assistance."
            },
            {
                "type": "Button",
                "id": "serviceType",
                "style": "expanded",
                "choices": [
                    {"id": "Main Menu", "title": "Main Menu", "value": "Main Menu"},
                    {"id": "Back To Menu", "title": "Back To Menu", "value": "Back To Menu"}
                ]
            }
        ]
    }
