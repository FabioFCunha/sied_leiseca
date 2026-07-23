import csv
import sys
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import User
from apps.schedules.models import Agent, Chief, Support
from apps.accounts.serializers import sync_user_lookup, team_for_user, fallback_team_for_user

class Command(BaseCommand):
    help = "Saneamento Fase 3 - Diagnóstico e Classificação de Vínculos Órfãos e Inativos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Executa as alterações no banco de dados. Se omitido, apenas gera o CSV de dry-run.",
        )
        parser.add_argument(
            "--csv-path",
            type=str,
            default="relatorio_saneamento_fase3.csv",
            help="Caminho para salvar o relatório CSV.",
        )

    def handle(self, *args, **options):
        commit = options["commit"]
        csv_path = options["csv_path"]

        self.stdout.write("Analisando registros (Fase 3)...")

        # Coletar todos os lookups e mapeá-los
        all_lookups = []
        for model in [Agent, Chief, Support]:
            for obj in model.objects.all():
                all_lookups.append(obj)

        source_ids_in_lookups = set(l.source_id for l in all_lookups if l.source_id)
        valid_source_ids = {f"user:{u.id}": u for u in User.objects.all()}

        actions = []

        # 1. Classificar Users ativos que não possuem Lookup
        users_with_roles = User.objects.filter(is_active=True)
        
        users_to_sync = [] # Categoria A (Apenas no commit)

        for u in users_with_roles:
            expected_source = f"user:{u.id}"
            if expected_source not in source_ids_in_lookups:
                # Classificar
                classificacao = ""
                motivo = ""
                
                team = team_for_user(u) or fallback_team_for_user(u)

                # Regras de Categoria B
                if u.role in [User.Role.ADMIN, User.Role.MANAGER, User.Role.VISITOR, User.Role.ALMOXARIFADO]:
                    classificacao = "MANTER_SEM_LOOKUP"
                    motivo = f"Papel administrativo/visitante ({u.role})"
                elif u.is_on_vacation:
                    classificacao = "MANTER_SEM_LOOKUP"
                    motivo = "Usuário em férias/afastamento"
                elif not team:
                    classificacao = "NECESSITA_ANALISE_MANUAL"
                    motivo = "Papel operacional, mas sem equipe definida (Coringa/Reserva?)"
                elif u.role not in [User.Role.USER, User.Role.SUPPORT, User.Role.SUPERVISOR]:
                    classificacao = "MANTER_SEM_LOOKUP"
                    motivo = f"Papel ignorado: {u.role}"
                else:
                    classificacao = "CRIAR_LOOKUP"
                    motivo = f"Papel operacional ativo com equipe definida."
                    users_to_sync.append(u)

                actions.append({
                    "entidade": "User",
                    "id": u.id,
                    "nome": u.full_name,
                    "cpf": u.cpf,
                    "email": u.email,
                    "grupos_perfis": u.role,
                    "classificacao": classificacao,
                    "motivo": motivo
                })

        # Para fins de dry-run, prever quais CPFs os users_to_sync vão tentar reclamar
        cpfs_to_reclaim = {u.cpf: u for u in users_to_sync if u.cpf}
        lookups_to_deactivate = []

        # 2. Identificar Lookups Órfãos (Apenas perfis indevidamente ATIVOS sem user)
        for l in all_lookups:
            if not l.is_active:
                continue

            # Órfão se não tem source_id ou se o source_id não mapeia para nenhum User válido
            if not l.source_id or l.source_id not in valid_source_ids:
                if not l.source_id and l.cpf and l.cpf in cpfs_to_reclaim:
                    # Será reclamado pelo sync do usuário, não desativar
                    pass
                else:
                    lookups_to_deactivate.append(l)
                    actions.append({
                        "entidade": l.__class__.__name__,
                        "id": l.id,
                        "nome": l.name,
                        "cpf": l.cpf,
                        "email": "",
                        "grupos_perfis": getattr(l, "role", ""),
                        "classificacao": "DESATIVAR_LOOKUP",
                        "motivo": f"Registro legado orfão sem usuário vinculado (source_id='{l.source_id}')."
                    })

        # 3. Gerar CSV
        try:
            with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["entidade", "id", "nome", "cpf", "email", "grupos_perfis", "classificacao", "motivo"])
                writer.writeheader()
                for row in actions:
                    writer.writerow(row)
            self.stdout.write(self.style.SUCCESS(f"Relatório gerado em: {csv_path}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Erro ao salvar CSV: {e}"))
            sys.exit(1)

        if not commit:
            self.stdout.write(self.style.WARNING("\nModo --dry-run finalizado. Nenhuma alteração foi salva no banco."))
            self.stdout.write("Nota: O comando com --commit não executará a criação automática ainda até segunda ordem do operador.")
            return

        # 4. Executar Alterações (Commit)
        self.stdout.write("\nAplicando correções...")
        
        try:
            with transaction.atomic():
                # A. Desativar Órfãos
                for l in lookups_to_deactivate:
                    l.refresh_from_db()
                    if l.source_id and l.source_id in valid_source_ids:
                        continue
                    
                    l.is_active = False
                    l.save(update_fields=['is_active'])
                    self.stdout.write(f"Desativado {l.__class__.__name__} ID {l.id} - {l.name}")

            self.stdout.write(self.style.SUCCESS("\nSaneamento Fase 3 (Desativação de Órfãos) concluído com sucesso!"))
            self.stdout.write(self.style.SUCCESS("As criações de perfis baseadas em usuários não foram executadas neste commit conforme regra de negócio."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Erro fatal durante saneamento: {e}"))
            sys.exit(1)
