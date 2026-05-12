# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from typing import Optional
# import asyncio
# import threading
# from datetime import datetime
# import logging
# import os
# from concurrent.futures import ThreadPoolExecutor
# from app.modules.core.configs.config import settings
# from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
# from app.modules.core.services.debug.debug_service import DebugService
# from app.modules.core.templates.email.email_template import email_template, email_template_with_click_button
 

# class EMailSenderService:
#     def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
#         self.host = settings.SMTP_HOST
#         self.port = settings.SMTP_PORT
#         self.user = settings.SMTP_AUTH_USER
#         self.password = settings.SMTP_AUTH_PASS
#         self.from_name = settings.SMTP_FROM_NAME
#         self.accept_language = accept_language
#         self.executor = ThreadPoolExecutor(max_workers=3)  # Limit concurrent email sending

    
#     def send_mail(self, to: str, subject: str, html_content: str):
#         try:
#             print(f"send_mail - to: {to}, subject: {subject}")
#             # settings
#             print(f"send_mail - host: {self.host}, port: {self.port}, user: {self.user}, password: {self.password}, from_name: {self.from_name}")
#             # Create SMTP session
#             server = smtplib.SMTP(self.host, self.port)
#             server.starttls()  # Secure the connection
#             server.login(self.user, self.password)

#             # Create the email
#             msg = MIMEMultipart()
#             msg["From"] = f"{self.from_name} <{self.user}>"
#             msg["To"] = to
#             msg["Subject"] = subject

#             # Attach HTML content
#             msg.attach(MIMEText(html_content, "html"))

#             # Send the email
#             server.sendmail(self.user, to, msg.as_string())
#             server.quit()

#             print(f"Email sent successfully to {to}.")
#             return True
#         except Exception as e:
#             print(f" in MailService Failed to send email: {e}")
#             raise
        
#     def sending_translated_email(self, 
#                                  email_to: str, 
#                                  subject: str, 
#                                  mail_title_translated: str,
#                                  mail_message_translated:str,
#                                  second_mail_message_translated:str,
#                                  mail_note_translated:str,
#                                  accept_language:str = 'fr'):
#         try: 
#             email_templ = email_template(
#                 mail_title_message=f"{mail_title_translated}",
#                 mail_message=f"{mail_message_translated}",
#                 second_mail_message=f"{second_mail_message_translated}",
#                 mail_note=f"{mail_note_translated}",
#                 accept_language=f"{accept_language}"
#             )
#             self.send_mail(to=email_to,subject= f"{subject}", html_content=email_templ)
#             DebugService.app_debug_print(f"Email sent successfully to {email_to}")
#         except Exception as e:
#             DebugService.app_debug_print(f"Failed to send email: {e}")
#             raise
        
        
#     def sending_translated_email_with_redirect_button(self, 
#                                                       email_to: str, 
#                                                       subject: str,
#                                                       action_button_text:str,
#                                                       action_button_url:str, 
#                                                       mail_title_translated: str,
#                                                       mail_message_translated:str,
#                                                       second_mail_message_translated:str,
#                                                       mail_note_translated:str,
#                                                       accept_language:str = 'fr'):
#         try: 
#             email_templ = email_template_with_click_button(
#                 mail_title_message=f"{mail_title_translated}",
#                 mail_message=f"{mail_message_translated}",
#                 second_mail_message=f"{second_mail_message_translated}",
#                 mail_note=f"{mail_note_translated}",
#                 accept_language=f"{accept_language}",
#                 action_button_text=f"{action_button_text}",
#                 action_button_url=f"{action_button_url}"
#             ) 
#             self.send_mail(to=email_to,subject= f"{subject}", html_content=email_templ)
#             DebugService.app_debug_print(f"Email sent successfully to {email_to}. with link button",True)
#         except Exception as e:
#             DebugService.app_debug_print(f"Failed to send email: {e}")
#             raise

#     async def send_mail_async(self, to: str, subject: str, html_content: str):
#         """Async version of send_mail that runs in a thread pool"""
#         try:
#             loop = asyncio.get_event_loop()
#             await loop.run_in_executor(self.executor, self.send_mail, to, subject, html_content)
#             return True
#         except Exception as e:
#             DebugService.app_debug_print(f"Failed to send email async: {e}")
#             raise

#     async def sending_translated_email_async(self,
#                                            email_to: str,
#                                            subject: str,
#                                            mail_title_translated: str,
#                                            mail_message_translated: str,
#                                            second_mail_message_translated: str,
#                                            mail_note_translated: str,
#                                            accept_language: str = 'fr'):
#         """Async version of sending_translated_email"""
#         try:
#             email_templ = email_template(
#                 mail_title_message=f"{mail_title_translated}",
#                 mail_message=f"{mail_message_translated}",
#                 second_mail_message=f"{second_mail_message_translated}",
#                 mail_note=f"{mail_note_translated}",
#                 accept_language=f"{accept_language}"
#             )
#             await self.send_mail_async(to=email_to, subject=f"{subject}", html_content=email_templ)
#             DebugService.app_debug_print(f"Email sent successfully to {email_to}")
#         except Exception as e:
#             DebugService.app_debug_print(f"Failed to send email: {e}")
#             raise

#     async def sending_translated_email_with_redirect_button_async(self,
#                                                                 email_to: str,
#                                                                 subject: str,
#                                                                 action_button_text: str,
#                                                                 action_button_url: str,
#                                                                 mail_title_translated: str,
#                                                                 mail_message_translated: str,
#                                                                 second_mail_message_translated: str,
#                                                                 mail_note_translated: str,
#                                                                 accept_language: str = 'fr'):
#         """Async version of sending_translated_email_with_redirect_button"""
#         try:
#             email_templ = email_template_with_click_button(
#                 mail_title_message=f"{mail_title_translated}",
#                 mail_message=f"{mail_message_translated}",
#                 second_mail_message=f"{second_mail_message_translated}",
#                 mail_note=f"{mail_note_translated}",
#                 accept_language=f"{accept_language}",
#                 action_button_text=f"{action_button_text}",
#                 action_button_url=f"{action_button_url}"
#             )
#             await self.send_mail_async(to=email_to, subject=f"{subject}", html_content=email_templ)
#             DebugService.app_debug_print(f"Email sent successfully to {email_to}. with link button", True)
#         except Exception as e:
#             DebugService.app_debug_print(f"Failed to send email: {e}")
#             raise

#     def send_email_background(self,
#                             email_to: str,
#                             subject: str,
#                             action_button_text: str,
#                             action_button_url: str,
#                             mail_title_translated: str,
#                             mail_message_translated: str,
#                             second_mail_message_translated: str,
#                             mail_note_translated: str,
#                             accept_language: str = 'fr'):
#         """Background task method for sending emails without blocking the request"""
#         try:
#             DebugService.app_debug_print(f"Starting background email send to {email_to}", True)
#             self.sending_translated_email_with_redirect_button(
#                 email_to=email_to,
#                 subject=subject,
#                 action_button_text=action_button_text,
#                 action_button_url=action_button_url,
#                 mail_title_translated=mail_title_translated,
#                 mail_message_translated=mail_message_translated,
#                 second_mail_message_translated=second_mail_message_translated,
#                 mail_note_translated=mail_note_translated,
#                 accept_language=accept_language
#             )
#             DebugService.app_debug_print(f"Background email sent successfully to {email_to}", True)
#         except Exception as e:
#             DebugService.app_debug_print(f"Failed to send background email to {email_to}: {e}", True)
#             # Don't raise here as this is a background task

#     def send_simple_email_background(
#         self,
#         email_to: str,
#         subject: str,
#         mail_title_translated: str,
#         mail_message_translated: str,
#         second_mail_message_translated: str,
#         mail_note_translated: str,
#         accept_language: str = 'fr'
#     ):
#         """Background task method for sending simple emails without blocking the request"""
#         try:
#             self._log_email_event("INFO", "Starting background simple email send", email_to, subject)

#             # Sending email (synchronous)
#             self.sending_translated_email(
#                 email_to=email_to,
#                 subject=subject,
#                 mail_title_translated=mail_title_translated,
#                 mail_message_translated=mail_message_translated,
#                 second_mail_message_translated=second_mail_message_translated,
#                 mail_note_translated=mail_note_translated,
#                 accept_language=accept_language
#             )

#             # Only log success if no exception
#             self._log_email_event("INFO", "Background simple email sent successfully", email_to, subject)

#         except Exception as e:
#             # Log error with full stack trace
#             self._log_email_event("ERROR", "Failed to send background simple email", email_to, subject, str(e))


#     def _setup_email_logger(self):
#         """Setup dedicated email logger for background tasks"""
#         self.email_logger = logging.getLogger('email_sender')
#         self.email_logger.setLevel(logging.INFO)

#         # Avoid duplicate handlers
#         if not self.email_logger.handlers:
#             # Create logs directory if it doesn't exist
#             log_dir = "logs"
#             if not os.path.exists(log_dir):
#                 os.makedirs(log_dir)

#             # File handler for email logs
#             email_log_file = os.path.join(log_dir, "email_sender.log")
#             file_handler = logging.FileHandler(email_log_file)
#             file_handler.setLevel(logging.INFO)

#             # Console handler for development
#             console_handler = logging.StreamHandler()
#             console_handler.setLevel(logging.INFO)

#             # Formatter
#             formatter = logging.Formatter(
#                 '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#             )
#             file_handler.setFormatter(formatter)
#             console_handler.setFormatter(formatter)

#             # Add handlers
#             self.email_logger.addHandler(file_handler)
#             if os.getenv("ENV") in ["local", "development"]:
#                 self.email_logger.addHandler(console_handler)

#     def _log_email_event(self, level: str, message: str, email_to: str = None, subject: str = None, error: str = None):
#         """Log email events with structured information"""
#         log_data = {
#             "timestamp": datetime.now().isoformat(),
#             "level": level,
#             "message": message,
#             "email_to": email_to,
#             "subject": subject,
#             "error": error,
#             "environment": os.getenv("ENV", "unknown")
#         }

#         log_message = f"{message}"
#         if email_to:
#             log_message += f" | To: {email_to}"
#         if subject:
#             log_message += f" | Subject: {subject}"
#         if error:
#             log_message += f" | Error: {error}"

#         if level.upper() == "ERROR":
#             self.email_logger.error(log_message)
#         elif level.upper() == "WARNING":
#             self.email_logger.warning(log_message)
#         else:
#             self.email_logger.info(log_message)