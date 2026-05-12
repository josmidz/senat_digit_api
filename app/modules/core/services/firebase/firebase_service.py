"""
Firebase Admin SDK Service
Handles Firebase initialization and token verification
"""

import os
import firebase_admin
from firebase_admin import credentials, auth, messaging
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status


class FirebaseService:
    """Service for Firebase Admin SDK operations"""

    _initialized = False

    @classmethod
    def initialize(cls, credentials_path: Optional[str] = None):
        """
        Initialize Firebase Admin SDK

        Args:
            credentials_path: Path to Firebase service account JSON file.
                            If None, tries to find it automatically.
        """
        if cls._initialized:
            return

        try:
            # Try to find credentials in order of preference
            if credentials_path is None:
                # 1. Check for firebase-service-account.json in current directory
                if os.path.exists("firebase-service-account.json"):
                    credentials_path = "firebase-service-account.json"
                # 2. Check GOOGLE_APPLICATION_CREDENTIALS env var
                elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

            if credentials_path and os.path.exists(credentials_path):
                # Initialize with service account credentials
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred)
                print(f"✅ Firebase Admin SDK initialized with credentials: {credentials_path}")
            else:
                # Initialize with default credentials (works in production/cloud)
                firebase_admin.initialize_app()
                print("✅ Firebase Admin SDK initialized with default credentials")

            cls._initialized = True
        except ValueError as e:
            # Firebase app already initialized
            if "already exists" in str(e):
                cls._initialized = True
                print("ℹ️ Firebase Admin SDK already initialized")
            else:
                raise
        except Exception as e:
            print(f"❌ Failed to initialize Firebase Admin SDK: {e}")
            print("💡 Tip: Download service account key from Firebase Console and save as 'firebase-service-account.json'")
            raise
    
    @classmethod
    def verify_id_token(cls, id_token: str) -> Dict[str, Any]:
        """
        Verify a Firebase ID token
        
        Args:
            id_token: The Firebase ID token to verify
            
        Returns:
            Dict containing the decoded token claims
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        if not cls._initialized:
            cls.initialize()
        
        try:
            # Verify the ID token
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except auth.ExpiredIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firebase token has expired"
            )
        except auth.RevokedIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firebase token has been revoked"
            )
        except auth.InvalidIdTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Firebase token: {str(e)}"
            )
        except Exception as e:
            print(f"Error verifying Firebase token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to verify Firebase token: {str(e)}"
            )
    
    @classmethod
    def get_user_by_email(cls, email: str) -> Optional[auth.UserRecord]:
        """
        Get Firebase user by email
        
        Args:
            email: User's email address
            
        Returns:
            UserRecord if found, None otherwise
        """
        if not cls._initialized:
            cls.initialize()
        
        try:
            return auth.get_user_by_email(email)
        except auth.UserNotFoundError:
            return None
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None
    
    @classmethod
    def get_user_by_uid(cls, uid: str) -> Optional[auth.UserRecord]:
        """
        Get Firebase user by UID

        Args:
            uid: User's Firebase UID

        Returns:
            UserRecord if found, None otherwise
        """
        if not cls._initialized:
            cls.initialize()

        try:
            return auth.get_user(uid)
        except auth.UserNotFoundError:
            return None
        except Exception as e:
            print(f"Error getting user by UID: {e}")
            return None

    @classmethod
    def send_notification_to_token(
        cls,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send a push notification to a specific device token

        Args:
            token: FCM device token
            title: Notification title
            body: Notification body
            data: Optional data payload

        Returns:
            Dict containing the message ID or error
        """
        if not cls._initialized:
            cls.initialize()

        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                token=token,
            )

            response = messaging.send(message)
            return {
                "success": True,
                "message_id": response
            }
        except Exception as e:
            print(f"Error sending notification to token: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @classmethod
    def send_notification_to_topic(
        cls,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send a push notification to a topic

        Args:
            topic: FCM topic name
            title: Notification title
            body: Notification body
            data: Optional data payload

        Returns:
            Dict containing the message ID or error
        """
        if not cls._initialized:
            cls.initialize()

        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                topic=topic,
            )

            response = messaging.send(message)
            return {
                "success": True,
                "message_id": response
            }
        except Exception as e:
            print(f"Error sending notification to topic: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @classmethod
    def send_multicast_notification(
        cls,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send a push notification to multiple device tokens

        Args:
            tokens: List of FCM device tokens
            title: Notification title
            body: Notification body
            data: Optional data payload

        Returns:
            Dict containing success count and failure details
        """
        if not cls._initialized:
            cls.initialize()

        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                tokens=tokens,
            )

            response = messaging.send_multicast(message)
            return {
                "success": True,
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "responses": [
                    {
                        "success": resp.success,
                        "message_id": resp.message_id if resp.success else None,
                        "error": str(resp.exception) if not resp.success else None
                    }
                    for resp in response.responses
                ]
            }
        except Exception as e:
            print(f"Error sending multicast notification: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
firebase_service = FirebaseService()

