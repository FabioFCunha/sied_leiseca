"""LGPD Privacy endpoints: consent, data export, data deletion, privacy policy."""
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import log_audit
from .models import AuditLog, User


PRIVACY_POLICY_TEXT = """
POLÍTICA DE PRIVACIDADE – SIED SISTEMA INTEGRADO DA EDUCAÇÃO

Última atualização: Julho/2026

1. CONTROLADOR DOS DADOS
Operação Lei Seca do Estado do Rio de Janeiro, responsável pelo tratamento dos dados
pessoais coletados através do SIED – Sistema Integrado da Educação.

2. DADOS COLETADOS
Coletamos os seguintes dados pessoais:
- Nome completo
- CPF (Cadastro de Pessoa Física)
- E-mail institucional
- Telefone de contato
- Dados de geolocalização (durante o preenchimento de relatórios)
- Endereço IP e user-agent (para fins de auditoria e segurança)

3. FINALIDADE DO TRATAMENTO
Os dados são tratados exclusivamente para:
- Gerenciamento de escalas operacionais e agendamento de ações educativas
- Produção de relatórios técnicos e operacionais
- Controle de frequência do efetivo
- Geração de estatísticas e indicadores de desempenho
- Garantia da segurança e integridade do sistema

4. BASE LEGAL (Art. 7º da LGPD)
- Execução de políticas públicas (Art. 7º, III)
- Cumprimento de obrigação legal ou regulatória (Art. 7º, II)
- Consentimento do titular (Art. 7º, I) para dados não obrigatórios

5. COMPARTILHAMENTO DE DADOS
Os dados poderão ser compartilhados com:
- Órgãos públicos competentes, quando exigido por lei
- Prestadores de serviço estritamente necessários para operação do sistema
Não comercializamos dados pessoais.

6. RETENÇÃO DE DADOS
Os dados serão mantidos pelo período necessário ao cumprimento das finalidades
descritas, respeitando os prazos legais de retenção obrigatória.

7. DIREITOS DO TITULAR (Art. 18 da LGPD)
Você tem direito a:
- Confirmar a existência de tratamento de dados
- Acessar seus dados pessoais
- Solicitar a correção de dados incompletos ou desatualizados
- Solicitar a portabilidade dos seus dados
- Solicitar a eliminação dos dados pessoais tratados com consentimento
- Revogar o consentimento a qualquer momento

8. SEGURANÇA
Adotamos medidas técnicas e organizacionais para proteger seus dados:
- Criptografia em trânsito (HTTPS/TLS)
- Controle de acesso baseado em funções
- Registro de auditoria de todas as operações
- Tokens de autenticação com validade limitada

9. CONTATO DO ENCARREGADO (DPO)
Para exercer seus direitos ou esclarecer dúvidas, entre em contato:
E-mail: ols.educacao.agenda@gmail.com
"""


class PrivacyPolicyView(APIView):
    """GET /api/auth/privacy-policy/ — retorna a política de privacidade."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"policy": PRIVACY_POLICY_TEXT.strip()})


class LGPDConsentView(APIView):
    """POST /api/auth/lgpd-consent/ — registra o consentimento LGPD do usuário."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user.lgpd_consent_at = timezone.now()
        user.save(update_fields=["lgpd_consent_at"])
        log_audit(
            request,
            AuditLog.Action.UPDATE,
            "LGPD",
            f"Consentimento LGPD registrado por {user.full_name or user.email}.",
        )
        return Response(
            {"detail": "Consentimento registrado com sucesso.", "lgpd_consent_at": user.lgpd_consent_at},
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        """DELETE — revoga o consentimento."""
        user = request.user
        user.lgpd_consent_at = None
        user.save(update_fields=["lgpd_consent_at"])
        log_audit(
            request,
            AuditLog.Action.UPDATE,
            "LGPD",
            f"Consentimento LGPD revogado por {user.full_name or user.email}.",
        )
        return Response({"detail": "Consentimento revogado."}, status=status.HTTP_200_OK)


class MyDataView(APIView):
    """GET /api/auth/my-data/ — exporta todos os dados pessoais do titular.
    DELETE /api/auth/my-data/ — solicita exclusão dos dados pessoais."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        log_audit(
            request,
            AuditLog.Action.REPORT_EXPORT,
            "LGPD",
            f"Exportação de dados pessoais solicitada por {user.full_name or user.email}.",
        )
        return Response({
            "dados_pessoais": {
                "nome_completo": user.full_name,
                "email": user.email,
                "cpf": user.cpf,
                "telefone": user.phone,
                "funcao": user.get_role_display() if hasattr(user, "get_role_display") else user.role,
                "setor": str(user.sector) if user.sector else None,
                "data_cadastro": user.date_joined.isoformat() if user.date_joined else None,
                "ultimo_acesso": user.last_login.isoformat() if user.last_login else None,
                "ultima_atividade": user.last_activity.isoformat() if user.last_activity else None,
                "consentimento_lgpd": user.lgpd_consent_at.isoformat() if user.lgpd_consent_at else None,
            },
            "registros_auditoria": list(
                AuditLog.objects.filter(user=user)
                .values("action", "module", "description", "created_at")
                .order_by("-created_at")[:100]
            ),
        })

    def delete(self, request):
        user = request.user
        log_audit(
            request,
            AuditLog.Action.DELETE,
            "LGPD",
            f"Solicitação de exclusão de dados pessoais por {user.full_name or user.email}.",
        )
        # Anonimizar dados em vez de excluir (preservar integridade de relatórios)
        user.full_name = "Usuário Removido"
        user.cpf = None
        user.phone = ""
        user.is_active = False
        user.lgpd_consent_at = None
        user.save(update_fields=["full_name", "cpf", "phone", "is_active", "lgpd_consent_at"])
        return Response(
            {"detail": "Seus dados pessoais foram anonimizados. Sua conta foi desativada."},
            status=status.HTTP_200_OK,
        )
