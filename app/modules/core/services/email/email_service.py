import re
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional,Set, List, Dict, Any
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.services.response.response_service import ResponseService
import dns.resolver
from app.modules.auth.enums.common import MessageCategory
from app.modules.core.constants.common import DISPOSABLE_DOMAINS, FREE_EMAIL_DOMAINS

class EmailService:
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE,company_domains: Optional[Set[str]] = None):
        """
        Initialize the email validator with optional company domains whitelist.
        
        Args:
            company_domains: Set of known company domains to whitelist
        """
        self.company_domains = company_domains or set() 
        # Common public sector domains
        self.public_sector_suffixes = {'.gov', '.mil', '.org', '.ngo', '.edu', '.ac.'}
        self.accept_language = accept_language
        
        
    def is_valid_email(self, email: str) -> bool:
        """Validate if a string is a properly formatted email address."""
        import re
        email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        return re.match(email_regex, email) is not None
    
    def normalize_email(self, email: str) -> str:
        """Normalize an email address by converting to lowercase and trimming whitespace."""
        if not email:
            return ""
        return email.lower().strip()
    
    def extract_domain(self, email: str) -> str:
        """Extract the domain part from an email address."""
        if not self.is_valid_email(email):
            return ""
        return email.split('@')[1]
        
        
    def is_company_email(self, email: str, *, check_mx: bool = True, strict: bool = False) -> bool:
        """Validate if a string is a properly formatted company email address.
        
        Args:
            email: The email address to validate
            check_mx: Whether to verify MX records for the domain (default: True)
            strict: Whether to require domain in whitelist if whitelist exists (default: False)
            
        Returns:
            bool: True if the email appears to be a company email, False otherwise
        """
        # Input validation
        if not email or not isinstance(email, str):
            return False
            
        if not self.is_valid_email(email):
            return False
            
        domain = self.extract_domain(email).lower()
        
        # Check against free email providers
        if self._is_free_email_domain(domain):
            return False
            
        # Check public sector domains
        if self._is_public_sector_domain(domain):
            return False
            
        # Check disposable domains if available
        if hasattr(self, 'disposable_domains') and domain in self.disposable_domains:
            return False
            
        # Check against company whitelist (if in strict mode)
        if self.company_domains:
            if strict and domain not in self.company_domains:
                return False
            elif domain in self.company_domains:
                return True
                
        # Verify MX records if enabled
        if check_mx and not self._has_valid_mx_records(domain):
            return False
            
        return True

    def _is_free_email_domain(self, domain: str) -> bool:
        """Check if domain is a free email provider or its subdomain."""
        # Check exact match
        if domain in FREE_EMAIL_DOMAINS:
            return True
            
        # Check subdomains of free providers
        for free_domain in FREE_EMAIL_DOMAINS:
            if domain.endswith(f'.{free_domain}'):
                return True
                
        # Check for personal domain patterns
        personal_keywords = {'mail', 'email', 'personal', 'my', 'name', 'user'}
        first_part = domain.split('.')[0]
        return any(keyword in first_part for keyword in personal_keywords)

    def _is_public_sector_domain(self, domain: str) -> bool:
        """Check if domain belongs to public sector."""
        return any(domain.endswith(suffix) for suffix in self.public_sector_suffixes)

    def _has_valid_mx_records(self, domain: str) -> bool:
        """Verify if domain has valid MX records."""
        try:
            # Timeout after 3 seconds
            answers = dns.resolver.resolve(domain, 'MX', lifetime=3)
            return len(answers) > 0
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, 
                dns.resolver.NoNameservers, dns.resolver.Timeout):
            return False
        except Exception:
            # Other DNS issues (possibly temporary)
            return True  # Give benefit of doubt
    # def is_company_email(self, email: str) -> bool:
    #     """Validate if a string is a properly formatted company email address.
        
    #     Args:
    #         email: The email address to validate
            
    #     Returns:
    #         bool: True if the email appears to be a company email, False otherwise
    #     """
    #     if not email or not isinstance(email, str):
    #         return False
            
    #     if not self.is_valid_email(email):
    #         return False
            
    #     # List of common free email providers and disposable domains
         
        
    #     domain = self.extract_domain(email).lower()
        
    #     # Check if the domain is a free email provider
    #     if domain in FREE_EMAIL_DOMAINS:
    #         return False
            
    #     # Check for educational domains
    #     if domain.endswith('.edu') or domain.endswith('.ac.'):
    #         return False
            
    #     # Check for government domains
    #     if domain.endswith('.gov') or domain.endswith('.mil'):
    #         return False
            
    #     # Check for common public sector domains
    #     if domain.endswith('.org') or domain.endswith('.ngo'):
    #         return False
            
    #     # Check for known disposable email domains (you can use your existing list)
    #     if hasattr(self, 'disposable_domains') and domain in self.disposable_domains:
    #         return False
            
    #     # Check for subdomains of free email providers
    #     for free_domain in FREE_EMAIL_DOMAINS:
    #         if domain.endswith(f'.{free_domain}'):
    #             return False
                
    #     # Check for common patterns in personal domains
    #     personal_keywords = ['mail', 'email', 'personal', 'my', 'name', 'user']
    #     if any(keyword in domain.split('.')[0] for keyword in personal_keywords):
    #         return False
            
    #     # Optional: Check domain MX records to verify it's a real company domain
    #     # (This would require additional implementation)
        
    #     # Optional: Check against a whitelist of known company domains
    #     # if hasattr(self, 'company_domains') and domain not in self.company_domains:
    #     #     return False
            
    #     return True
    
    def is_disposable_email(self, email: str) -> bool:
        """Check if the email is from a disposable email provider."""
        domain = self.extract_domain(email)
        return domain in DISPOSABLE_DOMAINS
    
    def mask_email(self, email: str) -> str:
        """Mask an email address for privacy (e.g., j***e@example.com)."""
        if not self.is_valid_email(email):
            return email
        
        username, domain = email.split('@')
        if len(username) <= 2:
            masked_username = username[0] + '*' * (len(username) - 1)
        else:
            masked_username = username[0] + '*' * (len(username) - 2) + username[-1]
        
        return f"{masked_username}@{domain}"
    
    def parse_email_parts(self, email: str) -> Dict[str, str]:
        """Parse an email into its component parts."""
        if not self.is_valid_email(email):
            return {"username": "", "domain": "", "tld": ""}
        
        username, domain_part = email.split('@')
        domain_parts = domain_part.split('.')
        tld = domain_parts[-1]
        domain = '.'.join(domain_parts[:-1])
        
        return {
            "username": username,
            "domain": domain,
            "tld": tld,
            "full_domain": domain_part
        }
    
    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = True, 
                  cc: List[str] = None, bcc: List[str] = None, attachments: List[str] = None,
                  from_email: str = None, reply_to: str = None) -> Dict[str, Any]:
        """Send an email with optional attachments, CC, and BCC recipients."""
        if not self.is_valid_email(to_email):
            return {"success": False, "message": "Invalid recipient email address"}
        
        try:
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['To'] = to_email
            
            # Set default from_email if not provided
            if from_email is None:
                from_email = os.getenv("EMAIL_FROM", "noreply@example.com")
            msg['From'] = from_email
            
            if reply_to:
                msg.add_header('Reply-To', reply_to)
            
            # Add CC recipients if provided
            if cc:
                msg['Cc'] = ", ".join(cc)
                
            # Add BCC recipients if provided (not visible in headers)
            
            # Attach the email body
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Add attachments if provided
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, 'rb') as file:
                            part = MIMEApplication(file.read(), Name=os.path.basename(attachment_path))
                        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                        msg.attach(part)
            
            # Get SMTP settings from environment or use defaults
            smtp_server = os.getenv("SMTP_SERVER", "localhost")
            smtp_port = int(os.getenv("SMTP_PORT", 25))
            smtp_username = os.getenv("SMTP_USERNAME", "")
            smtp_password = os.getenv("SMTP_PASSWORD", "")
            use_tls = os.getenv("SMTP_USE_TLS", "False").lower() == "true"
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if use_tls:
                    server.starttls()
                
                if smtp_username and smtp_password:
                    server.login(smtp_username, smtp_password)
                
                # Combine all recipients for sending
                all_recipients = [to_email]
                if cc:
                    all_recipients.extend(cc)
                if bcc:
                    all_recipients.extend(bcc)
                
                server.sendmail(from_email, all_recipients, msg.as_string())
                
            return {"success": True, "message": "Email sent successfully"}
            
        except Exception as e:
            return {"success": False, "message": f"Failed to send email: {str(e)}"}
     
    
    def validate_mx_record(self, email: str) -> bool:
        """Validate if the email domain has valid MX records (requires DNS lookup)."""
        try:
            import dns.resolver
            domain = self.extract_domain(email)
            mx_records = dns.resolver.resolve(domain, 'MX')
            return len(mx_records) > 0
        except Exception:
            return False
    
    def get_email_greeting(self, name: str = None) -> str:
        """Get a localized email greeting based on the accept_language."""
        greeting = ResponseService.get_response_message(MessageCategory.EMAIL_TEMPLATE, "GREETING", self.accept_language)
        if name:
            return f"{greeting} {name},"
        return f"{greeting},"