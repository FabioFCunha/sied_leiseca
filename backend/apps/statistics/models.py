from django.db import models
from django.core.exceptions import ValidationError
from apps.schedules.models import ActionType

class StatisticCategoryMapping(models.Model):
    """
    Parametrização da regra 'De -> Para'.
    Mapeia os nomes exatos encontrados na planilha histórica para a taxonomia atual do SIED.
    """
    INDICATOR_CHOICES = [
        ('AUDIENCE', 'Público'),
        ('ACTION', 'Ações'),
        ('MATERIAL', 'Materiais'),
    ]

    original_name = models.CharField(max_length=255, unique=True, help_text="Nome exato da coluna/categoria na planilha histórica")
    indicator_type = models.CharField(max_length=20, choices=INDICATOR_CHOICES)
    sied_action_type = models.ForeignKey(ActionType, on_delete=models.SET_NULL, null=True, blank=True)
    sied_requester_entity = models.CharField(max_length=255, null=True, blank=True, help_text="Tipo de entidade solicitante (ex: ESCOLA PUBLICA)")
    
    description = models.TextField(null=True, blank=True, help_text="Observações futuras sobre alterações de classificação histórica")
    
    # Controle e Auditoria (não apagamos, inativamos)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mapeamento Histórico"
        verbose_name_plural = "Mapeamentos Históricos"

    def __str__(self):
        return f"{self.original_name} -> {self.get_indicator_type_display()}"


class ConsolidatedStatistic(models.Model):
    """
    Camada de Estatística Consolidada SIED.
    Armazena os dados históricos (importados) e os dados operacionais gerados em tempo real (aprovados).
    """
    METHODOLOGY_CHOICES = [
        ('HISTORICAL_LEGACY', 'Histórico Planilha (até 08/07/2026)'),
        ('SIED_OPERATIONAL', 'Operacional SIED (a partir de 09/07/2026)'),
    ]

    # Dimensão de Tempo
    reference_date = models.DateField(null=True, blank=True, help_text="Obrigatório para SIED_OPERATIONAL")
    reference_year = models.IntegerField(db_index=True)
    reference_month = models.IntegerField(null=True, blank=True)

    # Dimensão de Categoria (Desnormalizada para performance e imutabilidade)
    indicator_type = models.CharField(max_length=20, choices=StatisticCategoryMapping.INDICATOR_CHOICES)
    category_action_type = models.ForeignKey(ActionType, on_delete=models.SET_NULL, null=True, blank=True)
    category_entity_type = models.CharField(max_length=255, null=True, blank=True)
    
    # Medida
    value = models.DecimalField(max_digits=12, decimal_places=2, help_text="Quantidade consolidada (Público, Ações ou Materiais)")
    
    # Rastreabilidade e Metodologia
    methodology = models.CharField(max_length=30, choices=METHODOLOGY_CHOICES, db_index=True)
    traceability_id = models.CharField(max_length=100, db_index=True, help_text="Ex: 'legacy_2015_bares' ou 'report_5501'")
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estatística Consolidada"
        verbose_name_plural = "Estatísticas Consolidadas"
        ordering = ['-reference_year', '-reference_month']

    def __str__(self):
        return f"{self.get_methodology_display()} | {self.reference_year} | {self.traceability_id} = {self.value}"

    def clean(self):
        super().clean()
        if self.methodology == 'HISTORICAL_LEGACY' and self.reference_date is not None:
            raise ValidationError({'reference_date': 'Dados do legado histórico (planilha) não podem ter data exata (reference_date).'})
        
        if self.methodology == 'SIED_OPERATIONAL' and self.reference_date is None:
            raise ValidationError({'reference_date': 'Dados operacionais do SIED exigem uma reference_date exata.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
