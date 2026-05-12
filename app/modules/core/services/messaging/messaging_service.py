from typing import Dict, Any, Optional, List
import json
from fastapi import HTTPException, status
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.redis.redis_service import AppRedisService
from app.modules.security.services.security_websocket_service import SecurityWebSocketService
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.generic.generic_services import GenericService
from datetime import datetime

from app.modules.core.services.email.email_service import EmailService
from app.modules.core.services.email_sender.email_sender_service import EMailSenderService

class MessengingService:
    """
    Service pour gérer la messagerie en temps réel avec support WebSocket et Redis.
    """
    
    def __init__(self, accept_language: Optional[str] = 'fr'):
        self.redis_service = AppRedisService()
        self.email_service = EmailService(accept_language=accept_language)
        self.email_sender_service = EMailSenderService(accept_language=accept_language)
        self.generic_service = GenericService(accept_language=accept_language)
        self.accept_language = accept_language
        
    async def send_message(
        self,
        user_account_socket_hash: str,
        message_data: Dict[str, Any],
        redis_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Envoie un message à un utilisateur spécifique via WebSocket ou le stocke dans Redis.
        
        Args:
            user_account_socket_hash: Le hash unique identifiant la connexion socket de l'utilisateur
            message_data: Les données du message à envoyer
            redis_data: Données optionnelles à stocker dans Redis
            
        Returns:
            Dict contenant le statut et le message
        """
        try:
            # Tenter d'envoyer le message via WebSocket
            result = await SecurityWebSocketService.send_event_to_client(
                user_account_socket_hash,
                message_data,
                redis_data
            )
            
            return result
            
        except Exception as e:
            DebugService.app_debug_print(f"Erreur lors de l'envoi du message: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    async def get_pending_messages(
        self,
        user_account_socket_hash: str
    ) -> Dict[str, Any]:
        """
        Récupère les messages en attente pour un utilisateur.
        
        Args:
            user_account_socket_hash: Le hash unique identifiant la connexion socket de l'utilisateur
            
        Returns:
            Dict contenant les messages en attente
        """
        try:
            # Récupérer tous les messages en attente de Redis
            message_pattern = f"notification:{user_account_socket_hash}:*"
            message_keys = await self.redis_service.get_keys_by_pattern(message_pattern)
            
            messages = []
            for key in message_keys:
                message_data = await self.redis_service.get_str_redis_value(key)
                if message_data:
                    try:
                        message = json.loads(message_data)
                        messages.append(message)
                        # Supprimer le message après l'avoir récupéré
                        await self.redis_service.delete_redis_value(key)
                    except json.JSONDecodeError:
                        DebugService.app_debug_print(f"Erreur de parsing des données du message: {message_data}")
            
            DebugService.app_debug_print(f"Récupération de {len(messages)} messages en attente pour {user_account_socket_hash}")
            return {
                "status": "success",
                "messages": messages
            }
            
        except Exception as e:
            DebugService.app_debug_print(f"Erreur lors de la récupération des messages en attente: {str(e)}")
            return {
                "status": "error",
                "messages": [],
                "error": str(e)
            }
            
    async def broadcast_message(
        self,
        message_data: Dict[str, Any],
        target_users: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Diffuse un message à plusieurs utilisateurs.
        
        Args:
            message_data: Les données du message à diffuser
            target_users: Liste optionnelle des hashs des utilisateurs cibles
            
        Returns:
            Dict contenant le statut et les résultats de la diffusion
        """
        try:
            results = []
            
            if target_users:
                # Diffuser uniquement aux utilisateurs spécifiés
                for user_hash in target_users:
                    result = await self.send_message(user_hash, message_data)
                    results.append({
                        "user_hash": user_hash,
                        "status": result.get("status", "error")
                    })
            else:
                # Diffuser à tous les utilisateurs connectés
                from app.modules import active_connections
                for user_hash in active_connections.keys():
                    result = await self.send_message(user_hash, message_data)
                    results.append({
                        "user_hash": user_hash,
                        "status": result.get("status", "error")
                    })
            
            return {
                "status": "success",
                "results": results
            }
            
        except Exception as e:
            DebugService.app_debug_print(f"Erreur lors de la diffusion du message: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    async def save_local_notification(
        self,
        title: str,
        notification: str,
        targeted_id: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sauvegarde une notification locale pour un utilisateur, puis pousse
        un évènement temps réel ``notification:new`` sur sa connexion
        WebSocket si elle est active. Le push est best-effort: une perte
        de socket n'invalide pas la sauvegarde DB.

        Args:
            title: Le titre de la notification
            notification: Le contenu de la notification
            targeted_id: L'ID de l'utilisateur cible
            additional_data: Données supplémentaires optionnelles

        Returns:
            Dict contenant le statut et les détails de la notification
        """
        try:
            notification_data = {
                "title": title,
                "notification": notification,
                "targeted_id": targeted_id,
                "is_read": False,
                "created_at": datetime.now().isoformat()
            }

            if additional_data:
                notification_data.update(additional_data)

            result = await self.generic_service.add_data_to_collection(
                collection_key=CollectionKey.NTF_NOTIFICATION,
                data=notification_data
            )

            # Best-effort live push: lookup the recipient's socket hash
            # and emit a `notification:new` event so the frontend bell
            # updates without waiting for its 60s poll tick.
            try:
                user_doc = await self.generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.SYS_USER,
                    accept_language=self.accept_language,
                    query={"filter___id": str(targeted_id)},
                    _skip_rls=True,
                )
                socket_hash = (user_doc or {}).get("user_account_socket_hash")
                if socket_hash:
                    await SecurityWebSocketService.send_event_to_client(
                        user_account_socket_hash=str(socket_hash),
                        data={
                            "event": "notification:new",
                            "message": notification_data,
                        },
                    )
                else:
                    DebugService.app_debug_print(
                        f"save_local_notification: no socket_hash for user {targeted_id} "
                        "— skipping live push (notification still saved to DB).",
                        False,
                    )
            except Exception as ws_err:  # noqa: BLE001 — push must never break save
                DebugService.app_debug_print(
                    f"save_local_notification: WebSocket push failed (non-fatal): {ws_err}",
                    True,
                )

            return {
                "status": "success",
                "notification": result
            }

        except Exception as e:
            DebugService.app_debug_print(f"Erreur lors de la sauvegarde de la notification: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
            
    async def send_email_to(
        self,
        email: str,
        subject: str,
        body: str,
        is_html: bool = True,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envoie un email à un destinataire spécifique.
        
        Args:
            email: L'adresse email du destinataire
            subject: Le sujet de l'email
            body: Le contenu de l'email
            is_html: Si le contenu est en HTML
            cc: Liste des destinataires en copie
            bcc: Liste des destinataires en copie cachée
            attachments: Liste des chemins des fichiers à attacher
            from_email: L'adresse email de l'expéditeur
            reply_to: L'adresse email pour la réponse
            
        Returns:
            Dict contenant le statut de l'envoi
        """
        try:
            result = self.email_service.send_email(
                to_email=email,
                subject=subject,
                body=body,
                is_html=is_html,
                cc=cc,
                bcc=bcc,
                attachments=attachments,
                from_email=from_email,
                reply_to=reply_to
            )
            
            return result
            
        except Exception as e:
            DebugService.app_debug_print(f"Erreur lors de l'envoi de l'email: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    async def send_email_to_users(
        self,
        emails: List[str],
        subject: str,
        body: str,
        is_html: bool = True,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envoie un email à plusieurs destinataires.
        
        Args:
            emails: Liste des adresses email des destinataires
            subject: Le sujet de l'email
            body: Le contenu de l'email
            is_html: Si le contenu est en HTML
            cc: Liste des destinataires en copie
            bcc: Liste des destinataires en copie cachée
            attachments: Liste des chemins des fichiers à attacher
            from_email: L'adresse email de l'expéditeur
            reply_to: L'adresse email pour la réponse
            
        Returns:
            Dict contenant le statut de l'envoi pour chaque destinataire
        """
        try:
            results = []
            
            for email in emails:
                try:
                    # Vérifier la validité de l'email
                    if not self.email_service.is_valid_email(email):
                        results.append({
                            "email": email,
                            "status": False,
                            "message": "Adresse email invalide"
                        })
                        continue
                        
                    # Envoyer l'email
                    result = self.email_sender_service.send_mail(
                        to=email,
                        subject=subject,
                        html_content=body if is_html else f"<pre>{body}</pre>"
                    )
                    
                    results.append({
                        "email": email,
                        "status": True,
                        "message": "Email envoyé avec succès"
                    })
                    
                except Exception as e:
                    DebugService.app_debug_print(f"Erreur lors de l'envoi de l'email à {email}: {str(e)}")
                    results.append({
                        "email": email,
                        "status": False,
                        "message": str(e)
                    })
            
            # Vérifier si tous les envois ont réussi
            all_success = all(result["status"] for result in results)
            
            return {
                "status": "success" if all_success else "partial",
                "results": results,
                "total_sent": sum(1 for r in results if r["status"]),
                "total_failed": sum(1 for r in results if not r["status"])
            }
            
        except Exception as e:
            DebugService.app_debug_print(f"Erreur lors de l'envoi des emails: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    async def save_multiple_local_notifications(
        self,
        notifications: List[Dict[str, Any]],
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Sauvegarde plusieurs notifications locales en une seule fois.
        
        Args:
            notifications: Liste des notifications à sauvegarder, chaque notification doit contenir:
                - title: Le titre de la notification
                - notification: Le contenu de la notification
                - targeted_id: L'ID de l'utilisateur cible
                - additional_data (optionnel): Données supplémentaires
            batch_size: Taille maximale des lots pour l'insertion en masse
            
        Returns:
            Dict contenant le statut et les détails des notifications sauvegardées
        """
        try:
            if not notifications:
                return {
                    "status": "success",
                    "message": "Aucune notification à sauvegarder",
                    "saved_count": 0
                }
                
            # Préparer les notifications avec les champs par défaut
            prepared_notifications = []
            for notification in notifications:
                if not all(key in notification for key in ["title", "notification", "targeted_id"]):
                    DebugService.app_debug_print("Notification invalide: champs requis manquants")
                    continue
                    
                notification_data = {
                    "title": notification["title"],
                    "notification": notification["notification"],
                    "targeted_id": notification["targeted_id"],
                    "is_read": False,
                    "created_at": datetime.now().isoformat()
                }
                
                if "additional_data" in notification:
                    notification_data.update(notification["additional_data"])
                    
                prepared_notifications.append(notification_data)
            
            if not prepared_notifications:
                return {
                    "status": "error",
                    "message": "Aucune notification valide à sauvegarder",
                    "saved_count": 0
                }
            
            # Sauvegarder les notifications par lots
            total_saved = 0
            for i in range(0, len(prepared_notifications), batch_size):
                batch = prepared_notifications[i:i + batch_size]
                result = await self.generic_service.add_multiple_data_to_collection(
                    collection_key=CollectionKey.NTF_NOTIFICATION,
                    data_list=batch
                )
                total_saved += len(batch)
            
            return {
                "status": "success",
                "message": f"{total_saved} notifications sauvegardées avec succès",
                "saved_count": total_saved
            }
            
        except Exception as e:
            DebugService.app_debug_print(f"Erreur lors de la sauvegarde des notifications: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "saved_count": 0
            } 