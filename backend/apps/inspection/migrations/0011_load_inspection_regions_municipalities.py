from django.db import migrations


REGIONS = {
    "COSTA_VERDE": {
        "name": "Costa Verde",
        "municipalities": [
            ("Angra dos Reis", "ANGRA DOS REIS"),
            ("Mangaratiba", "MANGARATIBA"),
            ("Paraty", "PARATY"),
        ],
    },
    "MEDIO_PARAIBA": {
        "name": "Médio Paraíba",
        "municipalities": [
            ("Barra do Piraí", "BARRA DO PIRAI"),
            ("Barra Mansa", "BARRA MANSA"),
            ("Itatiaia", "ITATIAIA"),
            ("Pinheiral", "PINHEIRAL"),
            ("Piraí", "PIRAI"),
            ("Porto Real", "PORTO REAL"),
            ("Quatis", "QUATIS"),
            ("Resende", "RESENDE"),
            ("Rio Claro", "RIO CLARO"),
            ("Rio das Flores", "RIO DAS FLORES"),
            ("Valença", "VALENCA"),
            ("Volta Redonda", "VOLTA REDONDA"),
        ],
    },
    "METROPOLITANA": {
        "name": "Metropolitana",
        "municipalities": [
            ("Belford Roxo", "BELFORD ROXO"),
            ("Cachoeiras de Macacu", "CACHOEIRAS DE MACACU"),
            ("Duque de Caxias", "DUQUE DE CAXIAS"),
            ("Guapimirim", "GUAPIMIRIM"),
            ("Itaboraí", "ITABORAI"),
            ("Itaguaí", "ITAGUAI"),
            ("Japeri", "JAPERI"),
            ("Magé", "MAGE"),
            ("Maricá", "MARICA"),
            ("Mesquita", "MESQUITA"),
            ("Nilópolis", "NILOPOLIS"),
            ("Niterói", "NITEROI"),
            ("Nova Iguaçu", "NOVA IGUACU"),
            ("Paracambi", "PARACAMBI"),
            ("Petrópolis", "PETROPOLIS"),
            ("Queimados", "QUEIMADOS"),
            ("Rio Bonito", "RIO BONITO"),
            ("Rio de Janeiro", "RIO DE JANEIRO"),
            ("São Gonçalo", "SAO GONCALO"),
            ("São João de Meriti", "SAO JOAO DE MERITI"),
            ("Seropédica", "SEROPEDICA"),
            ("Tanguá", "TANGUA"),
        ],
    },
    "CENTRO_SUL_FLUMINENSE": {
        "name": "Centro Sul Fluminense",
        "municipalities": [
            ("Areal", "AREAL"),
            ("Comendador Levy Gasparian", "COMENDADOR LEVY GASPARIAN"),
            ("Engenheiro Paulo de Frontin", "ENGENHEIRO PAULO DE FRONTIN"),
            ("Mendes", "MENDES"),
            ("Miguel Pereira", "MIGUEL PEREIRA"),
            ("Paraíba do Sul", "PARAIBA DO SUL"),
            ("Paty do Alferes", "PATY DO ALFERES"),
            ("Sapucaia", "SAPUCAIA"),
            ("Três Rios", "TRES RIOS"),
            ("Vassouras", "VASSOURAS"),
        ],
    },
    "BAIXADAS_LITORANEAS": {
        "name": "Baixadas Litorâneas",
        "municipalities": [
            ("Araruama", "ARARUAMA"),
            ("Armação dos Búzios", "ARMACAO DOS BUZIOS"),
            ("Arraial do Cabo", "ARRAIAL DO CABO"),
            ("Cabo Frio", "CABO FRIO"),
            ("Casimiro de Abreu", "CASIMIRO DE ABREU"),
            ("Iguaba Grande", "IGUABA GRANDE"),
            ("Rio das Ostras", "RIO DAS OSTRAS"),
            ("São Pedro da Aldeia", "SAO PEDRO DA ALDEIA"),
            ("Saquarema", "SAQUAREMA"),
            ("Silva Jardim", "SILVA JARDIM"),
        ],
    },
    "SERRANA": {
        "name": "Serrana",
        "municipalities": [
            ("Bom Jardim", "BOM JARDIM"),
            ("Cantagalo", "CANTAGALO"),
            ("Carmo", "CARMO"),
            ("Cordeiro", "CORDEIRO"),
            ("Duas Barras", "DUAS BARRAS"),
            ("Macuco", "MACUCO"),
            ("Nova Friburgo", "NOVA FRIBURGO"),
            ("Santa Maria Madalena", "SANTA MARIA MADALENA"),
            ("São José do Vale do Rio Preto", "SAO JOSE DO VALE DO RIO PRETO"),
            ("São Sebastião do Alto", "SAO SEBASTIAO DO ALTO"),
            ("Sumidouro", "SUMIDOURO"),
            ("Teresópolis", "TERESOPOLIS"),
            ("Trajano de Moraes", "TRAJANO DE MORAES"),
        ],
    },
    "NORTE_FLUMINENSE": {
        "name": "Norte Fluminense",
        "municipalities": [
            ("Campos dos Goytacazes", "CAMPOS DOS GOYTACAZES"),
            ("Carapebus", "CARAPEBUS"),
            ("Cardoso Moreira", "CARDOSO MOREIRA"),
            ("Conceição de Macabu", "CONCEICAO DE MACABU"),
            ("Macaé", "MACAE"),
            ("Quissamã", "QUISSAMA"),
            ("São Fidélis", "SAO FIDELIS"),
            ("São Francisco de Itabapoana", "SAO FRANCISCO DE ITABAPOANA"),
            ("São João da Barra", "SAO JOAO DA BARRA"),
        ],
    },
    "NOROESTE_FLUMINENSE": {
        "name": "Noroeste Fluminense",
        "municipalities": [
            ("Aperibé", "APERIBE"),
            ("Bom Jesus do Itabapoana", "BOM JESUS DO ITABAPOANA"),
            ("Cambuci", "CAMBUCI"),
            ("Italva", "ITALVA"),
            ("Itaocara", "ITAOCARA"),
            ("Itaperuna", "ITAPERUNA"),
            ("Laje do Muriaé", "LAJE DO MURIAE"),
            ("Miracema", "MIRACEMA"),
            ("Natividade", "NATIVIDADE"),
            ("Porciúncula", "PORCIUNCULA"),
            ("Santo Antônio de Pádua", "SANTO ANTONIO DE PADUA"),
            ("São José de Ubá", "SAO JOSE DE UBA"),
            ("Varre-Sai", "VARRE-SAI"),
        ],
    },
}


def load_regions_and_municipalities(apps, schema_editor):
    InspectionRegion = apps.get_model("inspection", "InspectionRegion")
    InspectionMunicipality = apps.get_model(
        "inspection",
        "InspectionMunicipality",
    )

    for code, data in REGIONS.items():
        region, _ = InspectionRegion.objects.update_or_create(
            code=code,
            defaults={
                "name": data["name"],
                "is_active": True,
            },
        )

        for name, normalized_name in data["municipalities"]:
            InspectionMunicipality.objects.update_or_create(
                normalized_name=normalized_name,
                defaults={
                    "name": name,
                    "region": region,
                    "is_active": True,
                },
            )


def unload_regions_and_municipalities(apps, schema_editor):
    InspectionMunicipality = apps.get_model(
        "inspection",
        "InspectionMunicipality",
    )
    InspectionRegion = apps.get_model("inspection", "InspectionRegion")

    InspectionMunicipality.objects.filter(
        normalized_name__in=[
            normalized_name
            for data in REGIONS.values()
            for _, normalized_name in data["municipalities"]
        ]
    ).delete()

    InspectionRegion.objects.filter(
        code__in=REGIONS.keys()
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "inspection",
            "0010_inspectionregion_inspectionmunicipality",
        ),
    ]

    operations = [
        migrations.RunPython(
            load_regions_and_municipalities,
            unload_regions_and_municipalities,
        ),
    ]