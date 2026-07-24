from django.test import TestCase
from rest_framework.exceptions import ValidationError
from apps.schedules.models import Kit, Material, Dynamic
from apps.schedules.serializers import EducationActionSerializer

class MaterialsValidationTest(TestCase):
    def setUp(self):
        # Create categories based on active status
        self.kit = Kit.objects.create(name="Kit com 7 Revistinhas", is_active=True)
        self.apoio = Material.objects.create(name="Barraca", is_active=True)
        self.dinamica = Dynamic.objects.create(name="Jogo Tabuleiro", is_active=True)
        self.serializer = EducationActionSerializer()

    def test_distribution_materials_accepts_kit(self):
        # material da categoria Distribuição é aceito
        val = self.serializer.validate_distribution_materials_distributed("Kit com 7 Revistinhas - 50")
        self.assertEqual(val, "Kit com 7 Revistinhas - 50")

    def test_distribution_materials_rejects_apoio(self):
        # Material de Apoio é rejeitado
        with self.assertRaisesMessage(ValidationError, "O material 'Barraca' não pertence à categoria Material para Distribuição."):
            self.serializer.validate_distribution_materials_distributed("Barraca - 1")

    def test_distribution_materials_rejects_dinamica(self):
        # Dinâmica é rejeitada
        with self.assertRaisesMessage(ValidationError, "O material 'Jogo Tabuleiro' não pertence à categoria Material para Distribuição."):
            self.serializer.validate_distribution_materials_distributed("Jogo Tabuleiro - 2")

    def test_distribution_materials_rejects_non_existent(self):
        # material inexistente é rejeitado
        with self.assertRaisesMessage(ValidationError, "O material 'Material Fantasma' não pertence à categoria Material para Distribuição."):
            self.serializer.validate_distribution_materials_distributed("Material Fantasma - 10")

    def test_distribution_materials_normalizes_names(self):
        # nomes com diferença de maiúsculas, espaços ou acentos são normalizados corretamente (o banco faz iexact)
        # We simulate the user typing in uppercase with spaces
        val = self.serializer.validate_distribution_materials_distributed("KIT COM 7 REVISTINHAS   -   50")
        self.assertEqual(val, "KIT COM 7 REVISTINHAS   -   50")

    def test_distribution_materials_empty_is_accepted(self):
        # relatório histórico continua sendo lido (empty or None validation)
        val = self.serializer.validate_distribution_materials_distributed("")
        self.assertEqual(val, "")
        val_none = self.serializer.validate_distribution_materials_distributed(None)
        self.assertEqual(val_none, None)

    def test_distribution_materials_zero_quantity_is_accepted(self):
        # material não cadastrado mas com quantidade zero é aceito (pois não foi distribuído)
        val = self.serializer.validate_distribution_materials_distributed("Certificado não oficial | 0")
        self.assertEqual(val, "Certificado não oficial | 0")

    def test_quantity_is_saved_exactly_as_informed(self):
        # quantidade distribuída é salva exatamente como informada
        val = self.serializer.validate_distribution_materials_distributed("Kit com 7 Revistinhas | 123")
        self.assertEqual(val, "Kit com 7 Revistinhas | 123")
