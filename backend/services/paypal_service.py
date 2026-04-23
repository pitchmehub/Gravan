"""
Serviço de integração com PayPal para pagamentos.
Suporta criação de pedidos e captura de pagamentos.
"""
import os
import paypalrestsdk
from dotenv import load_dotenv

load_dotenv()

# Configuração do PayPal
paypalrestsdk.configure({
    "mode": os.getenv("PAYPAL_MODE", "sandbox"),  # sandbox ou live
    "client_id": os.getenv("PAYPAL_CLIENT_ID"),
    "client_secret": os.getenv("PAYPAL_CLIENT_SECRET")
})


class PayPalService:
    """Serviço para gerenciar pagamentos via PayPal."""
    
    @staticmethod
    def create_payment(amount_cents: int, obra_id: str, comprador_id: str, return_url: str, cancel_url: str):
        """
        Cria um pagamento PayPal.
        
        Args:
            amount_cents: Valor em centavos (ex: 1000 = R$ 10,00)
            obra_id: ID da obra sendo comprada
            comprador_id: ID do comprador
            return_url: URL de retorno após pagamento aprovado
            cancel_url: URL de retorno se cancelar
            
        Returns:
            dict com approval_url e payment_id
        """
        amount_reais = amount_cents / 100.0
        
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": return_url,
                "cancel_url": cancel_url
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": f"Licença de Obra Musical - {obra_id}",
                        "sku": obra_id,
                        "price": f"{amount_reais:.2f}",
                        "currency": "BRL",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": f"{amount_reais:.2f}",
                    "currency": "BRL"
                },
                "description": f"Compra de licença musical - Obra ID: {obra_id}",
                "custom": comprador_id  # ID do comprador para rastreamento
            }]
        })
        
        if payment.create():
            # Sucesso - retorna URL de aprovação
            approval_url = next(
                (link.href for link in payment.links if link.rel == "approval_url"),
                None
            )
            return {
                "success": True,
                "payment_id": payment.id,
                "approval_url": approval_url
            }
        else:
            # Erro
            return {
                "success": False,
                "error": payment.error
            }
    
    @staticmethod
    def execute_payment(payment_id: str, payer_id: str):
        """
        Executa (captura) um pagamento após aprovação do usuário.
        
        Args:
            payment_id: ID do pagamento retornado na criação
            payer_id: ID do pagador (vem da URL de retorno)
            
        Returns:
            dict com status e detalhes da transação
        """
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if payment.execute({"payer_id": payer_id}):
            # Pagamento executado com sucesso
            transaction = payment.transactions[0]
            return {
                "success": True,
                "payment_id": payment.id,
                "state": payment.state,
                "payer_email": payment.payer.payer_info.email,
                "amount": transaction.amount.total,
                "currency": transaction.amount.currency,
                "obra_id": transaction.item_list.items[0].sku,
                "comprador_id": transaction.custom
            }
        else:
            # Erro na execução
            return {
                "success": False,
                "error": payment.error
            }
    
    @staticmethod
    def get_payment_details(payment_id: str):
        """
        Busca detalhes de um pagamento.
        
        Args:
            payment_id: ID do pagamento
            
        Returns:
            dict com detalhes do pagamento
        """
        try:
            payment = paypalrestsdk.Payment.find(payment_id)
            return {
                "success": True,
                "payment_id": payment.id,
                "state": payment.state,
                "create_time": payment.create_time,
                "update_time": payment.update_time
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
