import argparse
import os
import re

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
from django.apps import apps

if not apps.ready:
    django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.schedules.models import Agenda, Agent, EducationReport, ShiftSchedule, Support

User = get_user_model()
RONALDO_CPF = "01229890742"


def normalize_cpf(value):
    return "".join(char for char in str(value or "") if char.isdigit())


def cpf_variants(value):
    normalized = normalize_cpf(value)
    variants = {normalized}
    if len(normalized) == 11:
        variants.add(f"{normalized[:3]}.{normalized[3:6]}.{normalized[6:9]}-{normalized[9:]}")
    return {variant for variant in variants if variant}


def split_people(value):
    return [part.strip() for part in str(value or "").split(";") if part.strip()]


def join_people(values):
    return "; ".join(values)


def remove_person(value, names):
    parts = split_people(value)
    filtered = [part for part in parts if part not in names]
    return join_people(filtered), filtered != parts


def add_person(value, name):
    parts = split_people(value)
    if name not in parts:
        parts.append(name)
    return join_people(parts)


def resolve_user(cpf=None, source_id=None):
    if source_id and source_id.startswith("user:"):
        try:
            user = User.objects.filter(id=int(source_id.split(":", 1)[1])).first()
            if user:
                return user
        except ValueError:
            pass

    normalized = normalize_cpf(cpf)
    if not normalized:
        return None
    for user in User.objects.all().only("id", "cpf", "full_name", "role", "is_active"):
        if normalize_cpf(user.cpf) == normalized:
            return user
    return None


def first_support_slot(agenda):
    if not agenda.support_1_ref and not agenda.support_1:
        return "support_1"
    if not agenda.support_2_ref and not agenda.support_2:
        return "support_2"
    return None


def plan_report_text(value, names, support_name):
    text = value or ""
    match = re.search(r"(?ims)(Agentes?:)(.*?)(\nApoio:|\nApoios:|\Z)", text)
    if not match:
        return text, False

    agents_text = match.group(2).strip()
    new_agents, removed = remove_person(agents_text, names)
    if not removed:
        return text, False

    start, end = match.span(2)
    new_text = f"{text[:start]} {new_agents}{text[end:]}"
    support_match = re.search(r"(?ims)(\nApoio:|\nApoios:)(.*?)(\n\S|\Z)", new_text)
    if support_match:
        support_start, support_end = support_match.span(2)
        support_text = add_person(support_match.group(2), support_name)
        new_text = f"{new_text[:support_start]} {support_text}{new_text[support_end:]}"
    else:
        new_text = f"{new_text.rstrip()}\nApoio: {support_name}"
    return new_text, True


def clean_data(cpf=RONALDO_CPF, source_id=None, dry_run=True):
    user = resolve_user(cpf=cpf, source_id=source_id)
    print(f"\n--- Saneamento Ronaldo ---")
    print(f"Modo: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"CPF informado: {cpf or ''}")
    print(f"Source ID informado: {source_id or ''}")

    if not user:
        print("Usuario nao localizado por CPF normalizado ou source_id.")
        return []

    normalized = normalize_cpf(user.cpf or cpf)
    source_id = f"user:{user.id}"
    agent = Agent.objects.filter(source_id=source_id).first()
    if not agent and normalized:
        agent = Agent.objects.filter(cpf__in=cpf_variants(normalized)).first()
    support = Support.objects.filter(source_id=source_id).first()
    if not support and normalized:
        support = Support.objects.filter(cpf__in=cpf_variants(normalized)).first()

    print("\n[Usuario]")
    print(f"Nome: {user.full_name}")
    print(f"ID: {user.id}")
    print(f"Source ID: {source_id}")
    print(f"CPF normalizado: {normalized}")
    print(f"Role ativa: {user.role}")
    print(f"Agent residual: {agent.id if agent else 'nenhum'}")
    print(f"Support correto: {support.id if support else 'nenhum'}")

    if user.role != User.Role.SUPPORT:
        print("Abortado: usuario nao possui role SUPPORT ativa.")
        return []
    if not support:
        print("Abortado: nao existe vinculo Support para receber o usuario.")
        return []

    names = {user.full_name, support.name}
    if agent:
        names.add(agent.name)
    names = {name for name in names if name}
    support_name = support.name or user.full_name
    operations = []

    def record(label, before, after, apply=None):
        if before == after:
            return
        operations.append((label, before, after, apply))

    if agent:
        for field_name, target_field in (
            ("extra_agents", "extra_supports"),
            ("removed_agents", "removed_supports"),
            ("absent_agents", "absent_supports"),
        ):
            for schedule in ShiftSchedule.objects.filter(**{field_name: agent}):
                label = f"ShiftSchedule {schedule.id}.{field_name}"
                before = f"contem Agent {agent.id}; {target_field} contem Support {support.id}: {getattr(schedule, target_field).filter(id=support.id).exists()}"
                after = f"remove Agent {agent.id}; garante Support {support.id} em {target_field}"

                def apply(schedule=schedule, field_name=field_name, target_field=target_field):
                    getattr(schedule, field_name).remove(agent)
                    getattr(schedule, target_field).add(support)

                record(label, before, after, apply)

        for agenda in Agenda.objects.filter(agents_ref=agent):
            label = f"Agenda {agenda.id}.agents_ref"

            def apply(agenda=agenda):
                agenda.agents_ref.remove(agent)

            record(label, f"contem Agent {agent.id}", f"remove Agent {agent.id}", apply)

    for agenda in Agenda.objects.all():
        new_agents, changed = remove_person(agenda.agents, names)
        if changed:
            label = f"Agenda {agenda.id}.agents"

            def apply(agenda=agenda, new_agents=new_agents):
                agenda.agents = new_agents
                agenda.save(update_fields=["agents"])

            record(label, agenda.agents, new_agents, apply)

        slot = first_support_slot(agenda)
        has_support_ref = support in [agenda.support_1_ref, agenda.support_2_ref]
        has_support_name = support_name in {agenda.support_1, agenda.support_2}
        if slot and not has_support_ref and not has_support_name and any(name in (agenda.agents or "") for name in names):
            ref_field = f"{slot}_ref"
            label = f"Agenda {agenda.id}.{slot}"

            def apply(agenda=agenda, slot=slot, ref_field=ref_field):
                setattr(agenda, slot, support_name)
                setattr(agenda, ref_field, support)
                agenda.save(update_fields=[slot, ref_field])

            record(label, "slot vazio", support_name, apply)

    for report in EducationReport.objects.exclude(education_agents=""):
        new_text, changed = plan_report_text(report.education_agents, names, support_name)
        if changed:
            label = f"EducationReport {report.id}.education_agents"

            def apply(report=report, new_text=new_text):
                report.education_agents = new_text
                report.save(update_fields=["education_agents"])

            record(label, report.education_agents, new_text, apply)

    print("\n[Operacoes propostas]")
    if not operations:
        print("Nenhuma")
    for label, before, after, _apply in operations:
        print(f"\n{label}")
        print(f"Anterior: {before}")
        print(f"Proposto: {after}")

    if dry_run:
        print("\nDry run concluido. Nenhuma alteracao foi salva.")
        return operations

    with transaction.atomic():
        for _label, _before, _after, apply in operations:
            if apply:
                apply()
    print("\nExecute concluido com transaction.atomic().")
    return operations


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Saneamento controlado do Caso Ronaldo.")
    parser.add_argument("--cpf", default=RONALDO_CPF, help="CPF usado para localizar o usuario; padrao: Ronaldo.")
    parser.add_argument("--source-id", default=None, help="Source id no formato user:<id>.")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem gravar; e o padrao seguro.")
    parser.add_argument("--execute", action="store_true", help="Grava as alteracoes propostas dentro de transaction.atomic().")
    args = parser.parse_args()

    clean_data(cpf=args.cpf, source_id=args.source_id, dry_run=not args.execute)