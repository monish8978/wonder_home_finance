from app.db.mongo import db_manager
from app.utils.logger import logger
from app.utils import ui_templates
from app.services.otp_service import OTPService
from app.services.loan_service import LoanService
from datetime import datetime, timedelta

SESSION_TIMEOUT = timedelta(minutes=1000)

class ChatManager:
    @staticmethod
    async def get_user(wa_id: str):
        db = db_manager.get_db()
        return await db["chat_state"].find_one({"wa": wa_id})

    @staticmethod
    async def save_user(wa_id: str, data: dict):
        db = db_manager.get_db()
        await db["chat_state"].update_one(
            {"wa": wa_id},
            {"$set": {**data, "lastInteractionAt": datetime.utcnow()}},
            upsert=True
        )

    @staticmethod
    async def reset_flow(wa_id: str, clear_mobile=False):
        user = await ChatManager.get_user(wa_id)
        existing_mobile = user.get("mobile") if user else None
        
        db = db_manager.get_db()
        await db["chat_state"].delete_one({"wa": wa_id})
        
        new_state = {
            "wa": wa_id,
            "step": "LANG",
            "attempt": 0,
            "createdAt": datetime.utcnow(),
            "lastInteractionAt": datetime.utcnow()
        }
        if not clear_mobile and existing_mobile:
            new_state["mobile"] = existing_mobile
            
        await db["chat_state"].insert_one(new_state)
        return new_state

    @staticmethod
    async def process_message(wa_id: str, msg: str):
        msg_clean = msg.strip()
        cmd = msg_clean.upper()
        
        user = await ChatManager.get_user(wa_id)
        
        # Global Commands
        if cmd == "RESTART":
            await ChatManager.reset_flow(wa_id, clear_mobile=True)
            return ui_templates.get_welcome_card()

        # WhatsApp Flow Data Handle (Refer a Friend)
        if isinstance(msg, str) and "screen_0_Name_0" in msg:
            await ChatManager.save_user(wa_id, {"refer_data": msg, "step": "REFER_FRND"})
            return ui_templates.get_loan_submission_success_card("Friend") # Using generic success card

        if not user or (datetime.utcnow() - user.get("lastInteractionAt", datetime.utcnow()) > SESSION_TIMEOUT):
            user = await ChatManager.reset_flow(wa_id)
            return ui_templates.get_welcome_card()

        step = user.get("step", "LANG")
        
        # Greetings handle
        if msg_clean.lower() in ["hi", "hello", "hey", "start"]:
            if user.get("mobile"):
                await ChatManager.save_user(wa_id, {"step": "MAIN_MENU"})
                return ui_templates.get_main_menu_card()
            else:
                await ChatManager.reset_flow(wa_id)
                return ui_templates.get_welcome_card()

        # State Machine
        if step == "LANG":
            if msg_clean in ["English", "Hindi"]:
                await ChatManager.save_user(wa_id, {"step": "ASK_MOBILE", "lang": msg_clean})
                return ui_templates.get_ask_mobile_card()
            return ui_templates.get_welcome_card()

        elif step == "ASK_MOBILE":
            if msg_clean.isdigit() and len(msg_clean) == 10:
                otp_res = await OTPService.generate_otp(msg_clean)
                if otp_res and otp_res.get("operationStatus") == "1":
                    await ChatManager.save_user(wa_id, {
                        "mobile": msg_clean,
                        "smsRecordId": otp_res.get("smsRecordId"),
                        "step": "OTP",
                        "attempt": 0
                    })
                    return ui_templates.get_otp_sent_card()
            return ui_templates.get_ask_mobile_card()

        elif step == "OTP":
            if msg_clean == "RESEND OTP":
                otp_res = await OTPService.generate_otp(user["mobile"])
                if otp_res and otp_res.get("operationStatus") == "1":
                    await ChatManager.save_user(wa_id, {"smsRecordId": otp_res.get("smsRecordId")})
                    return ui_templates.get_otp_sent_card(resend=True)
            
            if msg_clean == "Change Number":
                await ChatManager.save_user(wa_id, {"step": "ASK_MOBILE"})
                return ui_templates.get_ask_mobile_card()

            # Validate OTP
            res = await OTPService.validate_otp(user["smsRecordId"], msg_clean)
            if res and res.get("operationStatus") == "1":
                await ChatManager.save_user(wa_id, {"step": "MAIN_MENU", "attempt": 0})
                return ui_templates.get_main_menu_card("Thanks for submitting the OTP! I'll be glad to assist you.")
            
            # Increment attempt
            attempts = user.get("attempt", 0) + 1
            if attempts >= settings.MAX_ATTEMPTS:
                await ChatManager.save_user(wa_id, {"step": "OTP_FAILED_MENU", "attempt": 0})
                return ui_templates.get_otp_failed_menu_card()
                
            await ChatManager.save_user(wa_id, {"attempt": attempts})
            return {"type": "adaptiveCard", "body": [{"type": "TextBlock", "text": f"Invalid OTP. Attempt {attempts}/{settings.MAX_ATTEMPTS}. Please try again."}]}

        elif step == "OTP_FAILED_MENU":
            if msg_clean == "RESEND OTP":
                otp_res = await OTPService.generate_otp(user["mobile"])
                if otp_res and otp_res.get("operationStatus") == "1":
                    await ChatManager.save_user(wa_id, {"step": "OTP", "smsRecordId": otp_res.get("smsRecordId"), "attempt": 0})
                    return ui_templates.get_otp_sent_card(resend=True)
            elif msg_clean == "Change Number":
                await ChatManager.save_user(wa_id, {"step": "ASK_MOBILE"})
                return ui_templates.get_ask_mobile_card()
            return ui_templates.get_otp_failed_menu_card()

        elif step == "MAIN_MENU":
            if msg_clean == "Existing Customer":
                # Check for existing loan details (using mobile from session or demo)
                mobile = user.get("mobile", "8076893187")
                loan_data = await LoanService.get_loan_details(mobile)
                
                if loan_data and loan_data.get("customerLoanDetails"):
                    from app.tasks.pdf_tasks import generate_loan_summary_pdf_task
                    generate_loan_summary_pdf_task.delay(wa_id)
                    
                    summary, customer_name = LoanService.format_loans_for_whatsapp(loan_data)
                    await ChatManager.save_user(wa_id, {"step": "EC_LOAN", "customer_name": customer_name})
                    
                    # Return the EC_LOAN card (summary + request for 5 digits)
                    return {
                        "type": "adaptiveCard",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": f"Hi {customer_name}, please find below the summary of your active home loan account with us.\n\n{summary} \n\nEnter the last 5 digits of your loan account number for more details."
                            }
                        ]
                    }
                else:
                    return ui_templates.get_no_loan_found_card()

            elif msg_clean == "Apply For New Loan":
                await ChatManager.save_user(wa_id, {"step": "NEW_LOAN_CONSENT"})
                return ui_templates.get_new_loan_consent_card()

            elif msg_clean == "Branch Locator":
                from app.tasks.whatsapp_tasks import send_whatsapp_template_task
                send_whatsapp_template_task.delay(wa_id, "branchlocator")
                return ui_templates.get_cta_sent_card()

            elif msg_clean == "Calculators":
                from app.tasks.whatsapp_tasks import send_whatsapp_template_task
                send_whatsapp_template_task.delay(wa_id, "calculators")
                return ui_templates.get_cta_sent_card()

            elif msg_clean == "Customer Support":
                from app.tasks.whatsapp_tasks import send_whatsapp_template_task
                send_whatsapp_template_task.delay(wa_id, "fqa_wonder_home")
                await ChatManager.save_user(wa_id, {"step": "CUSTOMER_SUPPORT"})
                return ui_templates.get_customer_support_card()

            return ui_templates.get_main_menu_card()

        elif step == "NEW_LOAN_CONSENT":
            if msg_clean == "Proceed":
                await ChatManager.save_user(wa_id, {"step": "NP_NAME"})
                return {"type": "adaptiveCard", "body": [{"type": "TextBlock", "text": "Please enter your full name."}]}
            return ui_templates.get_new_loan_consent_card()

        elif step == "EC_MENU":
            if msg_clean == "Documents":
                await ChatManager.save_user(wa_id, {"step": "DOC_MENU"})
                return ui_templates.get_doc_menu_card()
            
            elif msg_clean == "Refer a Friend":
                return ui_templates.get_refer_friend_card()

            elif msg_clean == "Branch Locator":
                from app.tasks.whatsapp_tasks import send_whatsapp_template_task
                send_whatsapp_template_task.delay(wa_id, "branchlocator")
                return ui_templates.get_cta_sent_card()
            
            elif msg_clean == "Pay EMI Now":
                # Trigger WhatsApp CTA template for payment (async task)
                from app.tasks.whatsapp_tasks import send_whatsapp_template_task
                send_whatsapp_template_task.delay(wa_id, "payemi")
                return ui_templates.get_cta_sent_card()

            elif msg_clean == "Install WHFL App":
                from app.tasks.whatsapp_tasks import send_whatsapp_template_task
                send_whatsapp_template_task.delay(wa_id, "whfl_app")
                return ui_templates.get_cta_sent_card()

            elif msg_clean == "Apply For Top Up Loan":
                await ChatManager.save_user(wa_id, {"step": "Apply_For_Top_Up_Loan"})
                return {"type": "adaptiveCard", "body": [{"type": "TextBlock", "text": "Enter the top-up loan amount you want to apply for."}]}

            elif msg_clean == "My Loans":
                # Show summary and stay in EC_MENU (mimicking legacy behavior)
                return {"type": "adaptiveCard", "body": [{"type": "TextBlock", "text": "Your active loans summary:\n- Loan ID: WHFL00123\n- Principal: ₹15,00,000\n- ROI: 8.5%\n- Tenure: 180 months"}]}

            elif msg_clean == "Contact Us":
                return ui_templates.get_critical_contact_card()

            elif msg_clean == "Back To Menu":
                await ChatManager.save_user(wa_id, {"step": "MAIN_MENU"})
                return ui_templates.get_main_menu_card()

            return ui_templates.get_ec_menu_card(user.get("customer_name", "Customer"))

        elif step == "DOC_MENU":
            if msg_clean == "Back To Menu":
                await ChatManager.save_user(wa_id, {"step": "EC_MENU"})
                return ui_templates.get_ec_menu_card(user.get("customer_name", "Customer"))
            
            if msg_clean in ["Interest Certificate", "Repayment Schedule", "Welcome Letter"]:
                from app.tasks.pdf_tasks import generate_interest_certificate_task
                generate_interest_certificate_task.delay(wa_id, msg_clean)
                return ui_templates.get_cta_sent_card()
                
            return ui_templates.get_doc_menu_card()

        elif step == "NP_NAME":
            await ChatManager.save_user(wa_id, {"step": "NP_LOAN_OPTIONS", "full_name": msg_clean})
            return ui_templates.get_loan_options_card(msg_clean)

        elif step == "NP_LOAN_OPTIONS":
            if msg_clean == "Back To Menu":
                await ChatManager.save_user(wa_id, {"step": "MAIN_MENU"})
                return ui_templates.get_main_menu_card()
            
            await ChatManager.save_user(wa_id, {"step": "NP_FLOW", "loan_type": msg_clean})
            return ui_templates.get_apply_loan_flow_card()

        elif step == "NP_FLOW":
            import json
            try:
                # Flow responses are sent as JSON strings
                flow_data = json.loads(msg)
                pan = flow_data.get("screen_0_Enter_Pan_No_1")
                if pan:
                    from app.tasks.cibil_tasks import verify_pan_and_check_cibil_task
                    verify_pan_and_check_cibil_task.delay(wa_id, pan, user.get("full_name"))
                    
                    await ChatManager.save_user(wa_id, {"step": "MAIN_MENU"})
                    return ui_templates.get_loan_submission_success_card(user.get("full_name", "Applicant"))
            except Exception as e:
                logger.error(f"Failed to parse flow response: {e}")
            
            return ui_templates.get_apply_loan_flow_card()

        elif step == "EC_LOAN":
            mobile = user.get("mobile", "8076893187")
            res = await LoanService.validate_loan_with_crm(mobile, msg_clean)
            
            if res["status"] == "MATCH":
                customer_name = res["customer_name"]
                await ChatManager.save_user(wa_id, {"step": "EC_MENU", "customer_name": customer_name})
                return ui_templates.get_ec_menu_card(customer_name)
            else:
                return ui_templates.get_loan_verification_failed_card()

        elif step == "Apply_For_Top_Up_Loan":
            # Any input is treated as amount (simplification)
            await ChatManager.save_user(wa_id, {"step": "MAIN_MENU"})
            return ui_templates.get_loan_submission_success_card(user.get("customer_name", "Customer"))

        elif step == "CUSTOMER_SUPPORT":
            if msg_clean == "Yes":
                await ChatManager.save_user(wa_id, {"step": "CRITICAL_CASE"})
                return ui_templates.get_customer_support_categories_card()
            elif msg_clean == "No":
                return ui_templates.get_cta_sent_card()
            elif msg_clean == "Back To Menu":
                await ChatManager.save_user(wa_id, {"step": "MAIN_MENU"})
                return ui_templates.get_main_menu_card()
            return ui_templates.get_customer_support_card()

        elif step == "CRITICAL_CASE":
            if msg_clean == "Back To Menu":
                await ChatManager.save_user(wa_id, {"step": "MAIN_MENU"})
                return ui_templates.get_main_menu_card()
            
            # For any selection, return agent transfer card (legacy behavior)
            return ui_templates.get_agent_transfer_card()

        # Global command handler for "Main Menu"
        if msg_clean == "Main Menu":
            await ChatManager.save_user(wa_id, {"step": "MAIN_MENU"})
            return ui_templates.get_main_menu_card()

        return ui_templates.get_invalid_response_card()
